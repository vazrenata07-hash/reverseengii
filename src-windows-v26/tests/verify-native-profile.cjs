'use strict';

// Offline compatibility checks only: no network, credentials, registration,
// device classifiers, or token SDK is executed by this test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const previous = path.resolve(root, '../src-windows-v25');
const read = (directory, name) => fs.readFileSync(path.join(directory, name), 'utf8');
const prefix = read(root, 'profile-and-bridge.js');
const generated = read(root, 'scripts/danill0.js');
const oldPrefix = read(previous, 'profile-and-bridge.js');
const oldGenerated = read(previous, 'scripts/danill0.js');
const methods = ['getAddDomListener', 'getElemhideSelectors', 'isElementsHidden',
  'setAddDomListener', 'setElementsHidden', 'setHideElementCount'];

function fixture(source, options = {}) {
  const state = { calls: [], listener: false, hidden: false, count: 0, entropyCalls: 0 };
  const native = {
    getAddDomListener() { state.calls.push(['getAddDomListener']); return state.listener; },
    getElemhideSelectors() { state.calls.push(['getElemhideSelectors']); return '[".offline-ad"]'; },
    isElementsHidden() { state.calls.push(['isElementsHidden']); return state.hidden; },
    setAddDomListener(value) { state.calls.push(['setAddDomListener', value]); state.listener = value; },
    setElementsHidden(value) { state.calls.push(['setElementsHidden', value]); state.hidden = value; },
    setHideElementCount(value) { state.calls.push(['setHideElementCount', value]); state.count = value; },
  };
  const uaData = {
    brands: Object.freeze([{ brand: 'Native engine sentinel', version: '131' }]),
    mobile: false,
    platform: 'Windows',
    getHighEntropyValues() { state.entropyCalls++; return Promise.resolve({ model: '' }); },
  };
  const profile = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    platform: 'Win32', vendor: 'Native vendor sentinel', maxTouchPoints: 0,
    userAgentData: uaData, language: 'en-US', languages: Object.freeze(['en-US']),
    hardwareConcurrency: 8, deviceMemory: 8, webdriver: false,
  };
  const navigatorPrototype = {};
  for (const [name, value] of Object.entries(profile)) {
    Object.defineProperty(navigatorPrototype, name, { configurable: true, enumerable: true, get() { return value; } });
  }
  // Chromium normally has no oscpu. Catch both shadowing native getters and
  // introducing an additional browser/OS property.
  const navigator = Object.create(navigatorPrototype);
  const beforeOwn = Object.getOwnPropertyDescriptors(navigator);
  const beforePrototype = Object.getOwnPropertyDescriptors(navigatorPrototype);
  const events = [];
  function node(tagName) {
    return {
      tagName, isConnected: false, nodeType: 1, textContent: '', style: {},
      matches() { return false; }, querySelectorAll() { return []; }, querySelector() { return null; },
      closest() { return null; }, getAttribute() { return null; }, hasAttribute() { return false; },
      getClientRects() { return []; }, setAttribute() {}, removeAttribute() {},
      appendChild(child) { child.isConnected = true; return child; },
    };
  }
  const document = {
    body: node('BODY'), documentElement: node('HTML'),
    createElement: node, querySelectorAll() { return []; },
    addEventListener(name, callback) { events.push([name, callback]); },
  };
  const hostObjects = options.throwingHost
    ? Object.defineProperty({}, 'sync', { get() { throw new Error('offline COM unavailable'); } })
    : { sync: { mintAdblock: options.missingHost ? undefined : native } };
  const timers = new Map();
  let nextTimer = 0;
  const sandbox = {
    navigator, document,
    location: { hostname: options.hostname || '888pg.cc', pathname: '/', hash: '' },
    history: { pushState() {}, replaceState() {} },
    chrome: options.noWebView ? undefined : { webview: { hostObjects, addEventListener() {}, postMessage() {} } },
    MutationObserver: class { observe() {} },
    addEventListener(name, callback) { events.push([name, callback]); },
    setTimeout(callback) { const id = ++nextTimer; timers.set(id, callback); return id; },
    clearTimeout(id) { timers.delete(id); },
  };
  if (Object.hasOwn(options, 'existingBridge')) sandbox.jsBridge = options.existingBridge;
  sandbox.window = sandbox;
  sandbox.top = options.frame ? {} : sandbox;
  vm.runInNewContext(source, sandbox, { timeout: 1000 });
  return { sandbox, state, events, assertNativeProfile() {
    assert.deepEqual(Object.getOwnPropertyDescriptors(navigator), beforeOwn);
    assert.deepEqual(Object.getOwnPropertyDescriptors(navigatorPrototype), beforePrototype);
    assert.equal(Object.getPrototypeOf(navigator), navigatorPrototype);
    for (const [name, value] of Object.entries(profile)) assert.equal(navigator[name], value, name);
    assert.equal('oscpu' in navigator, false);
    assert.equal(state.entropyCalls, 0);
  } };
}

let passed = 0;
function check(name, test) { test(); passed++; console.log(`PASS ${name}`); }

check('prefix and full embedded script preserve native navigator getters and UAData prototype', () => {
  for (const source of [prefix, generated]) {
    for (const hostname of ['888pg.cc', 'sub.888pg.cc', 'example.com']) {
      const result = fixture(source, { hostname });
      result.assertNativeProfile();
      if (hostname.endsWith('888pg.cc')) {
        assert.ok(result.sandbox.jsBridge);
        if (source === generated) {
          assert.equal(result.sandbox.__mintRebuilt21, 1);
          assert.deepEqual(result.state.calls, [
            ['setHideElementCount', 0], ['setElementsHidden', true], ['setAddDomListener', true],
          ]);
        }
      } else {
        assert.equal(result.sandbox.jsBridge, undefined);
        assert.equal(result.sandbox.__mintRebuilt21, undefined);
      }
    }
  }
});

check('native-profile assertions detect the removed V25 overrides', () => {
  assert.throws(() => fixture(oldPrefix).assertNativeProfile(), { name: 'AssertionError' });
});

check('all six adblock methods retain native forwarding and count bounds', () => {
  const { sandbox, state } = fixture(prefix);
  assert.deepEqual(Object.keys(sandbox.jsBridge).sort(), [...methods].sort());
  assert.deepEqual(Object.keys(sandbox.__mintAdblockBridge).sort(), [...methods].sort());
  assert.equal(Object.isFrozen(sandbox.__mintAdblockBridge), true);
  const bridge = sandbox.jsBridge;
  assert.equal(bridge.getAddDomListener(), false);
  assert.equal(bridge.getElemhideSelectors(), '[".offline-ad"]');
  assert.equal(bridge.isElementsHidden(), false);
  bridge.setAddDomListener(1); bridge.setElementsHidden(0);
  for (const value of [-1, '12', NaN, 2000000]) bridge.setHideElementCount(value);
  assert.deepEqual(state.calls, [
    ['getAddDomListener'], ['getElemhideSelectors'], ['isElementsHidden'],
    ['setAddDomListener', true], ['setElementsHidden', false],
    ['setHideElementCount', 0], ['setHideElementCount', 12], ['setHideElementCount', 0], ['setHideElementCount', 1000000],
  ]);
});

check('public V25 bridge callback remains extensible, callable and removable', () => {
  for (const source of [prefix, generated]) {
    const { sandbox } = fixture(source);
    const bridge = sandbox.jsBridge;
    assert.equal(Object.isExtensible(bridge), true);
    let received;
    bridge.onWebviewEvents = value => { received = value; };
    bridge.onWebviewEvents('offline-callback');
    assert.equal(received, 'offline-callback');
    delete bridge.onWebviewEvents;
    assert.equal(Object.hasOwn(bridge, 'onWebviewEvents'), false);
    bridge.onWebviewEvents = () => {};
    delete bridge.onWebviewEvents;
    assert.equal(bridge.postMessage, undefined);
  }
});

check('bridge guards reject other hosts, lookalike hosts and child frames', () => {
  for (const source of [prefix, generated]) {
    for (const options of [{ hostname: 'example.com' }, { hostname: 'evil888pg.cc' },
      { hostname: '888pg.cc.example.com' }, { frame: true }]) {
      const result = fixture(source, options);
      result.assertNativeProfile();
      assert.equal(result.sandbox.jsBridge, undefined);
      assert.equal(result.sandbox.__mintAdblockBridge, undefined);
    }
  }
});

check('existing page bridge survives; private bridge still forwards independently', () => {
  for (const source of [prefix, generated]) {
    const pageBridge = { pageOwned: true };
    const { sandbox, state } = fixture(source, { existingBridge: pageBridge });
    assert.equal(sandbox.jsBridge, pageBridge);
    assert.deepEqual(Object.keys(pageBridge), ['pageOwned']);
    sandbox.__mintAdblockBridge.setHideElementCount(3);
    assert.equal(state.count, 3);
  }
});

check('missing WebView or unavailable native host does not throw or alter navigator', () => {
  for (const source of [prefix, generated]) {
    for (const options of [{ missingHost: true }, { throwingHost: true }, { noWebView: true }]) {
      const result = fixture(source, options);
      result.assertNativeProfile();
      assert.equal(result.sandbox.jsBridge, undefined);
      assert.equal(result.sandbox.__mintAdblockBridge, undefined);
    }
  }
});

check('embedded JS has exact prefix, unchanged V25 suffix and unchanged native bridge bytes', () => {
  new vm.Script(generated);
  assert.ok(generated.startsWith(prefix + '\n'));
  assert.ok(oldGenerated.startsWith(oldPrefix + '\n'));
  assert.equal(generated.slice(prefix.length + 1), oldGenerated.slice(oldPrefix.length + 1));
  const bridgeStart = ' // Android Mint exposes these six native adblock methods';
  assert.equal(prefix.slice(prefix.indexOf(bridgeStart)), oldPrefix.slice(oldPrefix.indexOf(bridgeStart)));
  for (const filename of ['AdblockBridge.cs', 'Ledger.cs', 'InputDialog.cs', 'prepare-scripts.py']) {
    assert.deepEqual(fs.readFileSync(path.join(root, filename)), fs.readFileSync(path.join(previous, filename)), filename);
  }
  assert.match(read(root, 'MintBrowser.csproj'), /EmbeddedResource Include="scripts\/danill0\.js" LogicalName="mint-script\.js"/);
});

check('C# leaves engine UA/locale/emulation unset and cannot apply a legacy UA setting', () => {
  const browser = read(root, 'BrowserForm.cs');
  const program = read(root, 'Program.cs');
  assert.doesNotMatch(browser, /\bUserAgent\b|\bEditUserAgent\b|\bApplyProfileAsync\b|\bSizeProfileAsync\b|\bchromeVersion\b/);
  assert.doesNotMatch(browser, /Emulation\.|\bLanguage\s*=|--user-agent|--lang(?:=|\s)|userAgentMetadata/);
  assert.doesNotMatch(program, /\bUserAgent\b/);
  assert.match(program, /JsonSerializer\.Deserialize<Settings>\(File\.ReadAllText\(ConfigPath\)\)/);
  assert.match(program, /class Settings\s*\{\s*public bool CodeEntered\s*\{ get; set; \}\s*\}/);
  assert.match(browser, /script\s*=\s*Program\.Script\(\);/);
  assert.match(browser, /core\.AddHostObjectToScript\("mintAdblock",nativeBridge\)/);
  assert.match(browser, /--ignore-certificate-errors --autoplay-policy=no-user-gesture-required/);
  assert.match(browser, /ServerCertificateErrorDetected/);
});

console.log(`${passed} focused offline checks passed. No Windows/WebView2, actual COM, live site, or server acceptance test was performed.`);
