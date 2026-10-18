(function(){
 'use strict';
 // WebView2's CDP override supplies HTTP User-Agent and Client Hints.
 // This document-start fallback keeps JavaScript identification consistent.
 var version='__MINT_CHROME_VERSION__',major=version.split('.')[0];
 var brands=[{brand:'Chromium',version:major},{brand:'Android WebView',version:major},{brand:'Not_A Brand',version:'99'}];
 function getBrands(){return brands.map(function(b){return {brand:b.brand,version:b.version};});}
 function low(){return {brands:getBrands(),mobile:true,platform:'Android'};}
 var uaData={get brands(){return getBrands();},mobile:true,platform:'Android',toJSON:low,
  getHighEntropyValues:function(hints){
   var data=low(),known={architecture:'arm',bitness:'64',model:'SM-A536B',platformVersion:'13.0.0',
    uaFullVersion:version,wow64:false,formFactors:['Mobile'],
    fullVersionList:brands.map(function(b){return {brand:b.brand,version:b.brand==='Not_A Brand'?'99.0.0.0':version};})};
   if(Array.isArray(hints))hints.forEach(function(name){if(typeof name==='string')data[name]=Object.prototype.hasOwnProperty.call(known,name)?known[name]:'unknown';});
   return Promise.resolve(data);
  }
 };
 function identify(name,value){try{Object.defineProperty(navigator,name,{configurable:true,get:function(){return value;}});}catch(e){}}
 identify('platform','Linux armv8l');identify('vendor','Google Inc.');identify('maxTouchPoints',5);
 identify('userAgentData',uaData);identify('oscpu','Linux armv8l');

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
