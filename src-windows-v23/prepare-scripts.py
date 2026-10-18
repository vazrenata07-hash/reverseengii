from pathlib import Path

root = Path(__file__).resolve().parent
scripts = root / 'scripts'
scripts.mkdir(exist_ok=True)
prefix = (root / 'profile-and-bridge.js').read_text()
for variant in ['danill0']:
    source = (root.parent / 'variants-v21' / (variant + '.js')).read_text()
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
    source = source.replace(" // Keep the whitelist of controls separate from all user click handling.", """ if(window.jsBridge&&nativeCount!==current.size){
  try{window.jsBridge.setHideElementCount(current.size);window.jsBridge.setElementsHidden(true);window.jsBridge.setAddDomListener(true);nativeCount=current.size;}catch(e){}
 }
 // Keep the whitelist of controls separate from all user click handling.""")
    (scripts / (variant + '.js')).write_text(prefix + '\n' + source)
