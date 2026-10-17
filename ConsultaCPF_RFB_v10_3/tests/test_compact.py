import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_mode import browser_args
from compact_browser import click_verification
from wifi_networks import validate_settings
class Tests(unittest.TestCase):
    def test_compact_is_a_visible_app_window(self):
        args=browser_args('edge',9333,'profile','about:blank',True)
        self.assertIn('--app=about:blank',args)
        self.assertFalse(any('headless' in x for x in args))
        self.assertNotIn('--new-window',args)
        self.assertNotIn('about:blank',args)
    def test_disabled_compact_uses_normal_browser(self):
        args=browser_args('edge',9333,'profile','https://example.test',False)
        self.assertIn('--new-window',args);self.assertEqual(args[-1],'https://example.test')
        self.assertFalse(any(x.startswith('--app=') for x in args))
    def test_real_mouse_click_sequence(self):
        calls=[];scripts=[]
        def evaluate(js,**kwargs):
            scripts.append(js)
            return dict(status='click',x=28,y=39)
        cdp=SimpleNamespace(eval=evaluate,call=lambda method,params,**kw:calls.append((method,params)))
        self.assertEqual(click_verification(cdp),'started')
        self.assertEqual([p['type'] for m,p in calls],['mouseMoved','mousePressed','mouseReleased'])
        self.assertTrue(all(p['x']==28 and p['y']==39 for m,p in calls))
        self.assertIn('__cpfCaptchaStarted = true',scripts[-1])
    def test_does_not_click_absent_or_started_widget(self):
        for status in ['waiting','already','solved']:
            cdp=SimpleNamespace(eval=lambda *a,**kw:{'status':status},call=lambda *a,**kw:self.fail('unexpected click'))
            self.assertEqual(click_verification(cdp),status)
    def test_failed_click_is_not_marked_started(self):
        scripts=[]
        def evaluate(js,**kwargs):scripts.append(js);return dict(status='click',x=28,y=39)
        def call(*a,**kw):raise OSError('lost browser')
        with self.assertRaises(OSError):click_verification(SimpleNamespace(eval=evaluate,call=call))
        self.assertEqual(len(scripts),1)
    def test_setting_replaces_headless(self):
        s=validate_settings({'headless':True})
        self.assertFalse(s['compact_captcha']);self.assertNotIn('headless',s)
        self.assertTrue(validate_settings({'compact_captcha':True})['compact_captcha'])
        with self.assertRaises(ValueError):validate_settings({'compact_captcha':'yes'})
if __name__=='__main__':unittest.main()
