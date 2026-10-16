from pathlib import Path
p=Path('work/rebuild-filter.js');s=p.read_text().replace('__mintRebuilt17','__mintRebuilt18')
start=s.index('function autofill(){')
pin=r'''
// Withdrawal PIN is independent of the account password. Never submit a form.
var withdrawalPIN='232691',pinWritten=new WeakSet(),pinBusy=false;
var pinWidgets='.ui-password-input,.van-password-input';
var pinKeys='.ui-number-keyboard,.van-number-keyboard';
function visible(el){return !!el&&!!el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden'&&getComputedStyle(el).display!=='none';}
function withdrawalContext(el){
 if(el.closest(security))return false;
 var meta=[el.name,el.id,el.placeholder,el.getAttribute('aria-label')].join(' ');
 if(/captcha|otp|one.time|verifica|sms|c[oó]digo/i.test(meta))return false;
 if(/(?:withdraw|saque).*(?:pass|senha|pin)|(?:pass|senha|pin).*(?:withdraw|saque)/i.test(meta))return true;
 var area=el.closest('[role="dialog"],.ui-dialog,.ui-popup,.van-dialog,.van-popup');
 var text=(area||d.body).textContent||'';
 if(!/senha\s+(?:de |para (?:o )?)?saque/i.test(text))return false;
 return !!area||/(?:^|[\/#])(?:security|withdraw)(?:[\/?#]|$)/i.test(location.pathname+location.hash);
}
function pinInput(el){
 if(!withdrawalContext(el))return false;
 var meta=[el.name,el.id,el.placeholder,el.autocomplete,el.getAttribute('aria-label')].join(' ');
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
  if(cells[i].textContent.trim()||cells[i].querySelector('i:not([style*="display: none"])'))count++;
 }
 return count;
}
function customPIN(){
 if(pinBusy)return;
 var widgets=d.querySelectorAll(pinWidgets),target=null;
 for(var i=0;i<widgets.length;i++){
  var el=widgets[i];
  if(!visible(el)){pinWritten.delete(el);continue;}
  if(!pinWritten.has(el)&&withdrawalContext(el)&&!el.querySelector('input')&&filledCells(el)===0){target=el;break;}
 }
 if(!target)return;
 pinBusy=true;pinWritten.add(target);
 var focus=target.querySelector('ul')||target;focus.click();
 var index=0,waits=0;
 function step(){
  if(!target.isConnected||!visible(target)){pinBusy=false;return;}
  var boards=d.querySelectorAll(pinKeys),keyboard=null;
  for(var k=0;k<boards.length;k++)if(visible(boards[k])){keyboard=boards[k];break;}
  if(!keyboard){if(++waits<8){setTimeout(step,60);return;}pinWritten.delete(target);pinBusy=false;return;}
  if(index===0&&filledCells(target)>0){pinBusy=false;return;}
  if(index<6){
   if(!emitKeyboardDigit(keyboard,withdrawalPIN[index])){pinBusy=false;return;}
   index++;setTimeout(step,35);return;
  }
  pinBusy=false;setTimeout(customPIN,60);
 }
 setTimeout(step,60);
}
'''
s=s[:start]+pin+s[start:]
s=s.replace("var reg=route(),all=d.querySelectorAll('input'),first=null,named=null;", "var reg=route(),all=d.querySelectorAll('input'),first=null,named=null,segments=[];")
s=s.replace("if(el.type==='password'||/senha|password/.test(meta)){", """if(pinInput(el)){
   if(el.maxLength===1){segments.push(el);continue;}
   if(!el.value&&!pinWritten.has(el)){pinWritten.add(el);write(el,withdrawalPIN);}continue;
  }
  if(withdrawalContext(el))continue;
  if(el.type==='password'||/senha|password/.test(meta)){""")
s=s.replace(' var target=named||first;', ''' // Only complete groups of six empty single-character inputs are PINs.
 for(var j=0;j+5<segments.length;j+=6){
  var group=segments.slice(j,j+6);
  if(group.every(function(e){return !e.value&&!pinWritten.has(e);})){group.forEach(function(e,k){pinWritten.add(e);write(e,withdrawalPIN[k]);});}
 }
 customPIN();
 var target=named||first;''')
s=s.replace("node.matches('input')||node.querySelector('input')", "node.matches('input,'+pinWidgets+','+pinKeys)||node.querySelector('input,'+pinWidgets+','+pinKeys)")
s=s.replace("if(target.matches('input'))formDirty=true;", """if(target.matches('input'))formDirty=true;
   if((m.attributeName==='style'||m.attributeName==='class')&&
      (target.matches(pinWidgets+','+pinKeys)||target.matches('.ui-popup,.ui-dialog,.van-popup,.van-dialog')&&target.querySelector('input,'+pinWidgets)))formDirty=true;""")
s=s.replace("window.addEventListener('hashchange',navigation)", "d.addEventListener('focusin',function(e){if(e.target.matches('input')){formDirty=true;queue();}});\nd.addEventListener('click',function(e){if(e.target.closest&&e.target.closest(pinWidgets)){setTimeout(function(){formDirty=true;queue();},80);}},true);\nwindow.addEventListener('hashchange',navigation)")
p.write_text(s)
Path('work/rebuild-apk/assets/mint-rebuilt.js').write_text(s)
v=Path('work/variants-v18');v.mkdir(exist_ok=True)
for password in ['danill0','87654321']:(v/(password+'.js')).write_text(s.replace("write(el,'danill0')","write(el,'"+password+"')"))
p=Path('work/rebuild-apk/apktool.yml');p.write_text(p.read_text().replace('20220335','20220336').replace('3.9.3-Refeito-v17','3.9.3-Refeito-v18'))
p=Path('work/package18.py');p.write_text(Path('work/package17.py').read_text().split("p=Path('work/patch17.py')")[0].replace('v17','v18'))
