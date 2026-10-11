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
    assert 'data-finance-detail-action="edit"' in app
    assert 'Stok / Hizmet Kalemleri' in app
    assert '\\u0130\\u015flem A\\u00e7\\u0131klamas\\u0131 &amp; Notlar' in app
    assert '$("#dialogFooter").innerHTML=`<button type="button" class="secondary" data-finance-detail-action="print"' in app
    assert 'Cari Bor\\u00e7 Kapatma Referans\\u0131' in app
    assert 'Birim Fiyat' in app and 'Tahsilat / \\u0130\\u015flem Notu' in app
    cleanup = re.search(r'dialog\.classList\.remove\(([^)]*)\)', app)
    assert cleanup
    assert {'"finance-detail-dialog"', '"customer-editor-dialog"', '"service-accept-dialog"'} <= set(
        re.findall(r'"[^"]+"', cleanup.group(1))
    )
    assert '.finance-detail-ref{display:grid;grid-template-columns:minmax(250px,4fr) minmax(0,8fr)' in styles
    assert '@media(max-width:720px){.finance-detail-ref{grid-template-columns:minmax(0,1fr)}' in styles
