'use strict';

// Offline regression against exact code from the user-supplied lobby capture.
// This does not execute a login, make network requests, or claim server acceptance.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = process.env.MINT_REPO_ROOT || path.resolve(__dirname, '../..');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'lobby-contract.fixture.json'), 'utf8'));
const exact = fixture.exact;
const evidence = JSON.parse(JSON.stringify(fixture.provenance));

const siteFragment = [
  '"use strict";',
  `var ${exact.osEnum};`,
  `var ${exact.deviceAndClientEnums};`,
  `const ${exact.appAndVest};`,
  `const ${exact.osHelpers};`,
  `const ${exact.deviceModelHelper};`,
  `const ${exact.deviceAndClientHelpers};`,
  `const callbackOptions=${exact.callbackOptions};`,
  `const readLoginPayload=${exact.loginPayload};`,
  'globalThis.site={re,FI,il,WI,VI,Ug,Gg,callbackOptions,readLoginPayload};',
].join('\n');

const uaSource = fs.readFileSync(path.join(root, 'src-windows-v25/BrowserForm.cs'), 'utf8');
const ua = uaSource.match(/string UserAgent =>[^\n]*? : "([^"]+)";/)?.[1];
assert.ok(ua && ua.includes('Android 13') && ua.includes('Version/4.0') && !ua.includes('Chrome/'));
evidence.userAgent = ua;
evidence.parserFixture = 'Fixed parsed inputs for the actual Android Browser 4.0 UA: Android/mobile, not iOS, not WebSpace. The UA parser itself is not exercised.';

function run(version, options = {}) {
  const prefixPath = path.join(root, `src-windows-v${version}/profile-and-bridge.js`);
  const prefix = fs.readFileSync(prefixPath, 'utf8');
  const state = { listener: true, hidden: false, count: 0, calls: [] };
  const native = {
    getAddDomListener() { return state.listener; },
    getElemhideSelectors() { return '[".offline-fixture-ad"]'; },
    isElementsHidden() { return state.hidden; },
    setAddDomListener(value) { state.calls.push(['listener', value]); state.listener = value; },
    setElementsHidden(value) { state.calls.push(['hidden', value]); state.hidden = value; },
    setHideElementCount(value) { state.calls.push(['count', value]); state.count = value; },
  };
  const parsed = {
    os: { isAndroid: true, isWindows: false, isLinux: false, isIOS: false, isMacOS: false, name: 'Android' },
    browser: { isWebSpace: false, format: 'Android Browser v4.0' },
    device: { isMobile: true, isTablet: false },
  };
  const detected = { isIos: false, isAndroid: true, isAndroidPhone: true, isMobile: true, isTablet: false, isP2a: false, isH5Shortcut: false };
  const sandbox = {
    navigator: { userAgent: ua },
    location: { hostname: options.hostname || '888pg.cc', pathname: '/', origin: 'https://888pg.cc' },
    chrome: { webview: { hostObjects: { sync: { mintAdblock: options.missingHost ? undefined : native } } } },
    ht: () => parsed,
    Xe: () => detected,
    Pt: {},
    fn: { isActivated: false },
    ha: () => false,
    ah: { AgentPC: 'offline-agent-fixture', Sass: 'offline-saas-fixture' },
    // Only fill unrelated identifier slots; no real session, API, or response is used.
    zn: () => ({ uuid: 'offline-device-fixture', hash: 'offline-hash-fixture' }),
  };
  if (options.existingBridge) sandbox.jsBridge = options.existingBridge;
  sandbox.window = sandbox;
  sandbox.top = options.frame ? {} : sandbox;
  const context = vm.createContext(sandbox);
  vm.runInContext(prefix, context, { filename: prefixPath, timeout: 1000 });
  vm.runInContext(siteFragment, context, { filename: 'exact-captured-lobby-fragments.js', timeout: 1000 });
  return { sandbox, site: sandbox.site, state, context };
}

let passed = 0;
function check(name, fn) { fn(); passed++; console.log(`PASS ${name}`); }
function classification(run) {
  const { site } = run;
  const bag = site.re.package;
  const payload = site.readLoginPayload();
  return { isApp: !!bag.isApp, isVest: !!bag.isVest, isLite: !!bag.isLite,
    xDevice: `${site.Ug()}-${site.Gg()}`, os_type: payload.os_type,
    deviceOsType: payload.deviceOsType, clientType: payload.clientType, platformType: payload.platformType };
}

check('V24 exact site classifier and login metadata yield Android H5', () => {
  const result = run(24);
  assert.deepEqual(classification(result), { isApp: false, isVest: false, isLite: false,
    xDevice: '2-1', os_type: 6, deviceOsType: 6, clientType: 5, platformType: '1001' });
  assert.equal(result.site.callbackOptions.registerMessage(() => {}), undefined);
  assert.equal(result.site.callbackOptions.disabled(), true);
});

check('V23 frozen bridge reproduces the captured callback assignment TypeError', () => {
  const result = run(23);
  assert.equal(Object.isFrozen(result.sandbox.jsBridge), true);
  assert.throws(() => result.site.callbackOptions.registerMessage(() => {}), error =>
    error.name === 'TypeError' && /onWebviewEvents/.test(error.message));
});

check('V25 exact site classifier and login metadata yield Android Vest', () => {
  assert.deepEqual(classification(run(25)), { isApp: true, isVest: true, isLite: false,
    xDevice: '2-4', os_type: 6, deviceOsType: 2, clientType: 5, platformType: '1001' });
});

check('V25 exact callback registration supports set, invoke, cleanup, and re-register', () => {
  const { sandbox, site } = run(25);
  const received = [];
  assert.equal(Object.isExtensible(sandbox.jsBridge), true);
  const cleanup = site.callbackOptions.registerMessage(value => received.push(value));
  sandbox.jsBridge.onWebviewEvents('offline-callback-fixture');
  assert.deepEqual(received, ['offline-callback-fixture']);
  cleanup();
  assert.equal(Object.hasOwn(sandbox.jsBridge, 'onWebviewEvents'), false);
  const cleanup2 = site.callbackOptions.registerMessage(value => received.push(value));
  sandbox.jsBridge.onWebviewEvents('second-offline-callback-fixture');
  cleanup2();
  assert.deepEqual(received, ['offline-callback-fixture', 'second-offline-callback-fixture']);
});

check('V25 exposes only Android Mint adblock methods, with no fabricated site SDK', () => {
  const { sandbox, site } = run(25);
  const methods = ['getAddDomListener', 'getElemhideSelectors', 'isElementsHidden', 'setAddDomListener', 'setElementsHidden', 'setHideElementCount'];
  assert.deepEqual(Object.keys(sandbox.jsBridge).sort(), methods.sort());
  for (const name of ['getWGConfigInfo', 'postMessage', 'ifSchemaExists', 'share']) assert.equal(sandbox.jsBridge[name], undefined);
  for (const name of ['WgPackage', 'SpeedPackaeInit', 'Android', 'PlatNative', 'uni']) assert.equal(sandbox[name], undefined);
  assert.equal(site.callbackOptions.disabled(), true);
});

check('V25 private adblock functions remain frozen and native state still forwards', () => {
  const { sandbox, state } = run(25);
  const bridge = sandbox.__mintAdblockBridge;
  assert.equal(Object.isFrozen(bridge), true);
  assert.notEqual(bridge, sandbox.jsBridge);
  assert.equal(bridge.getAddDomListener(), true);
  assert.equal(bridge.isElementsHidden(), false);
  assert.deepEqual(JSON.parse(bridge.getElemhideSelectors()), ['.offline-fixture-ad']);
  sandbox.jsBridge.setAddDomListener = () => { throw new Error('public method replaced by offline fixture'); };
  bridge.setAddDomListener(false);
  bridge.setElementsHidden(true);
  bridge.setHideElementCount(4);
  assert.equal(state.listener, false);
  assert.equal(state.hidden, true);
  assert.equal(state.count, 4);
});

check('V25 keeps the host bridge scope, preserves a page bridge, and handles unavailable host', () => {
  const existing = { pageOwned: true };
  assert.equal(run(25, { existingBridge: existing }).sandbox.jsBridge, existing);
  for (const options of [{ hostname: 'example.com' }, { hostname: '888pg.cc.example.com' }, { frame: true }, { missingHost: true }]) {
    assert.equal(run(25, options).sandbox.jsBridge, undefined);
  }
  assert.ok(run(25, { hostname: 'sub.888pg.cc' }).sandbox.jsBridge);
});

check('V25 generated browser script compiles and contains the tested prefix', () => {
  const prefix = fs.readFileSync(path.join(root, 'src-windows-v25/profile-and-bridge.js'), 'utf8');
  const generated = fs.readFileSync(path.join(root, 'src-windows-v25/scripts/danill0.js'), 'utf8');
  new vm.Script(generated);
  assert.ok(generated.startsWith(prefix + '\n'));
  assert.ok(generated.slice(prefix.length).includes('window.__mintAdblockBridge.setHideElementCount'));
});

evidence.checksPassed = passed;
evidence.limits = 'Offline VM only. Browser parser outputs and native COM methods are fixtures. This directly runs exact captured classification, login-payload, and callback-registration code; it does not test the missing vendor factory or a full lobby startup, Windows/WebView2/COM, or server-side device acceptance.';
if (process.env.MINT_TEST_EVIDENCE) fs.writeFileSync(process.env.MINT_TEST_EVIDENCE, JSON.stringify(evidence, null, 2) + '\n');
console.log(`${passed} focused checks passed; exact source offsets and SHA-256 recorded in lobby-contract.fixture.json`);
