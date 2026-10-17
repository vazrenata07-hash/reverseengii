"""Loopback HTTP bridge. Credentials go only to the configured upstream proxy."""
import base64
import http.client
import ipaddress
import json
import select
import socket
import socketserver
import ssl
import threading
from urllib.parse import urlsplit


def validate_config(host, port, username, password, tls=False):
    host = host.strip()
    if '://' in host:
        parsed = urlsplit(host)
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            raise ValueError('Informe somente o servidor, sem credenciais no endereço.')
        tls = parsed.scheme == 'https'
        port = parsed.port or port
        host = parsed.hostname or ''
    if not host or any(c.isspace() or c in '/?#@' for c in host):
        raise ValueError('Informe um IP ou nome de servidor válido.')
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError('A porta deve estar entre 1 e 65535.')
    if ':' in username or any(c in username + password for c in '\r\n'):
        raise ValueError('Usuário/senha inválidos; usuário não pode conter dois-pontos.')
    return dict(host=host, port=port, username=username, password=password, tls=bool(tls))


def read_header(sock):
    data = bytearray()
    while b'\r\n\r\n' not in data:
        part = sock.recv(4096)
        if not part:
            raise OSError('Conexão encerrada durante os cabeçalhos.')
        data.extend(part)
        if len(data) > 65536:
            raise OSError('Cabeçalho muito grande.')
    header, rest = bytes(data).split(b'\r\n\r\n', 1)
    return header, rest


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        owner = self.server.owner
        upstream = None
        replied = False
        owner.track(self.request)
        try:
            self.request.settimeout(15)
            header, body = read_header(self.request)
            lines = header.split(b'\r\n')
            method, target, version = lines[0].split(b' ', 2)
            if method != b'CONNECT' and not target.startswith(b'http://'):
                raise OSError('Requisição de proxy inválida.')
            upstream = socket.create_connection((owner.config['host'], owner.config['port']), timeout=12)
            if owner.config['tls']:
                upstream = ssl.create_default_context().wrap_socket(upstream, server_hostname=owner.config['host'])
            owner.track(upstream)
            # Strip client-supplied proxy credentials and force one HTTP request
            # per upstream connection. CONNECT carries an opaque TLS tunnel.
            kept = [line for line in lines[1:] if line.split(b':', 1)[0].lower()
                    not in (b'proxy-authorization', b'proxy-connection', b'connection')]
            kept += [b'Proxy-Authorization: Basic ' + owner.auth,
                     b'Connection: close' if method != b'CONNECT' else b'Proxy-Connection: keep-alive']
            upstream.sendall(b'\r\n'.join([lines[0]] + kept) + b'\r\n\r\n' + body)
            response, extra = read_header(upstream)
            code = int(response.split(b' ', 2)[1])
            if code == 407:
                owner.last_error = 'Proxy recusou a autenticação (407). Confira usuário e senha.'
                raise OSError(owner.last_error)
            if method == b'CONNECT' and code != 200:
                owner.last_error = 'Proxy recusou a conexão (HTTP %s).' % code
                raise OSError(owner.last_error)
            owner.last_error = ''
            if method == b'CONNECT' and target.lower() == b'api.ipify.org:443':
                with owner.lock:
                    owner.ip_checks += 1
            self.request.sendall(response + b'\r\n\r\n' + extra)
            replied = True
            self.request.settimeout(20)
            upstream.settimeout(20)
            while not owner.stopped.is_set():
                ready, _, _ = select.select([self.request, upstream], [], [], 1)
                if isinstance(upstream, ssl.SSLSocket) and upstream.pending() and upstream not in ready:
                    ready.append(upstream)
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is self.request else self.request).sendall(data)
        except Exception:
            if not replied:
                if not owner.last_error:
                    owner.last_error = 'Não foi possível conectar ao proxy. Confira servidor, porta e conexão.'
                try:
                    self.request.sendall(b'HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
                except OSError:
                    pass
        finally:
            owner.untrack(self.request)
            if upstream:
                owner.untrack(upstream)
                upstream.close()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class ProxyBridge:
    def __init__(self, config):
        self.config = dict(config)
        self.auth = base64.b64encode((config['username'] + ':' + config['password']).encode('utf-8'))
        self.last_error = ''
        self.ip_checks = 0
        self.route_lock = threading.Lock()
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.sockets = set()
        self.server = Server(('127.0.0.1', 0), Handler)
        self.server.owner = self
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def track(self, sock):
        with self.lock:
            self.sockets.add(sock)

    def untrack(self, sock):
        with self.lock:
            self.sockets.discard(sock)

    def close(self):
        self.stopped.set()
        with self.lock:
            sockets = list(self.sockets)
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        self.server.shutdown()
        self.server.server_close()


def fetch_ip(bridge=None, context=None):
    if bridge:
        with bridge.route_lock:
            return _fetch_ip(bridge, context)
    return _fetch_ip(None, context)


def _fetch_ip(bridge=None, context=None):
    # Explicit connections avoid system proxy settings and environment bypasses.
    if bridge:
        connection = http.client.HTTPSConnection('127.0.0.1', bridge.port, timeout=15, context=context)
        connection.set_tunnel('api.ipify.org', 443)
    else:
        connection = http.client.HTTPSConnection('api.ipify.org', timeout=6, context=context)
    try:
        connection.request('GET', '/?format=json', headers={'Host': 'api.ipify.org', 'Connection': 'close'})
        response = connection.getresponse()
        if response.status != 200:
            raise OSError('Falha na consulta do IP público.')
        return str(ipaddress.IPv4Address(json.loads(response.read(1024))['ip']))
    finally:
        connection.close()
