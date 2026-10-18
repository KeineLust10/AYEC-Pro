from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_product_group_metrics_and_toolbar_match_desktop_density():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="product-groups"] .group-metrics article {\n    position: relative;\n    height: 82px;\n    min-height: 82px;' in styles
    assert 'body[data-page="product-groups"] .group-toolbar {\n    min-height: 50px;' in styles


def test_product_group_table_uses_compact_reference_rows():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="product-groups"] .group-list-card td {\n    height: 49px;' in styles
    assert 'body[data-page="product-groups"] .group-list-card th {\n    height: 29px;' in styles




def test_product_group_table_viewport_fits_ten_desktop_rows():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    start = styles.index('body[data-page="product-groups"] .group-list-card .table-wrap {')
    block = styles[start:styles.index("}", start)]
    assert "height: calc(100vh - 440px);" in block
    assert "max-height: calc(100vh - 440px);" in block



def test_product_group_pagination_footer_matches_compact_desktop_controls():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    start = styles.index('body[data-page="product-groups"] .group-list-card footer {')
    block = styles[start:styles.index("}", start)]
    assert "min-height: 36px;" in block
    assert "padding: 3px 12px;" in block


def test_product_group_table_columns_follow_desktop_proportions():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="product-groups"] #groupTable {\n    table-layout: fixed;' in styles
    for column, width in enumerate(("4%", "26%", "26%", "26%", "8%", "10%"), start=1):
        selector = f'#groupTable th:nth-child({column}),'
        assert selector in styles
        assert f"width: {width};" in styles


def test_product_group_heading_metric_icons_and_search_match_desktop():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    script = (WEB / "product-groups.js").read_text(encoding="utf-8")

    assert ".group-active-badge" in styles
    assert 'class="group-active-badge">${active} Aktif Kategori' in script
    assert 'body[data-page="product-groups"] .group-metrics article:nth-child(1)::after' in styles
    assert 'body[data-page="product-groups"] .group-metrics article:nth-child(4)::after' in styles
    assert styles.count("background-image: url(\"data:image/svg+xml,") == 4
    assert styles.count('content: "";') >= 4
    assert "flex: 0 0 286px;" in styles
    assert 'body[data-page="product-groups"] .group-view-toggle {\n    margin-left: auto;' in styles
    assert 'body[data-page="product-groups"] #groupExport {\n    width: 72px;' in styles
    assert 'body[data-page="product-groups"] #groupPdf {\n    width: 78px;' in styles
    assert 'body[data-page="product-groups"] #groupPrint {\n    width: 56px;' in styles
    assert 'body[data-page="product-groups"] #groupExport,\n  body[data-page="product-groups"] #groupPdf,\n  body[data-page="product-groups"] #groupPrint {\n    font-size: 9px;\n    white-space: nowrap;' in styles
