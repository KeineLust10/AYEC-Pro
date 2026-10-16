from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_account_suspend_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "audit-reference.js").read_text(encoding="utf-8")
    start = source.index("async function auditReferenceSuspend(account)")
    end = source.index("\n", start)
    block = source[start:end]

    assert "window.confirm" not in block
    assert 'openDialog("Hesab\\u0131 Ask\\u0131ya Al"' in block
    assert "A\\u00e7\\u0131k oturumlar sonland\\u0131r\\u0131lmaz" in block
    assert '"Evet, Kapat"' in block
    assert 'textContent="Hay\\u0131r"' in block
    assert '"/api/desktop/audit/suspend-user"' in block
