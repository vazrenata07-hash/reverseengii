"""Saved Windows WLAN profiles and the consultation's network rotation policy."""
import ctypes as C
import json
import os
import time
from pathlib import Path

U32 = C.c_uint32
class GUID(C.Structure):
    _fields_ = [('a', U32), ('b', C.c_uint16), ('c', C.c_uint16), ('d', C.c_ubyte * 8)]
    def key(self):
        return bytes(self).hex()
class Interface(C.Structure):
    _fields_ = [('guid', GUID), ('description', C.c_wchar * 256), ('state', U32)]
class Profile(C.Structure):
    _fields_ = [('name', C.c_wchar * 256), ('flags', U32)]
class SSID(C.Structure):
    _fields_ = [('length', U32), ('data', C.c_ubyte * 32)]
class AvailableNetwork(C.Structure):
    _fields_ = [('profile', C.c_wchar * 256), ('ssid', SSID), ('bss_type', U32),
                ('bssids', U32), ('connectable', U32), ('reason', U32),
                ('phy_count', U32), ('phy_types', U32 * 8), ('more_phy', U32),
                ('quality', U32), ('security', U32), ('auth', U32), ('cipher', U32),
                ('flags', U32), ('reserved', U32)]
class Connection(C.Structure):
    # Only the fixed prefix of WLAN_CONNECTION_ATTRIBUTES is read.
    _fields_ = [('state', U32), ('mode', U32), ('profile', C.c_wchar * 256)]
class Parameters(C.Structure):
    _fields_ = [('mode', U32), ('profile', C.c_wchar_p), ('ssid', C.c_void_p),
                ('bssids', C.c_void_p), ('bss_type', U32), ('flags', U32)]

class Cancelled(RuntimeError):
    pass
class SwitchRequired(RuntimeError):
    pass

class WindowsWifi:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Troca de Wi-Fi disponível apenas no Windows.')
        self.api = C.WinDLL('wlanapi.dll')
        ptr = C.c_void_p
        self.api.WlanOpenHandle.argtypes = [U32, ptr, C.POINTER(U32), C.POINTER(ptr)]
        self.api.WlanCloseHandle.argtypes = [ptr, ptr]
        self.api.WlanEnumInterfaces.argtypes = [ptr, ptr, C.POINTER(ptr)]
        self.api.WlanGetProfileList.argtypes = [ptr, C.POINTER(GUID), ptr, C.POINTER(ptr)]
        self.api.WlanGetProfile.argtypes = [ptr, C.POINTER(GUID), C.c_wchar_p, ptr,
                                            C.POINTER(ptr), C.POINTER(U32), C.POINTER(U32)]
        self.api.WlanGetAvailableNetworkList.argtypes = [ptr, C.POINTER(GUID), U32, ptr, C.POINTER(ptr)]
        self.api.WlanQueryInterface.argtypes = [ptr, C.POINTER(GUID), U32, ptr,
                                               C.POINTER(U32), C.POINTER(ptr), C.POINTER(U32)]
        self.api.WlanConnect.argtypes = [ptr, C.POINTER(GUID), C.POINTER(Parameters), ptr]
        self.api.WlanFreeMemory.argtypes = [ptr]
        for name in ('WlanOpenHandle', 'WlanCloseHandle', 'WlanEnumInterfaces',
                     'WlanGetProfileList', 'WlanGetProfile', 'WlanGetAvailableNetworkList',
                     'WlanQueryInterface', 'WlanConnect'):
            getattr(self.api, name).restype = U32
        self.api.WlanFreeMemory.restype = None
        self.handle = ptr()
        version = U32()
        self.check(self.api.WlanOpenHandle(2, None, C.byref(version), C.byref(self.handle)))

    @staticmethod
    def check(code):
        if code == 5:
            raise OSError('O Windows negou acesso ao Wi-Fi. Confira as permissões de localização '
                          'para aplicativos de desktop nas Configurações do Windows.')
        if code:
            raise OSError(code, C.FormatError(code))

    def close(self):
        if self.handle:
            self.api.WlanCloseHandle(self.handle, None)
            self.handle = None

    def interfaces(self):
        data = C.c_void_p()
        self.check(self.api.WlanEnumInterfaces(self.handle, None, C.byref(data)))
        try:
            count = U32.from_address(data.value).value
            return [Interface.from_buffer_copy(C.string_at(data.value + 8 + n * C.sizeof(Interface), C.sizeof(Interface)))
                    for n in range(count)]
        finally:
            self.api.WlanFreeMemory(data)

    def interface(self, key):
        for item in self.interfaces():
            if item.guid.key() == key:
                return item
        raise OSError('Adaptador Wi-Fi não encontrado. Abra Settings e selecione novamente.')

    def profiles(self, key):
        item = self.interface(key)
        data = C.c_void_p()
        self.check(self.api.WlanGetProfileList(self.handle, C.byref(item.guid), None, C.byref(data)))
        try:
            count = U32.from_address(data.value).value
            return [Profile.from_address(data.value + 8 + n * C.sizeof(Profile)).name for n in range(count)]
        finally:
            self.api.WlanFreeMemory(data)

    def saved_networks(self, key):
        # No plaintext-key flag is requested. Only SSID metadata is extracted;
        # profile XML and any encrypted key material are never stored or logged.
        import xml.etree.ElementTree as ET
        item = self.interface(key)
        result = []
        for name in self.profiles(key):
            data, flags, access = C.c_void_p(), U32(0), U32()
            self.check(self.api.WlanGetProfile(self.handle, C.byref(item.guid), name, None,
                                               C.byref(data), C.byref(flags), C.byref(access)))
            try:
                root = ET.fromstring(C.wstring_at(data.value))
                node = root.find('.//{*}SSID/{*}hex')
                if node is not None and node.text:
                    ssid = bytes.fromhex(node.text).decode('utf-8', errors='replace')
                else:
                    node = root.find('.//{*}SSID/{*}name')
                    ssid = node.text if node is not None else name
                result.append(dict(ssid=ssid, profile=name))
            finally:
                self.api.WlanFreeMemory(data)
        return result

    def available(self, key):
        item = self.interface(key)
        data = C.c_void_p()
        self.check(self.api.WlanGetAvailableNetworkList(self.handle, C.byref(item.guid), 0, None, C.byref(data)))
        try:
            count = U32.from_address(data.value).value
            names = []
            for n in range(count):
                value = AvailableNetwork.from_address(data.value + 8 + n * C.sizeof(AvailableNetwork))
                ssid = bytes(value.ssid.data[:min(value.ssid.length, 32)]).decode('utf-8', errors='replace')
                if ssid and ssid not in names:
                    names.append(ssid)
            return names
        finally:
            self.api.WlanFreeMemory(data)

    def current(self, key):
        item = self.interface(key)
        data = C.c_void_p()
        size, kind = U32(), U32()
        code = self.api.WlanQueryInterface(self.handle, C.byref(item.guid), 7, None,
                                          C.byref(size), C.byref(data), C.byref(kind))
        if code == 5023:  # ERROR_INVALID_STATE: disconnected
            return None
        self.check(code)
        try:
            value = Connection.from_address(data.value)
            return value.profile if value.state == 1 else None
        finally:
            self.api.WlanFreeMemory(data)

    def connect(self, key, profile, stop, timeout=25):
        item = self.interface(key)
        if profile not in self.profiles(key):
            raise OSError('Perfil Wi-Fi não salvo neste adaptador: ' + profile)
        if stop.is_set():
            raise Cancelled('Troca de rede cancelada.')
        params = Parameters(0, profile, None, None, 3, 0)
        self.check(self.api.WlanConnect(self.handle, C.byref(item.guid), C.byref(params), None))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if stop.is_set():
                raise Cancelled('Troca de rede cancelada.')
            if self.current(key) == profile:
                return
            stop.wait(0.2)
        raise OSError('O Windows não confirmou conexão ao perfil ' + profile + '. Confira sinal e credenciais salvas.')

DEFAULTS = dict(mode='off', interval=60, interface='', networks=[], headless=False)

def validate_settings(value):
    mode = value.get('mode', 'off')
    if mode not in ('off', 'interval', 'stalled'):
        raise ValueError('Modo de troca inválido.')
    interval = float(value.get('interval', 60))
    import math
    if not math.isfinite(interval) or interval < 1:
        raise ValueError('Informe um intervalo de pelo menos 1 segundo.')
    networks = []
    for item in value.get('networks', []):
        ssid, profile = str(item.get('ssid', '')), str(item.get('profile', ''))
        if not ssid or not profile:
            raise ValueError('Preencha o nome real (SSID) de cada rede salva no Windows.')
        if any(n['profile'] == profile or n['ssid'] == ssid for n in networks):
            raise ValueError('Adicione redes Wi-Fi diferentes, sem repetir o mesmo SSID.')
        networks.append(dict(ssid=ssid, profile=profile))
    interface = str(value.get('interface', ''))
    if mode != 'off' and (not interface or len(networks) < 2):
        raise ValueError('Selecione um adaptador e adicione pelo menos dois perfis Wi-Fi diferentes.')
    headless = value.get('headless', False)
    if not isinstance(headless, bool):
        raise ValueError('Modo sem janela inválido.')
    return dict(mode=mode, interval=interval, interface=interface, networks=networks, headless=headless)

def load_settings(path):
    try:
        return validate_settings(json.loads(Path(path).read_text(encoding='utf-8')))
    except FileNotFoundError:
        return dict(DEFAULTS)

def save_settings(path, settings):
    value = validate_settings(settings)
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)
    return value

class Rotation:
    def __init__(self, settings, now=time.monotonic):
        self.settings = validate_settings(settings)
        self.now = now
        self.deadline = now() + self.settings['interval']
        self.label = ''

    def due(self):
        return self.settings['mode'] == 'interval' and self.now() >= self.deadline

    def connect(self, wifi, stop, advance=True):
        key = self.settings['interface']
        current = wifi.current(key)
        networks = self.settings['networks']
        index = next((n for n, item in enumerate(networks) if item['profile'] == current), None)
        if index is None:
            target = networks[0]
        else:
            target = networks[(index + int(advance)) % len(networks)]
        if current != target['profile']:
            wifi.connect(key, target['profile'], stop)
        if stop.is_set():
            raise Cancelled('Troca cancelada.')
        # connect() confirms the profile before the timer can restart.
        self.label = target['ssid']
        self.deadline = self.now() + self.settings['interval']
        return target

class VerificationWatch:
    def __init__(self, loaded_at, now=time.monotonic):
        self.deadline = loaded_at + 2.0
        self.now = now
        self.started = False

    def observe(self, status):
        if status in ('started', 'already', 'solved'):
            self.started = True

    def expired(self):
        return not self.started and self.now() >= self.deadline

    def budget(self):
        return max(0.05, min(0.5, self.deadline - self.now()))
