const {chromium}=require('playwright'),fs=require('fs'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
 const page=await b.newPage({viewport:{width:540,height:850},hasTouch:true});
 await page.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));await page.goto('https://888pg.cc/');
 await page.addScriptTag({content:fs.readFileSync(process.argv[2]||'work/rebuild-filter.js','utf8')});
 for(const obstructed of [false,true]){
 await page.evaluate(({obstructed})=>{
 document.body.innerHTML='<main id="app"><section id="reward" style="position:fixed;inset:0"><p>Bônus de login diário</p><button id="open">ABRIR</button><div id="close-hit" style="position:fixed;left:245px;top:500px;width:50px;height:50px"><button id="close" class="close" style="width:50px;height:50px">×</button></div><button class="close desktop" style="display:none">×</button><div class="close-icon-copy" style="display:none"></div></section><div id="ad" style="position:fixed;top:100px;left:0;width:80px;height:80px"><button class="close">×</button></div></main>';
 window.rewardClosed=0;window.rewardOpened=0;document.getElementById('close').onclick=()=>{window.rewardClosed++;document.getElementById('reward').remove();document.getElementById('rain')?.remove()};document.getElementById('open').onclick=()=>window.rewardOpened++;
 if(obstructed){let rain=document.createElement('div');rain.id='rain';rain.style.cssText='position:fixed;inset:0;z-index:999;pointer-events:auto';document.body.append(rain)}
 },{obstructed});await page.waitForTimeout(30);
 assert.equal(await page.locator('#close-hit').isVisible(),true,'close hit area with duplicate responsive controls must stay visible');
 await page.touchscreen.tap(270,525);await page.waitForTimeout(50);
 assert.equal(await page.evaluate(()=>window.rewardClosed),1,'close handler must receive one click, obstruction='+obstructed);
 assert.equal(await page.evaluate(()=>window.rewardOpened),0,'no opening/redeeming');assert.equal(await page.locator('#ad').isVisible(),false);
 }
 console.log('PASS: responsive duplicate close controls + touch intercepted by separate overlay; original close callback once; no ABRIR action; advertisement remains blocked.');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
