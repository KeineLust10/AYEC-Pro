from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_finance_rows_open_reference_detail_dialog_with_footer_actions():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert 'data-action="finance-detail"' in app
    assert 'if(action==="finance-detail")financeDetailDialog(item)' in app
    assert 'finance-detail-dialog' in app
    assert 'data-finance-detail-action="print"' in app
    assert 'data-finance-detail-action="receipt-print"' in app
    assert 'data-finance-detail-action="customer360"' in app
    assert 'data-finance-detail-action="copy-tracking"' in app
    assert 'data-finance-detail-action="service-form"' in app
    assert 'data-finance-detail-action="edit"' in app
    assert 'const receiptAction=item.source==="accounting"&&item.receipt_available?' in app
    assert '/api/desktop/accounting/${encodeURIComponent(button.dataset.id)}/receipt/download' in app
    assert 'Stok / Hizmet Kalemleri' in app
    assert '\\u0130\\u015flem A\\u00e7\\u0131klamas\\u0131 &amp; Notlar' in app
    assert '$("#dialogFooter").innerHTML=`${serviceAction}${customerAction}${receiptAction}<button type="button" class="secondary" data-finance-detail-action="receipt-print"' in app
    assert 'function printFinanceTransactionReceipt(item)' in app
    assert '@page{size:A4;margin:16mm}' in app
    assert 'const amount=Number(currency==="TRY"?(item.amount_try??item.amount??0):(item.amount??0))||0' in app
    assert '["Tarih",item.date||item.created_at||"-"]' in app
    assert '["Islem Turu",item.type_label||item.type||"Tahsilat"]' in app
    assert '["Musteri",item.customer_name||item.customer||"-"]' in app
    assert '["Referans",financeDetailReference(item)||item.tracking_no||item.ref_no||"-"]' in app
    receipt_audit = (ROOT / "tools" / "quality" / "accounting_receipt_offscreen.cjs").read_text(encoding="utf-8")
    assert 'amount:999,amount_try:73,currency:"TRY"' in receipt_audit
    assert 'amount:123,amount_try:999' in receipt_audit
    assert 'foreignReceiptMarkup.includes("Alinan Tutar</small><strong>"+money(123,"USD"))' in receipt_audit
    assert 'if(button.dataset.financeDetailAction==="receipt-print"){printFinanceTransactionReceipt(item);return}' in app
    assert 'if(button.dataset.financeDetailAction==="customer360"){' in app
    assert 'const customer=db.customers.find(row=>String(row.id)===String(item.customer_id))' in app
    assert 'function financeDetailReference(item)' in app
    assert 'function financeDetailServiceLines(service)' in app
    assert 'const displayLines=lines.length?lines:financeDetailFallbackLines(item,reference,linkedService)' in app
    assert 'function financeDetailSelectedLines(payload)' in app
    assert 'function financeDetailDescriptionLines(description)' in app
    assert 'function financeDetailFallbackLines(item,reference,linkedService)' in app
    assert 'const serviceWorkLines=financeDetailServiceLines(linkedService)' in app
    assert 'item.operator_name||item.created_by_name||item.created_by||item.operator' in app
    assert 'item.timestamp||item.created_at||item.updated_at' in app
    assert 'navigator.clipboard.writeText(reference)' in app
    assert 'if(button.dataset.financeDetailAction==="service-form"){' in app
    assert 'findService(financeDetailReference(item))' in app
    assert 'match(/(?:^|[|\\s])Ref\\s*[:#]?\\s*([A-Za-z0-9._-]+)/i)?.[1]||""' in app
    assert 'Cari Bor\\u00e7 Kapatma Referans\\u0131' in app
    assert 'Birim Fiyat' in app and 'Tahsilat / \\u0130\\u015flem Notu' in app


    open_dialog_start = app.index("function openDialog")
    customer_form_start = app.index("function customerForm", open_dialog_start)
    open_dialog = app[open_dialog_start:customer_form_start]
    cleanup = re.search(r'dialog\.classList\.remove\(([^)]*)\)', open_dialog)
    assert cleanup
    assert {'"finance-detail-dialog"', '"customer-editor-dialog"', '"service-accept-dialog"'} <= set(
        re.findall(r'"[^"]+"', cleanup.group(1))
    )
    assert '.finance-detail-ref{display:grid;grid-template-columns:minmax(250px,4fr) minmax(0,8fr)' in styles
    assert '@media(max-width:720px){.finance-detail-ref{grid-template-columns:minmax(0,1fr)}' in styles


def test_finance_ledger_renders_expenses_as_negative_outflows():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'function ayecFinanceLedgerAmount(value,type)' in app
    assert 'for(const item of ayecFinanceLedgerItems)' in app
    assert 'return type==="Gider"?-Math.abs(amount):amount' in app
    assert 'original=currency==="TRY"?"--":financeDashboardMoney(ayecFinanceLedgerAmount(item.original_amount,item.type),currency)' in app
    assert 'total=financeDashboardMoney(ayecFinanceLedgerAmount(item.try_equivalent,item.type),"TRY")' in app
def test_finance_detail_dialog_uses_native_desktop_size_and_mobile_fit():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "accounting_dialogs" / "transaction_details_dialog.py").read_text(encoding="utf-8")

    assert 'title="\\u0130\\u015flem Detay\\u0131", width=1440, height=1040' in desktop
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'finance-detail-title-row' in app
    assert 'item.status_label||item.status||"Kay\\u0131t"' in app
    assert '#KAYIT-${String(item.id)}' in app
    assert '.finance-detail-status-badge' in styles
    assert '.finance-detail-record-badge' in styles
    assert '#appDialog.finance-detail-dialog{width:min(1440px,calc(100vw - 40px));max-width:none;height:min(1040px,calc(100vh - 40px));max-height:none' in styles
    assert '#appDialog.finance-detail-dialog>form{display:flex;min-height:0;height:100%;flex-direction:column}' in styles
    assert '#appDialog.finance-detail-dialog #dialogFooter{display:flex;flex:0 0 95px;min-height:95px;align-items:center' in styles
    assert '#appDialog.finance-detail-dialog>form>header>div::before{position:absolute;box-sizing:border-box;left:-13px;top:calc(50% - 2px);width:40px;height:40px' in styles
    assert 'border:1px solid #1e3a5f;border-radius:11px;background:#0c1b2c' in styles
    assert "viewBox='0 0 40 40'" in styles
    assert "stroke-width='1.25'" in styles
    assert "rect x='12' y='8' width='16' height='24' rx='1'" in styles
    assert "M16 16h8M16 21h8M16 26h6" in styles
    assert 'data:image/svg+xml,%3Csvg xmlns=' in styles
    assert '@media(max-width:720px){#appDialog.finance-detail-dialog{box-sizing:border-box;width:calc(100vw - 20px);height:94vh;max-height:94vh' in styles
    assert '#appDialog.finance-detail-dialog>form{box-sizing:border-box;height:100%;max-height:100%;min-height:0}' in styles
    assert '#appDialog.finance-detail-dialog #dialogFooter button{box-sizing:border-box;height:34px;min-height:34px}' in styles


def test_finance_dashboard_uses_native_currency_and_compact_control_layout():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    base_styles = (WEB / "styles.css").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'const metricCurrency="TRY";' in app
    assert 'new Intl.NumberFormat("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})' in app
    assert 'Finansal Dashboard &amp; Defter Takibi' in app
    assert 'body[data-page="finance"] .content{padding:8px 8px 48px}' in styles
    assert 'body[data-page="finance"] .finance-layout{grid-template-columns:minmax(0,1fr) 254px;gap:8px}' in styles
    assert '.finance-quick-grid button{min-height:38px;border:0;border-radius:4px;background:#152338;color:#E2E8F0;font-weight:700;font-size:10px;padding:2px}' in base_styles
    assert '.finance-quick-grid button.green{background:#073034;color:#4EDEA3}' in base_styles
    assert '.finance-quick-grid button.red{background:#3B2B0B;color:#C084FC}' in base_styles
    assert 'styles.css?v=20261029-proforma-dialog-fit-1' in index
    assert 'midnight-reference.css?v=20261029-finance-detail-print-1' in index
    assert 'body[data-page="finance"] aside .finance-ref-status.card{box-sizing:border-box;padding:10px 12px;border:1px solid #1B2A42;border-top:3px solid #4EDEA3;border-radius:8px;background:#0D1829;box-shadow:none;gap:6px}' in styles
    assert 'body[data-page="finance"] aside .finance-ref-status.card:nth-of-type(4){border-top-color:#2563EB}' in styles
    period_start = app.index('pageHead("Finansal Dashboard &amp; Defter Takibi"')
    period_end = app.index('<div class="finance-ref-metrics">', period_start)
    assert 'data-action="collect-finance"' not in app[period_start:period_end]


def test_finance_ledger_groups_rows_by_day_and_allows_expansion():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const groups=new Map()" in app
    assert 'class="finance-ledger-day-row"' in app
    assert 'data-finance-day-toggle="${esc(date)}" aria-expanded="${expanded}"' in app
    assert 'ayecFinanceOpenDate=button.getAttribute("data-finance-day-toggle")' in app
    assert 'finance-ledger tr[hidden]{display:none!important}' in styles
    assert 'groupToggleWorked: initialVisibleRows' in audit
    assert 'dayGroupCount !== 4 || result.financeLedgerGroupWorkflow.rowCount !== 5 || financeCapture.rowCount !== 5 || !financeCapture.groupToggleWorked || financeCapture.visibleRows !== 1' in audit


def test_finance_bank_balance_refresh_keeps_native_try_metric():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("async function ayecLoadFinanceBankBalances")
    end = app.index("function ayecLocalDateKey", start)
    assert 'financeDashboardMoney(balanceTry,"TRY")' in app[start:end]
    assert 'balanceTry/rate' not in app[start:end]
    assert 'loadAllDesktopTableRows("bank_accounts")' in app[start:end]


def test_technician_payment_picker_loads_all_bank_accounts():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("technicianDialog=async function(customer,service)")
    end = app.index("window.ayecBindTechnicianPhotoGallery", start)
    assert 'loadAllDesktopTableRows("bank_accounts").catch(()=>[])' in app[start:end]
    assert 'bank_accounts?limit=500' not in app[start:end]


def test_finance_ledger_uses_desktop_columns_and_row_timestamp():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    source = (ROOT / "src" / "utils" / "finance_manager.py").read_text(encoding="utf-8")
    assert 'item.created_at?.slice(11,16)' in app
    assert r'<th>T\u00fcr</th>' not in app[app.index("function ayecFinanceLedgerMarkup"):app.index("async function ayecLoadFinanceLedger")]
    assert r'<th>Tutar (D\u00f6viz)</th><th>Kur</th><th>Toplam (TRY)</th><th>Durum</th><th>Bakiye (TRY)</th>' in app
    assert '"created_at": created_at' in source


def test_finance_ledger_shows_native_cash_and_receivables_footer():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'class="finance-ledger-summary"' in app
    assert 'Kasa: ${financeDashboardMoney(bankTotal,"TRY")}' in app
    assert 'Bekleyen Alacaklar: ${financeDashboardMoney(receivables,"TRY")}' in app
