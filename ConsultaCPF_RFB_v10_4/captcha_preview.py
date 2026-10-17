"""Cropped live verification images. Browser DOM, form and tokens stay intact."""
import time

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
        if self.clicked_at is None:
            box=state['box']
            # Sending input is only an attempt, never evidence of success.
            cdp.call('Page.bringToFront',timeout=timeout)
            dispatch_click(cdp,box['clientX']+min(28,box['width']/2),box['clientY']+box['height']/2,timeout)
            self.clicked_at=self.now()
        elif not self.api_attempted and self.now()-self.clicked_at>=.75:
            self.api_attempted=True
            cdp.eval(api_script,timeout=timeout)
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
