const {chromium}=require('playwright'),fs=require('fs'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
for(const password of ['danill0','87654321']){
 const p=await b.newPage();await p.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));
 async function load(path,html,setup){await p.goto('https://a.888pg.cc/home/'+path);await p.setContent(html);if(setup)await p.evaluate(setup);await p.evaluate(()=>{window.submits=0;document.addEventListener('submit',e=>{e.preventDefault();submits++});document.querySelectorAll('button').forEach(e=>e.onclick=()=>submits++);});await p.addScriptTag({content:fs.readFileSync('work/variants-v18/'+password+'.js','utf8')});await p.waitForTimeout(80);}
 await load('security','<form>Senha de Saque<input type=password aria-label="Defina sua senha de saque"><input type=password aria-label="Confirmar Nova Senha"><button>Confirmar</button></form>');
 assert.deepEqual(await p.locator('input').evaluateAll(es=>es.map(e=>e.value)),['232691','232691']);assert.equal(await p.evaluate(()=>submits),0);
 await load('withdraw','<form>Verificar Senha de Saque<input id=amount placeholder="Valor do Saque" maxlength=6 value=0><input id=pin aria-label="Verificar Senha de Saque" maxlength=6><input id=otp autocomplete="one-time-code" maxlength=6><div class=captcha><input type=password></div><button>Confirmar saque</button></form>');
 assert.deepEqual(await p.locator('input').evaluateAll(es=>es.map(e=>e.value)),['0','232691','','']);assert.equal(await p.evaluate(()=>submits),0);
 await load('withdraw','Senha de Saque<form>'+Array(6).fill('<input type=tel maxlength=1>').join('')+'<button>Confirmar saque</button></form>');assert.equal(await p.locator('input').evaluateAll(es=>es.map(e=>e.value).join('')),'232691');assert.equal(await p.evaluate(()=>submits),0);
 await load('withdraw','<div class=ui-dialog>Inserir senha <label>Senha de Saque</label><input type=password value=123456></div>');assert.equal(await p.locator('input').inputValue(),'123456');
 await load('register','<input placeholder=conta><input type=password><input type=password>');assert.match(await p.locator('input').nth(0).inputValue(),/^[a-zA-Z0-9]{15}$/);assert.equal(await p.locator('input').nth(1).inputValue(),password);
 // Display-only six-cell widgets with the touch keyboard event contract.
 const widget='<div class=ui-password-input><ul>'+Array(6).fill('<li><i style="display:none"></i></li>').join('')+'</ul></div>';
 await load('security','Senha de Saque'+widget+widget+'<div class=ui-number-keyboard style="display:none">'+Array.from({length:10},(_,i)=>'<div class=ui-key>'+i+'</div>').join('')+'</div><button>Confirmar</button>',()=>{
  window.values=['',''];window.active=-1;const fields=[...document.querySelectorAll('.ui-password-input')],keyboard=document.querySelector('.ui-number-keyboard');fields.forEach((el,i)=>el.addEventListener('click',()=>{active=i;keyboard.style.display='block'}));document.querySelectorAll('.ui-key').forEach(key=>key.addEventListener('touchend',()=>{if(active<0)return;values[active]+=key.textContent;fields[active].querySelectorAll('i').forEach((dot,i)=>dot.style.display=i<values[active].length?'block':'none');}));
 });await p.waitForTimeout(1000);assert.deepEqual(await p.evaluate(()=>values),['232691','232691']);assert.equal(await p.evaluate(()=>submits),0);
 await p.close();
}
console.log('PASS: both APK scripts; setup/confirmation, withdraw verification, modal, six inputs, touch keyboards; login preserved; amounts/OTP/CAPTCHA/existing PIN untouched; zero submit/confirm actions.');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
