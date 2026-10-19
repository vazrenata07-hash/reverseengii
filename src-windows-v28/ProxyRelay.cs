using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace MintWindows;

// HTTP/1.x loopback proxy. Authentication here is independent of upstream
// authentication. Configuration changes terminate old connections; they never
// retry a request directly when an upstream is configured.
internal sealed class ProxyRelay : IDisposable
{
    const int HeaderLimit = 64 * 1024;
    readonly object gate = new();
    readonly TcpListener listener;
    readonly CancellationTokenSource lifetime = new();
    readonly SemaphoreSlim slots = new(128, 128);
    readonly Dictionary<long, Session> clients = new();
    readonly byte[] localCredentials;
    readonly Task acceptTask;
    ProxyEndpoint? endpoint;
    long epoch, nextId;
    bool disposed, acceptEnded, cleaned;

    public int Port { get; }
    public string LocalUsername { get; } = "mint-local";
    public string LocalPassword { get; } = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
    public string AuthenticationChallenge { get; } =
        "Basic realm=\"Mint-" + Convert.ToHexString(RandomNumberGenerator.GetBytes(16)) + "\"";

    public ProxyRelay()
    {
        localCredentials = Encoding.UTF8.GetBytes(LocalUsername + ":" + LocalPassword);
        listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start(128);
        Port = ((IPEndPoint)listener.LocalEndpoint).Port;
        acceptTask = Task.Run(AcceptAsync);
    }

    public void Configure(ProxyEndpoint? value)
    {
        if (value != null)
        {
            if (string.IsNullOrWhiteSpace(value.Host) || value.Host.Any(char.IsWhiteSpace) ||
                value.Host.IndexOfAny(new[] { '\r', '\n', '/', '\\', '@' }) >= 0 ||
                value.Port is < 1 or > 65535 ||
                value.Protocol is not (ProxyProtocol.Http or ProxyProtocol.Https or ProxyProtocol.Socks5))
                throw new ArgumentException("Configuração de proxy inválida.");
            if (value.Protocol == ProxyProtocol.Socks5 && HasCredentials(value) &&
                (Encoding.UTF8.GetByteCount(value.Username) is < 1 or > 255 ||
                 Encoding.UTF8.GetByteCount(value.Password) is < 1 or > 255))
                throw new ArgumentException("SOCKS5 exige usuário e senha de 1 a 255 bytes.");
        }
        Session[] old;
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            endpoint = value;
            epoch++;
            old = clients.Values.Where(client => client.Epoch != epoch).ToArray();
        }
        foreach (var client in old) client.Close();
    }

    async Task AcceptAsync()
    {
        try
        {
            while (!lifetime.IsCancellationRequested)
            {
                await slots.WaitAsync(lifetime.Token).ConfigureAwait(false);
                bool ownsSlot = true;
                TcpClient? accepted = null;
                try
                {
                    accepted = await listener.AcceptTcpClientAsync(lifetime.Token).ConfigureAwait(false);
                    accepted.NoDelay = true;
                    Session session;
                    lock (gate)
                    {
                        if (disposed) break;
                        session = new Session(++nextId, epoch, endpoint, accepted, lifetime.Token);
                        clients.Add(session.Id, session);
                        accepted = null;
                        ownsSlot = false;
                    }
                    _ = HandleAsync(session); // HandleAsync catches all failures and owns cleanup.
                }
                finally
                {
                    accepted?.Dispose();
                    if (ownsSlot) slots.Release();
                }
            }
        }
        catch { /* Closing the listener or exhausting a transport ends acceptance. */ }
        finally
        {
            lock (gate) { acceptEnded = true; CleanupIfFinished(); }
        }
    }

    async Task HandleAsync(Session session)
    {
        bool responseStarted = false;
        NetworkStream? local = null;
        try
        {
            local = session.Local.GetStream();
            using var handshake = CancellationTokenSource.CreateLinkedTokenSource(session.Token);
            handshake.CancelAfter(TimeSpan.FromSeconds(20));
            var block = await ReadHeaderAsync(local, null, handshake.Token).ConfigureAwait(false);
            var request = ParseRequest(block.Header);
            if (!Authenticate(request.Headers))
            {
                responseStarted = true;
                await ReplyAsync(local, 407, "Proxy Authentication Required", handshake.Token,
                    "Proxy-Authenticate: " + AuthenticationChallenge + "\r\n").ConfigureAwait(false);
                return;
            }

            using var remote = await ConnectAsync(session, request, handshake.Token).ConfigureAwait(false);
            if (request.Connect)
            {
                responseStarted = true;
                await WriteAsync(local, "HTTP/1.1 200 Connection Established\r\n\r\n", handshake.Token).ConfigureAwait(false);
                if (remote.Pending.Length != 0)
                    await local.WriteAsync(remote.Pending, handshake.Token).ConfigureAwait(false);
            }
            else
            {
                var header = BuildForwardHeader(request, remote.AbsoluteForm, session.Endpoint);
                await WriteAsync(remote.Stream, header, handshake.Token).ConfigureAwait(false);
            }
            if (block.Pending.Length != 0)
                await remote.Stream.WriteAsync(block.Pending, handshake.Token).ConfigureAwait(false);
            handshake.CancelAfter(Timeout.InfiniteTimeSpan);

            using var transfer = CancellationTokenSource.CreateLinkedTokenSource(session.Token);
            var upload = local.CopyToAsync(remote.Stream, 32768, transfer.Token);
            Task download;
            if (!request.Connect)
            {
                download = CopyHttpResponseAsync(remote.Stream, local, transfer.Token,
                    () => responseStarted = true);
            }
            else
            {
                download = remote.Stream.CopyToAsync(local, 32768, transfer.Token);
            }
            try
            {
                var first = await Task.WhenAny(upload, download).ConfigureAwait(false);
                await first.ConfigureAwait(false);
                if (first == upload)
                {
                    // A client can half-close its request and still await the response.
                    await remote.ShutdownWriteAsync(transfer.Token).ConfigureAwait(false);
                    await download.ConfigureAwait(false);
                }
            }
            finally
            {
                transfer.Cancel();
                session.CloseRemote();
                await IgnoreAsync(upload).ConfigureAwait(false);
                await IgnoreAsync(download).ConfigureAwait(false);
            }
        }
        catch (BadRequestException)
        {
            if (local != null && !responseStarted && !session.Token.IsCancellationRequested)
                await SafeReplyAsync(local, 400, "Bad Request").ConfigureAwait(false);
        }
        catch
        {
            if (local != null && !responseStarted && !session.Token.IsCancellationRequested)
                await SafeReplyAsync(local, 502, "Bad Gateway").ConfigureAwait(false);
        }
        finally
        {
            session.Close();
            session.DisposeCancellation();
            slots.Release();
            lock (gate) { clients.Remove(session.Id); CleanupIfFinished(); }
        }
    }

    bool Authenticate(List<Field> headers)
    {
        var values = headers.Where(field => field.Name.Equals("Proxy-Authorization", StringComparison.OrdinalIgnoreCase)).ToArray();
        if (values.Length != 1) return false;
        var value = values[0].Value;
        if (!value.StartsWith("Basic ", StringComparison.OrdinalIgnoreCase)) return false;
        byte[] decoded;
        try { decoded = Convert.FromBase64String(value[6..].Trim()); }
        catch { return false; }
        try
        {
            return decoded.Length == localCredentials.Length &&
                CryptographicOperations.FixedTimeEquals(decoded, localCredentials);
        }
        finally { CryptographicOperations.ZeroMemory(decoded); }
    }

    async Task<RemoteConnection> ConnectAsync(Session session, Request request, CancellationToken cancellation)
    {
        var proxy = session.Endpoint;
        var tcp = new TcpClient { NoDelay = true };
        session.AttachRemote(tcp);
        Stream? stream = null;
        try
        {
            await tcp.ConnectAsync(proxy?.Host.Trim('[', ']') ?? request.Host,
                proxy?.Port ?? request.Port, cancellation).ConfigureAwait(false);
            stream = tcp.GetStream();
            if (proxy?.Protocol == ProxyProtocol.Https)
            {
                var tls = new SslStream(stream, false);
                stream = tls;
                // Use ordinary certificate and hostname validation for the proxy.
                await tls.AuthenticateAsClientAsync(new SslClientAuthenticationOptions
                {
                    TargetHost = proxy.Host.Trim('[', ']')
                }, cancellation).ConfigureAwait(false);
            }
            if (proxy?.Protocol == ProxyProtocol.Socks5)
                await SocksConnectAsync(stream, proxy, request.Host, request.Port, cancellation).ConfigureAwait(false);
            if (proxy?.Protocol is ProxyProtocol.Http or ProxyProtocol.Https)
            {
                if (!request.Connect)
                    return new RemoteConnection(tcp, stream, true, Array.Empty<byte>());
                var authority = Authority(request.Host, request.Port);
                var auth = UpstreamAuthorization(proxy);
                await WriteAsync(stream, "CONNECT " + authority + " HTTP/1.1\r\nHost: " + authority +
                    "\r\n" + auth + "\r\n", cancellation).ConfigureAwait(false);
                var response = await ReadHeaderAsync(stream, null, cancellation).ConfigureAwait(false);
                var status = Status(response.Header);
                if (status is < 200 or >= 300) throw new IOException("Upstream CONNECT failed.");
                return new RemoteConnection(tcp, stream, false, response.Pending);
            }
            return new RemoteConnection(tcp, stream, false, Array.Empty<byte>());
        }
        catch
        {
            stream?.Dispose();
            tcp.Dispose();
            throw;
        }
    }

    static async Task SocksConnectAsync(Stream stream, ProxyEndpoint proxy, string host, int port, CancellationToken cancellation)
    {
        bool credentials = HasCredentials(proxy);
        byte method = credentials ? (byte)2 : (byte)0;
        await stream.WriteAsync(new byte[] { 5, 1, method }, cancellation).ConfigureAwait(false);
        var greeting = new byte[2];
        await stream.ReadExactlyAsync(greeting, cancellation).ConfigureAwait(false);
        if (greeting[0] != 5 || greeting[1] != method) throw new IOException("SOCKS authentication unavailable.");
        if (credentials)
        {
            var user = Encoding.UTF8.GetBytes(proxy.Username);
            var password = Encoding.UTF8.GetBytes(proxy.Password);
            var auth = new byte[3 + user.Length + password.Length];
            auth[0] = 1; auth[1] = (byte)user.Length;
            user.CopyTo(auth, 2);
            auth[2 + user.Length] = (byte)password.Length;
            password.CopyTo(auth, 3 + user.Length);
            try { await stream.WriteAsync(auth, cancellation).ConfigureAwait(false); }
            finally { CryptographicOperations.ZeroMemory(auth); CryptographicOperations.ZeroMemory(password); }
            await stream.ReadExactlyAsync(greeting, cancellation).ConfigureAwait(false);
            if (greeting[0] != 1 || greeting[1] != 0) throw new IOException("SOCKS authentication failed.");
        }
        byte type;
        byte[] address;
        if (IPAddress.TryParse(host, out var ip))
        {
            address = ip.GetAddressBytes();
            type = address.Length == 4 ? (byte)1 : (byte)4;
        }
        else
        {
            // Leave destination resolution to SOCKS; never resolve it locally.
            var name = Encoding.ASCII.GetBytes(new IdnMapping().GetAscii(host));
            if (name.Length is < 1 or > 255) throw new IOException("SOCKS host is invalid.");
            type = 3;
            address = new byte[name.Length + 1]; address[0] = (byte)name.Length; name.CopyTo(address, 1);
        }
        var command = new byte[6 + address.Length];
        command[0] = 5; command[1] = 1; command[2] = 0; command[3] = type;
        address.CopyTo(command, 4);
        command[^2] = (byte)(port >> 8); command[^1] = (byte)port;
        await stream.WriteAsync(command, cancellation).ConfigureAwait(false);
        var response = new byte[4];
        await stream.ReadExactlyAsync(response, cancellation).ConfigureAwait(false);
        if (response[0] != 5 || response[1] != 0 || response[2] != 0) throw new IOException("SOCKS connection failed.");
        int addressSize;
        if (response[3] == 1) addressSize = 4;
        else if (response[3] == 4) addressSize = 16;
        else if (response[3] == 3)
        {
            var length = new byte[1];
            await stream.ReadExactlyAsync(length, cancellation).ConfigureAwait(false);
            addressSize = length[0];
        }
        else throw new IOException("SOCKS reply is invalid.");
        await stream.ReadExactlyAsync(new byte[addressSize + 2], cancellation).ConfigureAwait(false);
    }

    static Request ParseRequest(byte[] bytes)
    {
        var lines = Encoding.Latin1.GetString(bytes, 0, bytes.Length - 4).Split("\r\n");
        var first = lines[0].Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (first.Length != 3 || !Token(first[0]) || first[2] is not ("HTTP/1.0" or "HTTP/1.1"))
            throw new BadRequestException();
        var headers = new List<Field>();
        foreach (var line in lines.Skip(1))
        {
            int colon = line.IndexOf(':');
            if (colon <= 0 || !Token(line[..colon])) throw new BadRequestException();
            var value = line[(colon + 1)..].Trim(' ', '\t');
            if (value.Any(character => character == 127 || character < 32 && character != '\t'))
                throw new BadRequestException();
            headers.Add(new Field(line[..colon], value));
        }
        if (headers.Count(field => field.Name.Equals("Host", StringComparison.OrdinalIgnoreCase)) > 1)
            throw new BadRequestException();
        var lengths = headers.Where(field => field.Name.Equals("Content-Length", StringComparison.OrdinalIgnoreCase)).ToArray();
        bool transferEncoding = headers.Any(field => field.Name.Equals("Transfer-Encoding", StringComparison.OrdinalIgnoreCase));
        if (lengths.Length > 1 || lengths.Length == 1 &&
            (!long.TryParse(lengths[0].Value, NumberStyles.None, CultureInfo.InvariantCulture, out var length) || length < 0 || transferEncoding))
            throw new BadRequestException();
        bool connect = first[0].Equals("CONNECT", StringComparison.OrdinalIgnoreCase);
        Uri uri;
        if (connect)
        {
            if (!Uri.TryCreate("http://" + first[1], UriKind.Absolute, out var parsed) ||
                parsed.AbsolutePath != "/" || parsed.Query.Length != 0 || parsed.Fragment.Length != 0)
                throw new BadRequestException();
            uri = parsed;
        }
        else
        {
            if (!Uri.TryCreate(first[1], UriKind.Absolute, out var parsed) ||
                parsed.Scheme is not ("http" or "ws") || parsed.Fragment.Length != 0)
                throw new BadRequestException();
            uri = parsed;
        }
        if (uri.UserInfo.Length != 0 || uri.Host.Length == 0 || uri.Port is < 1 or > 65535)
            throw new BadRequestException();
        return new Request(first[0], first[1], first[2], uri.IdnHost.Trim('[', ']'), uri.Port,
            uri.PathAndQuery.Length == 0 ? "/" : uri.PathAndQuery, connect, headers);
    }

    static string BuildForwardHeader(Request request, bool absoluteForm, ProxyEndpoint? proxy)
    {
        var connectionTokens = request.Headers.Where(field => field.Name.Equals("Connection", StringComparison.OrdinalIgnoreCase))
            .SelectMany(field => field.Value.Split(',')).Select(value => value.Trim()).ToHashSet(StringComparer.OrdinalIgnoreCase);
        bool upgrade = connectionTokens.Contains("Upgrade") && request.Headers.Any(field =>
            field.Name.Equals("Upgrade", StringComparison.OrdinalIgnoreCase) && field.Value.Length != 0);
        var result = new StringBuilder();
        result.Append(request.Method).Append(' ').Append(absoluteForm ? request.AbsoluteTarget : request.OriginTarget)
            .Append(' ').Append(request.Version).Append("\r\nHost: ").Append(Authority(request.Host, request.Port)).Append("\r\n");
        foreach (var field in request.Headers)
        {
            if (field.Name.Equals("Host", StringComparison.OrdinalIgnoreCase) ||
                field.Name.Equals("Proxy-Authorization", StringComparison.OrdinalIgnoreCase) ||
                field.Name.Equals("Proxy-Connection", StringComparison.OrdinalIgnoreCase) ||
                field.Name.Equals("Connection", StringComparison.OrdinalIgnoreCase) ||
                field.Name.Equals("Keep-Alive", StringComparison.OrdinalIgnoreCase) ||
                connectionTokens.Contains(field.Name) && !(upgrade && field.Name.Equals("Upgrade", StringComparison.OrdinalIgnoreCase)))
                continue;
            if (field.Name.Equals("Upgrade", StringComparison.OrdinalIgnoreCase) && !upgrade) continue;
            result.Append(field.Name).Append(": ").Append(field.Value).Append("\r\n");
        }
        if (absoluteForm && proxy != null) result.Append(UpstreamAuthorization(proxy));
        result.Append(upgrade ? "Connection: Upgrade\r\n\r\n" : "Connection: close\r\n\r\n");
        return result.ToString();
    }

    static async Task CopyHttpResponseAsync(Stream source, Stream destination, CancellationToken cancellation, Action commit)
    {
        byte[]? pending = null;
        for (;;)
        {
            var block = await ReadHeaderAsync(source, pending, cancellation).ConfigureAwait(false);
            var status = Status(block.Header);
            if (status == 407) throw new IOException("Upstream authentication failed.");
            bool interim = status is >= 100 and < 200 && status != 101;
            if (!interim) commit();
            var header=interim || status==101 ? block.Header : ClosingResponseHeader(block.Header);
            await destination.WriteAsync(header, cancellation).ConfigureAwait(false);
            if (interim) { pending = block.Pending; continue; }
            if (block.Pending.Length != 0) await destination.WriteAsync(block.Pending, cancellation).ConfigureAwait(false);
            await source.CopyToAsync(destination, 32768, cancellation).ConfigureAwait(false);
            return;
        }
    }

    static byte[] ClosingResponseHeader(byte[] header)
    {
        // One ordinary HTTP request per local connection: do not let browser
        // reuse forward another absolute-form request or local credentials raw.
        var lines=Encoding.Latin1.GetString(header,0,header.Length-4).Split("\r\n");
        var result=new StringBuilder(lines[0]).Append("\r\n");
        foreach(var line in lines.Skip(1))
        {
            int colon=line.IndexOf(':');
            if(colon<=0)throw new IOException("Invalid response header.");
            var name=line[..colon];
            if(name.Equals("Connection",StringComparison.OrdinalIgnoreCase) ||
               name.Equals("Keep-Alive",StringComparison.OrdinalIgnoreCase) ||
               name.Equals("Proxy-Connection",StringComparison.OrdinalIgnoreCase) ||
               name.Equals("Proxy-Authenticate",StringComparison.OrdinalIgnoreCase))continue;
            result.Append(line).Append("\r\n");
        }
        result.Append("Connection: close\r\n\r\n");
        return Encoding.Latin1.GetBytes(result.ToString());
    }

    static async Task<HeaderBlock> ReadHeaderAsync(Stream stream, byte[]? pending, CancellationToken cancellation)
    {
        var bytes = new byte[HeaderLimit + 8192];
        int used = pending?.Length ?? 0, search = 0;
        if (used > bytes.Length) throw new BadRequestException();
        pending?.CopyTo(bytes, 0);
        for (;;)
        {
            for (int index = search; index + 3 < used; index++)
            {
                if (bytes[index] != 13 || bytes[index + 1] != 10 || bytes[index + 2] != 13 || bytes[index + 3] != 10) continue;
                int end = index + 4;
                if (end > HeaderLimit) throw new BadRequestException();
                return new HeaderBlock(bytes[..end], bytes[end..used]);
            }
            if (used >= HeaderLimit) throw new BadRequestException();
            search = Math.Max(0, used - 3);
            int read = await stream.ReadAsync(bytes.AsMemory(used, Math.Min(8192, bytes.Length - used)), cancellation).ConfigureAwait(false);
            if (read == 0) throw new IOException("Connection closed before headers.");
            used += read;
        }
    }

    static int Status(byte[] header)
    {
        var lineEnd = Array.IndexOf(header, (byte)'\r');
        if (lineEnd < 0) throw new IOException("Invalid upstream response.");
        var parts = Encoding.Latin1.GetString(header, 0, lineEnd).Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length < 2 || parts[0] is not ("HTTP/1.0" or "HTTP/1.1") ||
            !int.TryParse(parts[1], NumberStyles.None, CultureInfo.InvariantCulture, out var code) || code is < 100 or > 599)
            throw new IOException("Invalid upstream response.");
        return code;
    }

    static bool Token(string value) => value.Length != 0 && value.All(character =>
        character is >= '0' and <= '9' or >= 'A' and <= 'Z' or >= 'a' and <= 'z' || "!#$%&'*+-.^_`|~".Contains(character));
    static bool HasCredentials(ProxyEndpoint value) => !string.IsNullOrEmpty(value.Username) || !string.IsNullOrEmpty(value.Password);
    static string UpstreamAuthorization(ProxyEndpoint value) => HasCredentials(value)
        ? "Proxy-Authorization: Basic " + Convert.ToBase64String(Encoding.UTF8.GetBytes(value.Username + ":" + value.Password)) + "\r\n" : "";
    static string Authority(string host, int port) => (host.Contains(':') ? "[" + host + "]" : host) + ":" + port.ToString(CultureInfo.InvariantCulture);
    static Task WriteAsync(Stream stream, string value, CancellationToken cancellation) =>
        stream.WriteAsync(Encoding.Latin1.GetBytes(value), cancellation).AsTask();
    static Task ReplyAsync(Stream stream, int code, string reason, CancellationToken cancellation, string extra = "") =>
        WriteAsync(stream, "HTTP/1.1 " + code.ToString(CultureInfo.InvariantCulture) + " " + reason + "\r\n" + extra +
            "Content-Length: 0\r\nConnection: close\r\n\r\n", cancellation);
    static async Task SafeReplyAsync(Stream stream, int code, string reason)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        try { await ReplyAsync(stream, code, reason, timeout.Token).ConfigureAwait(false); } catch { }
    }
    static async Task IgnoreAsync(Task task) { try { await task.ConfigureAwait(false); } catch { } }

    public void Dispose()
    {
        Session[] active;
        lock (gate)
        {
            if (disposed) return;
            disposed = true;
            active = clients.Values.ToArray();
        }
        try { lifetime.Cancel(); } catch { }
        try { listener.Stop(); } catch { }
        foreach (var client in active) client.Close();
        lock (gate) CleanupIfFinished();
    }

    void CleanupIfFinished()
    {
        // Called under gate only. Every handler releases its slot before removal.
        if (!disposed || !acceptEnded || clients.Count != 0 || cleaned) return;
        cleaned = true;
        lifetime.Dispose(); slots.Dispose();
        CryptographicOperations.ZeroMemory(localCredentials);
    }

    sealed class Session
    {
        readonly CancellationTokenSource stop;
        TcpClient? remote;
        int closed;
        public long Id { get; }
        public long Epoch { get; }
        public ProxyEndpoint? Endpoint { get; }
        public TcpClient Local { get; }
        public CancellationToken Token { get; }
        public Session(long id, long epoch, ProxyEndpoint? endpoint, TcpClient local, CancellationToken lifetime)
        {
            Id = id; Epoch = epoch; Endpoint = endpoint; Local = local;
            stop = CancellationTokenSource.CreateLinkedTokenSource(lifetime); Token = stop.Token;
        }
        public void AttachRemote(TcpClient value)
        {
            Interlocked.Exchange(ref remote, value)?.Dispose();
            if (Volatile.Read(ref closed) != 0) { value.Dispose(); throw new OperationCanceledException(Token); }
        }
        public void CloseRemote() { try { Interlocked.Exchange(ref remote, null)?.Dispose(); } catch { } }
        public void Close()
        {
            if (Interlocked.Exchange(ref closed, 1) != 0) return;
            try { stop.Cancel(); } catch { }
            try { Local.Dispose(); } catch { }
            CloseRemote();
        }
        public void DisposeCancellation() { stop.Dispose(); }
    }

    sealed class RemoteConnection : IDisposable
    {
        readonly TcpClient tcp;
        public Stream Stream { get; }
        public bool AbsoluteForm { get; }
        public byte[] Pending { get; }
        public RemoteConnection(TcpClient tcp, Stream stream, bool absoluteForm, byte[] pending)
        { this.tcp = tcp; Stream = stream; AbsoluteForm = absoluteForm; Pending = pending; }
        public async Task ShutdownWriteAsync(CancellationToken cancellation)
        {
            if (Stream is SslStream tls) await tls.ShutdownAsync().WaitAsync(cancellation).ConfigureAwait(false);
            else { try { tcp.Client.Shutdown(SocketShutdown.Send); } catch { } }
        }
        public void Dispose() { try { Stream.Dispose(); } catch { } try { tcp.Dispose(); } catch { } }
    }

    sealed record HeaderBlock(byte[] Header, byte[] Pending);
    sealed record Field(string Name, string Value);
    sealed record Request(string Method, string AbsoluteTarget, string Version, string Host, int Port,
        string OriginTarget, bool Connect, List<Field> Headers);
    sealed class BadRequestException : IOException { }
}
