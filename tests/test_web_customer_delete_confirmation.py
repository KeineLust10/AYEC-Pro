from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_customer_delete_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "customer-context-parity.js").read_text(encoding="utf-8")
    start = source.index("function deleteCustomer(customer)")
    end = source.index("function customerAction", start)
    block = source[start:end]

    assert "window.confirm" not in block
    assert 'window.openDialog("M\\u00fc\\u015fteriyi Sil", "S\\u0130LME ONAYI"' in block
    assert '"Evet, Sil"' in block
    assert 'textContent = "Hay\\u0131r"' in block
    assert '"/api/desktop/customer/delete"' in block
    assert 'db.customers = db.customers.filter' in block


def test_customer_context_uses_app_lexical_state_helpers():
    source = (ROOT / "Web_Arayuzu" / "web" / "customer-context-parity.js").read_text(encoding="utf-8")

    assert "window.db" not in source
    assert "window.money" not in source
    assert "window.save();" not in source
    assert "db.customers.find" in source
    assert "money(amount, \"TRY\")" in source
    assert "save();" in source
