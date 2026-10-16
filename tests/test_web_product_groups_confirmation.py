from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_product_group_delete_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "product-groups.js").read_text(encoding="utf-8")
    start = source.index("async function groupAction(action,id)")
    end = source.index("\n  function showHierarchy", start)
    block = source[start:end]

    assert "window.confirm" not in block and "!confirm(" not in block
    assert 'openDialog("\\u00dcr\\u00fcn Grubunu Sil"' in block
    assert '"Evet, Sil"' in block
    assert 'textContent="Hay\\u0131r"' in block
    assert 'JSON.stringify({id:row.id,_action:"delete"})' in block
