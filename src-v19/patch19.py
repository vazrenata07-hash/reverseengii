from pathlib import Path
p=Path('work/rebuild-filter.js');s=p.read_text().replace('__mintRebuilt18','__mintRebuilt19')
s=s.replace("pinWritten=new WeakSet(),pinBusy=false", "pinWritten=new WeakSet(),pinAttempts=new WeakMap(),pinBusy=false")
s=s.replace("var dot=cells[i].querySelector('i');", "var dot=cells[i].querySelector('i:not([class*=\"cursor\"])');")
start=s.index('function customPIN(){');end=s.index('function autofill(){',start)
s=s[:start]+r'''function focusPIN(target){
 var focus=target.querySelector('ul')||target;
 // These password widgets receive focus via touchstart, not a mouse click.
 focus.dispatchEvent(new Event('touchstart',{bubbles:true,cancelable:true}));
 focus.dispatchEvent(new Event('touchend',{bubbles:true,cancelable:true}));
 focus.click();
}
function customPIN(){
 if(pinBusy)return;
 var widgets=d.querySelectorAll(pinWidgets),target=null;
 for(var i=0;i<widgets.length;i++){
  var el=widgets[i];
  if(!visible(el)){pinWritten.delete(el);pinAttempts.delete(el);continue;}
  if(!pinWritten.has(el)&&(pinAttempts.get(el)||0)<2&&withdrawalContext(el)&&!el.querySelector('input')&&filledCells(el)===0){target=el;break;}
 }
 if(!target)return;
 pinBusy=true;pinAttempts.set(target,(pinAttempts.get(target)||0)+1);
 focusPIN(target);
 var index=0,waits=0,ackWaits=0;
 function stop(){
  pinBusy=false;
  if(target.isConnected&&visible(target)&&filledCells(target)===0&&(pinAttempts.get(target)||0)<2)setTimeout(customPIN,250);
 }
 function step(){
  if(!target.isConnected||!visible(target)){stop();return;}
  var count=filledCells(target);
  // Wait for this widget to acknowledge the last digit before proceeding.
  if(count!==index){
   if(count===index-1&&++ackWaits<15){setTimeout(step,40);return;}
   stop();return;
  }
  ackWaits=0;
  if(index===6){pinWritten.add(target);pinBusy=false;setTimeout(customPIN,180);return;}
  var boards=d.querySelectorAll(pinKeys),keyboard=null;
  for(var k=0;k<boards.length;k++)if(visible(boards[k])){keyboard=boards[k];break;}
  if(!keyboard){if(++waits<15){setTimeout(step,60);return;}stop();return;}
  waits=0;
  if(!emitKeyboardDigit(keyboard,withdrawalPIN[index])){stop();return;}
  index++;setTimeout(step,40);
 }
 setTimeout(step,120);
}
'''+s[end:]
p.write_text(s);Path('work/rebuild-apk/assets/mint-rebuilt.js').write_text(s)
v=Path('work/variants-v19');v.mkdir(exist_ok=True)
for password in ['danill0','87654321']:(v/(password+'.js')).write_text(s.replace("write(el,'danill0')","write(el,'"+password+"')"))
p=Path('work/rebuild-apk/apktool.yml');p.write_text(p.read_text().replace('20220336','20220337').replace('3.9.3-Refeito-v18','3.9.3-Refeito-v19'))
Path('work/package19.py').write_text(Path('work/package18.py').read_text().replace('v18','v19'))
