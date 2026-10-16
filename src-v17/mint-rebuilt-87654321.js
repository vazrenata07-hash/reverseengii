(function(){
'use strict';
if(window.top!==window||window.__mintRebuilt17)return;
var host=location.hostname.toLowerCase();
if(host!=='888pg.cc'&&host.slice(-9)!=='.888pg.cc')return;
window.__mintRebuilt17=1;
var d=document,tag='data-mint17-ad',style=d.createElement('style');
var security='[class*="captcha" i],[id*="captcha" i],[class*="geetest" i],[class*="yidun" i],[class*="turnstile" i],[class*="hcaptcha" i],[class*="_moreInterception_1s3a2_"]';
var username='',wasRegister=false,visit=0,written=new WeakMap(),passwordWritten=new WeakSet();
// These are component signatures observed in the user's 16 October capture.
// No generic dialog, close-button, gift, envelope or geometry classification.
var rules=[
 {name:'registration-promotion',selector:'.ui-dialog[class*="_registerRechargeDialog_11sp7_"]',close:'[class*="_closeIcon_11sp7_"]'},
 {name:'app-download',selector:'.ui-dialog[class*="_download_1dot2_"]'},
 {name:'advertisement-carousel',selector:'.ui-dialog[class*="_modal_dtape_"]',child:'[class*="_main_y93eo_"]'},
 {name:'prize-wheel-promotion',selector:'.ui-dialog[class*="_slashDialogBox_1uifh_"]'},
 {name:'prize-choice-promotion',selector:'.ui-dialog[class*="_dialogBox_16fxx_"]',child:'[class*="_main_1mmwx_"]'},
 {name:'task-promotion',selector:'.ui-dialog[class*="_dialogBox_1t5m3_"]'},
 {name:'find-us-promotion',selector:'.ui-dialog[class*="_find-us_17o64_"]'},
 {name:'push-promotion',selector:'.notic-user-tip-warp',close:'.web-push-tip-cancel'}
];
style.textContent='.float-bar-main .fast-entry-item{display:none!important}['+tag+'],['+tag+'] *{visibility:hidden!important;pointer-events:none!important}';
function protectedDialog(el){
 return !!el.querySelector(security)||el.matches(security)||
 /\babrir\b|b[oô]nus de (?:login|aposta)/i.test(el.textContent||'')||
 !!el.querySelector('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]),textarea');
}
var attempts=new WeakMap(),marked=new Set();
function dismiss(root,node,rule){
 var close=node.querySelector(rule.close||'.ui-dialog-close-box__icon');
 if(!close||typeof close.click!=='function')return;
 var state=attempts.get(root);
 if(!state||state.control!==close){state={control:close,count:0,last:0};attempts.set(root,state);}
 var now=Date.now();if(state.count>=3||now-state.last<120)return;
 if(!root.isConnected||root.style.display==='none'||!root.getClientRects().length)return;
 if(/leave-active|leave-to|leave-from/.test(root.className+' '+node.className))return;
 state.count++;state.last=now;
 // The captured native close control advances the site's popup queue.
 // Never click claim/activate buttons or remove a component's DOM ourselves.
 close.click();
 if(state.count<3)setTimeout(schedule,state.count===1?150:500);
}
function filter(){
 if(!d.documentElement)return;
 if(!style.isConnected)d.documentElement.appendChild(style);
 var current=new Map();
 for(var i=0;i<rules.length;i++){
  var rule=rules[i],nodes=d.querySelectorAll(rule.selector);
  for(var j=0;j<nodes.length;j++){
   var node=nodes[j];if(rule.child&&!node.querySelector(rule.child))continue;
   var root=node.closest('.ui-overlay')||node;
   if(protectedDialog(root))continue;
   current.set(root,{node:node,rule:rule});
  }
 }
 marked.forEach(function(root){if(!current.has(root)){root.removeAttribute(tag);attempts.delete(root);marked.delete(root);}});
 current.forEach(function(item,root){if(root.getAttribute(tag)!==item.rule.name)root.setAttribute(tag,item.rule.name);marked.add(root);});
 // Keep the whitelist of controls separate from all user click handling.
 current.forEach(function(item,root){dismiss(root,item.node,item.rule);});
}
function register(){return /(?:^|[\/#])register(?:[\/?#]|$)/i.test(location.pathname+location.hash)}
function accountFlow(){return /(?:^|[\/#])(?:register|login|signup|signin|verify|captcha)(?:[\/?#]|$)/i.test(location.pathname+location.hash)}
function randomName(){var abc='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',s='',a=new Uint8Array(32);while(s.length<15){crypto.getRandomValues(a);for(var i=0;i<a.length&&s.length<15;i++)if(a[i]<248)s+=abc[a[i]%62]}return s}
function route(){var reg=register();if(reg&&!wasRegister){username=randomName();visit++}wasRegister=reg;return reg}
function write(el,value){var setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(el,value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))}
function autofill(){
 var reg=route(),all=d.querySelectorAll('input'),first=null,named=null;
 for(var i=0;i<all.length;i++){
  var el=all[i],meta=[el.name,el.id,el.placeholder,el.autocomplete,el.getAttribute('aria-label')].join(' ').toLowerCase();
  if(el.disabled||el.readOnly||!el.getClientRects().length||el.closest(security)||/captcha|otp|one.time|verifica/.test(meta))continue;
  if(el.type==='password'||/senha|password/.test(meta)){
   if(!el.value&&!passwordWritten.has(el)){passwordWritten.add(el);write(el,'87654321')}continue;
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

// Animation styles and SVG/Lottie updates do not change the ad rules.
// Only structural changes involving known dialogs or inputs trigger searches.
var ruleSelector=rules.map(function(rule){return rule.selector;}).join(',');
var queued=false,busy=false,filterDirty=true,formDirty=true;
function run(){
 if(busy)return;busy=true;
 var f=filterDirty,a=formDirty;filterDirty=false;formDirty=false;
 try{if(f)filter();if(a)autofill();}finally{busy=false;}
}
function queue(){if(!queued){queued=true;Promise.resolve().then(function(){queued=false;run();});}}
function schedule(){filterDirty=true;queue();}
function inspectNode(node){
 if(!node||node.nodeType!==1)return;
 if(node.namespaceURI==='http://www.w3.org/2000/svg')return;
 if(!filterDirty&&(node.matches(ruleSelector)||node.querySelector(ruleSelector)))filterDirty=true;
 if(!formDirty&&(node.matches('input')||node.querySelector('input')))formDirty=true;
 prepareImages(node);
}
var images=new WeakSet(),imageObserver=null;
if(window.IntersectionObserver)imageObserver=new IntersectionObserver(function(entries){
 for(var i=0;i<entries.length;i++)if(entries[i].isIntersecting){
  var img=entries[i].target;imageObserver.unobserve(img);
  if(img.getAttribute('loading')==='lazy')img.loading='eager';
  img.decoding='async';
  if(img.complete&&img.naturalWidth&&img.decode)img.decode().catch(function(){});
 }
},{rootMargin:'600px 0px'});
function prepareImages(node){
 if(!imageObserver||!node.querySelectorAll)return;
 var list=node.matches('img.lobby-image')?[node]:node.querySelectorAll('img.lobby-image');
 for(var i=0;i<list.length;i++)if(!images.has(list[i])){images.add(list[i]);imageObserver.observe(list[i]);}
}
new MutationObserver(function(ms){
 for(var i=0;i<ms.length;i++){
  var m=ms[i],target=m.target.nodeType===1?m.target:m.target.parentElement;
  if(!target||target===style||target.namespaceURI==='http://www.w3.org/2000/svg')continue;
  if(m.type==='attributes'){
   if(target.matches('input'))formDirty=true;
   if(m.attributeName==='style'&&(target.matches(ruleSelector)||target.hasAttribute(tag)))filterDirty=true;
   if(m.attributeName==='class'&&(target.matches(ruleSelector)||target.hasAttribute(tag)||target.closest(ruleSelector)||target.closest('['+tag+']')))filterDirty=true;
  }else{
   if(target.closest(ruleSelector)||target.closest('['+tag+']'))filterDirty=true;
   if(m.type==='childList'){
    for(var j=0;j<m.addedNodes.length;j++)inspectNode(m.addedNodes[j]);
    for(var k=0;k<m.removedNodes.length;k++){
     var removed=m.removedNodes[k];
     if(removed.nodeType===1&&(removed.hasAttribute(tag)||removed.matches(ruleSelector)||removed.querySelector(ruleSelector)))filterDirty=true;
    }
   }
  }
 }
 if(filterDirty||formDirty)queue();
}).observe(d,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class','style','type','name','placeholder','disabled','readonly']});
function navigation(){route();filterDirty=true;formDirty=true;queue();}
['pushState','replaceState'].forEach(function(name){var original=history[name];history[name]=function(){var result=original.apply(this,arguments);navigation();return result;};});
window.addEventListener('hashchange',navigation);window.addEventListener('popstate',navigation);window.addEventListener('load',navigation);
d.addEventListener('DOMContentLoaded',function(){if(d.body)prepareImages(d.body);navigation();});
if(d.body)prepareImages(d.body);run();
})();
