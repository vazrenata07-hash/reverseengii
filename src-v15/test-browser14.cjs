const {chromium}=require('playwright');
const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try {
 const page=await browser.newPage({viewport:{width:540,height:850}});
 await page.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));
 await page.goto('https://888pg.cc/');
 await page.addScriptTag({content:fs.readFileSync('work/rebuild-filter.js','utf8')});
 for(const [kind,title] of [['bag','Bônus de aposta efetivo'],['green','Bônus de login diário'],['envelope','']]){
 await page.evaluate(({kind,title})=>{
 document.body.innerHTML=`<main id="app"><section id="reward" style="position:fixed;inset:0"><div id="title" style="position:fixed;top:100px;left:100px">${title}</div><div id="art" ${kind==='envelope'?'class="_fastBackground_3tzh2_112"':''} style="position:fixed;top:200px;left:140px;width:260px;height:260px;background:green"><button id="open" style="margin:100px">ABRIR</button></div><div id="hit" style="position:fixed;top:500px;left:245px;width:50px;height:50px"><button id="close" class="close" style="width:50px;height:50px">×</button></div></section><aside id="ad" style="position:fixed;left:0;top:150px;width:75px;height:90px"><button class="close">×</button>5G bet</aside></main>`;
 window.closedReward=0;window.openedReward=0;
 document.getElementById('close').onclick=()=>{closedReward++;document.getElementById('reward').remove()};
 document.getElementById('open').onclick=()=>openedReward++;
 },{kind,title});
 await page.waitForTimeout(30);
 assert.equal(await page.locator('#ad').isVisible(),false);
 await page.locator('#open').click({timeout:1500});
 assert.equal(await page.evaluate(()=>openedReward),1);
 // A physical pointer click, including hit testing and CSS pointer-events.
 await page.locator('#close').click({timeout:1500});
 assert.equal(await page.evaluate(()=>closedReward),1);
 assert.equal(await page.locator('#reward').count(),0);
 }
 // A late reward label must restore a hit area classified before it mounted.
 await page.evaluate(()=>{document.body.innerHTML='<section id="reward" style="position:fixed;inset:0"><div id="title"></div><div id="hit" style="position:fixed;top:100px;left:100px;width:50px;height:50px"><button class="close">×</button></div></section>'});
 await page.waitForTimeout(30);
 await page.locator('#title').evaluate(el=>el.textContent='Bônus de login diário');
 await page.waitForTimeout(30);
 assert.equal(await page.locator('#hit').isVisible(),true);
 console.log('PASS Chromium: physical Open and Close clicks for all 3 rewards; ad remains hidden; late reward label restores hit area.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
