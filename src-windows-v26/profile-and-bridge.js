(function(){
 'use strict';
 // Android Mint exposes these six native adblock methods as window.jsBridge.
 // The captured lobby adds/deletes jsBridge.onWebviewEvents during registration.
 // Keep our own wrapper frozen, and expose an extensible copy for that callback.
 if(window.top===window&&/(^|\.)888pg\.cc$/i.test(location.hostname)&&window.chrome&&chrome.webview){
  try{
   var hostBridge=chrome.webview.hostObjects.sync.mintAdblock;
   if(hostBridge){
    window.__mintAdblockBridge=Object.freeze({
     getAddDomListener:function(){return !!hostBridge.getAddDomListener();},
     getElemhideSelectors:function(){return String(hostBridge.getElemhideSelectors());},
     isElementsHidden:function(){return !!hostBridge.isElementsHidden();},
     setAddDomListener:function(value){hostBridge.setAddDomListener(!!value);},
     setElementsHidden:function(value){hostBridge.setElementsHidden(!!value);},
     setHideElementCount:function(value){hostBridge.setHideElementCount(Math.max(0,Math.min(1000000,Number(value)||0)));}
    });
    if(typeof window.jsBridge==='undefined'){
     window.jsBridge=Object.assign({},window.__mintAdblockBridge);
    }
   }
  }catch(e){}
 }

 if(!/^\/h5\/games\/9\/9014\//.test(location.pathname)||!/(^|\.)brteachcor\.com$/i.test(location.hostname))return;
 if(!window.chrome||!chrome.webview)return;
 var channel='mint-counter-windows-v21',sequence=0,waiting=new Map();
 var token=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)+'-';
 chrome.webview.addEventListener('message',function(event){
  var data=event.data;if(!data||data.channel!==channel)return;
  var entry=waiting.get(data.id);if(!entry)return;
  clearTimeout(entry.timer);waiting.delete(data.id);entry.resolve(JSON.stringify(data.result||{error:true}));
 });
 function request(action,game,round,milli){
  return new Promise(function(resolve){
   var id=token+(++sequence);
   var timer=setTimeout(function(){waiting.delete(id);resolve('{"error":true}');},10000);
   waiting.set(id,{resolve:resolve,timer:timer});
   try{chrome.webview.postMessage({channel:channel,id:id,action:action,game:game,round:round,milli:milli});}
   catch(e){clearTimeout(timer);waiting.delete(id);resolve('{"error":true}');}
  });
 }
 window.MintWagerCounter={total:function(){return request('total');},record:function(game,round,milli){return request('record',game,round,milli);}};
})();
