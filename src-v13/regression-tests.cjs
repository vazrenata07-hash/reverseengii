const {JSDOM}=require('./testdeps/node_modules/jsdom');
const fs=require('fs'),assert=require('node:assert/strict');
const script=fs.readFileSync('work/rebuild-filter.js','utf8');
const wait=()=>new Promise(r=>setTimeout(r,15));
function page(url='https://888pg.cc/home',html=''){
 const dom=new JSDOM(html,{url,runScripts:'outside-only'}),w=dom.window;
 w.HTMLElement.prototype.getClientRects=function(){return this.hidden?[]:[{}]};
 w.HTMLElement.prototype.getBoundingClientRect=function(){return {left:0,right:100,top:0,bottom:100,width:100,height:100}};
 w.eval(script);return w;
}
function native(w,file){w.bridge={getElemhideSelectors:()=>JSON.stringify(['.lobby-image','.native-block']),setHideElementCount:()=>{}};w.eval(fs.readFileSync('work/rebuild-apk/assets/adblock/'+file,'utf8').replaceAll('{{DEBUG}}','').replaceAll('{{BRIDGE}}','bridge'));}
(async()=>{
 for(const host of ['888pg.cc','a.888pg.cc','a.b.888pg.cc']){
  const w=page('https://'+host+'/home/register','<input type=tel placeholder="Digite o Número do Celular/E-mail/Conta"><input type=password><input type=password>');await wait();
  const fields=w.document.querySelectorAll('input');assert.match(fields[0].value,/^[A-Za-z0-9]{15}$/);assert.equal(fields[1].value,'danill0');assert.equal(fields[2].value,'danill0');const name=fields[0].value;
  fields[0].value='manual';w.document.body.append(w.document.createElement('span'));await wait();assert.equal(fields[0].value,'manual');
  w.history.pushState({},'','/home');w.history.pushState({},'','/home/register');await wait();assert.match(fields[0].value,/^[A-Za-z0-9]{15}$/);assert.notEqual(fields[0].value,name);
  w.history.pushState({},'','/home/login');fields[0].value='saved-login';w.document.body.append(w.document.createElement('span'));await wait();assert.equal(fields[0].value,'saved-login');
  w.history.pushState({},'','/#/register');await wait();assert.match(fields[0].value,/^[A-Za-z0-9]{15}$/);
 }
 for(const host of ['evil888pg.cc','888pg.cc.example.com','example.com']){
  const w=page('https://'+host+'/home/register','<input placeholder=conta><input type=password>');await wait();assert.equal(w.document.querySelector('input').value,'');assert.equal(w.document.querySelectorAll('style').length,0);
 }
 const w=page('https://888pg.cc/home','<div id=ad style="position:fixed;display:flex"><img src="/ad.png"><button class=close>×</button></div>');await wait();const ad=w.document.getElementById('ad');assert.equal(ad.getAttribute('data-mint13-hidden'),'1');assert.equal(ad.style.display,'flex');
 let clicks=0;w.document.addEventListener('click',()=>clicks++);
 ad.innerHTML='<div class="_fastBtn_3tzh2_99"><div class="lobby-image lobby-image--use-bg _fastBackground_3tzh2_112"><img class="lobby-image _fastImg_3tzh2_117"><img class="lobby-image _closeIcon_3tzh2_141"></div></div>';ad.style.display='grid';await wait();assert(!ad.hasAttribute('data-mint13-hidden'));assert.equal(ad.style.display,'grid');assert.equal(clicks,0);
 const r=page('https://888pg.cc/home','<div class=native-block style="position:fixed"><img class="lobby-image _fastImg_3tzh2_117"><img class="lobby-image _closeIcon_3tzh2_141"></div>');native(r,'css.js');native(r,'hide.js');await wait();assert.notEqual(r.getComputedStyle(r.document.querySelector('img')).display,'none');assert(!r.document.querySelector('div').hasAttribute('data-mint13-hidden'));
 const original=page('https://example.com/home','<div class=native-block><img class=lobby-image></div>');native(original,'css.js');native(original,'hide.js');assert.equal(original.document.querySelector('img').style.display,'none');
 for(const content of ['<iframe></iframe>','<canvas></canvas>','<div role=slider></div>','<div class=geetest_panel></div>','<p>Bônus de aposta efetivo</p><button>ABRIR</button>','<p>Bônus de login diário</p><button>ABRIR</button>']){
  const x=page('https://888pg.cc/home','<div class=ui-overlay style="position:fixed"><div style="position:absolute"><button class=close>×</button></div>'+content+'</div>');await wait();assert.equal(x.document.querySelectorAll('[data-mint13-hidden]').length,0,content);
 }
 const captcha=page('https://888pg.cc/home/register','<input placeholder=conta><input type=password><div style="position:fixed"><button class=close>×</button><div id=payload></div></div>');await wait();assert.equal(captcha.document.querySelectorAll('[data-mint13-hidden]').length,0);captcha.document.getElementById('payload').innerHTML='<input class=captcha placeholder=Resposta>';await wait();assert.equal(captcha.document.querySelector('.captcha').value,'');

 // The fast component must never exempt other promotions on the same page.
 const content=`<div id="reward" style="position:fixed"><div class="_fastBtn_3tzh2_99"><div class="_fastBackground_3tzh2_112"><img class="_fastImg_3tzh2_117"><img class="_closeIcon_3tzh2_141"></div></div></div>
 <div id="float1" class="gift" style="position:fixed"><img src="tree.png"><button class="close">×</button></div>
 <div id="float2" class="chest" style="position:fixed"><img src="5gbet.png"><button class="close">×</button></div>
 <div id="float3" style="position:fixed"><img src="referral.png"><button class="close">×</button></div>
 <div id="signup" role="dialog" style="position:fixed"><div class="gift">Parabéns, Cadastro Concluído! Primeiro depósito</div><button>Deposite agora</button><button class="close">×</button></div>
 <div id="vip" role="dialog" style="position:fixed"><img src="panda.png"><button>Clube VIP</button><button>Convidar amigos</button><label><input type="checkbox">Não mostrar novamente hoje</label><button class="close">×</button></div>
 <div id="draw" role="dialog" style="position:fixed"><h1>Sorteio</h1>Escolha um prêmio de até188,00<div class="treasure-chest">Ativar</div></div>
 <div id="realreward" role="dialog" style="position:fixed">Bônus de login diário<button>ABRIR</button><button class="close">×</button></div>
 <div id="captcha" role="dialog" style="position:fixed"><div class="geetest_panel"></div><button class="close">×</button></div>`;
 const scene=page('https://888pg.cc/home',content);await wait();
 for(const id of ['float1','float2','float3','signup','vip','draw'])assert.equal(scene.document.getElementById(id).getAttribute('data-mint13-hidden'),'1',id);
 for(const id of ['reward','realreward','captcha'])assert.equal(scene.document.getElementById(id).querySelectorAll('[data-mint13-hidden]').length,0,id);
 assert.equal(scene.document.getElementById('reward').hasAttribute('data-mint13-hidden'),false);
 // Late text in an existing modal must be detected too.
 const late=scene.document.createElement('section');late.style.position='fixed';late.innerHTML='<span>Sorteio</span><span id="late"></span>';scene.document.body.append(late);await wait();late.querySelector('#late').textContent='Escolha um prêmio';await wait();assert.equal(late.getAttribute('data-mint13-hidden'),'1');
 // Site's own close handler removes the backdrop; never click CAPTCHA/ABRIR.
 const events=page('https://888pg.cc/home','');let adCloses=0,rewardClicks=0;
 const root=events.document.createElement('div');root.setAttribute('role','dialog');root.innerHTML='<p>Cadastro Concluído!</p><button class=close>×</button>';root.querySelector('button').onclick=()=>{adCloses++;root.remove()};events.document.body.append(root);
 const reward=events.document.createElement('div');reward.style.position='fixed';reward.innerHTML='<p>Bônus de aposta efetivo</p><button class=close>×</button><button>ABRIR</button>';reward.onclick=()=>rewardClicks++;events.document.body.append(reward);await wait();assert.equal(adCloses,1);assert.equal(rewardClicks,0);assert(!root.isConnected);
 console.log('PASS: all screenshot promotion fixtures blocked with fast reward present; exact reward and CAPTCHA preserved; native dismissal for identified ad only; 15-character route generation; password; domain scope.');
})().catch(e=>{console.error(e);process.exit(1)});
