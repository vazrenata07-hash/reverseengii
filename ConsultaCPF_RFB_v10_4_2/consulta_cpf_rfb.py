# -*- coding: utf-8 -*-
import base64
import json
import os
import re
import socket
import subprocess
import tempfile
import queue
import threading
import time
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path
from ip_monitor import IPMonitor
from wifi_networks import (WindowsWifi, Rotation, VerificationWatch, SwitchRequired,
                           Cancelled, load_settings, DEFAULTS)
from wifi_settings import open_settings
from browser_mode import browser_args
from browser_window import BrowserWindow
from captcha_preview import CaptchaPreview, PreviewStream, forward_click
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
            deadline = getattr(self, "read_deadline", None)
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Tempo excedido aguardando navegador")
                self.sock.settimeout(remaining)
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
        provider = getattr(self, 'timeout_provider', None)
        if provider:
            timeout = min(timeout, provider())
        previous_timeout = self.sock.gettimeout()
        self.read_deadline = time.monotonic() + timeout
        self.sock.settimeout(max(0.05, timeout))
        try:
            return self._call(method, params, timeout)
        finally:
            self.read_deadline = None
            self.sock.settimeout(previous_timeout)

    def _call(self, method, params=None, timeout=10):
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

    def eval(self, expression, timeout=10):
        result = self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        }, timeout=timeout)
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
 if (window.__cpfCaptchaStartFailed) return 'failed';
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



class CompactBrowserError(RuntimeError):
    pass

class IPChanged(RuntimeError):
    pass


class App:
    def __init__(self, root):
        self.root = root
        self.closing = False
        root.title("Consulta CPF RFB — v10.4.2 — CAPTCHA responsivo")
        root.geometry("1060x640")
        root.minsize(900, 540)

        APP_HOME.mkdir(exist_ok=True)
        global PROFILE, PORT
        PROFILE = Path(tempfile.mkdtemp(prefix="captcha_compacto_", dir=APP_HOME))
        with socket.socket() as port_socket:
            port_socket.bind(('127.0.0.1', 0))
            PORT = port_socket.getsockname()[1]
        OUT.mkdir(exist_ok=True)

        self.wifi_settings_path = APP_HOME / "wifi_settings.json"
        try:
            self.wifi_settings = load_settings(self.wifi_settings_path)
        except (ValueError, OSError, TypeError, KeyError) as error:
            self.wifi_settings = dict(DEFAULTS)
            messagebox.showwarning("Settings", "Configuração Wi-Fi inválida; troca desativada. " + str(error))
        self.compact_active = False
        self.captcha_preview = CaptchaPreview()
        self.preview_stream = None
        self.preview_clicks = queue.Queue()
        self.next_preview_at = 0
        self.preview_expanded = False
        self.expanded_captcha = None
        self.rotation = None
        self.network_ready = True
        self.network_stop = threading.Event()
        self.verification_watch = None
        self.form_loaded_at = None
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

        ttk.Button(top, text="Settings", command=lambda: open_settings(self)).pack(side="left", padx=6)

        self.info = ttk.Label(root, text="Carregue TXT: CPF|Nome|Sexo|DD/MM/AAAA")
        self.info.pack(anchor="w", padx=8, pady=(0,8))

        cols = ("cpf","nome","nasc","status")
        self.tree = ttk.Treeview(root, columns=cols, show="headings")
        for col, title, width in [
            ("cpf","CPF",120), ("nome","Nome",390), ("nasc","Nascimento",110), ("status","Status",190)
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center" if col != "nome" else "w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0,8))

        summary = ttk.Frame(root, padding=(8,0,8,8))
        summary.pack(fill="x")
        summary.columnconfigure(0, weight=1)
        left = ttk.Frame(summary)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        self.status = ttk.Label(left, text="Parado", wraplength=600)
        self.status.pack(anchor="w", pady=(0,4))
        self.progress = ttk.Progressbar(left, mode="determinate", length=280)
        self.progress.pack(anchor="w", pady=(0,8))
        self.bandwidth = ttk.Label(left, text="Tráfego parcial da aba: 0,00 MB | Formulários novos: 0", wraplength=600)
        self.bandwidth.pack(anchor="w", pady=(0,6))
        self.network_label = ttk.Label(left, text="Wi-Fi: troca automática desligada", wraplength=600)
        self.network_label.pack(anchor="w", pady=(0,4))
        self.ip_label = ttk.Label(left, text="IP público: aguardando início", wraplength=600)
        self.ip_label.pack(anchor="w")
        def wrap_summary(event):
            for label in (self.status, self.bandwidth, self.network_label, self.ip_label):
                label.config(wraplength=max(200, event.width-8))
        left.bind('<Configure>', wrap_summary)
        self.captcha_panel = ttk.LabelFrame(summary, text="Verificação", padding=4)
        self.captcha_panel.grid(row=0, column=1, sticky="ne")
        self.small_captcha_host = tk.Frame(self.captcha_panel, width=336, height=104, bg="white")
        self.small_captcha_host.pack()
        self.small_captcha_host.pack_propagate(False)
        self.captcha_host = self.small_captcha_host
        self.captcha_hint = tk.Label(self.small_captcha_host, text="O CAPTCHA aparecerá aqui ao iniciar.", bg="white", borderwidth=0, highlightthickness=0)
        self.captcha_hint.place(relx=.5, rely=.5, anchor="center")
        self.captcha_hint.bind('<Button-1>', self.preview_click)
        self.preview_label = self.captcha_hint
        ttk.Button(self.captcha_panel, text="Ampliar", command=self.expand_captcha).pack(anchor="e", pady=(3,0))
        if not self.wifi_settings.get('compact_captcha', False):
            self.captcha_panel.grid_remove()
        self.ip_monitor = IPMonitor(active=lambda: self.running and self.network_ready, interval=1)
        self.tree.pack_forget()
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.root.after(100, self.poll_preview)
        self.root.after(500, self.update_ip_display)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def clear_preview(self):
        for label in {self.captcha_hint,self.preview_label}:
            label.configure(image='',text='Carregando CAPTCHA...',cursor='arrow')
            label.snapshot=None
            label.photo=None

    def preview_click(self, event):
        label=event.widget
        snapshot=getattr(label, 'snapshot', None)
        if snapshot and (not self.preview_expanded or label==self.preview_label):
            self.preview_clicks.put((snapshot,event.x,event.y,label.photo.width(),label.photo.height()))

    def render_preview(self, snapshot):
        if self.closing or not self.compact_active:
            return
        label=self.preview_label
        photo=tk.PhotoImage(data=snapshot['data'])
        width=max(1,self.captcha_host.winfo_width()-4)
        height=max(1,self.captcha_host.winfo_height()-4)
        factor=max(1,(photo.width()+width-1)//width,(photo.height()+height-1)//height)
        if factor>1:photo=photo.subsample(factor,factor)
        label.configure(image=photo,text='',cursor='hand2')
        label.photo=photo
        label.snapshot=snapshot

    def service_preview(self):
        # Input stays on the main CDP connection. This never captures images.
        if not self.compact_active or not self.cdp:
            return
        try:
            while True:
                item=self.preview_clicks.get_nowait()
                forward_click(self.cdp,*item)
        except queue.Empty:
            pass

    def start_preview_stream(self, url):
        if self.preview_stream:
            self.preview_stream.close()
        self.preview_stream=PreviewStream(url,CDP,
            active=lambda:self.running and self.compact_active and self.waiting_for_captcha,
            expanded=lambda:self.preview_expanded)

    def poll_preview(self):
        if self.closing:
            return
        stream=self.preview_stream
        if stream:
            frame=stream.take()
            if frame:self.render_preview(frame)
        self.root.after(100,self.poll_preview)

    def expand_captcha(self):
        if self.expanded_captcha and self.expanded_captcha.winfo_exists():
            self.expanded_captcha.lift();return
        window=tk.Toplevel(self.root)
        self.expanded_captcha=window
        self.preview_expanded=True
        window.title('Somente verificação — ampliada')
        window.geometry('460x640');window.minsize(360,440);window.transient(self.root)
        ttk.Button(window,text='Reduzir para o canto',command=self.dock_captcha).pack(anchor='e',padx=6,pady=6)
        self.captcha_host=tk.Frame(window,bg='white')
        self.captcha_host.pack(fill='both',expand=True)
        self.preview_label=tk.Label(self.captcha_host,text='Carregando verificação...',bg='white',borderwidth=0,highlightthickness=0)
        self.preview_label.place(relx=.5,rely=.5,anchor='center')
        self.preview_label.bind('<Button-1>',self.preview_click)
        self.next_preview_at=0
        window.protocol('WM_DELETE_WINDOW',self.dock_captcha)

    def dock_captcha(self):
        self.preview_expanded=False
        self.captcha_host=self.small_captcha_host
        self.preview_label=self.captcha_hint
        if self.expanded_captcha and self.expanded_captcha.winfo_exists():self.expanded_captcha.destroy()
        self.expanded_captcha=None
        self.next_preview_at=0

    def update_ip_display(self):
        ip, revision, available = self.ip_monitor.snapshot()
        text = "IP público (IPv4): " + (ip or "aguardando consulta")
        if ip and not available:
            text += " — última leitura; consulta sem resposta"
        if not self.running:
            text += " — monitor pausado"
        self.ip_label.config(text=text)
        self.root.after(500, self.update_ip_display)

    def ui(self, func, *args):
        if self.closing:
            return
        try:
            self.root.after(0, func, *args)
        except (tk.TclError, RuntimeError):
            if not self.closing:
                raise

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
            if not self.running:
                self.root.after(100, self.start)
            return
        self.compact_active = self.wifi_settings.get("compact_captcha", False)
        if self.compact_active:
            self.captcha_panel.grid()
        else:
            self.dock_captcha()
            self.captcha_panel.grid_remove()
        self.rotation = Rotation(self.wifi_settings)
        self.network_stop.clear()
        self.verification_watch = None
        self.form_loaded_at = None
        self.resume_requested = False
        self.running = True
        self.last_ip_revision = self.ip_monitor.begin()
        self.ip_monitor.wake()
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.worker_thread.start()

    def release_browser_connection(self):
        if self.preview_stream:
            self.preview_stream.close()
            self.preview_stream=None
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
        args = browser_args(exe, PORT, PROFILE, "about:blank" if self.compact_active else RFB_URL, self.compact_active)
        self.log_diagnostic("Modo do navegador: " + ("CAPTCHA compacto" if self.compact_active else "janela normal"))
        self.browser = subprocess.Popen(args)
        version = wait_debug()
        time.sleep(1.0)
        page = get_page()
        self.cdp = CDP(page["webSocketDebuggerUrl"])
        self.cdp.timeout_provider = self.browser_timeout
        if self.compact_active:
            # Edge may use a launcher PID; get the owner from the browser CDP
            # endpoint rather than choosing an unrelated desktop window.
            self.browser_window_pid = self.browser.pid
            browser_connection = None
            try:
                browser_connection = CDP(version['webSocketDebuggerUrl'])
                processes = browser_connection.call('SystemInfo.getProcessInfo').get('processInfo', [])
                self.browser_window_pid = int(next(p['id'] for p in processes if p['type'] == 'browser'))
            except Exception as error:
                self.log_diagnostic('PID do navegador: usando processo iniciado. ' + str(error))
            finally:
                if browser_connection:
                    browser_connection.sock.close()
            if os.name=='nt':
                window=BrowserWindow()
                deadline=time.monotonic()+12
                while self.running:
                    if window.move_offscreen(self.browser_window_pid):break
                    if time.monotonic()>=deadline:
                        raise CompactBrowserError('Não foi possível preparar a visualização isolada do CAPTCHA.')
                    time.sleep(.1)
        self.configure_network()
        if self.compact_active:self.start_preview_stream(page["webSocketDebuggerUrl"])
        self.navigate_home()
        self.browser_started_fresh = True

    def reconnect(self):
        previous = self.cdp
        self.cdp = None
        if previous:
            self.partial_network_bytes += previous.transferred_bytes
            try: previous.sock.close()
            except Exception: pass
        page = get_page()
        self.cdp = CDP(page["webSocketDebuggerUrl"])
        self.cdp.timeout_provider = self.browser_timeout
        self.configure_network()
        if self.compact_active:self.start_preview_stream(page["webSocketDebuggerUrl"])

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
        if self.compact_active:
            self.cdp.call('Emulation.setDeviceMetricsOverride',{'width':1280,'height':900,'deviceScaleFactor':1,'mobile':False})
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
        self.verification_watch = None
        self.form_loaded_at = None
        self.captcha_preview.reset()
        if self.compact_active:self.ui(self.clear_preview)
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
                    self.form_loaded_at = time.monotonic()
                    if self.rotation and self.rotation.settings['mode'] == 'stalled':
                        self.verification_watch = VerificationWatch(self.form_loaded_at)
                    return
            except Exception:
                pass
            time.sleep(0.15)
        if self.running:
            raise RuntimeError("O formulário novo não terminou de carregar. Pare e tente continuar.")

    def fill_current(self, r):
        js = FILL_JS.replace("__CPF__", json.dumps(r["cpf"])).replace("__NASC__", json.dumps(r["nasc"]))
        out = self.cdp.eval(js, timeout=self.verification_watch.budget() if self.verification_watch else 10)
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
            timeout = self.verification_watch.budget() if self.verification_watch else 1
            if self.compact_active:
                first_attempt = self.captcha_preview.attempted_at is None
                status = self.captcha_preview.start(self.cdp, START_CAPTCHA_JS, timeout=timeout)
                if first_attempt and status=='pending':
                    self.ui(self.status.config, {'text':'Tentativa de clique enviada; aguardando resposta do CAPTCHA.'})
            else:
                status = self.cdp.eval(START_CAPTCHA_JS, timeout=timeout) or "waiting"
            if self.verification_watch:
                self.verification_watch.observe(status)
            return status
        except Exception:
            return "waiting"

    def click_submit(self):
        try:
            return bool(self.cdp.eval(CLICK_SUBMIT_JS))
        except Exception:
            return False

    def browser_timeout(self):
        budget = 10.0
        if (self.rotation and self.rotation.settings['mode'] == 'interval'
                and self.rotation.deadline is not None):
            budget = max(0.05, min(budget, self.rotation.deadline - time.monotonic()))
        if self.verification_watch and not self.verification_watch.started:
            budget = min(budget, self.verification_watch.budget())
        return budget

    def check_ip_change(self):
        if self.rotation:
            ip, _, available = self.ip_monitor.snapshot()
            if available:
                self.rotation.observe_ip(ip)
        if self.rotation and self.rotation.due():
            raise SwitchRequired("Intervalo atingido; alternando rede Wi-Fi.")
        if self.verification_watch and self.verification_watch.expired():
            raise SwitchRequired("Verificação não iniciou em 2 segundos; alternando rede Wi-Fi.")
        _, revision, _ = self.ip_monitor.snapshot()
        if revision != self.last_ip_revision:
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
            connection.timeout_provider = None
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

    def switch_wifi(self, advance=True):
        self.save_outputs()
        self.network_ready = False
        self.verification_watch = None
        self.close_consultation_browser()
        self.last_ip_revision = self.ip_monitor.begin()
        self.ui(self.ip_label.config, {"text": "IP público: aguardando a nova rede"})
        wifi = WindowsWifi()
        try:
            self.ui(self.status.config, {"text": "Conectando à próxima rede Wi-Fi..."})
            target = self.rotation.connect(wifi, self.network_stop, advance=advance)
        finally:
            wifi.close()
        if not self.running:
            raise Cancelled("Troca cancelada.")
        self.last_ip_revision = self.ip_monitor.begin()
        self.network_ready = True
        self.ip_monitor.wake()
        self.ui(self.network_label.config, {"text": "Wi-Fi conectado: " + target['ssid']})
        self.ui(self.status.config, {"text": "Wi-Fi conectado; reabrindo navegador e retomando consulta pendente..."})

    def worker(self):
        try:
            if not find_browser():
                raise FileNotFoundError("Microsoft Edge ou Google Chrome não encontrado.")
            # A new process is required for launch-mode flags to take effect.
            self.close_consultation_browser()
            if self.rotation.settings['mode'] != 'off':
                self.switch_wifi(advance=False)
            else:
                self.ui(self.network_label.config, {"text": "Wi-Fi: troca automática desligada"})
            while self.running:
                try:
                    self.check_ip_change()
                    self.run_queries()
                    break
                except CompactBrowserError:
                    raise
                except SwitchRequired as reason:
                    if not self.running:
                        break
                    self.log_diagnostic(str(reason))
                    self.switch_wifi()
                    continue
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
                        ip, revision, available = self.ip_monitor.snapshot()
                        if available:
                            self.rotation.observe_ip(ip)
                        if self.rotation.due():
                            self.switch_wifi()
                            break
                        if available and time.monotonic() >= retry_at:
                            self.last_ip_revision = revision
                            break
                        self.ui(self.status.config, {"text": "Aguardando conexão para reabrir o Edge e continuar..."})
                        time.sleep(0.5)
        except Cancelled:
            pass
        except Exception as error:
            self.log_diagnostic("Erro: " + str(error))
            self.ui(self.status.config, {"text": f"Erro: {error}"})
            self.ui(messagebox.showerror, "Erro", str(error))
        finally:
            if self.compact_active:
                try:
                    self.close_consultation_browser()
                except Exception as error:
                    self.log_diagnostic("Encerramento do navegador compacto: " + str(error))
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
                time.sleep(0.05)

                self.check_ip_change()
                self.service_preview()

                if not ip_retry_pending and not auto_submitted and not captcha_start_attempted:
                    started = self.start_captcha()
                    if (started in ("started", "already", "solved")
                            or (not self.verification_watch and
                                (started not in ("waiting", "pending") or time.monotonic() >= captcha_start_deadline))):
                        captcha_start_attempted = True
                        text = (("Verificação detectada. Use Ampliar se aparecer desafio."
                                 if self.compact_active else "Verificação iniciada; resolva o desafio se aparecer.")
                                if started in ("started", "already", "solved")
                                else "Sem confirmação da verificação. Clique no checkbox mostrado no painel.")
                        self.ui(self.status.config, {"text": f"{i+1}/{len(self.rows)} - {text}"})

                try:
                    res = self.cdp.eval(RESULT_JS, timeout=self.verification_watch.budget()
                                        if self.verification_watch and not self.verification_watch.started else 10) or {}
                except Exception:
                    self.check_ip_change()
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
                    ip, _, available = self.ip_monitor.snapshot()
                    if self.rotation.verification_succeeded(ip if available else None):
                        self.log_diagnostic('Contador de troca iniciado após a primeira verificação validada no IP atual.')
                    self.ui(
                        self.status.config,
                        {"text": f"{i+1}/{len(self.rows)} - CAPTCHA novo validado; enviando..."}
                    )

                    if self.click_submit():
                        auto_submitted = True
                        self.waiting_for_captcha = False
                        submitted_epoch = res.get("documentEpoch")
                        self.consumed_tokens.add(current_token)
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
        self.network_stop.set()
        self.waiting_for_captcha = False
        self.running = False
        self.save_outputs()
        self.status.config(text=f"Parado. Saídas salvas em {OUT}")

    def open_output(self):
        OUT.mkdir(exist_ok=True)
        os.startfile(str(OUT))

    def on_close(self):
        self.closing = True
        self.network_stop.set()
        self.waiting_for_captcha = False
        self.running = False
        try:
            self.save_outputs()
        finally:
            self.ip_monitor.close()
            self.root.destroy()

def main():
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
