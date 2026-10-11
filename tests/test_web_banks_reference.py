from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_bank_reference_keeps_account_movements_linked_to_real_bank_ids():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function ayecBankUpdateLedger()")
    end = source.index("async function ayecLoadBankReference()", start)
    code = source[start:end]
    assert "row.bank_account_id&&ids.has(Number(row.bank_account_id))" in code
    assert "Number(row.bank_account_id)===selected" in code
    assert "financeTryValue(row)" in code
    assert 'apiFetch("/api/desktop/table/bank_accounts?limit=500")' in source


def test_bank_summary_converts_mixed_account_currencies_to_try():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function ayecBankRenderData(rows)")
    end = source.index("function ayecBankUpdateLedger()", start)
    code = source[start:end]
    assert 'rateForCode(row.currency||"TRY")' in code
    assert "reduce((sum,row)=>sum+toTry(row),0)" in code


def test_bank_account_reference_has_responsive_treasury_composition():
    css = CSS.read_text(encoding="utf-8")
    assert 'body[data-page="banks"] .bank-ref-metrics' in css
    assert 'body[data-page="banks"] .bank-ref-columns' in css
    assert '@media(max-width:1100px){body[data-page="banks"]' in css
    assert '@media(max-width:700px){body[data-page="banks"]' in css
    assert '@media(max-width:420px){body[data-page="banks"]' in css
    assert '@media print{body[data-page="banks"]' in css
