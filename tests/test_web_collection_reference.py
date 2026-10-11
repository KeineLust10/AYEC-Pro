from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_collection_dialog_keeps_readable_financial_labels_on_desktop_and_mobile():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    base_styles = (WEB / "styles.css").read_text(encoding="utf-8")
    server = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    assert 'id="collectionDebtValue"' in app
    assert 'id="collectionSelectedValue"' in app
    assert 'id="collectionTryEquivalent"' in app
    assert ".collection-section-head{font-size:12px}" in styles
    assert ".collection-balance-row,.collection-net small,.collection-net span" in styles
    assert "@media(max-width:760px){.collection-section-head" in styles
    assert "/api/desktop/customer/open-debts?customer_id=" in app
    assert 'debtPanel.className="collection-debt-list"' in app
    assert 'selected_debt_ids:[...selectedDebtIds]' in app
    assert 'type="checkbox" name="collectionDebt"' in app
    assert 'id="collectionDebtSelectedTotal"' in app
    assert ".collection-debt-item{display:grid" in styles
    assert ".collection-layout{grid-template-columns:repeat(2,minmax(0,1fr))}" in base_styles
    assert "@media(max-width:760px){.collection-layout{grid-template-columns:1fr}}" in base_styles
    assert ".collection-debt-items{max-height:150px}" in styles
    assert ".collection-debt-list>footer{display:flex;justify-content:flex-end" in styles
    assert ".collection-debt-list>header strong{font-size:13px" in styles
    assert ".collection-debt-item strong{overflow:hidden;font-size:13px" in styles
    assert "@media(max-width:760px){.collection-debt-items{max-height:170px}.collection-debt-item{padding:8px 6px}.collection-debt-item small{font-size:12px}" in styles
    assert 'path == "/api/desktop/customer/open-debts"' in server
    assert "def customer_open_debt_items" in server


def test_collection_payment_labels_and_currency_summary_are_readable():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert ".collection-method{font-size:12px}" in styles
    assert ".collection-currency strong{font-size:13px}" in styles
    assert ".collection-aside>header strong{font-size:13px}" in styles
    assert ".collection-customer small,.collection-customer span{font-size:12px}" in styles
    assert ".collection-debt-list>header strong{font-size:14px}" in styles
    assert ".collection-debt-item strong,.collection-debt-item>b{font-size:14px}" in styles
    assert ".collection-count{font-size:12px}" in styles
