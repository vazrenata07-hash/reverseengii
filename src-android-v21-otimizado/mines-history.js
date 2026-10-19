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
