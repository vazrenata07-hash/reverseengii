(function(){
'use strict';
if(window.top!==window||window.__mintRebuilt19)return;
var host=location.hostname.toLowerCase();
if(host!=='888pg.cc'&&host.slice(-9)!=='.888pg.cc')return;
window.__mintRebuilt19=1;
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

// Withdrawal PIN is independent of the account password. Never submit a form.
var withdrawalPIN='232691',pinWritten=new WeakSet(),pinAttempts=new WeakMap(),pinBusy=false;
var pinWidgets='.ui-password-input,.van-password-input';
var pinKeys='.ui-number-keyboard,.van-number-keyboard';
function visible(el){return !!el&&!!el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden'&&getComputedStyle(el).display!=='none';}
function withdrawalContext(el){
 if(el.closest(security))return false;
 var meta=[el.name,el.id,el.placeholder,el.getAttribute('aria-label')].join(' ');
 if(/captcha|otp|one.time|sms|c[oó]digo/i.test(meta))return false;
 if(/(?:withdraw|saque).*(?:pass|senha|pin)|(?:pass|senha|pin).*(?:withdraw|saque)/i.test(meta))return true;
 var area=el.closest('[role="dialog"],.ui-dialog,.ui-popup,.van-dialog,.van-popup');
 var text=(area||d.body).textContent||'';
 if(!/senha\s+(?:de |para (?:o )?)?saque/i.test(text))return false;
 return !!area||/(?:^|[\/#])(?:security|withdraw)(?:[\/?#]|$)/i.test(location.pathname+location.hash);
}
function pinInput(el){
 if(!withdrawalContext(el))return false;
 var meta=[el.name,el.id,el.placeholder,el.autocomplete,el.getAttribute('aria-label')].join(' ');
 if(/valor|amount|quantia|balance|saldo|cpf|telefone|phone|email|pix|account|conta|username|login/i.test(meta))return false;
 return el.type==='password'||el.maxLength===6||el.maxLength===1||/senha|password|withdraw.?pin|saque.?pin/i.test(meta);
}
function emitKeyboardDigit(keyboard,digit){
 // Prefer the keyboard's own Vue input event: same handler as tapping a key.
 var instance=keyboard.__vueParentComponent;
 for(var n=0;instance&&n<4;n++,instance=instance.parent){
  var name=(instance.type&&(instance.type.name||instance.type.__name))||'';
  var props=instance.vnode&&instance.vnode.props;
  if(/number.?keyboard/i.test(name)&&props&&typeof props.onInput==='function'&&typeof instance.emit==='function'){
   instance.emit('input',digit);return true;
  }
 }
 var keys=keyboard.querySelectorAll('.ui-key,.van-key,[role="button"],button');
 for(var i=0;i<keys.length;i++)if(keys[i].textContent.trim()===digit){
  // Vant-compatible keyboards use touchend, not a synthetic click.
  var key=keys[i];
  key.dispatchEvent(new Event('touchstart',{bubbles:true,cancelable:true}));
  key.dispatchEvent(new Event('touchend',{bubbles:true,cancelable:true}));
  return true;
 }
 return false;
}
function filledCells(widget){
 var cells=widget.querySelectorAll('li');var count=0;
 for(var i=0;i<cells.length;i++){
  var dot=cells[i].querySelector('i:not([class*="cursor"])');
  if(cells[i].textContent.trim()||dot&&getComputedStyle(dot).display!=='none'&&getComputedStyle(dot).visibility!=='hidden')count++;
 }
 return count;
}
function focusPIN(target){
 var focus=target.querySelector('ul')||target;
 // These password widgets receive focus via touchstart, not a mouse click.
 focus.dispatchEvent(new Event('touchstart',{bubbles:true,cancelable:true}));
 focus.dispatchEvent(new Event('touchend',{bubbles:true,cancelable:true}));
 focus.click();
}
function customPIN(){
 if(pinBusy)return;
 var widgets=d.querySelectorAll(pinWidgets),target=null;
 for(var i=0;i<widgets.length;i++){
  var el=widgets[i];
  if(!visible(el)){pinWritten.delete(el);pinAttempts.delete(el);continue;}
  if(!pinWritten.has(el)&&(pinAttempts.get(el)||0)<2&&withdrawalContext(el)&&!el.querySelector('input')&&filledCells(el)===0){target=el;break;}
 }
 if(!target)return;
 pinBusy=true;pinAttempts.set(target,(pinAttempts.get(target)||0)+1);
 focusPIN(target);
 var index=0,waits=0,ackWaits=0;
 function stop(){
  pinBusy=false;
  if(target.isConnected&&visible(target)&&filledCells(target)===0&&(pinAttempts.get(target)||0)<2)setTimeout(customPIN,250);
 }
 function step(){
  if(!target.isConnected||!visible(target)){stop();return;}
  var count=filledCells(target);
  // Wait for this widget to acknowledge the last digit before proceeding.
  if(count!==index){
   if(count===index-1&&++ackWaits<15){setTimeout(step,40);return;}
   stop();return;
  }
  ackWaits=0;
  if(index===6){pinWritten.add(target);pinBusy=false;setTimeout(customPIN,180);return;}
  var boards=d.querySelectorAll(pinKeys),keyboard=null;
  for(var k=0;k<boards.length;k++)if(visible(boards[k])){keyboard=boards[k];break;}
  if(!keyboard){if(++waits<15){setTimeout(step,60);return;}stop();return;}
  waits=0;
  if(!emitKeyboardDigit(keyboard,withdrawalPIN[index])){stop();return;}
  index++;setTimeout(step,40);
 }
 setTimeout(step,120);
}
function autofill(){
 var reg=route(),all=d.querySelectorAll('input'),first=null,named=null,segments=[];
 for(var i=0;i<all.length;i++){
  var el=all[i],meta=[el.name,el.id,el.placeholder,el.autocomplete,el.getAttribute('aria-label')].join(' ').toLowerCase();
  if(!visible(el)){pinWritten.delete(el);continue;}
  if(el.disabled||el.readOnly||!el.getClientRects().length||el.closest(security)||/captcha|otp|one.time|sms/.test(meta)||(/verifica/.test(meta)&&!pinInput(el)))continue;
  if(pinInput(el)){
   if(el.maxLength===1){segments.push(el);continue;}
   if(!el.value&&!pinWritten.has(el)){pinWritten.add(el);write(el,withdrawalPIN);}continue;
  }
  if(withdrawalContext(el))continue;
  if(el.type==='password'||/senha|password/.test(meta)){
   if(!el.value&&!passwordWritten.has(el)){passwordWritten.add(el);write(el,'danill0')}continue;
  }
  if(!reg||!/^(text|tel|email|number)$/.test(el.type)||/cpf|c[oó]digo|code|convite|invite|search|busca|confirma/.test(meta))continue;
  if(!first)first=el;
  if(!named&&/conta|account|usu[aá]rio|username|user.?name/.test(meta))named=el;
 }
 // Only complete groups of six empty single-character inputs are PINs.
 for(var j=0;j+5<segments.length;j+=6){
  var group=segments.slice(j,j+6);
  if(group.every(function(e){return !e.value&&!pinWritten.has(e);})){group.forEach(function(e,k){pinWritten.add(e);write(e,withdrawalPIN[k]);});}
 }
 customPIN();
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
 if(!formDirty&&(node.matches('input,'+pinWidgets+','+pinKeys)||node.querySelector('input,'+pinWidgets+','+pinKeys)))formDirty=true;
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
   if((m.attributeName==='style'||m.attributeName==='class')&&
      (target.matches(pinWidgets+','+pinKeys)||target.matches('.ui-popup,.ui-dialog,.van-popup,.van-dialog')&&target.querySelector('input,'+pinWidgets)))formDirty=true;
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
d.addEventListener('focusin',function(e){if(e.target.matches('input')){formDirty=true;queue();}});
d.addEventListener('click',function(e){if(e.target.closest&&e.target.closest(pinWidgets)){setTimeout(function(){formDirty=true;queue();},80);}},true);
window.addEventListener('hashchange',navigation);window.addEventListener('popstate',navigation);window.addEventListener('load',navigation);
d.addEventListener('DOMContentLoaded',function(){if(d.body)prepareImages(d.body);navigation();});
if(d.body)prepareImages(d.body);run();
})();
