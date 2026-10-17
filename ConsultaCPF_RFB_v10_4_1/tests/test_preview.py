import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_mode import browser_args
from captcha_preview import CaptchaPreview, forward_click
from wifi_networks import validate_settings

def state(**kwargs):
    result=dict(epoch=1,box=dict(x=300,y=80,clientX=300,clientY=80,width=304,height=78),challenge=None,solved=False)
    result.update(kwargs);return result
class Tests(unittest.TestCase):
    def test_compact_uses_offscreen_visible_browser(self):
        args=browser_args('edge',9333,'profile','about:blank',True)
        self.assertIn('--window-position=-32000,-32000',args)
        self.assertFalse(any('headless' in arg for arg in args))
    def test_normal_browser_is_still_available(self):
        self.assertIn('--new-window',browser_args('edge',9333,'p','url',False))
    def test_click_dispatch_is_pending_not_confirmed(self):
        calls=[];cdp=SimpleNamespace(eval=lambda *a,**k:state(),call=lambda *a,**k:calls.append(a))
        view=CaptchaPreview()
        self.assertEqual(view.start(cdp,'api'),'pending')
        self.assertEqual([x[1]['type'] for x in calls if x[0]=='Input.dispatchMouseEvent'],['mouseMoved','mousePressed','mouseReleased'])
        count=len(calls);self.assertEqual(view.start(cdp,'api'),'pending');self.assertEqual(len(calls),count)
    def test_confirmed_challenge_or_token_is_progress(self):
        for values,expected in [(dict(solved=True),'solved'),(dict(challenge={'width':330}),'started')]:
            cdp=SimpleNamespace(eval=lambda *a,**k:state(**values),call=lambda *a,**k:self.fail('no new click'))
            self.assertEqual(CaptchaPreview().start(cdp,'api'),expected)
    def test_api_call_is_not_confirmation(self):
        clock=[0];scripts=[]
        def evaluate(js,**k):scripts.append(js);return state()
        cdp=SimpleNamespace(eval=evaluate,call=lambda *a,**k:None)
        view=CaptchaPreview(now=lambda:clock[0]);view.start(cdp,'api');clock[0]=2
        self.assertEqual(view.start(cdp,'api'),'pending');self.assertIn('api',scripts)
    def test_capture_is_only_the_widget_rectangle(self):
        calls=[]
        def call(method,params,**kw):calls.append(params);return {'data':'png'}
        cdp=SimpleNamespace(eval=lambda *a,**k:state(),call=call)
        snapshot=CaptchaPreview().capture(cdp)
        self.assertEqual(calls[0]['clip'],dict(x=300,y=80,width=304,height=78,scale=1))
        self.assertEqual(snapshot['epoch'],1)
    def test_expanded_capture_selects_challenge_only(self):
        challenge=dict(x=100,y=100,clientX=100,clientY=100,width=350,height=500)
        cdp=SimpleNamespace(eval=lambda *a,**k:state(challenge=challenge),call=lambda *a,**k:{'data':'png'})
        self.assertEqual(CaptchaPreview().capture(cdp,True)['region'],challenge)
    def test_pointer_mapping_and_stale_page_rejection(self):
        snapshot=dict(epoch=1,region=state()['box']);calls=[]
        cdp=SimpleNamespace(eval=lambda *a,**k:1,call=lambda *a,**k:calls.append(a))
        self.assertTrue(forward_click(cdp,snapshot,14,20,152,39))
        self.assertEqual(calls[0][1]['x'],328)
        self.assertEqual(calls[0][1]['y'],120)
        cdp.eval=lambda *a,**k:2
        before=len(calls);self.assertFalse(forward_click(cdp,snapshot,14,20,152,39));self.assertEqual(len(calls),before)
    def test_old_headless_setting_is_ignored(self):
        self.assertNotIn('headless',validate_settings({'headless':True}))
        self.assertTrue(validate_settings({'compact_captcha':True})['compact_captcha'])
if __name__=='__main__':unittest.main()
