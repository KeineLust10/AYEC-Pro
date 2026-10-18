from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_product_group_page_matches_reference_metrics_and_table_structure():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "product-groups.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    table = script.split('id="groupTable"', 1)[1].split("</table>", 1)[0]

    assert 'id="groupMetrics"' in script
    assert 'id="groupTable"' in script
    assert "Ba\\u011fl\\u0131 marka / kategori" in script
    assert "Standart servis \\u015fablonu" in script
    assert "En y\\u00fcksek servis hacmi" in script
    assert 'esc(volumeGroup?.name||"\\u2014")' in script
    assert "groupDevices(volumeGroup?.name)" in script
    assert "Kay\\u0131tl\\u0131 cihaz envanteri" not in table
    assert "esc(groupTemplate(row.name))" in script
    assert ".group-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))" in styles
    assert ".group-list-card.cards-mode .table-wrap{display:none}" in styles
    assert "@media(max-width:520px){.group-metrics" in styles
    assert "product-groups.js?v=20261007-1" in html


def test_product_group_rows_keep_desktop_id_order_and_number_format():
    script = (WEB / "product-groups.js").read_text(encoding="utf-8")

    assert '.sort((a,b)=>Number(a.id)-Number(b.id))' in script
    assert 'String((groupPage-1)*groupPageSize+index+1).padStart(2,"0")' in script
    assert 'const brandText=row=>String(row?.brand??row?.name??"").trim()' in script
    assert '.map(brandText).filter(Boolean)' in script
    assert '${linked.length} Marka${linked.length?` (' in script
