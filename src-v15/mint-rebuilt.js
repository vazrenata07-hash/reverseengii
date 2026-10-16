(function(){
'use strict';
if(window.top!==window||window.__mintRebuilt15)return;
var host=location.hostname.toLowerCase();
if(host!=='888pg.cc'&&host.slice(-9)!=='.888pg.cc')return;
window.__mintRebuilt15=1;
var d=document,tag='data-mint15-hidden',style=d.createElement('style');
style.textContent='['+tag+'="1"]{display:none!important;visibility:hidden!important;pointer-events:none!important}';
var fast='[class*="_fastBtn_"],[class*="_fastBackground_"],[class*="_fastImg_"],[class*="_closeIcon_3tzh2_"],[class*="_3tzh2_"]';
var security='iframe,canvas,[role="slider"],[class*="captcha" i],[id*="captcha" i],[class*="geetest" i],[class*="verify" i],[class*="yidun" i],[class*="turnstile" i],[class*="hcaptcha" i],[class*="puzzle" i]';
// Only the reported component is an unconditional reward exception.
var rewards=fast;
var closeQuery='[class*="close" i],[aria-label*="fechar" i],[aria-label*="close" i],img[src*="close" i],button,[role="button"]';
var inputs='input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])';
var protectedRoots=[],rewardRoots=[],username='',wasRegister=false,visit=0,written=new WeakMap(),passwordWritten=new WeakSet();
function register(){return /(?:^|[\/#])register(?:[\/?#]|$)/i.test(location.pathname+location.hash)}
function accountFlow(){return /(?:^|[\/#])(?:register|login|signup|signin|verify|captcha)(?:[\/?#]|$)/i.test(location.pathname+location.hash)}
function randomName(){var abc='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',s='',a=new Uint8Array(32);while(s.length<15){crypto.getRandomValues(a);for(var i=0;i<a.length&&s.length<15;i++)if(a[i]<248)s+=abc[a[i]%62]}return s}
function route(){var reg=register();if(reg&&!wasRegister){username=randomName();visit++}wasRegister=reg;return reg}
function protectedText(el){return /b[oô]nus de (?:login|aposta)|captcha|verifica[çc][aã]o|arraste|deslize/.test((el.textContent||'').toLowerCase())||(!promotion(el)&&/\babrir\b/i.test(el.textContent||''))}
function promotion(el){
 var text=(el.textContent||'').replace(/\s+/g,' ').toLowerCase();
 return /cadastro conclu[ií]do|deposite agora/.test(text)||
 (/clube vip/.test(text)&&/convidar amigos|n[aã]o mostrar novamente/.test(text))||
 (/sorteio/.test(text)&&/escolha um pr[eê]mio|ativar/.test(text));
}
function has(el,selector){return el.matches(selector)||!!el.querySelector(selector)}
function locateScope(el){
 var node=el,scope=el;
 while(node&&node!==d.body&&node!==d.documentElement){
  // Stop at the app, not at a count of close icons: responsive dialogs can
  // carry several hidden desktop/mobile versions of the same close control.
  if(node.matches('#app,#root,main,[role="main"]')||promotion(node))break;
  var pos=getComputedStyle(node).position;
  var dialog=node.matches('[role="dialog"],[aria-modal="true"],.ui-overlay');
  if(dialog||pos==='fixed'||pos==='absolute'){
   scope=node;
   var controls=node.querySelectorAll(closeQuery);
   for(var i=0;i<controls.length;i++)if(isClose(controls[i]))return scope;
  }
  node=node.parentElement;
 }
 return scope;
}
function rewardText(value){return /b[oô]nus de (?:login|aposta)/i.test(value)||/^\s*abrir\s*$/i.test(value)}
function snapshotProtection(){
 protectedRoots=[];rewardRoots=[];
 var nodes=d.querySelectorAll(rewards);
 for(var i=0;i<nodes.length;i++)rewardRoots.push(locateScope(nodes[i]));
 var secure=d.querySelectorAll(security);
 for(var k=0;k<secure.length;k++)protectedRoots.push(locateScope(secure[k]));
 // Labels, artwork and the close hit area can be siblings. Resolve the whole
 // reward before classifying any close control, regardless of DOM order.
 var walker=d.createTreeWalker(d.body||d.documentElement,NodeFilter.SHOW_TEXT),text;
 while((text=walker.nextNode())){
  var parent=text.parentElement;
  if(parent&&!parent.matches('script,style')&&rewardText(text.nodeValue))rewardRoots.push(locateScope(parent));
 }
 protectedRoots=protectedRoots.concat(rewardRoots);
}
function preserve(el){
 if(has(el,rewards+','+security+','+inputs)||protectedText(el))return true;
 for(var i=0;i<protectedRoots.length;i++)if(el===protectedRoots[i]||el.contains(protectedRoots[i])||protectedRoots[i].contains(el))return true;
 return false;
}
function isClose(el){var text=(el.textContent||'').trim();return /close|fechar|dismiss/i.test([el.getAttribute('class'),el.getAttribute('aria-label'),el.getAttribute('src')].join(' '))||/^[×✕✖xX]$/.test(text)}
function candidate(close){
 var node=close.parentElement,absolute=null;
 while(node&&node!==d.body&&node!==d.documentElement){
  if(preserve(node))return null;
  var cs=getComputedStyle(node),rect=node.getBoundingClientRect();
  if(rect.width>28&&rect.height>28){
   var dialog=node.matches('[role="dialog"],[aria-modal="true"],.ui-overlay');
   var full=rect.width>=innerWidth*.95&&rect.height>=innerHeight*.95;
   var layer=/overlay|backdrop|modal|popup|dialog|mask/i.test(node.className||'');
   if(dialog||cs.position==='fixed'&&(!full||layer||promotion(node)))return node;
   if(cs.position==='absolute')absolute=node;
  }
  node=node.parentElement;
 }
 return absolute;
}
function promotionRoot(el){
 var node=el,best=null;
 while(node&&node!==d.body&&node!==d.documentElement){
  if(preserve(node))break;
  var cs=getComputedStyle(node);
  if(node.matches('[role="dialog"],[aria-modal="true"],.ui-overlay')||cs.position==='fixed'||cs.position==='absolute')best=node;
  node=node.parentElement;
 }
 return best;
}
var dismissed=new WeakSet();
function dismissPromotion(el){
 // Dismiss only positively identified advertisements, never an unknown dialog.
 // Let the site's own handler remove its dimmer and restore page interaction.
 if(!promotion(el)||dismissed.has(el))return;
 var buttons=el.querySelectorAll(closeQuery);
 for(var i=0;i<buttons.length;i++)if(isClose(buttons[i])&&!preserve(buttons[i])){
  dismissed.add(el);buttons[i].click();return;
 }
}
function write(el,value){var setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))}
function autofill(){
 var reg=route(),all=d.querySelectorAll('input'),first=null,named=null;
 for(var i=0;i<all.length;i++){
  var el=all[i],meta=[el.name,el.id,el.placeholder,el.autocomplete,el.getAttribute('aria-label')].join(' ').toLowerCase();
  if(el.disabled||el.readOnly||!el.getClientRects().length||el.closest(security)||/captcha|otp|one.time|verifica/.test(meta))continue;
  if(el.type==='password'||/senha|password/.test(meta)){
   if(!el.value&&!passwordWritten.has(el)){passwordWritten.add(el);write(el,'danill0')}continue;
  }
  if(!reg||!/^(text|tel|email|number)$/.test(el.type)||/cpf|c[oó]digo|code|convite|invite|search|busca|confirma/.test(meta))continue;
  if(!first)first=el;
  if(!named&&/conta|account|usu[aá]rio|username|user.?name/.test(meta))named=el;
 }
 var target=named||first;
 if(reg&&target&&written.get(target)!==visit){
  if(!username)username=randomName();
  if(target.type==='email'||target.type==='number')target.type='text';
  target.setAttribute('inputmode','text');written.set(target,visit);write(target,username);
 }
}
var busy=false;
function run(){
 if(busy)return;busy=true;
 try{
  if(!d.documentElement)return;
  if(d.documentElement&&!style.isConnected)d.documentElement.appendChild(style);
  snapshotProtection();
  var old=d.querySelectorAll('['+tag+'="1"]');
  for(var i=0;i<old.length;i++)if(preserve(old[i]))old[i].removeAttribute(tag);
  var hide=[],closes=accountFlow()?[]:d.querySelectorAll(closeQuery);
  for(var j=0;j<closes.length;j++)if(isClose(closes[j])){
   var el=candidate(closes[j]);if(el&&hide.indexOf(el)<0)hide.push(el);
  }
  // Identified promotions also cover the prize-selection layer without an X.
  var textNodes=d.createTreeWalker(d.body||d.documentElement,NodeFilter.SHOW_TEXT),textNode;
  while(textNodes.root&&(textNode=textNodes.nextNode())){
   if(!/cadastro|deposite|clube vip|sorteio/i.test(textNode.nodeValue))continue;
   var parent=textNode.parentElement;
   while(parent&&parent!==d.body&&parent!==d.documentElement){
    if(promotion(parent)){var promo=promotionRoot(parent);if(promo&&hide.indexOf(promo)<0)hide.push(promo);break;}
    parent=parent.parentElement;
   }
  }
  for(var k=0;k<hide.length;k++){
   if(preserve(hide[k]))continue;
   dismissPromotion(hide[k]);
   if(hide[k].isConnected&&hide[k].getAttribute(tag)!=='1')hide[k].setAttribute(tag,'1');
  }
  autofill();
 }finally{busy=false}
}
// Relay a real user's tap if a decorative portal intercepts the visible X.
// Invoke the site's original handler; never remove reward DOM or invent state.
window.addEventListener('click',function(event){
 if(!event.isTrusted||event.detail===0)return;
 if(event.target&&event.target.closest&&event.target.closest(security))return;
 var target=null,bestArea=Infinity;
 for(var i=0;i<rewardRoots.length;i++){
  var root=rewardRoots[i];
  if(!root.isConnected||has(root,security)||promotion(root))continue;
  var controls=root.querySelectorAll(closeQuery);
  for(var j=0;j<controls.length;j++){
   var close=controls[j];if(!isClose(close))continue;
   var rect=close.getBoundingClientRect(),cs=getComputedStyle(close);
   if(rect.width<12||rect.height<12||rect.width>128||rect.height>128||cs.display==='none'||cs.visibility==='hidden')continue;
   if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)continue;
   // The normal event is already routed to this control; do not duplicate it.
   if(close===event.target||close.contains(event.target))return;
   var area=rect.width*rect.height;if(area<bestArea){target=close;bestArea=area;}
  }
 }
 if(target){event.preventDefault();event.stopImmediatePropagation();target.click();}
},true);
var queued=false;
function schedule(){if(!queued){queued=true;Promise.resolve().then(function(){queued=false;run()})}}
new MutationObserver(function(ms){
 for(var i=0;i<ms.length;i++)if(ms[i].target!==style){schedule();return}
}).observe(d,{childList:true,characterData:true,subtree:true,attributes:true,attributeFilter:['class','id','style','src','type','name','placeholder','disabled','readonly','role','aria-modal','aria-label']});
['pushState','replaceState'].forEach(function(name){var original=history[name];history[name]=function(){var result=original.apply(this,arguments);route();schedule();return result}});
['transitionstart','transitionend','animationstart','animationend'].forEach(function(type){d.addEventListener(type,schedule,true)});
window.addEventListener('hashchange',schedule);window.addEventListener('popstate',schedule);window.addEventListener('load',schedule);
d.addEventListener('DOMContentLoaded',schedule);d.addEventListener('focusin',schedule);run();
})();
