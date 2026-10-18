import json
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wifi_networks import (Rotation, VerificationWatch, SwitchRequired, Cancelled,
                           validate_settings, save_settings, load_settings)
from consulta_cpf_rfb import App, CDP
from ip_monitor import IPMonitor

def settings(mode='interval'):
    return dict(mode=mode,interval=10,interface='adapter',networks=[
        dict(ssid='WiFi Casa',profile='WiFi Casa'),dict(ssid='WiFi Celular',profile='WiFi Celular')])

class FakeWifi:
    def __init__(self, current='WiFi Casa'): self.profile=current;self.calls=[]
    def current(self,key): return self.profile
    def connect(self,key,profile,stop):
        if stop.is_set(): raise Cancelled()
        self.calls.append(profile);self.profile=profile
    def close(self): pass

class Tests(unittest.TestCase):
    def test_round_robin_uses_real_current_profile(self):
        r=Rotation(settings());wifi=FakeWifi();stop=threading.Event()
        self.assertEqual(r.connect(wifi,stop)['ssid'],'WiFi Celular')
        self.assertEqual(r.connect(wifi,stop)['ssid'],'WiFi Casa')
        self.assertEqual(wifi.calls,['WiFi Celular','WiFi Casa'])
    def test_start_keeps_current_configured_network(self):
        r=Rotation(settings());wifi=FakeWifi('WiFi Celular')
        self.assertEqual(r.connect(wifi,threading.Event(),advance=False)['ssid'],'WiFi Celular')
        self.assertEqual(wifi.calls,[])
    def test_unknown_network_enters_first_configured(self):
        r=Rotation(settings());wifi=FakeWifi('Other')
        self.assertEqual(r.connect(wifi,threading.Event(),False)['ssid'],'WiFi Casa')
        self.assertEqual(wifi.calls,['WiFi Casa'])
    def test_interval_waits_for_verification_after_each_connection(self):
        clock=[0];r=Rotation(settings(),now=lambda:clock[0])
        clock[0]=100;self.assertFalse(r.due())
        self.assertTrue(r.verification_succeeded('203.0.113.1'))
        clock[0]=109.9;self.assertFalse(r.due());clock[0]=110;self.assertTrue(r.due())
        wifi=FakeWifi();r.connect(wifi,threading.Event())
        clock[0]=1000;self.assertFalse(r.due())
        r.verification_succeeded('203.0.113.2')
        clock[0]=1009.9;self.assertFalse(r.due());clock[0]=1010;self.assertTrue(r.due())
    def test_later_verifications_do_not_extend_timer(self):
        clock=[0];r=Rotation(settings(),now=lambda:clock[0])
        r.verification_succeeded('203.0.113.1');clock[0]=8
        self.assertFalse(r.verification_succeeded('203.0.113.1'))
        clock[0]=10;self.assertTrue(r.due())
    def test_new_ip_waits_for_first_valid_verification(self):
        clock=[0];r=Rotation(settings(),now=lambda:clock[0])
        r.verification_succeeded('203.0.113.1');clock[0]=5
        r.observe_ip('203.0.113.2');clock[0]=50;self.assertFalse(r.due())
        r.verification_succeeded('203.0.113.2');clock[0]=60;self.assertTrue(r.due())
    def test_first_ip_read_after_verification_keeps_timer(self):
        clock=[0];r=Rotation(settings(),now=lambda:clock[0])
        r.verification_succeeded();clock[0]=5;r.observe_ip('203.0.113.1')
        clock[0]=10;self.assertTrue(r.due())
    def test_unarmed_timer_does_not_limit_browser_wait(self):
        app=App.__new__(App);app.rotation=Rotation(settings());app.verification_watch=None
        self.assertEqual(app.browser_timeout(),10)
    def test_failed_switch_does_not_advance_timer_or_label(self):
        clock=[0];r=Rotation(settings(),now=lambda:clock[0]);r.verification_succeeded();clock[0]=11
        wifi=FakeWifi();wifi.connect=lambda *args: (_ for _ in ()).throw(OSError('unavailable'))
        with self.assertRaises(OSError):r.connect(wifi,threading.Event())
        self.assertTrue(r.due());self.assertEqual(r.label,'')
    def test_cancel_stops_switch(self):
        stop=threading.Event();stop.set();r=Rotation(settings())
        with self.assertRaises(Cancelled):r.connect(FakeWifi(),stop)
    def test_watch_exact_two_seconds(self):
        clock=[100];w=VerificationWatch(100,now=lambda:clock[0])
        w.observe('waiting');clock[0]=101.999;self.assertFalse(w.expired())
        clock[0]=102;self.assertTrue(w.expired())
    def test_open_challenge_never_times_out_waiting_for_human(self):
        clock=[0];w=VerificationWatch(0,now=lambda:clock[0]);w.observe('started')
        clock[0]=10000;self.assertFalse(w.expired())
    def test_failed_start_is_not_success(self):
        clock=[0];w=VerificationWatch(0,now=lambda:clock[0]);w.observe('failed')
        clock[0]=2;self.assertTrue(w.expired())
    def test_two_different_saved_profiles_required(self):
        s=settings();s['networks'][1]['profile']='WiFi Casa'
        with self.assertRaises(ValueError):validate_settings(s)
        s=settings();s['networks'].pop()
        with self.assertRaises(ValueError):validate_settings(s)
    def test_reject_invalid_interval(self):
        for value in [0,-1,'nan','inf','bad']:
            with self.subTest(value=value):
                s=settings();s['interval']=value
                with self.assertRaises(ValueError):validate_settings(s)
    def test_config_round_trip_unicode_and_no_password(self):
        s=settings();s['networks'][0]['ssid']='Rede família'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'wifi.json';save_settings(path,s)
            self.assertEqual(load_settings(path)['networks'][0]['ssid'],'Rede família')
            self.assertNotIn('password',path.read_text());self.assertFalse(path.with_suffix('.tmp').exists())
    def test_modes_do_not_mix_interval_and_watchdog(self):
        r=Rotation(settings('stalled'),now=lambda:100)
        r.deadline=0;self.assertFalse(r.due())
        r=Rotation(dict(mode='off',interval=1,interface='',networks=[]),now=lambda:100)
        r.deadline=0;self.assertFalse(r.due())
    def test_app_checks_watchdog_before_ip_monitor(self):
        app=App.__new__(App);app.rotation=Rotation(settings('stalled'))
        app.ip_monitor=SimpleNamespace(snapshot=lambda:(None,0,False))
        app.verification_watch=VerificationWatch(0,now=lambda:2)
        with self.assertRaises(SwitchRequired):app.check_ip_change()
    def test_switch_closes_browser_before_connection_and_preserves_rows(self):
        app=App.__new__(App);events=[]
        app.rows=[{'status':'REGULAR'},{'status':''}];before=[dict(x) for x in app.rows]
        app.rotation=Rotation(settings());app.network_stop=threading.Event();app.running=True
        app.ip_monitor=IPMonitor(lambda:False);app.ip_monitor.record('177.223.38.57')
        app.save_outputs=lambda:events.append('save')
        app.close_consultation_browser=lambda:events.append('close')
        app.ui=lambda *args:None
        app.ip_label=app.network_label=app.status=SimpleNamespace(config=lambda **kw:None)
        wifi=FakeWifi()
        def connect(key,profile,stop): events.append('connect');wifi.profile=profile
        wifi.connect=connect
        try:
            with patch('consulta_cpf_rfb.WindowsWifi',return_value=wifi):app.switch_wifi()
            self.assertEqual(events,['save','close','connect'])
            self.assertEqual(app.rows,before);self.assertTrue(app.network_ready)
            self.assertIsNone(app.ip_monitor.snapshot()[0])
        finally:app.ip_monitor.close();app.ip_monitor.thread.join(2)
    def test_deadline_budget_limits_browser_calls(self):
        app=App.__new__(App);app.rotation=Rotation(settings())
        app.rotation.deadline=time.monotonic()+.1;app.verification_watch=None
        self.assertLessEqual(app.browser_timeout(),.1)
        app.rotation.deadline=0
        self.assertEqual(app.browser_timeout(),.05)
    def test_ssid_is_not_replaced_by_a_nickname_or_trimmed(self):
        s=settings();s['networks'][0]=dict(ssid=' Minha Rede ',profile='perfil-renomeado')
        checked=validate_settings(s)
        self.assertEqual(checked['networks'][0],dict(ssid=' Minha Rede ',profile='perfil-renomeado'))

    def test_quiet_cdp_respects_short_timeout(self):
        left,right=socket.socketpair();left.settimeout(10)
        cdp=CDP.__new__(CDP);cdp.sock=left;cdp.seq=0;cdp._buffer=b'';cdp._fragment=bytearray()
        try:
            start=time.monotonic()
            with self.assertRaises(TimeoutError):cdp.call('Runtime.evaluate',{},timeout=.1)
            self.assertLess(time.monotonic()-start,.5)
            self.assertEqual(left.gettimeout(),10)
        finally:left.close();right.close()

if __name__ == '__main__':
    unittest.main()
