using System;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;

namespace MintWindows;

public enum ProxyProtocol { Http, Https, Socks5 }

public sealed record ProxyEndpoint(ProxyProtocol Protocol, string Host, int Port, string Username, string Password);

public sealed class ProxySettings
{
    public bool Enabled { get; set; }
    public ProxyProtocol Protocol { get; set; } = ProxyProtocol.Http;
    public string Host { get; set; } = string.Empty;
    public int Port { get; set; } = 8080;
    public string Username { get; set; } = string.Empty;
    public string PasswordProtected { get; set; } = string.Empty;

    public bool IsConfigured => Enum.IsDefined(typeof(ProxyProtocol), Protocol)
        && Port >= 1 && Port <= 65535 && TryNormalizeHost(Host, out _);

    public ProxyEndpoint GetEndpoint()
    {
        if (!IsConfigured || !TryNormalizeHost(Host, out string host))
            throw new InvalidOperationException("A configuração do proxy está incompleta ou inválida.");
        string password = ReadPassword();
        string username = Username ?? string.Empty;
        if (!ValidateCredentials(Protocol, username, password, out string error))
            throw new InvalidOperationException(error);
        return new ProxyEndpoint(Protocol, host, Port, username, password);
    }

    public string ReadPassword()
    {
        if (string.IsNullOrEmpty(PasswordProtected)) return string.Empty;
        byte[] encrypted;
        try { encrypted = Convert.FromBase64String(PasswordProtected); }
        catch (FormatException ex) { throw new CryptographicException("Não foi possível recuperar a senha salva do proxy.", ex); }
        byte[] plaintext = Array.Empty<byte>();
        try
        {
            plaintext = TransformPassword(encrypted, false);
            return Encoding.UTF8.GetString(plaintext);
        }
        finally
        {
            Array.Clear(encrypted, 0, encrypted.Length);
            Array.Clear(plaintext, 0, plaintext.Length);
        }
    }

    public void SetPassword(string password)
    {
        if (string.IsNullOrEmpty(password)) { PasswordProtected = string.Empty; return; }
        byte[] plaintext = Encoding.UTF8.GetBytes(password);
        byte[] encrypted = Array.Empty<byte>();
        try
        {
            encrypted = TransformPassword(plaintext, true);
            PasswordProtected = Convert.ToBase64String(encrypted);
        }
        finally
        {
            Array.Clear(plaintext, 0, plaintext.Length);
            Array.Clear(encrypted, 0, encrypted.Length);
        }
    }

    public static bool TryNormalizeHost(string value, out string host)
    {
        host = string.Empty;
        if (string.IsNullOrEmpty(value)) return false;
        foreach (char character in value)
            if (char.IsWhiteSpace(character) || char.IsControl(character) || "/\\@?#%".IndexOf(character) >= 0) return false;
        string candidate = value;
        if (candidate.StartsWith("[", StringComparison.Ordinal) && candidate.EndsWith("]", StringComparison.Ordinal))
        {
            candidate = candidate.Substring(1, candidate.Length - 2);
            if (candidate.IndexOf(':') < 0) return false;
        }
        if (candidate.IndexOf(':') >= 0)
        {
            if (!IPAddress.TryParse(candidate, out IPAddress? address) || address.AddressFamily != AddressFamily.InterNetworkV6) return false;
            host = address.ToString();
            return true;
        }
        if (candidate.IndexOf('[') >= 0 || candidate.IndexOf(']') >= 0) return false;
        bool numeric = true;
        foreach (char character in candidate) if ((character < '0' || character > '9') && character != '.') numeric = false;
        if (numeric)
        {
            string[] parts = candidate.Split('.');
            if (parts.Length != 4) return false;
            var bytes = new byte[4];
            for (int i = 0; i < parts.Length; i++)
                if (parts[i].Length < 1 || parts[i].Length > 3 || !byte.TryParse(parts[i], NumberStyles.None, CultureInfo.InvariantCulture, out bytes[i])) return false;
            host = new IPAddress(bytes).ToString();
            return true;
        }
        try
        {
            bool trailingDot = candidate.EndsWith(".", StringComparison.Ordinal);
            string ascii = new IdnMapping().GetAscii(trailingDot ? candidate.Substring(0, candidate.Length - 1) : candidate);
            if (ascii.Length == 0 || ascii.Length > 253) return false;
            foreach (string label in ascii.Split('.'))
            {
                if (label.Length == 0 || label.Length > 63 || label[0] == '-' || label[label.Length - 1] == '-') return false;
                foreach (char character in label)
                    if (!(character >= 'a' && character <= 'z') && !(character >= 'A' && character <= 'Z')
                        && !(character >= '0' && character <= '9') && character != '-') return false;
            }
            host = ascii.ToLowerInvariant() + (trailingDot ? "." : string.Empty);
            return true;
        }
        catch (ArgumentException) { return false; }
    }

    public static bool ValidateCredentials(ProxyProtocol protocol, string username, string password, out string error)
    {
        error = string.Empty;
        username ??= string.Empty;
        password ??= string.Empty;
        if (username.Length == 0 && password.Length != 0)
            error = "Informe o usuário para utilizar uma senha, ou deixe os dois campos vazios.";
        else if ((protocol == ProxyProtocol.Http || protocol == ProxyProtocol.Https) && username.IndexOf(':') >= 0)
            error = "O usuário de um proxy HTTP ou HTTPS não pode conter dois-pontos (:).";
        else if (ContainsControl(username) || ContainsControl(password))
            error = "Usuário e senha não podem conter quebras de linha ou caracteres de controle.";
        else if (protocol == ProxyProtocol.Socks5 && username.Length != 0 && password.Length == 0)
            error = "Informe a senha do SOCKS5 ou deixe usuário e senha vazios para usar sem autenticação.";
        else if (protocol == ProxyProtocol.Socks5 && (Encoding.UTF8.GetByteCount(username) > 255 || Encoding.UTF8.GetByteCount(password) > 255))
            error = "No SOCKS5, usuário e senha devem ter no máximo 255 bytes UTF-8 cada.";
        return error.Length == 0;
    }

    private static bool ContainsControl(string value)
    {
        foreach (char character in value) if (char.IsControl(character)) return true;
        return false;
    }

    private static byte[] TransformPassword(byte[] input, bool protect)
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            throw new PlatformNotSupportedException("A proteção da senha do proxy exige o Windows.");
        var source = new DataBlob { Length = input.Length, Data = Marshal.AllocHGlobal(input.Length) };
        DataBlob destination = default;
        try
        {
            Marshal.Copy(input, 0, source.Data, input.Length);
            bool success = protect
                ? CryptProtectData(ref source, null, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 1, out destination)
                : CryptUnprotectData(ref source, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 1, out destination);
            if (!success) throw new CryptographicException(Marshal.GetLastWin32Error());
            var result = new byte[destination.Length];
            if (destination.Length > 0) Marshal.Copy(destination.Data, result, 0, destination.Length);
            return result;
        }
        finally
        {
            ClearNative(source.Data, source.Length);
            Marshal.FreeHGlobal(source.Data);
            if (destination.Data != IntPtr.Zero)
            {
                ClearNative(destination.Data, destination.Length);
                LocalFree(destination.Data);
            }
        }
    }

    private static void ClearNative(IntPtr data, int length)
    {
        for (int i = 0; i < length; i++) Marshal.WriteByte(data, i, 0);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct DataBlob { public int Length; public IntPtr Data; }

    [DllImport("crypt32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptProtectData(ref DataBlob input, string? description, IntPtr entropy, IntPtr reserved, IntPtr prompt, uint flags, out DataBlob output);

    [DllImport("crypt32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CryptUnprotectData(ref DataBlob input, IntPtr description, IntPtr entropy, IntPtr reserved, IntPtr prompt, uint flags, out DataBlob output);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr memory);
}
