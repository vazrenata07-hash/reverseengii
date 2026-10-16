(function(){
'use strict';
if(window.top!==window||window.__mintRebuilt12)return;
var host=location.hostname.toLowerCase();
if(host!=='888pg.cc'&&host.slice(-9)!=='.888pg.cc')return;
window.__mintRebuilt12=1;
var d=document,tag='data-mint12-hidden',style=d.createElement('style');
style.textContent='['+tag+'="1"]{display:none!important;visibility:hidden!important;pointer-events:none!important}';
var fast='[class*="_fastBtn_"],[class*="_fastBackground_"],[class*="_fastImg_"],[class*="_closeIcon_3tzh2_"]';
var security='iframe,canvas,[role="slider"],[class*="captcha" i],[id*="captcha" i],[class*="geetest" i],[class*="verify" i],[class*="yidun" i],[class*="turnstile" i],[class*="hcaptcha" i],[class*="puzzle" i]';
var rewards=fast+',[class*="redpacket" i],[class*="red-packet" i],[class*="red_bag" i],[class*="red-bag" i],[class*="redbag" i],[class*="envelop" i],[class*="hongbao" i],[class*="gift" i],[class*="chest" i],[class*="treasure" i]';
var closeQuery='[class*="close" i],[aria-label*="fechar" i],[aria-label*="close" i],img[src*="close" i],button,[role="button"]';
var inputs='input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])';
var protectedRoots=[],username='',wasRegister=false,visit=0,written=new WeakMap(),passwordWritten=new WeakSet();
function register(){return /(?:^|[\/#])register(?:[\/?#]|$)/i.test(location.pathname+location.hash)}
function accountFlow(){return /(?:^|[\/#])(?:register|login|signup|signin|verify|captcha)(?:[\/?#]|$)/i.test(location.pathname+location.hash)}
function randomName(){var abc='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',s='',a=new Uint8Array(32);while(s.length<15){crypto.getRandomValues(a);for(var i=0;i<a.length&&s.length<15;i++)if(a[i]<248)s+=abc[a[i]%62]}return s}
function route(){var reg=register();if(reg&&!wasRegister){username=randomName();visit++}wasRegister=reg;return reg}
function protectedText(el){return /\babrir\b|resgatar|coletar|b[oô]nus de (?:login|aposta)|ba[uú]|captcha|verifica[çc][aã]o|seguran[çc]a|arraste|deslize/.test((el.textContent||'').toLowerCase())}
function has(el,selector){return el.matches(selector)||!!el.querySelector(selector)}
function locateScope(el){
 var node=el,positioned=null;
 while(node&&node!==d.body&&node!==d.documentElement){
  if(node.matches('[role="dialog"],[aria-modal="true"],.ui-overlay'))return node;
  var pos=getComputedStyle(node).position;
  if(!positioned&&(pos==='fixed'||pos==='absolute'))positioned=node;
  node=node.parentElement;
 }
 return positioned||el;
}
function rewardDialogOpen(){
 // The reported controls and the modal card can be separate portal roots.
 if(!d.querySelector(fast))return false;
 var layers=d.querySelectorAll('body *');
 for(var i=0;i<layers.length;i++){
  var el=layers[i],r=el.getBoundingClientRect();
  if(r.width<innerWidth*.75||r.height<innerHeight*.75)continue;
  var cs=getComputedStyle(el);
  if(cs.display==='none'||cs.visibility==='hidden')continue;
  // A dimmer starting its CSS fade-in is already an active modal; waiting for
  // opacity to become nonzero can hide the card before the next DOM mutation.
  if(cs.opacity==='0'&&cs.pointerEvents==='none')continue;
  if(cs.position!=='fixed'&&cs.position!=='absolute')continue;
  var name=[el.className,el.getAttribute('role')].join(' ');
  var color=cs.backgroundColor||'',rgba=color.match(/rgba\([^,]+,[^,]+,[^,]+,\s*([\d.]+)\)/i);
  var dimColor=rgba&&Number(rgba[1])>0&&Number(rgba[1])<1;
  var opacity=cs.opacity===''?1:Number(cs.opacity);
  var fading=opacity<1&&cs.pointerEvents!=='none';
  var blur=cs.backdropFilter&&cs.backdropFilter!=='none';
  if(dimColor||fading||blur||/overlay|backdrop|mask|dialog|fastBackground/i.test(name)||el.getAttribute('aria-modal')==='true')return true;
 }
 return false;
}
function snapshotProtection(){
 protectedRoots=[];
 var nodes=d.querySelectorAll(rewards+','+security);
 for(var i=0;i<nodes.length;i++)protectedRoots.push(locateScope(nodes[i]));
}
function preserve(el){
 if(accountFlow()||has(el,rewards+','+security+','+inputs)||protectedText(el))return true;
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
   var dialog=node.matches('[role="dialog"],[aria-modal="true"]');
   var page=rect.width>=innerWidth*.95&&rect.height>=innerHeight*.95&&!dialog;
   if(!page&&(cs.position==='fixed'||dialog))return absolute||node;
   if(cs.position==='absolute'&&!absolute)absolute=node;
  }
  node=node.parentElement;
 }
 return absolute;
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
  if(d.documentElement&&!style.isConnected)d.documentElement.appendChild(style);
  snapshotProtection();
  var rewardOpen=rewardDialogOpen();
  var old=d.querySelectorAll('['+tag+'="1"]');
  for(var i=0;i<old.length;i++)if(rewardOpen||preserve(old[i]))old[i].removeAttribute(tag);
  // Find every protected component before hiding anything: no discovery-order race.
  var hide=[],closes=(accountFlow()||rewardOpen)?[]:d.querySelectorAll(closeQuery);
  for(var j=0;j<closes.length;j++)if(isClose(closes[j])){
   var el=candidate(closes[j]);if(el&&hide.indexOf(el)<0)hide.push(el);
  }
  for(var k=0;k<hide.length;k++)if(hide[k].getAttribute(tag)!=='1')hide[k].setAttribute(tag,'1');
  autofill();
 }finally{busy=false}
}
var queued=false;
function schedule(){if(!queued){queued=true;Promise.resolve().then(function(){queued=false;run()})}}
new MutationObserver(function(ms){
 for(var i=0;i<ms.length;i++)if(ms[i].target!==style){schedule();return}
}).observe(d,{childList:true,subtree:true,attributes:true,attributeFilter:['class','id','style','src','type','name','placeholder','disabled','readonly']});
['pushState','replaceState'].forEach(function(name){var original=history[name];history[name]=function(){var result=original.apply(this,arguments);route();schedule();return result}});
['transitionstart','transitionend','animationstart','animationend'].forEach(function(type){d.addEventListener(type,schedule,true)});
window.addEventListener('hashchange',schedule);window.addEventListener('popstate',schedule);window.addEventListener('load',schedule);
d.addEventListener('DOMContentLoaded',schedule);d.addEventListener('focusin',schedule);run();
})();
