from pathlib import Path
import subprocess


def test_voice_customer_360_and_accounting_actions_match_desktop_behavior():
    source = (
        Path(__file__).resolve().parents[1]
        / "Web_Arayuzu"
        / "web"
        / "customer-360-voice-reference.js"
    ).read_text(encoding="utf-8")
    harness = r'''const assert = require("node:assert/strict");
const vm = require("node:vm");
const source = require("node:fs").readFileSync(0, "utf8");
const calls = { opened: [], navigated: [], notices: [], base: 0, api: [], selected: "" };
const search = { value: "", dispatchEvent: () => {} };
const customerSearch = { value: "", dispatchEvent: () => {}, focus: () => { calls.customerSearchFocused = true; } };
const row = { dataset: { devicePicker: "R-12" }, click: () => { calls.selected = row.dataset.devicePicker; } };
const root = { querySelectorAll: () => [row] };
const content = { querySelectorAll: () => [
  { getAttribute: () => null, textContent: "New service", title: "", getClientRects: () => [1] },
  { getAttribute: () => null, textContent: "Customer search", title: "", getClientRects: () => [1] },
  { getAttribute: () => null, textContent: "Hidden action", title: "", getClientRects: () => [] },
  { getAttribute: () => null, textContent: "Disabled action", title: "", disabled: true, getClientRects: () => [1] }
] };
const context = {
  window: { ayecExecuteVoiceAction: () => { calls.base += 1; return true; } },
  setTimeout: callback => callback(),
  ayecNormalizeVoicePhrase: value => String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[\u0131\u0130]/g, "i").toLowerCase(),
  customerDirectoryRows: () => [
    { id: 1, name: "Ali" },
    { id: 2, name: "\u00c7a\u011fr\u0131 \u00d6zt\u00fcrk", services: [{ no: "R-12", serial: "SN123", device: "Laptop", status: "Beklemede" }] }
  ],
  customer360: customer => calls.opened.push(customer),
  navigate: page => calls.navigated.push(page),
  toast: (message, type) => calls.notices.push({ message, type }),
  apiFetch: path => { calls.api.push(path); return Promise.resolve({ gross_revenue: 1200, expenses: 300, net: 900 }); },
  money: amount => String(amount),
  db: {
    customers: [{ name: "\u00c7a\u011fr\u0131 \u00d6zt\u00fcrk", services: [{ no: "R-12", serial: "SN123", device: "Laptop", status: "Beklemede" }] }],
    stock: [
      { qty: 5, min: 3 },
      { qty: 1, min: 2 },
      { qty: 0, min: 0 },
      { qty: 0, min: 9, is_deleted: 1 }
    ]
  },
  document: { querySelector: selector => selector === "#devicePickerSearch" ? search : selector === "#devicePickerRows" ? root : selector === "#content" ? content : selector === "#customerSearch" ? customerSearch : null },
  Event: function Event() {}
};
vm.runInNewContext(source, context);
const action = context.window.ayecExecuteVoiceAction;
async function run() {
assert.equal(action({ action: "customer_360" }, "M\u00fc\u015fteri 360"), true);
assert.equal(calls.base, 1);
assert.equal(action({ action: "accounting_summary" }, "Mali durum"), true);
assert.equal(calls.base, 2);
assert.equal(action({ action: "select_service_device" }, "R-12"), true);
assert.equal(calls.base, 3);
assert.equal(action({ action: "musteri_bul" }, "M\u00fc\u015fteri bul \u00c7a\u011fr\u0131 \u00d6zt\u00fcrk"), true);
assert.equal(customerSearch.value, "\u00c7a\u011fr\u0131 \u00d6zt\u00fcrk");
assert.equal(calls.customerSearchFocused, true);
assert.equal(calls.navigated.at(-1), "customers");
assert.equal(action({ action: "musteri_bul" }, "M\u00fc\u015fteri bul Bulunamayan"), true);
assert.equal(customerSearch.value, "");
assert.equal(calls.base, 3);
assert.equal(action({ action: "stock_summary" }, "Stok ozeti"), true);
assert.equal(calls.base, 4);
const pageBeforeHelp = calls.navigated.at(-1);
assert.equal(action({ action: "assistant_help" }, "Bu ekranda ne yapabilirim"), true);
assert.match(calls.notices.at(-1).message, /New service.*Customer search/);
assert.doesNotMatch(calls.notices.at(-1).message, /Hidden action|Disabled action/);
assert.equal(calls.navigated.at(-1), pageBeforeHelp);
}
run().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=source,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout

\n