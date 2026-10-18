(function(){
 'use strict';
 // Match the legacy Android Browser UA supplied at HTTP/CDP level.
 // Do not supply Chrome WebView Client Hints or a fabricated OS-version mapping.
 function identify(name,value){try{Object.defineProperty(navigator,name,{configurable:true,get:function(){return value;}});}catch(e){}}
 identify('platform','Linux armv8l');identify('vendor','Google Inc.');identify('maxTouchPoints',5);
 identify('userAgentData',undefined);identify('oscpu','Linux armv8l');

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
