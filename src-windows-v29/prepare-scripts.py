from pathlib import Path

root = Path(__file__).resolve().parent
scripts = root / 'scripts'
scripts.mkdir(exist_ok=True)
prefix = (root / 'profile-and-bridge.js').read_text()
for variant in ['danill0']:
    source = (root.parent / 'src-v21' / ('mint-rebuilt-' + variant + '.js')).read_text()
    source = source.replace('function readTotal(){\n if(!store)return;',
        'var readBusy=false,inFlight=new Set();\nasync function readTotal(){\n if(!store||readBusy)return;\n readBusy=true;')
    source = source.replace('JSON.parse(store.total())', 'JSON.parse(await store.total())')
    source = source.replace('refreshLabel();}}catch(e){}\n}\nfunction persist(round,milli){',
        'refreshLabel();}}catch(e){}finally{readBusy=false;}\n}\nasync function persist(round,milli){')
    source = source.replace('if(seen.has(round)||!store)return;\n pending.set(round,milli);',
        'if(seen.has(round)||!store||inFlight.has(round))return;\n inFlight.add(round);\n pending.set(round,milli);')
    source = source.replace("JSON.parse(store.record('jdb-mines-9014',round,milli))",
        "JSON.parse(await store.record('jdb-mines-9014',round,milli))")
    source = source.replace('}catch(e){saveFailed=true;refreshLabel();}\n}',
        '}catch(e){saveFailed=true;refreshLabel();}finally{inFlight.delete(round);}\n}')
    # Publish real filter state through the ported Mint adblock interface.
    source = source.replace("var attempts=new WeakMap(),marked=new Set();", "var attempts=new WeakMap(),marked=new Set(),nativeCount=-1;")
    source = source.replace(" // Keep the whitelist of controls separate from all user click handling.", """ if(window.__mintAdblockBridge&&nativeCount!==current.size){
  try{window.__mintAdblockBridge.setHideElementCount(current.size);window.__mintAdblockBridge.setElementsHidden(true);window.__mintAdblockBridge.setAddDomListener(true);nativeCount=current.size;}catch(e){}
 }
 // Keep the whitelist of controls separate from all user click handling.""")
    # Avoid repeated whole-dialog/body reads while classifying the same input.
    # No events or DOM writes occur between the reused classification results.
    source = source.replace('function pinInput(el){\n if(!withdrawalContext(el))return false;', 'function pinInput(el,isWithdrawal){\n if(!isWithdrawal)return false;')
    source = source.replace('  if(el.disabled||el.readOnly||!el.getClientRects().length||el.closest(security)||/captcha|otp|one.time|sms/.test(meta)||(/verifica/.test(meta)&&!pinInput(el)))continue;\n  if(pinInput(el)){', "  if(el.disabled||el.readOnly||el.closest(security)||/captcha|otp|one.time|sms/.test(meta))continue;\n  // Reuse context only within this input's read-only classification.\n  // It can otherwise read the dialog/body text twice per input.\n  var isWithdrawal=withdrawalContext(el),isPIN=pinInput(el,isWithdrawal);\n  if(/verifica/.test(meta)&&!isPIN)continue;\n  if(isPIN){")
    source = source.replace('  if(withdrawalContext(el))continue;', '  if(isWithdrawal)continue;')
    (scripts / (variant + '.js')).write_text(prefix + '\n' + source)
