(function () {
'use strict';
if (window.top !== window || window.MintPopupCapture) return;
var host = location.hostname.toLowerCase();
if (host !== '888pg.cc' && !host.endsWith('.888pg.cc')) return;
var d = document, running = true, events = [], seq = 0, nextLayer = 0;
var pageId = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
var tracked = new Map(), known = new WeakMap(), pending = new Set(), scanTimer = null;
var labels = /(?:b[oô]nus de aposta efetivo|b[oô]nus de login di[aá]rio|clube vip|cadastro conclu[ií]do|n[aã]o mostrar novamente hoje|convidar amigos|deposite agora|sorteio|escolha um pr[eê]mio|abrir|fechar|ativar|registro|registrar|captcha|verifica[çc][aã]o)/ig;
var closes = '[class*="close" i],[class*="fechar" i],[aria-label*="close" i],[aria-label*="fechar" i],img[src*="close" i],button,[role="button"]';
var layers = '[role="dialog"],[aria-modal="true"],[class*="popup" i],[class*="modal" i],[class*="overlay" i],[class*="dialog" i],[class*="mask" i],[class*="_fast" i]';
function cleanPath(value) {
 try { var u = new URL(value, location.href); return u.protocol === 'http:' || u.protocol === 'https:' ? u.origin + u.pathname.replace(/[A-Za-z0-9_-]{70,}/g,'[long-id]') : '[' + u.protocol + ']'; } catch (_) { return ''; }
}
function allowedLabels(el) {
 if (!el || el.matches('input,textarea,script,style,[contenteditable]') || el.closest('[contenteditable]')) return [];
 var found = [], walk = d.createTreeWalker(el, NodeFilter.SHOW_TEXT), node, visited = 0;
 while ((node = walk.nextNode()) && ++visited < 250) {
  if (node.parentElement.closest('input,textarea,script,style,[contenteditable]')) continue;
  var matches = (node.nodeValue || '').match(labels) || [];
  for (var i=0;i<matches.length;i++) if (found.indexOf(matches[i]) < 0) found.push(matches[i]);
  if (found.length >= 12) break;
 }
 return found;
}
function escapeCSS(s) { return window.CSS && CSS.escape ? CSS.escape(s) : s.replace(/[^a-zA-Z0-9_-]/g, function(c){return '\\' + c.codePointAt(0).toString(16) + ' ';}); }
function selector(el) {
 if (!el || !el.tagName) return '';
 var parts = [], n = el;
 for (var i=0;n && n!==d.documentElement && i<5;i++,n=n.parentElement) {
  var part = n.tagName.toLowerCase();
  if (n.id) {parts.unshift(part+'#'+escapeCSS(n.id.slice(0,100)));break;}
  var names = Array.from(n.classList).slice(0,5); if(names.length) part += '.'+names.map(escapeCSS).join('.');
  if(n.parentElement) {var peers=Array.from(n.parentElement.children).filter(function(x){return x.tagName===n.tagName});if(peers.length>1)part+=':nth-of-type('+(peers.indexOf(n)+1)+')';}
  parts.unshift(part);
 }
 return parts.join(' > ');
}
function rect(el) {var r=el.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)};}
function visible(el) {if(!el || !el.isConnected || !el.getClientRects().length)return false;var s=getComputedStyle(el);return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)!==0;}
function info(el) {
 if (!el || !el.tagName) return null;
 var s=getComputedStyle(el), out={tag:el.tagName.toLowerCase(),selector:selector(el),class:Array.from(el.classList).slice(0,12),role:el.getAttribute('role'),box:rect(el),visible:visible(el),css:{display:s.display,visibility:s.visibility,position:s.position,zIndex:s.zIndex,pointerEvents:s.pointerEvents,opacity:s.opacity,overflow:s.overflow,transform:s.transform,filter:s.filter,backdropFilter:s.backdropFilter||''}};
 if(el.matches('img,iframe'))out.src=cleanPath(el.getAttribute('src')||'');
 if(el.matches('input,textarea'))out.field=true;
 return out;
}
function snapshot(el) {
 var out=info(el);out.labels=allowedLabels(el);out.tree=[];
 var list=el.querySelectorAll('*');
 for(var i=0;i<list.length&&out.tree.length<60;i++){
  var n=list[i];if(n.matches('script,style,input,textarea,option,[contenteditable]')||n.closest('[contenteditable]'))continue;
  if(i<24||n.matches('img,button,[role="button"],svg,[class*="close" i],[class*="_fast" i]'))out.tree.push(info(n));
 }
 out.truncated=list.length>out.tree.length;return out;
}
function emit(kind,data) {
 if(!running || seq>=1000)return;
 var event={schema:1,kind:kind,pageId:pageId,seq:++seq,time:Date.now(),page:cleanPath(location.href),data:data};
 events.push(event);

}
function isClose(el) {return /close|fechar|dismiss/i.test([el.getAttribute('class'),el.getAttribute('aria-label'),el.getAttribute('src')].join(' '))||/^[×✕✖xX]$/.test((el.textContent||'').trim());}
function consider(el) {
 if(!el||!el.tagName||el===d.body||el===d.documentElement||el.matches('#app,#root,main,[role="main"]'))return;
 if(known.has(el))return;
 var r=el.getBoundingClientRect();if(r.width<24||r.height<24||!visible(el))return;
 var s=getComputedStyle(el),hint=el.matches(layers),positioned=s.position==='fixed'||s.position==='absolute';
 if(!hint&&!positioned)return;
 if(!hint && r.width<70 && r.height<70)return;
 if(!hint && !el.querySelector(closes) && !el.querySelector('img,canvas') && !allowedLabels(el).length)return;
 var id=++nextLayer;known.set(el,id);tracked.set(el,{id:id,visible:true});
 emit('popup_seen',{id:id,popup:snapshot(el)});
 if(tracked.size>100)tracked.delete(tracked.keys().next().value);
}
function scan() {
 scanTimer=null;if(!running||!d.body)return;
 var nodes=d.querySelectorAll(layers+','+closes);
 for(var i=0;i<nodes.length&&i<450;i++){
  var n=nodes[i];consider(n);
  if(n.matches(closes)&&isClose(n))for(var p=n.parentElement,depth=0;p&&depth<7;p=p.parentElement,depth++)consider(p);
 }
 pending.forEach(function(n){if(n.nodeType!==1)return;consider(n);var descendants=n.querySelectorAll('*');for(var j=0;j<descendants.length&&j<120;j++)consider(descendants[j]);});pending.clear();
 tracked.forEach(function(state,el){var v=visible(el);if(v!==state.visible){state.visible=v;emit(v?'popup_shown':'popup_hidden',{id:state.id,connected:el.isConnected,popup:info(el)});}if(!el.isConnected)tracked.delete(el);});
}
function schedule(){if(!scanTimer&&running)scanTimer=setTimeout(scan,180);}
var observer=new MutationObserver(function(ms){for(var i=0;i<ms.length&&pending.size<180;i++){var m=ms[i];if(m.type==='childList')for(var j=0;j<m.addedNodes.length&&pending.size<180;j++)pending.add(m.addedNodes[j]);else pending.add(m.target);}schedule();});
observer.observe(d,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style','hidden','aria-hidden','src']});
var interaction=0;
function onAction(event) {
 if(!running||!event.isTrusted)return;
 var target=event.target&&event.target.nodeType===1?event.target:event.target.parentElement;
 if(!target||target.closest('input,textarea,select,[contenteditable]'))return;
 var point=event.changedTouches&&event.changedTouches[0]||event;
 var x=Number(point.clientX)||0,y=Number(point.clientY)||0,id=++interaction;
 // Snapshot in capture phase, before the site can detach the clicked popup.
 scan();
 var ancestors=[],p=target;for(var i=0;p&&i<9;p=p.parentElement,i++)ancestors.push(info(p));
 var stack=d.elementsFromPoint?d.elementsFromPoint(x,y).slice(0,9).map(info):[];
 var active=[];tracked.forEach(function(state,el){if(visible(el)&&active.length<8)active.push({id:state.id,node:el});});
 emit('interaction',{id:id,event:event.type,point:{x:x,y:y},target:info(target),labels:allowedLabels(target),ancestors:ancestors,hitStack:stack,popups:active.map(function(v){return {id:v.id,popup:snapshot(v.node)};})});
 [120,500,1200].forEach(function(delay){setTimeout(function(){if(!running)return;emit('after_interaction',{id:id,delay:delay,popups:active.map(function(v){return {id:v.id,connected:v.node.isConnected,visible:visible(v.node),state:info(v.node)};})});},delay);});
}
var actionEvents=window.PointerEvent?['pointerdown','click']:['touchstart','click'];
actionEvents.forEach(function(name){window.addEventListener(name,onAction,{capture:true,passive:true});});
function route(){emit('navigation',{});schedule();}
window.addEventListener('hashchange',route);window.addEventListener('popstate',route);

function report(){return JSON.stringify({schema:1,build:'windows-console-1',observerOnly:true,events:events},null,2);}
function stop(){
 if(running)emit('capture_stopped',{});running=false;observer.disconnect();clearTimeout(scanTimer);
 actionEvents.forEach(function(name){window.removeEventListener(name,onAction,true);});
 window.removeEventListener('hashchange',route);window.removeEventListener('popstate',route);
 d.removeEventListener('DOMContentLoaded',schedule);
 return events.length;
}
window.MintPopupCapture={exportJSON:report,stop:stop,download:function(){
 stop();
 var blob=new Blob([report()],{type:'application/json'}),url=URL.createObjectURL(blob),a=d.createElement('a');
 a.href=url;a.download='captura-popups-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';a.click();
 setTimeout(function(){URL.revokeObjectURL(url)},30000);
 console.log('Captura encerrada. Relatório baixado com '+events.length+' registros.');
},status:function(){return {active:running,records:events.length,popups:nextLayer};}};
console.log('CAPTURA ATIVA: feche os pop-ups manualmente. Ao terminar, execute MintPopupCapture.download() neste Console. Não recarregue a página antes de salvar.');
emit('capture_started',{viewport:{width:innerWidth,height:innerHeight},observerOnly:true,fieldsRecorded:false});
if(d.body)pending.add(d.body);schedule();d.addEventListener('DOMContentLoaded',schedule);
})();