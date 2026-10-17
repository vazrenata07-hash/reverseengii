"""Visible verification viewport and a normal mouse click through CDP."""
CAPTCHA_VIEW_JS = r'''
(() => {
 const install = () => {
  if (!document.documentElement || document.getElementById('cpf-captcha-view')) return;
  const s = document.createElement('style'); s.id = 'cpf-captcha-view';
  s.textContent = `
   html,body { margin:0!important; padding:0!important; overflow:hidden!important; background:white!important; }
   body,body * { color:transparent!important; text-shadow:none!important; }
   body *:not(iframe):not(:has(iframe[src*="hcaptcha"],iframe[src*="recaptcha"],iframe[src*="frame=checkbox"])) {
     opacity:0!important; pointer-events:none!important;
   }
   iframe:not([src*="hcaptcha"]):not([src*="recaptcha"]):not([src*="frame=checkbox"]) {
     opacity:0!important; pointer-events:none!important;
   }
   .h-captcha,#hcaptcha,.g-recaptcha {
     position:fixed!important; left:8px!important; top:8px!important;
     margin:0!important; padding:0!important; z-index:2147483000!important;
   }
   iframe[src*="frame=checkbox"],iframe[src*="recaptcha"][src*="anchor"] {
     position:fixed!important;left:8px!important;top:8px!important;
     margin:0!important;border:0!important;opacity:1!important;pointer-events:auto!important;
   }
  `;
  document.documentElement.appendChild(s);
 };
 install(); new MutationObserver(install).observe(document,{childList:true,subtree:true});
})()
'''

CHECKBOX_JS = r'''
(() => {
 if (window.__cpfCaptchaStarted) return {status:'already'};
 try {
  if (window.hcaptcha && hcaptcha.getResponse()) return {status:'solved'};
  if (window.grecaptcha && grecaptcha.getResponse()) return {status:'solved'};
 } catch(e) {}
 const f=document.querySelector('#hcaptcha iframe[src*="frame=checkbox"],.h-captcha iframe[src*="frame=checkbox"],iframe[src*="recaptcha"][src*="anchor"]');
 if (!f) return {status:'waiting'};
 const r=f.getBoundingClientRect(), s=getComputedStyle(f);
 if (r.width<40 || r.height<30 || s.display==='none' || s.visibility==='hidden') return {status:'waiting'};
 const x=r.left+Math.min(28,r.width/2),y=r.top+r.height/2;
 if (x<0 || y<0 || x>=innerWidth || y>=innerHeight) return {status:'waiting'};
 return {status:'click',x:x,y:y};
})()
'''

def click_verification(cdp, timeout=1):
    point = cdp.eval(CHECKBOX_JS, timeout=timeout) or {}
    if point.get('status') != 'click':
        return point.get('status', 'waiting')
    coords = dict(x=point['x'], y=point['y'])
    cdp.call('Input.dispatchMouseEvent', dict(type='mouseMoved', **coords), timeout=timeout)
    cdp.call('Input.dispatchMouseEvent', dict(type='mousePressed', button='left', clickCount=1, **coords), timeout=timeout)
    cdp.call('Input.dispatchMouseEvent', dict(type='mouseReleased', button='left', clickCount=1, **coords), timeout=timeout)
    cdp.eval('window.__cpfCaptchaStarted = true', timeout=timeout)
    return 'started'
