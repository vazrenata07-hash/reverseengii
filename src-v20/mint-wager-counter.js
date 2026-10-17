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
   var mediator=facade.retrieveMediator('AppMediator');if(mediator)mount(mediator.infoPanel);
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
