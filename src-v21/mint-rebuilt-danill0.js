(function(){
'use strict';
if(window.top!==window||window.__mintRebuilt21)return;
var host=location.hostname.toLowerCase();
if(host!=='888pg.cc'&&host.slice(-9)!=='.888pg.cc')return;
window.__mintRebuilt21=1;
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

(function(){
'use strict';
// Adapter derived from the captured JDB Mines 9014 protocol and Cocos modules.
// Runs inside the game frame, independently of the main page's ad/autofill code.
if(!/^\/h5\/games\/9\/9014\//.test(location.pathname)||window.__mintMinesCounter20)return;
if(!/(^|\.)brteachcor\.com$/i.test(location.hostname))return;
window.__mintMinesCounter20=true;
var cc=null,loadingCC=false,proxy=null,panel=null,label=null,total=null,saveFailed=false,stopped=false;
var start=Date.now(),timer=null,store=window.MintWagerCounter;
var pending=new Map(),seen=new Set(),lastRead=0;
// Passive history adapter for JDB Mines 9014. Called by the existing game adapter.
// Never selects cards, sends a game request, changes autoplay, or ranks positions.
function createMinesHistory(getEngine){
 'use strict';
 var key='mint.mines9014.revealed.v21',rows=[],counts=new Array(25).fill(0);
 var visible=false,button=null,view=null,nodes=[],labels=[],currentRound=null,saveTimer=null;
 var storageFailed=false;
 function validId(id){return /^\d{1,24}$/.test(String(id));}
 function validRow(row){
  return row&&validId(row.id)&&Array.isArray(row.mines)&&row.mines.length===25&&
   row.mines.every(function(n){return n===0||n===1;});
 }
 try{
  var saved=JSON.parse(localStorage.getItem(key)||'[]');
  if(Array.isArray(saved))rows=saved.filter(validRow).slice(-10);
 }catch(e){storageFailed=true;}
 function recount(){
  counts.fill(0);
  rows.forEach(function(row){for(var i=0;i<25;i++)counts[i]+=row.mines[i];});
 }
 recount();
 function save(){
  if(saveTimer!==null)clearTimeout(saveTimer);
  saveTimer=setTimeout(function(){
   saveTimer=null;
   try{localStorage.setItem(key,JSON.stringify(rows));storageFailed=false;}catch(e){storageFailed=true;}
   caption();
  },0);
 }
 function caption(){
  if(!button)return;
  var text=(visible?'Ocultar':'Histórico')+' · '+rows.length+'/10'+(storageFailed?' *':'');
  if(button.textContent!==text)button.textContent=text;
  button.setAttribute('aria-pressed',String(visible));
  button.title='Bombas reveladas nas últimas '+rows.length+' rodadas'+
   (storageFailed?' · Histórico somente nesta sessão':'');
 }
 function redraw(){
  if(!visible)return;
  for(var i=0;i<labels.length;i++){
   var value=rows.length?String(counts[i]):'—';
   if(labels[i].string!==value)labels[i].string=value;
  }
 }
 function destroyNumbers(){
  nodes.forEach(function(n){if(n&&n.isValid!==false)n.destroy();});nodes=[];labels=[];
 }
 function ensureNumbers(){
  var cc=getEngine();
  if(!cc||!view||!view.cards||view.cards.length!==25)return false;
  if(nodes.length===25&&nodes.every(function(n){return n.isValid!==false;}))return true;
  destroyNumbers();
  try{
   for(var i=0;i<25;i++){
    var card=view.cards[i].node,transform=card.getComponent(cc.UITransform);
    var node=new cc.Node('MintHistoryCount'+i);node.layer=card.layer;node.active=false;
    card.addChild(node);nodes.push(node);
    var box=node.addComponent(cc.UITransform);
    box.setContentSize(transform?transform.width:100,transform?transform.height:100);
    // A child at the card's visual center preserves the game's own index/layout.
    node.setPosition(transform?(0.5-transform.anchorX)*transform.width:0,
     transform?(0.5-transform.anchorY)*transform.height:0,0);
    var label=node.addComponent(cc.Label);label.useSystemFont=true;label.fontFamily='Arial';
    label.fontSize=Math.max(28,Math.min(52,(transform?transform.width:100)*0.48));
    label.lineHeight=label.fontSize+8;label.isBold=true;label.color=new cc.Color(255,255,255,255);
    label.horizontalAlign=1;label.verticalAlign=1;label.overflow=2;label.enableWrapText=false;
    // Share glyphs instead of giving every cell an independent font texture.
    label.cacheMode=2;
    if(cc.LabelOutline){var outline=node.addComponent(cc.LabelOutline);outline.color=new cc.Color(10,24,43,255);outline.width=5;}
    labels.push(label);
   }
  }catch(e){destroyNumbers();return false;}
  return true;
 }
 function toggle(){
  if(!visible&&!ensureNumbers())return;
  visible=!visible;
  nodes.forEach(function(n){if(n.isValid!==false)n.active=visible;});
  redraw();caption();
 }
 function mount(next){
  if(!next||!next.gameView||!next.gameView.cards||next.gameView.cards.length!==25)return;
  if(view!==next.gameView){destroyNumbers();view=next.gameView;if(visible){ensureNumbers();nodes.forEach(function(n){n.active=true;});redraw();}}
  if(!button&&document.body){
   button=document.createElement('button');button.type='button';button.id='mint-mines-history';
   button.setAttribute('aria-label','Mostrar ou ocultar contagem de bombas das últimas dez rodadas');
   button.style.cssText='position:fixed;right:8px;top:8px;z-index:2147483647;padding:9px 12px;border:1px solid #9bb5d0;border-radius:18px;background:#102a43;color:#fff;font:bold 13px Arial;line-height:18px;touch-action:manipulation;pointer-events:auto;';
   button.onclick=function(event){event.stopPropagation();toggle();};
   document.body.appendChild(button);caption();
  }
 }
 function observeBet(data){
  if(data&&data.spinResult&&data.betResult&&validId(data.betResult.gameSeq))currentRound=String(data.betResult.gameSeq);
 }
 function completed(data,id){
  // cashoutResponse includes the public final board after wins AND losses.
  // Card.State.OpenMine=4 and Card.State.CoveredMine=7 in the captured version.
  var result=data&&data.gameResult,map=result&&result.map;
  if(!validId(id)||!result||result.bpsGame!=='Mines'||!Array.isArray(map)||map.length!==25)return;
  if(!map.every(function(n){return Number.isInteger(n)&&n>=3&&n<=7;}))return;
  id=String(id);if(rows.some(function(row){return row.id===id;}))return;
  rows.push({id:id,mines:map.map(function(n){return n===4||n===7?1:0;})});
  if(rows.length>10)rows.shift();recount();redraw();caption();save();
 }
 function watch(next){
  if(!next||typeof next.cashoutRequest!=='function'||next.cashoutRequest.__mintHistory21)return;
  var original=next.cashoutRequest;
  var wrapped=function(){
   var id=currentRound;
   try{var round=this.appData&&this.appData.roundData;if(round&&validId(round.id))id=String(round.id);}catch(e){}
   var result=original.apply(this,arguments);
   // Observe only the existing request; preserve its exact returned promise.
   if(result&&typeof result.then==='function')result.then(function(data){try{completed(data,id);}catch(e){}},function(){});
   return result;
  };
  wrapped.__mintHistory21=true;try{next.cashoutRequest=wrapped;}catch(e){}
 }
 return {watch:watch,mount:mount,observeBet:observeBet};
}

var history=createMinesHistory(function(){return cc;});
function amount(milli){return (milli/1000).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});}
function readTotal(){
 if(!store)return;
 try{var data=JSON.parse(store.total());if(!data.error&&Number.isSafeInteger(data.milli)&&data.milli>=0){total=data.milli;lastRead=Date.now();refreshLabel();}}catch(e){}
}
function persist(round,milli){
 if(seen.has(round)||!store)return;
 pending.set(round,milli);
 try{
  var data=JSON.parse(store.record('jdb-mines-9014',round,milli));
  if(data.error||!Number.isSafeInteger(data.milli))throw new Error('counter storage');
  pending.delete(round);seen.add(round);total=data.milli;saveFailed=pending.size>0;refreshLabel();
 }catch(e){saveFailed=true;refreshLabel();}
}
function confirmed(data,bet){
 history.observeBet(data);
 // Only the first accepted spin includes betResult/gameSeq. Reveals and
 // cashouts are not additional wagers. Creating a board does not charge it.
 if(!data||!data.betResult||!data.spinResult)return;
 var result=data.betResult,round=result.gameSeq;
 if(typeof round==='number'&&!Number.isSafeInteger(round))return;
 round=String(round);
 var milli=Math.round(Number(bet)*1000);
 if(!/^\d{1,24}$/.test(round)||!Number.isSafeInteger(milli)||milli<=0||milli>1000000000)return;
 persist(round,milli);
}
function watchProxy(next){
 history.watch(next);
 if(!next||typeof next.checkRequest!=='function')return;
 if(next.checkRequest.__mintWager20){proxy=next;return;}
 var original=next.checkRequest;
 var wrapped=function(indices,bet){
  var result=original.apply(this,arguments),stake=Number(bet);
  // Return the exact original promise; never change requests, resolutions,
  // error handling, click controls, balance, or autoplay behavior.
  if(result&&typeof result.then==='function')result.then(function(data){try{confirmed(data,stake);}catch(e){}},function(){});
  return result;
 };
 wrapped.__mintWager20=true;
 try{next.checkRequest=wrapped;if(next.checkRequest===wrapped)proxy=next;}catch(e){}
}
function alive(node){return node&&node.isValid!==false;}
function refreshLabel(){
 if(!label||!alive(label.node))return;
 var value=total===null?'—':'R$ '+amount(total);
 var next='Apostado: '+value+(saveFailed?' *':'');
 if(label.string!==next)label.string=next;
 positionLabel();
}
function positionLabel(){
 try{
  if(!panel||!panel.balance||!label)return;
  var base=panel.balance.node,bt=base.getComponent(cc.UITransform),p=base.position;
  var sx=base.scale.x,sy=base.scale.y;
  var x=p.x+(1-bt.anchorX)*bt.width*sx+12;
  var parent=base.parent,pt=parent.getComponent(cc.UITransform);
  var right=pt?(1-pt.anchorX)*pt.width:340;
  // Reserve space for the existing round ID on the same line, if present.
  var seq=panel.gameSeq&&panel.gameSeq.node;
  if(seq&&seq.parent===parent&&Math.abs(seq.position.y-p.y)<40){var st=seq.getComponent(cc.UITransform);if(st)right=Math.min(right,seq.position.x-st.anchorX*st.width*seq.scale.x-12);}
  var width=Math.max(80,Math.min(330,right-x-8));
  label.node.setPosition(x,p.y,base.position.z);
  var transform=label.node.getComponent(cc.UITransform);transform.setContentSize(width,Math.max(32,(panel.balance.lineHeight||30)*sy));
 }catch(e){}
}
function mount(next){
 if(!cc||!next||!next.balance||!alive(next.balance.node))return;
 if(panel===next&&label&&alive(label.node)){positionLabel();return;}
 if(label&&alive(label.node))label.node.destroy();
 panel=next;
 var base=next.balance,node=new cc.Node('MintWagerTotal');node.layer=base.node.layer;
 base.node.parent.addChild(node);
 var transform=node.addComponent(cc.UITransform);transform.setAnchorPoint(0,base.node.getComponent(cc.UITransform).anchorY);
 label=node.addComponent(cc.Label);label.useSystemFont=true;label.fontFamily='Arial';
 label.fontSize=Math.max(14,Math.min(24,base.fontSize*base.node.scale.y));label.lineHeight=label.fontSize+4;
 label.color=base.color.clone();label.horizontalAlign=0;label.verticalAlign=1;
 label.overflow=2;label.enableWrapText=false;
 // Reposition only when balance text/layout changes, never on every frame.
 if(!next.setBalance.__mintWager20){
  var original=next.setBalance;
  var update=function(){var result=original.apply(this,arguments);try{positionLabel();}catch(e){}return result;};
  update.__mintWager20=true;next.setBalance=update;
 }
 refreshLabel();
}
function loadEngine(){
 if(cc||loadingCC||!window.System||typeof System.import!=='function')return;
 loadingCC=true;
 System.import('cc').then(function(module){cc=module;loadingCC=false;tick();},function(){loadingCC=false;});
}
function tick(){
 if(stopped)return;
 if(timer){clearTimeout(timer);timer=null;}
 try{
  if(!store)store=window.MintWagerCounter;
  if(total===null||Date.now()-lastRead>15000)readTotal();
  loadEngine();
  if(window.puremvc&&puremvc.Facade){
   var facade=puremvc.Facade.getInstance();
   watchProxy(facade.retrieveProxy('MinesServerProxy'));
   var mediator=facade.retrieveMediator('AppMediator');if(mediator){mount(mediator.infoPanel);history.mount(mediator);}
  }
  pending.forEach(function(value,key){persist(key,value);});
 }catch(e){}
 // Constant-size lookups only. Stop startup polling if this version is unsupported.
 if((proxy&&label)||Date.now()-start<300000)timer=setTimeout(tick,proxy&&label?2500:300);
}
window.addEventListener('pagehide',function(){stopped=true;if(timer)clearTimeout(timer);});
window.addEventListener('pageshow',function(){stopped=false;start=Date.now();tick();});
window.addEventListener('resize',positionLabel);
tick();
})();
