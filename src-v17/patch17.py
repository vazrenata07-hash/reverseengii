from pathlib import Path
import re
p=Path('work/rebuild-filter.js');s=p.read_text().replace('Rebuilt16','Rebuilt17').replace('mint16','mint17')
a=s.index('var queued=false,busy=false;')
s=s[:a]+'''// Animation styles and SVG/Lottie updates do not change the ad rules.
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
 if(!formDirty&&(node.matches('input')||node.querySelector('input')))formDirty=true;
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
window.addEventListener('hashchange',navigation);window.addEventListener('popstate',navigation);window.addEventListener('load',navigation);
d.addEventListener('DOMContentLoaded',function(){if(d.body)prepareImages(d.body);navigation();});
if(d.body)prepareImages(d.body);run();
})();
'''
p.write_text(s);Path('work/rebuild-apk/assets/mint-rebuilt.js').write_text(s)
# Patch the browser's SSL decision path, rather than merely hiding its dialog.
paths=['smali/com/miui/org/chromium/chrome/browser/adblock/AdblockWebView$e.smali','smali_classes2/com/miui/org/chromium/chrome/browser/webview/f.smali','smali_classes2/com/miui/org/chromium/chrome/browser/m0/e.smali']
backup=Path('work/ssl-before-v17');backup.mkdir(exist_ok=True)
for i,name in enumerate(paths):
 p=Path('work/rebuild-apk')/name;text=p.read_text();(backup/(str(i)+'.smali')).write_text(text)
 pattern=r'\.method public onReceivedSslError\(Landroid/webkit/WebView;Landroid/webkit/SslErrorHandler;Landroid/net/http/SslError;\)V.*?\.end method'
 replacement='''.method public onReceivedSslError(Landroid/webkit/WebView;Landroid/webkit/SslErrorHandler;Landroid/net/http/SslError;)V
    .locals 0
    invoke-virtual {p2}, Landroid/webkit/SslErrorHandler;->proceed()V
    return-void
.end method'''
 text,n=re.subn(pattern,lambda m:replacement,text,flags=re.S);assert n==1,(name,n);p.write_text(text)
p=Path('work/rebuild-apk/apktool.yml');p.write_text(p.read_text().replace('20220334','20220335').replace('Refeito-v16','Refeito-v17'))
