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
    assert '@page{size:A4;margin:0}body{font:9pt Inter,"Segoe UI",Arial,sans-serif;margin:4px}' in app
    assert 'const amount=Number(currency==="TRY"?(item.amount_try||0):(item.amount||0))||0' in app
    assert '`Tarih: ${item.date||""}`' in app
    assert '`Tur: ${item.type_label||""}`' in app
    assert '`Musteri: ${item.customer_name||""}`' in app
    assert '`Tutar: ${money(amount,currency)}`' in app
    receipt_audit = (ROOT / "tools" / "quality" / "accounting_receipt_offscreen.cjs").read_text(encoding="utf-8")
    assert 'amount:999,amount_try:73,currency:"TRY"' in receipt_audit
    assert 'amount:123,amount_try:999' in receipt_audit
    assert 'foreignReceiptMarkup.includes("Tutar: "+money(123,"USD"))' in receipt_audit
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
