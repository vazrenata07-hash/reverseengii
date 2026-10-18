import queue
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from captcha_preview import CaptchaPreview, PreviewStream, PROBE_JS
from consulta_cpf_rfb import App

def state():return dict(epoch=1,solved=False,challenge=None,box=dict(x=0,y=0,clientX=0,clientY=0,width=304,height=78))
class Tests(unittest.TestCase):
    def test_api_not_ready_is_retried_when_ready(self):
        clock=[0];results=iter(['waiting','started']);calls=[]
        def evaluate(script,**kw):
            if script==PROBE_JS:return state()
            calls.append(script);return next(results)
        cdp=SimpleNamespace(eval=evaluate,call=lambda *a,**k:None)
        view=CaptchaPreview(now=lambda:clock[0])
        self.assertEqual(view.start(cdp,'official_api'),'pending')
        self.assertFalse(view.api_attempted)
        clock[0]=.2
        self.assertEqual(view.start(cdp,'official_api'),'pending')
        self.assertTrue(view.api_attempted)
        clock[0]=2;view.start(cdp,'official_api')
        self.assertEqual(calls,['official_api','official_api'])
    def test_official_start_is_attempted_immediately(self):
        calls=[]
        def evaluate(script,**kw):return state() if script==PROBE_JS else 'started'
        cdp=SimpleNamespace(eval=evaluate,call=lambda *a,**kw:calls.append(a))
        view=CaptchaPreview(now=lambda:0)
        self.assertEqual(view.start(cdp,'official_api'),'pending')
        self.assertTrue(view.api_attempted)
        self.assertEqual(calls,[])
    def test_slow_image_does_not_block_manual_click_processing(self):
        entered=threading.Event();release=threading.Event()
        def capture(*a,**kw):entered.set();release.wait(2);return None
        connection=SimpleNamespace(sock=SimpleNamespace(shutdown=lambda *a:release.set(),close=lambda:None))
        with patch('captcha_preview.CaptchaPreview.capture',capture):
            stream=PreviewStream('ws',lambda url:connection,lambda:True,lambda:False)
            try:
                self.assertTrue(entered.wait(1))
                app=App.__new__(App);app.compact_active=True;app.cdp=object();app.preview_clicks=queue.Queue()
                app.preview_clicks.put(('snapshot',1,2,304,78))
                with patch('consulta_cpf_rfb.forward_click') as click:
                    app.service_preview()
                    click.assert_called_once_with(app.cdp,'snapshot',1,2,304,78)
                self.assertFalse(release.is_set(),'Capture must still be blocked while the click was processed')
            finally:
                release.set();stream.close()
            self.assertFalse(stream.thread.is_alive())
if __name__=='__main__':unittest.main()
