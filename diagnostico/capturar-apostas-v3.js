(function(){
'use strict';
var outerFrames=Array.from(document.querySelectorAll('iframe')).filter(function(e){var r=e.getBoundingClientRect();return r.width>150&&r.height>150;});
if(!document.querySelector('canvas')&&outerFrames.length){
 console.error('CAPTURA NÃO INICIADA: este contexto contém outro iframe. No menu de contexto do Console (top), selecione o frame abaixo e execute novamente este script. Não é necessário registrar rodadas nesta camada.');
 console.table(outerFrames.map(function(e){try{var u=new URL(e.src,location.href);return {selecionar:u.hostname,caminho:u.pathname};}catch(err){return {selecionar:'frame interno'};}}));
 return;
}
if(window.BetCapture){console.info('Já existe uma captura neste contexto. Para recuperar sem download: copy(BetCapture.json()) se disponível; caso contrário use o comando anterior que copia o Blob.');return;}
var hooks={},started=Date.now(),events=[],undo=[],active=true,seq=0,refs=new Map(),seenSockets=new WeakSet();
var secret=/password|passwd|senha|token|authorization|cookie|secret|session|credential|email|phone|cpf|pix|username|account|player|userid|user_id|signature|salt|nonce/i;
var money=/^(amount|bet|bets|betamount|betvalue|totalbet|total_bet|stake|wager|wageramount|balance|credits|credit|debit|win|wins|totalwin|payout|profit|coinvalue|coin_value|betlevel|bet_level|denomination|currency|tb|tbb|bl|blb|bla|tw|cs|ml)$/i;
var action=/^(action|event|type|command|cmd|method|state|status|success|error|code|currency|operation|op)$/i;
function ref(v){var key=typeof v+':'+v;if(!refs.has(key))refs.set(key,'ref-'+(refs.size+1));return refs.get(key);}
function clean(v,key,depth){
 if(secret.test(key||''))return '[omitido]';
 if(depth>8)return '[profundidade]';
 if(typeof v==='string'&&v.length<200000&&/^[\[{]/.test(v.trim())){try{return clean(JSON.parse(v),key,depth+1);}catch(e){}}
 if(v===null||typeof v==='boolean')return v;
 if(Array.isArray(v))return v.slice(0,30).map(function(x){return clean(x,key,depth+1);});
 if(typeof v==='object'){var out={};Object.keys(v).slice(0,100).forEach(function(k){out[k.slice(0,100)]=clean(v[k],k,depth+1);});return out;}
 if(/(?:round|transaction|request|message|spin).*id|^(id|rid|sid)$/i.test(key||''))return ref(v);
 if(typeof v==='number')return Number.isFinite(v)?v:null;
 if(money.test(key||'')&&/^-?\d+(?:[.,]\d+)?$/.test(String(v)))return v;
 if(action.test(key||'')&&(typeof v==='number'||/^[a-z0-9_ .:-]{1,60}$/i.test(String(v))))return v;
 return '['+typeof v+']';
}
function url(raw){try{var u=new URL(raw,location.href),query={};u.searchParams.forEach(function(v,k){query[k]=clean(v,k,0);});return {origin:u.origin,path:u.pathname.replace(/[a-z0-9_-]{35,}/ig,'[id]'),query:query};}catch(e){return {invalid:true};}}
function payload(body){
 if(body==null)return null;
 if(typeof body==='string'){
  if(body.length>250000)return {format:'large',bytes:body.length};
  try{return {format:'json',data:clean(JSON.parse(body),'',0)};}catch(e){}
  if(/^[a-zA-Z_][a-zA-Z0-9_.-]{0,60}=/.test(body)){try{var out={};new URLSearchParams(body).forEach(function(v,k){try{out[k]=JSON.parse(v);}catch(e){out[k]=v;}});return {format:'form',data:clean(out,'',0)};}catch(e){}}
  return {format:'text',length:body.length};
 }
 if(body instanceof URLSearchParams)return payload(body.toString());
 if(typeof FormData!=='undefined'&&body instanceof FormData){var o={};body.forEach(function(v,k){o[k]=typeof v==='string'?v:'[file]';});return {format:'form',data:clean(o,'',0)};}
 if(typeof Blob!=='undefined'&&body instanceof Blob)return {format:'binary',bytes:body.size};
 if(body instanceof ArrayBuffer||ArrayBuffer.isView(body))return {format:'binary',bytes:body.byteLength};
 return {format:'object',data:clean(body,'',0)};
}
function log(kind,data){if(active&&events.length<1600)events.push({t:Date.now()-started,kind:kind,data:data});}
function attempt(fn){try{fn();}catch(e){log('capture-error',{type:e.name});}}
function rect(e){var r=e.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)};}
function node(e){return {tag:e.tagName,classes:typeof e.className==='string'?e.className.slice(0,250):'',rect:rect(e)};}
function snapshot(){
 var d=document,labels=[],all=d.querySelectorAll('body *');
 for(var i=0;i<all.length&&i<30000&&labels.length<100;i++){
  var e=all[i];if(e.children.length||/INPUT|TEXTAREA|SCRIPT|STYLE/.test(e.tagName))continue;
  var t=(e.textContent||'').trim();
  if(/^(?:R\$\s*[\d.,]+|saldo|aposta|apostas|ganha|minas|parar autoplay|começar|apostar)$/i.test(t)&&e.getClientRects().length){var item=node(e);item.label=t;labels.push(item);}
 }
 return {page:url(location.href),topFrame:window===window.top,viewport:{width:innerWidth,height:innerHeight},canvases:Array.from(d.querySelectorAll('canvas')).map(function(e){return Object.assign(node(e),{width:e.width,height:e.height});}),iframes:Array.from(d.querySelectorAll('iframe')).map(function(e){return Object.assign(node(e),{source:url(e.src)});}),scripts:Array.from(d.scripts).filter(function(e){return e.src;}).slice(0,80).map(function(e){return url(e.src);}),engines:{phaser:!!window.Phaser,pixi:!!window.PIXI,cocos:!!window.cc,unity:!!window.unityInstance},labels:labels};
}
function replace(obj,key,value,label){
 label=label||key;
 try{
  var original=obj[key];
  obj[key]=value;
  if(obj[key]!==value)throw new TypeError('Property unchanged');
  hooks[label]='installed';
  undo.push(function(){try{if(obj[key]===value)obj[key]=original;}catch(e){}});
  return true;
 }catch(e){
  hooks[label]='unavailable';
  log('hook-unavailable',{api:label,reason:e.name});
  console.warn('Captura: '+label+' protegido; continuando pelos outros canais.');
  return false;
 }
}
if(window.fetch){var originalFetch=window.fetch;replace(window,'fetch',function(input,init){
 var id=++seq,result=originalFetch.apply(this,arguments);
 attempt(function(){log('fetch-request',{id:id,url:url(typeof input==='string'?input:input.url),method:init&&init.method||input.method||'GET',body:payload(init&&init.body)});
  if(input instanceof Request&&!(init&&init.body)&&input.method!=='GET')input.clone().text().then(function(t){log('fetch-request-body',{id:id,body:payload(t)});}).catch(function(){});
  result.then(function(response){attempt(function(){var ct=response.headers.get('content-type')||'';log('fetch-status',{id:id,status:response.status});if(/json|text|form/i.test(ct))response.clone().text().then(function(t){log('fetch-response',{id:id,body:payload(t)});}).catch(function(){});});},function(){log('fetch-error',{id:id});});
 });return result;
});}
if(window.XMLHttpRequest){var xp=XMLHttpRequest.prototype,open=xp.open,send=xp.send,xhrMeta=new WeakMap();
 replace(xp,'open',function(method,address){var result=open.apply(this,arguments);xhrMeta.set(this,{method:method,url:url(address)});return result;},'xhr.open');
 replace(xp,'send',function(body){var xhr=this,id=++seq;attempt(function(){log('xhr-request',Object.assign({id:id,body:payload(body)},xhrMeta.get(xhr)||{}));xhr.addEventListener('loadend',function(){attempt(function(){var rt=xhr.responseType;log('xhr-response',{id:id,status:xhr.status,body:rt==='json'?{format:'json',data:clean(xhr.response,'',0)}:rt===''||rt==='text'?payload(xhr.responseText):{format:rt}});});},{once:true});});return send.apply(this,arguments);},'xhr.send');
}
function watchSocket(socket){if(seenSockets.has(socket))return;seenSockets.add(socket);var listener=function(e){attempt(function(){log('ws-receive',{url:url(socket.url),body:payload(e.data)});});};socket.addEventListener('message',listener);undo.push(function(){socket.removeEventListener('message',listener);});}
if(window.WebSocket){var OriginalSocket=WebSocket,wsSend=OriginalSocket.prototype.send;replace(OriginalSocket.prototype,'send',function(body){var result=wsSend.apply(this,arguments),socket=this;attempt(function(){watchSocket(socket);log('ws-send',{url:url(socket.url),body:payload(body)});});return result;},'websocket.send');
 if(window.Proxy)replace(window,'WebSocket',new Proxy(OriginalSocket,{construct:function(target,args){var socket=Reflect.construct(target,args);watchSocket(socket);return socket;}}));
}
var click=function(e){attempt(function(){log('click',{x:Math.round(e.clientX),y:Math.round(e.clientY),target:node(e.target)});});};document.addEventListener('click',click,true);undo.push(function(){document.removeEventListener('click',click,true);});
// Resource timings are read-only observations: available even with frozen APIs.
if(window.PerformanceObserver)attempt(function(){
 var observer=new PerformanceObserver(function(list){list.getEntries().forEach(function(e){
  if(/^(fetch|xmlhttprequest|other)$/.test(e.initiatorType))log('resource',{url:url(e.name),type:e.initiatorType,duration:Math.round(e.duration)});
 });});
 observer.observe({type:'resource',buffered:true});
 undo.push(function(){observer.disconnect();});
});
var initial=snapshot();
window.BetCapture={json:function(){return JSON.stringify({version:3,hooks:hooks,started:new Date(started).toISOString(),initial:initial,final:snapshot(),events:events},null,2);},status:function(){return {active:active,hooks:hooks,events:events.length,seconds:Math.round((Date.now()-started)/1000),frame:location.origin,canvas:initial.canvases.length};},download:function(){var report={version:3,hooks:hooks,started:new Date(started).toISOString(),initial:initial,final:snapshot(),events:events};var a=document.createElement('a'),link=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));a.href=link;a.download='captura-apostas-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';a.click();setTimeout(function(){URL.revokeObjectURL(link);},30000);console.info('Arquivo JSON solicitado ao Chrome. Eventos:',events.length);},stop:function(){active=false;undo.reverse().forEach(function(fn){attempt(fn);});console.info('Captura encerrada. BetCapture.download() continua disponível.');}};
var networkAvailable=hooks.fetch==='installed'||hooks['xhr.send']==='installed'||hooks['websocket.send']==='installed';
console.info('%c'+(networkAvailable?'CAPTURA DE APOSTAS ATIVA':'CAPTURA LIMITADA — APIs de rede protegidas'),'background:#065f46;color:white;padding:8px;font-size:16px',BetCapture.status());
if(!networkAvailable)console.warn('Não registre novas rodadas para esta captura: os dados das respostas não estão acessíveis. Copie agora o diagnóstico com copy(BetCapture.json()).');
if(initial.iframes.length&&!initial.canvases.length)console.warn('Este contexto pode ser só a página externa. Selecione o frame do jogo no menu "top" do Console e cole o script também nesse frame. Baixe o relatório no contexto do jogo.');
console.info('Somente observa. Não aposta, não bloqueia cliques e não altera respostas. Copiar sem download: copy(BetCapture.json()) | Parar: BetCapture.stop()');
})();
