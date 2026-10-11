from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_product_group_metrics_and_toolbar_match_desktop_density():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="product-groups"] .group-metrics article {\n    height: 82px;\n    min-height: 82px;' in styles
    assert 'body[data-page="product-groups"] .group-toolbar {\n    min-height: 50px;' in styles


def test_product_group_table_uses_compact_reference_rows():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="product-groups"] .group-list-card td {\n    height: 49px;' in styles
    assert 'body[data-page="product-groups"] .group-list-card th {\n    height: 29px;' in styles

