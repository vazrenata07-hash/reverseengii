const {JSDOM}=require('./testdeps/node_modules/jsdom');
const fs=require('fs'),assert=require('node:assert/strict');
const code=fs.readFileSync(process.argv[2]||'work/rebuild-filter.js','utf8');
const wait=()=>new Promise(r=>setTimeout(r,15));
const names=['Bônus de aposta efetivo','Bônus de login diário',''];
(async()=>{
 for(let i=0;i<3;i++){
  const html=`<div id="reward" style="position:fixed"><div id="title">${names[i]}</div><div id="art" ${i===2?'class="_fastBackground_3tzh2_112"':''} style="position:absolute"><img ${i===2?'class="_fastImg_3tzh2_117"':''} src="/hashed-art.webp"><button id="open">ABRIR</button></div><div id="hit" style="position:fixed"><button id="close" class="_close_${i===2?'3tzh2':'abcdef'}_88">×</button></div></div><div id="advert" style="position:fixed"><img src="/advert.webp"><button class="close">×</button></div>`;
  const dom=new JSDOM(html,{url:'https://888pg.cc/',runScripts:'outside-only'}),w=dom.window,d=w.document;
  w.HTMLElement.prototype.getBoundingClientRect=function(){return {x:0,y:0,left:0,top:0,right:100,bottom:100,width:100,height:100}};
  let closed=0,opened=0;d.getElementById('close').onclick=()=>{closed++;d.getElementById('reward').remove()};d.getElementById('open').onclick=()=>opened++;
  w.eval(code);await wait();
  const blocked=[...d.querySelectorAll('[id=reward],[id=reward] *')].filter(el=>w.getComputedStyle(el).display==='none'||w.getComputedStyle(el).pointerEvents==='none');
  assert.equal(blocked.length,0,`reward ${i}: hidden or inert: ${blocked.map(e=>e.id)}`);
  assert.equal(w.getComputedStyle(d.getElementById('advert')).display,'none','ad must remain blocked');
  assert.equal(closed,0,'must not automatically close rewards');
  d.getElementById('open').click();assert.equal(opened,1);d.getElementById('close').click();assert.equal(closed,1);assert(!d.getElementById('reward'));await wait();
 }
 console.log('PASS: 3 complete reward components, nested fixed close hit areas, original open/close callbacks, independent advertisement remains blocked.');
})().catch(e=>{console.error(e);process.exit(1)});
