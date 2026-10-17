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
