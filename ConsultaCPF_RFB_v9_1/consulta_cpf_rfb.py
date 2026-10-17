# -*- coding: utf-8 -*-
import base64
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path
from ip_monitor import IPMonitor
from proxy_bridge import ProxyBridge, validate_config, fetch_ip
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

RFB_URL = "https://servicos.receita.fazenda.gov.br/Servicos/CPF/ConsultaSituacao/ConsultaPublica.asp"
APP_HOME = Path.home() / "ConsultaCPF_RFB"
PROFILE = APP_HOME / "browser_profile"
OUT = APP_HOME / "saidas"
PORT = 9333

def digits(s):
    return re.sub(r"\D", "", s or "")

def parse_row(line):
    raw = line.rstrip("\r\n")
    parts = raw.split("|")
    if len(parts) < 4:
        raise ValueError("Formato inválido: esperado CPF|Nome|Sexo|DD/MM/AAAA")
    cpf = digits(parts[0])
    nasc = parts[3].strip()
    if len(cpf) != 11:
        raise ValueError("CPF deve ter 11 dígitos")
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", nasc):
        raise ValueError("Data deve estar no formato DD/MM/AAAA")
    return {
        "raw": raw,
        "cpf": cpf,
        "nome": parts[1].strip(),
        "sexo": parts[2].strip(),
        "nasc": nasc,
        "status": ""
    }

def find_browser():
    env = os.environ
    candidates = [
        Path(env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(env.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        Path(env.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(env.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(env.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None

def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Conexão WebSocket encerrada")
        data += chunk
    return data

class CDP:
    def __init__(self, ws_url):
        m = re.match(r"ws://([^/:]+):(\d+)(/.*)", ws_url)
        if not m:
            raise RuntimeError("URL WebSocket inválida")
        host, port, path = m.group(1), int(m.group(2)), m.group(3)
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(4096)
        if b"101" not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError("Falha ao abrir WebSocket do navegador")
        self.seq = 0
        self.transferred_bytes = 0
        self.cache_hits = 0
        self.blocked_requests = 0
        self.network_enabled = False
        self._buffer = response.split(b"\r\n\r\n", 1)[1]
        self._fragment = bytearray()

    def _send_frame(self, payload, opcode=1):
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        first = bytes([0x80 | opcode])
        n = len(data)
        if n < 126:
            header = first + bytes([0x80 | n])
        elif n < 65536:
            header = first + bytes([0x80 | 126]) + n.to_bytes(2, "big")
        else:
            header = first + bytes([0x80 | 127]) + n.to_bytes(8, "big")
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + mask + masked)

    def _read(self, n):
        while len(self._buffer) < n:
            chunk = self.sock.recv(max(4096, n - len(self._buffer)))
            if not chunk:
                raise ConnectionError("Conexão WebSocket encerrada")
            self._buffer += chunk
        result, self._buffer = self._buffer[:n], self._buffer[n:]
        return result

    def _recv_frame(self):
        while True:
            h = self._read(2)
            final, opcode = bool(h[0] & 0x80), h[0] & 0x0F
            n, masked = h[1] & 0x7F, bool(h[1] & 0x80)
            if n == 126: n = int.from_bytes(self._read(2), "big")
            elif n == 127: n = int.from_bytes(self._read(8), "big")
            mask = self._read(4) if masked else None
            payload = self._read(n)
            if mask: payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 8: raise ConnectionError("WebSocket fechado")
            if opcode == 9:
                self._send_frame(payload, opcode=10)
                continue
            if opcode == 10: continue
            if opcode == 1:
                self._fragment = bytearray(payload)
            elif opcode == 0:
                self._fragment.extend(payload)
            else: continue
            if final:
                result = bytes(self._fragment).decode("utf-8")
                self._fragment.clear()
                return result

    def call(self, method, params=None, timeout=10):
        self.seq += 1
        ident = self.seq
        message = {"id": ident, "method": method}
        if params is not None:
            message["params"] = params
        self._send_frame(json.dumps(message))
        end = time.time() + timeout
        while time.time() < end:
            raw = self._recv_frame()
            if not raw:
                continue
            obj = json.loads(raw)
            event = obj.get("method")
            params = obj.get("params", {})
            if event in ("Inspector.detached", "Inspector.targetCrashed"):
                raise ConnectionError("A aba do navegador foi fechada ou desconectada")
            if event == "Network.loadingFinished":
                self.transferred_bytes += max(0, int(params.get("encodedDataLength", 0)))
            elif event == "Network.requestServedFromCache":
                self.cache_hits += 1
            elif event == "Network.loadingFailed" and params.get("blockedReason") == "inspector":
                self.blocked_requests += 1
            if obj.get("id") == ident:
                if "error" in obj:
                    raise RuntimeError(obj["error"].get("message", "Erro CDP"))
                return obj.get("result", {})
        raise TimeoutError("Tempo excedido aguardando navegador")

    def eval(self, expression):
        result = self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        if result.get("exceptionDetails"):
            raise RuntimeError("Falha no script da página: " + result["exceptionDetails"].get("text", "erro"))
        return result.get("result", {}).get("value")

def http_json(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

def wait_debug():
    for _ in range(100):
        try:
            return http_json(f"http://127.0.0.1:{PORT}/json/version")
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("Não foi possível conectar ao Edge/Chrome")

def get_page():
    pages = http_json(f"http://127.0.0.1:{PORT}/json")
    for p in pages:
        if p.get("type") == "page" and "receita.fazenda.gov.br" in p.get("url", ""):
            return p
    for p in pages:
        if p.get("type") == "page":
            return p
    raise RuntimeError("Nenhuma aba utilizável encontrada")

FILL_JS = r'''
(() => {
 const cpf = __CPF__;
 const nasc = __NASC__;
 const els = [...document.querySelectorAll('input')];
 function setv(el,v) {
   const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
   setter.call(el,v);
   el.dispatchEvent(new Event('input',{bubbles:true}));
   el.dispatchEvent(new Event('change',{bubbles:true}));
 }
 let c = document.querySelector('input[name="txtCPF"]') ||
         document.querySelector('input[id*="CPF" i]') ||
         els.find(e => /cpf/i.test((e.name||'')+' '+(e.id||'')+' '+(e.placeholder||'')));
 let d = document.querySelector('input[name="txtDataNascimento"]') ||
         document.querySelector('input[id*="Nascimento" i]') ||
         els.find(e => /nascimento|data/i.test((e.name||'')+' '+(e.id||'')+' '+(e.placeholder||'')));
 if (c) setv(c, cpf);
 if (d) setv(d, nasc);
 if (c) c.focus();
 return {cpf:!!c,nasc:!!d,url:location.href,title:document.title};
})()
'''

RESULT_JS = r'''
(() => {
 const t = document.body ? document.body.innerText : '';
 const clean = s => (s||'').replace(/\s+/g,' ').trim();

 const tokenEl = document.querySelector(
   'textarea[name="h-captcha-response"],' +
   'textarea[name="g-recaptcha-response"],' +
   'input[name="h-captcha-response"],' +
   'input[name="g-recaptcha-response"]'
 );
 const token = tokenEl ? (tokenEl.value || tokenEl.textContent || '').trim() : '';
 let apiToken = '';
 try {
   if (window.hcaptcha && typeof hcaptcha.getResponse === 'function') apiToken = hcaptcha.getResponse();
   else if (window.grecaptcha && typeof grecaptcha.getResponse === 'function') apiToken = grecaptcha.getResponse();
 } catch(e) {}
 const captchaReady = !!token && apiToken === token;


 const m = t.match(/Situa(?:ç|c)[aã]o\s+Cadastral\s*:\s*([^\n\r]+)/i);
 if (m) {
   return {
     done:true,
     status:clean(m[1]).replace(/\s{2,}.*/,''),
     captchaReady:captchaReady,
     captchaToken:token,
     documentEpoch:performance.timeOrigin
   };
 }

 const known = [
   ['Anti-Robô não foi preenchido corretamente','CAPTCHA RECUSADO'],
   ['Anti-Robo nao foi preenchido corretamente','CAPTCHA RECUSADO'],
   ['CPF não é válido','CPF INVÁLIDO'],
   ['CPF nao e valido','CPF INVÁLIDO'],
   ['Data de nascimento informada','DATA DIVERGENTE'],
   ['dados informados não conferem','DADOS DIVERGENTES'],
   ['dados informados nao conferem','DADOS DIVERGENTES'],
   ['No momento não podemos atender','SERVIÇO INDISPONÍVEL'],
   ['No momento nao podemos atender','SERVIÇO INDISPONÍVEL']
 ];

 for (const [needle,status] of known) {
   if (t.toLowerCase().includes(needle.toLowerCase())) {
     return {
       done:true,
       status:status,
       captchaReady:captchaReady,
       captchaToken:token,
     documentEpoch:performance.timeOrigin
     };
   }
 }

 return {
   done:false,
   status:'',
   captchaReady:captchaReady,
   captchaToken:token,
     documentEpoch:performance.timeOrigin
 };
})()
'''

CLICK_SUBMIT_JS = r'''
(() => {
 // Keep the site's own click/validation even though its button is hidden.
 const official = document.querySelector('#theForm #id_submit,form input[type="submit"]');
 if (official && !official.disabled) { official.click(); return true; }
 const elements = [...document.querySelectorAll(
   'button,input[type="submit"],input[type="button"],a'
 )];

 const candidates = elements.filter(el => {
   const txt = (
     (el.innerText||'') + ' ' +
     (el.value||'') + ' ' +
     (el.id||'') + ' ' +
     (el.name||'')
   ).toLowerCase();

   return /consultar|continuar|prosseguir|enviar/.test(txt);
 });

 const visible = candidates.find(el => {
   const r = el.getBoundingClientRect();
   const s = getComputedStyle(el);
   return r.width > 0 &&
          r.height > 0 &&
          s.visibility !== 'hidden' &&
          s.display !== 'none' &&
          !el.disabled;
 });

 if (!visible) return false;
 visible.click();
 return true;
})()
'''
# These URL patterns apply only to decoration from Receita and known analytics.
# The form scripts, jQuery, hCaptcha/reCAPTCHA and their CDNs remain available.
BLOCKED_URLS = [
    "*://*.receita.fazenda.gov.br/tema/*",
    "*://*.receita.fazenda.gov.br/estatistica/*",
    "*://*.receita.fazenda.gov.br/*.css*",
    "*://fonts.googleapis.com/*",
    "*://*.google-analytics.com/*",
    "*://*.googletagmanager.com/*",
    "*://*.doubleclick.net/*",
]
for ext in ("png", "jpg", "jpeg", "gif", "webp", "svg", "ico", "woff", "woff2", "ttf", "otf", "mp4", "webm", "mp3"):
    BLOCKED_URLS.append("*://*.receita.fazenda.gov.br/*." + ext + "*")

MINIMAL_JS = r'''
(() => {
 const install = () => {
   if (!document.documentElement || document.getElementById('cpf-minimal-style')) return;
   const style = document.createElement('style');
   style.id = 'cpf-minimal-style';
   style.textContent = `
     html,body { background:#fff!important; color:#111!important; font:16px Arial,sans-serif!important; }
     body { margin:12px!important; }
     header,footer,nav,h2,h3,.aviso,.quadroAviso,#id_clear { display:none!important; }
     #rfb-main-container,.caixaRecuada,#fieldForm,#inputConsultaSituacao,#idRepCatchaFrame {
       width:auto!important; height:auto!important; margin:0!important; padding:0!important;
       position:static!important; float:none!important; background:none!important;
     }
     #inputConsultaSituacao input { font:16px Arial!important; padding:5px!important; }
     #fieldForm {
       display:grid!important; grid-template-columns:240px 304px!important;
       column-gap:64px!important; align-items:center!important; justify-content:start!important;
     }
     #inputConsultaSituacao { grid-column:1!important; }
     #idRepCatchaFrame { grid-column:2!important; margin:0!important; }
     #id_submit { display:none!important; }
     @media (max-width:640px) {
       #fieldForm { grid-template-columns:1fr!important; row-gap:24px!important; }
       #idRepCatchaFrame { grid-column:1!important; }
     }
     #idMensagemErro { color:#b00020!important; }
   `;
   document.documentElement.appendChild(style);
 };
 install();
 if (!document.documentElement) {
   const observer = new MutationObserver(() => {
     if (document.documentElement) { install(); observer.disconnect(); }
   });
   observer.observe(document, {childList:true});
 }
})()
'''


START_CAPTCHA_JS = r'''
(() => {
 // Start the official verification flow; challenges remain for the user.
 if (window.__cpfCaptchaStarted) return 'already';
 const api = window.hcaptcha;
 const iframe = document.querySelector('#hcaptcha iframe[src*="frame=checkbox"],.h-captcha iframe[src*="frame=checkbox"]');
 if (!api || typeof api.execute !== 'function' || !iframe) return 'waiting';
 try {
   const id = new URLSearchParams(new URL(iframe.src).hash.slice(1)).get('id') || undefined;
   if (api.getResponse(id)) return 'solved';
   window.__cpfCaptchaStarted = true;
   const pending = api.execute(id, {async:true});
   if (pending && typeof pending.catch === 'function') {
     pending.catch(() => { window.__cpfCaptchaStartFailed = true; });
   }
   return 'started';
 } catch (e) {
   window.__cpfCaptchaStarted = true;
   window.__cpfCaptchaStartFailed = true;
   return 'failed';
 }
})()
'''


RESTART_AFTER_IP_JS = r'''
(() => {
 const api = window.hcaptcha;
 const iframe = document.querySelector('#hcaptcha iframe[src*="frame=checkbox"],.h-captcha iframe[src*="frame=checkbox"]');
 if (!api || typeof api.reset !== 'function' || typeof api.execute !== 'function' || !iframe) return 'waiting';
 const id = new URLSearchParams(new URL(iframe.src).hash.slice(1)).get('id') || undefined;
 let response;
 try { response = api.getResponse(id); } catch(e) { return 'waiting'; }
 if (response) return 'solved';
 try {
   api.reset(id);
   window.__cpfCaptchaStarted = true;
   window.__cpfCaptchaStartFailed = false;
   const pending = api.execute(id, {async:true});
   if (pending && typeof pending.catch === 'function') {
     pending.catch(() => { window.__cpfCaptchaStartFailed = true; });
   }
   return 'restarted';
 } catch(e) {
   window.__cpfCaptchaStartFailed = true;
   return 'failed';
 }
})()
'''



class IPChanged(RuntimeError):
    pass


class App:
    def __init__(self, root):
        self.root = root
        root.title("Consulta CPF RFB — Banda mínima v9.1 — Proxy verificado")
        root.geometry("980x600")
        root.minsize(800, 480)

        APP_HOME.mkdir(exist_ok=True)
        PROFILE.mkdir(exist_ok=True)
        OUT.mkdir(exist_ok=True)

        self.proxy_bridge = None
        self.network_ready = False
        self.proxy_config = None
        self.browser_route = "ainda não verificada"
        self.rows = []
        self.running = False
        self.waiting_for_captcha = False
        self.worker_thread = None
        self.resume_requested = False
        self.browser = None
        self.cdp = None
        self.source_path = None
        self.partial_network_bytes = 0
        self.full_reloads = 0
        self.consumed_tokens = set()

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Carregar lista", command=self.load_file).pack(side="left")
        ttk.Button(top, text="Iniciar / continuar", command=self.start).pack(side="left", padx=6)
        ttk.Button(top, text="Parar e salvar", command=self.stop_save).pack(side="left")
        ttk.Button(top, text="Abrir pasta de saída", command=self.open_output).pack(side="left", padx=6)

        self.info = ttk.Label(top, text="Carregue TXT: CPF|Nome|Sexo|DD/MM/AAAA")
        self.info.pack(side="left", padx=12)

        proxy_frame = ttk.LabelFrame(root, text="Proxy do navegador (HTTP/HTTPS)", padding=6)
        proxy_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.proxy_enabled = tk.BooleanVar(value=False)
        self.proxy_host = tk.StringVar()
        self.proxy_port = tk.StringVar(value="823")
        self.proxy_user = tk.StringVar()
        self.proxy_password = tk.StringVar()
        self.proxy_tls = tk.BooleanVar(value=False)
        self.restart_on_ip = tk.BooleanVar(value=True)
        ttk.Checkbutton(proxy_frame, text="Ativar proxy", variable=self.proxy_enabled).grid(row=0, column=0, padx=4)
        for column, label, variable, width in [
            (1, "IP / servidor", self.proxy_host, 24), (2, "Porta", self.proxy_port, 6),
            (3, "Usuário", self.proxy_user, 22), (4, "Senha", self.proxy_password, 18)]:
            ttk.Label(proxy_frame, text=label).grid(row=0, column=column, sticky="w")
            ttk.Entry(proxy_frame, textvariable=variable, width=width,
                      show="*" if column == 4 else "").grid(row=1, column=column, padx=4, sticky="ew")
        ttk.Checkbutton(proxy_frame, text="TLS até o proxy (somente se o fornecedor exigir)",
                        variable=self.proxy_tls).grid(row=2, column=1, columnspan=3, sticky="w")
        ttk.Checkbutton(proxy_frame, text="Reabrir Edge quando o IP mudar", variable=self.restart_on_ip).grid(row=3, column=1, columnspan=3, sticky="w")
        self.test_proxy_button = ttk.Button(proxy_frame, text="Testar proxy", command=self.test_proxy)
        self.test_proxy_button.grid(row=1, column=0, padx=4)
        ttk.Button(proxy_frame, text="Aplicar proxy / reabrir Edge",
                   command=self.apply_proxy).grid(row=1, column=1, columnspan=3, sticky="w")
        ttk.Label(proxy_frame, text="Teste não ativa o proxy. Use Aplicar proxy / reabrir Edge. Senha somente nesta execução.").grid(row=4, column=0, columnspan=5, sticky="w")

        cols = ("cpf","nome","nasc","status")
        self.tree = ttk.Treeview(root, columns=cols, show="headings")
        for col, title, width in [
            ("cpf","CPF",120), ("nome","Nome",390), ("nasc","Nascimento",110), ("status","Status",190)
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center" if col != "nome" else "w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0,8))

        bottom = ttk.Frame(root, padding=(8,0,8,8))
        bottom.pack(fill="x")
        self.status = ttk.Label(bottom, text="Parado")
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(side="right", fill="x", expand=True, padx=(12,0))

        self.bandwidth = ttk.Label(root, text="Tráfego parcial da aba: 0,00 MB | Formulários novos: 0")
        self.bandwidth.pack(anchor="w", padx=8, pady=(0,8))
        self.ip_label = ttk.Label(root, text="IP público: aguardando início")
        self.ip_label.pack(anchor="w", padx=8, pady=(0,8))
        self.ip_monitor = IPMonitor(active=lambda: self.running and self.network_ready,
                                    fetch=lambda: fetch_ip(self.proxy_bridge), interval=5)
        self.root.after(500, self.update_ip_display)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def read_proxy_config(self):
        return validate_config(self.proxy_host.get(), self.proxy_port.get(),
                               self.proxy_user.get(), self.proxy_password.get(), self.proxy_tls.get())

    def test_proxy(self):
        try:
            config = self.read_proxy_config()
        except (ValueError, TypeError) as error:
            messagebox.showerror("Proxy", str(error))
            return
        self.test_proxy_button.config(state="disabled")
        self.status.config(text="Testando autenticação e acesso HTTPS pelo proxy...")
        def test():
            bridge = None
            try:
                bridge = ProxyBridge(config)
                address = fetch_ip(bridge)
                self.ui(self.status.config, {"text": "Teste OK (não aplicado ao Edge). IP de saída: " + address})
                self.ui(messagebox.showinfo, "Proxy", "Teste HTTPS OK. IP de saída: " + address + "\nPara ativar no navegador, marque Ativar proxy e clique em Aplicar proxy / reabrir Edge.")
            except Exception:
                detail = (bridge.last_error if bridge else '') or "Falha no teste HTTPS. Confira servidor, porta, credenciais e opção TLS."
                self.ui(messagebox.showerror, "Proxy", detail)
                self.ui(self.status.config, {"text": detail})
            finally:
                if bridge:
                    bridge.close()
                self.ui(self.test_proxy_button.config, {"state": "normal"})
        threading.Thread(target=test, daemon=True).start()

    def apply_proxy(self):
        try:
            if self.proxy_enabled.get():
                self.read_proxy_config()
        except (ValueError, TypeError) as error:
            messagebox.showerror("Proxy", str(error))
            return
        if not self.rows:
            messagebox.showinfo("Proxy", "Carregue uma lista antes de aplicar e iniciar o navegador.")
            return
        self.stop_save()
        self.status.config(text="Aguardando a consulta atual parar para aplicar a configuração...")
        def restart():
            if self.worker_thread and self.worker_thread.is_alive():
                self.root.after(200, restart)
                return
            self.start()
        self.root.after(200, restart)

    def setup_proxy(self):
        self.network_ready = False
        self.browser_route = "aguardando verificação no Edge"
        # Reopen the dedicated browser so flags cannot retain the prior route.
        self.close_consultation_browser()
        if self.proxy_bridge:
            self.proxy_bridge.close()
            self.proxy_bridge = None
        if self.proxy_config:
            self.proxy_bridge = ProxyBridge(self.proxy_config)
        self.last_ip_revision = self.ip_monitor.begin()
        self.network_ready = True
        self.ip_monitor.wake()

    def update_ip_display(self):
        ip, revision, available = self.ip_monitor.snapshot()
        text = ("IP de saída do monitor (" + ("proxy" if self.proxy_config else "direto") + "): "
                + (ip or "aguardando consulta") + " | Edge: " + self.browser_route)
        if ip and not available:
            text += " — última leitura; consulta sem resposta"
        if not self.running:
            text += " — monitor pausado"
        self.ip_label.config(text=text)
        self.root.after(500, self.update_ip_display)

    def ui(self, func, *args):
        self.root.after(0, func, *args)

    def load_file(self):
        p = filedialog.askopenfilename(filetypes=[("Lista TXT","*.txt"),("Todos","*.*")])
        if not p:
            return
        rows, errors = [], []
        for n, line in enumerate(Path(p).read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(parse_row(line))
            except Exception as e:
                errors.append(f"Linha {n}: {e}")
        if not rows:
            messagebox.showerror("Erro", "Nenhuma linha válida encontrada.")
            return
        self.rows = rows
        self.source_path = Path(p)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["cpf"], r["nome"], r["nasc"], "PENDENTE"))
        self.progress["maximum"] = len(rows)
        self.progress["value"] = 0
        self.info.config(text=f"{len(rows)} registros carregados")
        if errors:
            messagebox.showwarning("Aviso", "\n".join(errors[:20]) + ("\n..." if len(errors)>20 else ""))

    def start(self):
        if not self.rows:
            messagebox.showinfo("Lista", "Carregue uma lista primeiro.")
            return
        # Never start concurrent workers on the same browser/socket/list.
        if self.worker_thread and self.worker_thread.is_alive():
            self.resume_requested = True
            self.status.config(text="Consulta em execução. Para alterar o proxy, use Aplicar proxy / reabrir Edge.")
            if not self.running:
                self.root.after(100, self.start)
            return
        try:
            self.proxy_config = self.read_proxy_config() if self.proxy_enabled.get() else None
        except (ValueError, TypeError) as error:
            messagebox.showerror("Proxy", str(error))
            return
        self.ip_restart_enabled = self.restart_on_ip.get()
        self.network_ready = False
        self.resume_requested = False
        self.running = True
        self.last_ip_revision = self.ip_monitor.begin()
        self.ip_monitor.wake()
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.worker_thread.start()

    def release_browser_connection(self):
        if self.cdp:
            self.partial_network_bytes += self.cdp.transferred_bytes
            try: self.cdp.sock.close()
            except Exception: pass
        self.cdp = None
        self.browser = None

    def recover_connection(self, row):
        self.connection_restarted = False
        try:
            self.reconnect()
            self.resume_requested = False
            return True
        except Exception:
            # Handle Iniciar clicked before the previous worker noticed closure.
            if self.resume_requested and self.running:
                self.resume_requested = False
                self.ensure_browser()
                self.connection_restarted = True
                if not self.wait_form_and_fill(row, timeout=12):
                    raise RuntimeError("Não consegui preencher a consulta ao retomar.")
                return True
            raise RuntimeError("Conexão com o navegador interrompida; retomando automaticamente.")

    def ensure_browser(self):
        self.browser_started_fresh = False
        if self.browser and self.browser.poll() is None and self.cdp:
            return
        exe = find_browser()
        if not exe:
            raise RuntimeError("Microsoft Edge ou Google Chrome não encontrado.")
        args = [
            exe,
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={PROFILE}",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--disable-default-apps",
            "--disable-domain-reliability",
            "--disk-cache-size=134217728",
            RFB_URL
        ]
        if self.proxy_bridge:
            args[1:1] = [f"--proxy-server=http://127.0.0.1:{self.proxy_bridge.port}",
                         "--disable-quic", "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
        else:
            args.insert(1, "--no-proxy-server")
        self.browser = subprocess.Popen(args)
        wait_debug()
        time.sleep(1.0)
        page = get_page()
        self.cdp = CDP(page["webSocketDebuggerUrl"])
        self.verify_browser_route()
        self.configure_network()
        self.navigate_home()
        self.browser_started_fresh = True

    def verify_browser_route(self):
        if self.proxy_bridge:
            with self.proxy_bridge.route_lock:
                return self._verify_browser_route()
        return self._verify_browser_route()

    def _verify_browser_route(self):
        # A fresh top-level request uses the browser's own proxy configuration.
        # The bridge must also observe that CONNECT, preventing a false success
        # from an old Edge process that ignored the new command-line flags.
        import ipaddress
        before = self.proxy_bridge.ip_checks if self.proxy_bridge else 0
        self.cdp.call("Page.navigate", {"url": "https://api.ipify.org/?format=json&check=" + str(time.time_ns())})
        deadline = time.monotonic() + 20
        address = None
        while self.running and time.monotonic() < deadline:
            try:
                value = self.cdp.eval("document.body ? document.body.innerText : ''")
                address = str(ipaddress.IPv4Address(json.loads(value)["ip"]))
                break
            except (ValueError, TypeError, KeyError, RuntimeError):
                time.sleep(0.25)
        if not address:
            raise RuntimeError("Não foi possível verificar o IP pelo Edge. Consulta não iniciada.")
        if self.proxy_bridge and self.proxy_bridge.ip_checks <= before:
            raise RuntimeError("O Edge não passou pela ponte do proxy. Feche o Edge dedicado e tente aplicar novamente.")
        self.browser_route = ("proxy verificado: " if self.proxy_bridge else "direto: ") + address

    def reconnect(self):
        previous = self.cdp
        self.cdp = None
        if previous:
            self.partial_network_bytes += previous.transferred_bytes
            try: previous.sock.close()
            except Exception: pass
        page = get_page()
        self.cdp = CDP(page["webSocketDebuggerUrl"])
        self.configure_network()

    def log_diagnostic(self, text):
        try:
            OUT.mkdir(exist_ok=True)
            with (OUT / "diagnostico.txt").open("a", encoding="utf-8") as log:
                log.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
        except OSError:
            pass

    def configure_network(self):
        self.log_diagnostic("Conexão com navegador estabelecida.")
        self.cdp.call("Runtime.enable")
        warnings = []
        for method, params in [
            ("Page.enable", {}),
            ("Network.enable", {}),
            ("Network.setCacheDisabled", {"cacheDisabled": False}),
            ("Network.setBlockedURLs", {"urls": BLOCKED_URLS}),
            ("Page.addScriptToEvaluateOnNewDocument", {"source": MINIMAL_JS}),
        ]:
            try:
                self.cdp.call(method, params, timeout=5)
                self.log_diagnostic(method + ": OK")
            except Exception as e:
                warnings.append(method)
                self.log_diagnostic(method + ": " + str(e))
        try:
            self.cdp.eval(MINIMAL_JS)
        except Exception as e:
            self.log_diagnostic("Estilo simples: " + str(e))
        if warnings:
            self.ui(messagebox.showwarning, "Compatibilidade do navegador",
                    "Alguns ajustes de economia não puderam ser aplicados. "
                    "A consulta continuará. Detalhes em diagnostico.txt na pasta de saída.\n" + ", ".join(warnings))

    def update_bandwidth(self):
        total = self.partial_network_bytes + (self.cdp.transferred_bytes if self.cdp else 0)
        text = (f"Tráfego parcial da aba: {total / 1_000_000:.2f} MB | "
                f"Formulários novos: {self.full_reloads} | "
                "Não inclui todo o tráfego do navegador/CAPTCHA")
        self.ui(self.bandwidth.config, {"text": text})

    def navigate_home(self):
        # Always GET a fresh form; never reuse a restored POST/CAPTCHA state.
        # Cache and decoration blocks stay enabled throughout the navigation.
        self.log_diagnostic("Abrindo formulário da Receita.")
        try:
            old_epoch = self.cdp.eval("performance.timeOrigin")
        except Exception:
            old_epoch = None
        result = self.cdp.call("Page.navigate", {"url": RFB_URL})
        if result.get("errorText"):
            raise RuntimeError("Falha ao abrir o formulário: " + result["errorText"])
        self.full_reloads += 1
        deadline = time.monotonic() + 20
        while self.running and time.monotonic() < deadline:
            self.check_ip_change()
            try:
                state = self.cdp.eval(r'''
                  (() => ({
                    epoch: performance.timeOrigin,
                    ready: document.readyState !== 'loading',
                    form: !!document.querySelector('input[name="txtCPF"]') &&
                          !!document.querySelector('input[name="txtDataNascimento"]')
                  }))()
                ''') or {}
                if state.get("epoch") != old_epoch and state.get("ready") and state.get("form"):
                    return
            except Exception:
                pass
            time.sleep(0.15)
        if self.running:
            raise RuntimeError("O formulário novo não terminou de carregar. Pare e tente continuar.")

    def fill_current(self, r):
        js = FILL_JS.replace("__CPF__", json.dumps(r["cpf"])).replace("__NASC__", json.dumps(r["nasc"]))
        out = self.cdp.eval(js)
        if not out or not out.get("cpf") or not out.get("nasc"):
            raise RuntimeError("Não consegui localizar os campos CPF/data na página.")

    def wait_form_and_fill(self, r, timeout=12):
        end = time.time() + timeout
        while self.running and time.time() < end:
            self.check_ip_change()
            try:
                self.fill_current(r)
                return True
            except Exception:
                time.sleep(0.35)
        return False

    def restart_captcha_after_ip(self):
        try:
            return self.cdp.eval(RESTART_AFTER_IP_JS) or "waiting"
        except Exception:
            return "waiting"

    def start_captcha(self):
        try:
            return self.cdp.eval(START_CAPTCHA_JS) or "waiting"
        except Exception:
            return "waiting"

    def click_submit(self):
        try:
            return bool(self.cdp.eval(CLICK_SUBMIT_JS))
        except Exception:
            return False

    def check_ip_change(self):
        _, revision, _ = self.ip_monitor.snapshot()
        if revision != self.last_ip_revision and self.ip_restart_enabled:
            raise IPChanged("IP público mudou; reiniciando o Edge e a consulta pendente.")

    def close_consultation_browser(self):
        # This CDP endpoint belongs to the dedicated consultation profile.
        process = self.browser
        connection = self.cdp
        if connection is None:
            try:
                connection = CDP(get_page()["webSocketDebuggerUrl"])
                self.cdp = connection
            except Exception:
                pass
        if connection:
            try:
                connection.call("Browser.close", timeout=2)
            except Exception:
                pass
        self.release_browser_connection()
        if process and process.poll() is None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, timeout=5)
                else:
                    process.terminate()
                process.wait(timeout=5)

    def worker(self):
        try:
            if not find_browser():
                raise FileNotFoundError("Microsoft Edge ou Google Chrome não encontrado.")
            self.setup_proxy()
            while self.running:
                try:
                    self.check_ip_change()
                    self.run_queries()
                    break
                except Exception as error:
                    if not self.running:
                        break
                    self.log_diagnostic("Retomada automática: " + str(error))
                    self.save_outputs()
                    self.ui(self.status.config, {"text": str(error)})
                    self.close_consultation_browser()
                    self.ip_monitor.wake()
                    # Keep the supervisor alive during a 4G outage. Failed IP
                    # requests never replace the last known address.
                    retry_at = time.monotonic() + 3
                    while self.running:
                        _, revision, available = self.ip_monitor.snapshot()
                        if available and time.monotonic() >= retry_at:
                            self.last_ip_revision = revision
                            break
                        self.ui(self.status.config, {"text": (self.proxy_bridge.last_error if self.proxy_bridge else "") or "Aguardando conexão para reabrir o Edge e continuar..."})
                        time.sleep(0.5)
        except Exception as error:
            self.log_diagnostic("Erro: " + str(error))
            self.ui(self.status.config, {"text": f"Erro: {error}"})
            self.ui(messagebox.showerror, "Erro", str(error))
        finally:
            self.save_outputs()
            self.waiting_for_captcha = False
            self.update_bandwidth()
            self.running = False

    def run_queries(self):
        self.ui(self.status.config, {"text": "Abrindo Receita e conectando ao navegador..."})
        self.ensure_browser()
        first_pending = True

        for i, r in enumerate(self.rows):
            if not self.running:
                break
            self.check_ip_change()
            if r["status"]:
                continue

            self.ui(
                self.status.config,
                {"text": f"{i+1}/{len(self.rows)} - preparando consulta..."}
            )

            if first_pending:
                # ensure_browser already loaded a fresh form for a new browser.
                # Continuing an existing browser also needs a new document.
                if not self.browser_started_fresh:
                    self.navigate_home()
                first_pending = False
            else:
                self.navigate_home()
            if not self.wait_form_and_fill(r, timeout=12):
                raise RuntimeError("Não consegui preencher o formulário novo da Receita.")

            self.update_bandwidth()

            self.ui(
                self.status.config,
                {"text": f"{i+1}/{len(self.rows)} - resolva o CAPTCHA; o envio será automático"}
            )

            auto_submitted = False
            submitted_epoch = None
            captcha_start_attempted = False
            captcha_start_deadline = time.monotonic() + 15
            last_ip_revision = self.last_ip_revision
            self.waiting_for_captcha = True
            self.ip_monitor.wake()
            ip_retry_pending = False
            ip_retry_deadline = 0

            while self.running:
                time.sleep(0.30)

                self.check_ip_change()

                if not ip_retry_pending and not auto_submitted and not captcha_start_attempted:
                    started = self.start_captcha()
                    if started != "waiting" or time.monotonic() >= captcha_start_deadline:
                        captcha_start_attempted = True
                        text = ("Verificação iniciada; resolva o desafio se aparecer."
                                if started in ("started", "already", "solved")
                                else "Clique em Sou humano: o início automático não ficou disponível.")
                        self.ui(self.status.config, {"text": f"{i+1}/{len(self.rows)} - {text}"})

                try:
                    res = self.cdp.eval(RESULT_JS) or {}
                except Exception:
                    if self.recover_connection(r):
                        if self.connection_restarted:
                            auto_submitted = False
                            submitted_epoch = None
                            captcha_start_attempted = False
                            captcha_start_deadline = time.monotonic() + 15
                            last_ip_revision = self.last_ip_revision
                            self.waiting_for_captcha = True
                            self.ip_monitor.wake()
                            ip_retry_pending = False
                        continue
                    break

                self.resume_requested = False
                current_token = (res.get("captchaToken") or "").strip()

                # Only accept a non-empty token that is NOT the token already
                # consumed by the previous CPF.
                fresh_token = (
                    bool(current_token)
                    and bool(res.get("captchaReady"))
                    and current_token not in self.consumed_tokens
                )

                if fresh_token and not auto_submitted:
                    self.ui(
                        self.status.config,
                        {"text": f"{i+1}/{len(self.rows)} - CAPTCHA novo validado; enviando..."}
                    )

                    if self.click_submit():
                        auto_submitted = True
                        self.waiting_for_captcha = False
                        submitted_epoch = res.get("documentEpoch")
                        self.consumed_tokens.add(current_token)
                        time.sleep(0.8)
                        continue

                if (res.get("done") and auto_submitted
                        and res.get("documentEpoch") != submitted_epoch):
                    st = (res.get("status") or "SEM RESULTADO").strip()

                    if st == "CAPTCHA RECUSADO":
                        # The page may clear CPF/data after rejecting a token.
                        # Refill the SAME record and wait for a genuinely fresh
                        # captcha before trying again.
                        auto_submitted = False

                        self.ui(
                            self.status.config,
                            {"text": f"{i+1}/{len(self.rows)} - CAPTCHA recusado; preparando nova tentativa..."}
                        )

                        self.waiting_for_captcha = False
                        self.navigate_home()
                        if not self.wait_form_and_fill(r, timeout=12):
                            raise RuntimeError("Não consegui restaurar o formulário da Receita.")
                        self.update_bandwidth()
                        captcha_start_attempted = False
                        captcha_start_deadline = time.monotonic() + 15
                        last_ip_revision = self.last_ip_revision
                        self.waiting_for_captcha = True
                        self.ip_monitor.wake()

                        self.ui(
                            self.status.config,
                            {"text": f"{i+1}/{len(self.rows)} - resolva novamente o CAPTCHA"}
                        )
                        continue

                    self.update_bandwidth()
                    r["status"] = st
                    self.save_outputs()
                    self.ui(self.update_tree_row, i, st)
                    break

        self.save_outputs()

        if self.running:
            self.ui(self.status.config, {"text": "Consulta concluída"})
            self.ui(
                messagebox.showinfo,
                "Concluído",
                f"Processamento finalizado.\nArquivos em:\n{OUT}"
            )

    def update_tree_row(self, i, status):
        items = self.tree.get_children()
        if i < len(items):
            vals = list(self.tree.item(items[i], "values"))
            vals[3] = status
            self.tree.item(items[i], values=vals)
            self.tree.see(items[i])
        self.progress["value"] = sum(bool(r["status"]) for r in self.rows)

    def save_outputs(self):
        if not self.rows:
            return

        regulars, pending = [], []

        for r in self.rows:
            status = (r["status"] or "").strip().upper()
            if status:
                if status == "REGULAR":
                    regulars.append(r["raw"])
            else:
                pending.append(r["raw"])

        (OUT / "regulares.txt").write_text(
            "\n".join(regulars) + ("\n" if regulars else ""),
            encoding="utf-8"
        )
        (OUT / "nao_checados.txt").write_text(
            "\n".join(pending) + ("\n" if pending else ""),
            encoding="utf-8"
        )

    def stop_save(self):
        self.waiting_for_captcha = False
        self.running = False
        self.save_outputs()
        self.status.config(text=f"Parado. Saídas salvas em {OUT}")

    def open_output(self):
        OUT.mkdir(exist_ok=True)
        os.startfile(str(OUT))

    def on_close(self):
        self.waiting_for_captcha = False
        self.running = False
        try:
            self.save_outputs()
        finally:
            self.ip_monitor.close()
            if self.proxy_bridge:
                self.proxy_bridge.close()
            self.root.destroy()

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
