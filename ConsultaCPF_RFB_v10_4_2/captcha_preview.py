"""Cropped live verification images. Browser DOM, form and tokens stay intact."""
import time
import queue
import threading

PROBE_JS = r'''
(() => {
 const visible = f => {
  const r=f.getBoundingClientRect();
  if (r.width<30 || r.height<20) return false;
  for(let e=f;e;e=e.parentElement){const s=getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0)return false;}
  return true;
 };
 const box=document.querySelector('#hcaptcha iframe[src*="frame=checkbox"],.h-captcha iframe[src*="frame=checkbox"],iframe[src*="recaptcha"][src*="anchor"]');
 const challenge=[...document.querySelectorAll('iframe[src*="frame=challenge"],iframe[src*="recaptcha"][src*="bframe"]')].find(visible);
 let solved=false;
 try {solved=!!((window.hcaptcha&&hcaptcha.getResponse())||(window.grecaptcha&&grecaptcha.getResponse()));}catch(e){}
 const rect=f=>{if(!f||!visible(f))return null;const r=f.getBoundingClientRect();return {x:Math.max(0,r.left+scrollX),y:Math.max(0,r.top+scrollY),clientX:r.left,clientY:r.top,width:r.width,height:r.height};};
 return {epoch:performance.timeOrigin,box:rect(box),challenge:rect(challenge),solved:solved};
})()
'''

class CaptchaPreview:
    def __init__(self, now=time.monotonic):
        self.now=now
        self.reset()

    def reset(self):
        self.epoch=None
        self.clicked_at=None
        self.api_attempted=False
        self.next_api_at=0
        self.attempted_at=None

    def probe(self, cdp, timeout=1):
        state=cdp.eval(PROBE_JS,timeout=timeout) or {}
        if state.get('epoch')!=self.epoch:
            self.reset();self.epoch=state.get('epoch')
        return state

    def start(self, cdp, api_script, timeout=1):
        state=self.probe(cdp,timeout)
        if state.get('solved'):return 'solved'
        if state.get('challenge'):return 'started'
        if not state.get('box'):return 'waiting'
        now=self.now()
        if not self.api_attempted and now>=self.next_api_at:
            self.next_api_at=now+.2
            result=cdp.eval(api_script,timeout=timeout)
            # 'waiting' only means the provider API is not ready yet.
            # It must not permanently disable starting the verification.
            if result in ('started','already','solved','failed'):
                self.api_attempted=True
                self.attempted_at=now
        if self.clicked_at is None and (self.attempted_at is None or now-self.attempted_at>=.75):
            box=state['box']
            cdp.call('Page.bringToFront',timeout=timeout)
            dispatch_click(cdp,box['clientX']+min(28,box['width']/2),box['clientY']+box['height']/2,timeout)
            self.clicked_at=now
            if self.attempted_at is None:self.attempted_at=now
        return 'pending'

    def capture(self, cdp, expanded=False):
        state=self.probe(cdp)
        region=state.get('challenge') if expanded and state.get('challenge') else state.get('box')
        if not region:return None
        clip={key:region[key] for key in ('x','y','width','height')}
        image=cdp.call('Page.captureScreenshot',{'format':'png','clip':dict(clip,scale=1),'captureBeyondViewport':True},timeout=2)
        return dict(data=image['data'],region=region,epoch=state.get('epoch'),challenge=bool(state.get('challenge')))

def dispatch_click(cdp,x,y,timeout=1):
    for kind in ('mouseMoved','mousePressed','mouseReleased'):
        params=dict(type=kind,x=x,y=y)
        if kind!='mouseMoved':params.update(button='left',clickCount=1)
        cdp.call('Input.dispatchMouseEvent',params,timeout=timeout)

def forward_click(cdp,snapshot,x,y,image_width,image_height):
    if cdp.eval('performance.timeOrigin',timeout=1)!=snapshot['epoch']:
        return False
    box=snapshot['region']
    dispatch_click(cdp,box['clientX']+x*box['width']/image_width,
                   box['clientY']+y*box['height']/image_height)
    return True


class PreviewStream:
    """Use a separate CDP session so image capture cannot delay input/results."""
    def __init__(self, url, factory, active, expanded, interval=.5):
        self.url,self.factory,self.active,self.expanded=url,factory,active,expanded
        self.interval=interval
        self.stop=threading.Event()
        self.frames=queue.Queue(maxsize=1)
        self.connection=None
        self.last_error=None
        self.thread=threading.Thread(target=self.run,daemon=True)
        self.thread.start()

    def run(self):
        try:
            connection=self.factory(self.url)
            self.connection=connection
            if self.stop.is_set():return
            view=CaptchaPreview()
            while not self.stop.is_set():
                if not self.active():
                    self.stop.wait(.05)
                    continue
                started=time.monotonic()
                try:
                    frame=view.capture(connection,self.expanded())
                    if frame and not self.stop.is_set():
                        try:self.frames.get_nowait()
                        except queue.Empty:pass
                        self.frames.put_nowait(frame)
                    self.last_error=None
                except Exception as error:
                    self.last_error=type(error).__name__
                self.stop.wait(max(.05,self.interval-(time.monotonic()-started)))
        except Exception as error:
            self.last_error=type(error).__name__
        finally:
            if self.connection:
                try:self.connection.sock.close()
                except OSError:pass

    def take(self):
        try:return self.frames.get_nowait()
        except queue.Empty:return None

    def close(self):
        self.stop.set()
        if self.connection:
            try:self.connection.sock.shutdown(2)
            except OSError:pass
        if threading.current_thread()!=self.thread:self.thread.join(timeout=.2)
