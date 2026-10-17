"""Observe public IPv4 changes; failures never count as a changed address."""
import ipaddress
import json
import threading
import time
import urllib.request


def fetch_public_ip():
    # Each check gets a fresh connection so route/VPN changes are observable.
    request = urllib.request.Request('https://api.ipify.org/?format=json',
        headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=4) as response:
        value = json.loads(response.read(1024))['ip']
    address = ipaddress.IPv4Address(value)
    return str(address)


class IPMonitor:
    def __init__(self, active, fetch=fetch_public_ip, interval=1):
        self.active, self.fetch, self.interval = active, fetch, interval
        self.lock = threading.Lock()
        self.ip = None
        self.revision = 0
        self.available = False
        self.reference = None
        self.epoch = 0
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def begin(self):
        with self.lock:
            self.epoch += 1
            self.reference = None
            self.ip = None
            self.available = False
            return self.revision

    def record(self, ip, epoch=None):
        normalized = str(ipaddress.IPv4Address(ip))
        with self.lock:
            if epoch is not None and epoch != self.epoch:
                return
            if self.reference is not None and normalized != self.reference:
                self.revision += 1
            self.reference = normalized
            self.ip, self.available = normalized, True

    def snapshot(self):
        with self.lock:
            return self.ip, self.revision, self.available

    def wake(self):
        self.wake_event.set()

    def run(self):
        while not self.stop_event.is_set():
            started = time.monotonic()
            if self.active():
                with self.lock:
                    epoch = self.epoch
                try:
                    value = self.fetch()
                    if self.active():
                        self.record(value, epoch)
                except Exception:
                    with self.lock:
                        if epoch == self.epoch:
                            self.available = False
            self.wake_event.wait(max(0.1, self.interval - (time.monotonic() - started)))
            self.wake_event.clear()

    def close(self):
        self.stop_event.set()
        self.wake_event.set()
