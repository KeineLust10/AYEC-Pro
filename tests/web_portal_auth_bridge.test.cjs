const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const sourcePath = path.join(__dirname, '..', 'premium-field-app', 'src', 'api', 'webPortalAuth.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const builder = new Function(`${source.replace('export function', 'function')}\nreturn buildPortalAuthScript;`)();

function bridge(token) {
    const sent = [];
    const requests = [];
    class MockXHR {
        constructor() { this.headers = {}; this.listeners = {}; this.status = 200; }
        open(method, url) { this.method = method; this.url = url; }
        send() { requests.push({ type: 'xhr', url: this.url, headers: { ...this.headers } }); }
        setRequestHeader(name, value) { this.headers[name] = value; }
        addEventListener(name, callback) { this.listeners[name] = callback; }
    }
    const context = {
        URL,
        Headers,
        XMLHttpRequest: MockXHR,
        location: { href: 'https://panel.example.test/', origin: 'https://panel.example.test' },
        ReactNativeWebView: { postMessage: (value) => sent.push(value) },
        fetch: async (input, init = {}) => {
            requests.push({ type: 'fetch', url: String(input), headers: Object.fromEntries(new Headers(init.headers).entries()) });
            return { status: input === '/api/expired' ? 401 : 200 };
        },
    };
    context.window = context;
    vm.runInNewContext(builder(token), context);
    return { context, requests, sent };
}

test('adds bearer only to same-origin API calls and reports expired sessions', async () => {
    const state = bridge('sample-token');
    await state.context.fetch('/api/desktop/bootstrap');
    await state.context.fetch('/api/expired');
    await state.context.fetch('https://other.example.test/api/data');
    await state.context.fetch('/assets/app.js');
    assert.equal(state.requests[0].headers.authorization, 'Bearer sample-token');
    assert.equal(state.requests[1].headers.authorization, 'Bearer sample-token');
    assert.equal(state.requests[2].headers.authorization, undefined);
    assert.equal(state.requests[3].headers.authorization, undefined);
    assert.deepEqual(state.sent, ['AYEC_AUTH_EXPIRED']);
});

test('adds bearer to same-origin API XMLHttpRequests only', () => {
    const state = bridge('sample-token');
    const api = new state.context.XMLHttpRequest();
    api.open('POST', '/api/desktop/smart-import');
    api.send();
    const external = new state.context.XMLHttpRequest();
    external.open('POST', 'https://other.example.test/api/desktop/smart-import');
    external.send();
    assert.equal(api.headers.Authorization, 'Bearer sample-token');
    assert.equal(external.headers.Authorization, undefined);
});

test('does not install the authorization bridge without a token', async () => {
    const state = bridge('');
    await state.context.fetch('/api/desktop/bootstrap');
    assert.equal(state.requests[0].headers.authorization, undefined);
});
