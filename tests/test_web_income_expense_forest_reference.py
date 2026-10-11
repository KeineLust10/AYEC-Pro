from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_income_and_expense_views_use_forest_surface_tokens():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    for page in ("income", "expense"):
        scope = f'html[data-theme="forest"] body[data-page="{page}"]'
        assert f"{scope} .ie-page" in styles
        assert f"{scope} .ie-metrics article" in styles
        assert f"{scope} .ie-panel" in styles
        assert f"{scope} .ie-table-wrap" in styles
        assert "background: var(--surface);" in styles
        assert "background: var(--surface-2);" in styles
        assert "background: var(--input-bg, var(--surface));" in styles

