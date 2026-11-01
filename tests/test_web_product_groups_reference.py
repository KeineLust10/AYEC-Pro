from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_product_group_page_matches_reference_metrics_and_table_structure():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "product-groups.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    parity = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    table = script.split('id="groupTable"', 1)[1].split("</table>", 1)[0]

    assert 'id="groupMetrics"' in script
    assert 'id="groupTable"' in script
    assert "Ba\\u011fl\\u0131 marka / kategori" in script
    assert "Standart servis \\u015fablonu" in script
    assert "En y\\u00fcksek servis hacmi" in script
    assert 'esc(volumeGroup?.name||"\\u2014")' in script
    assert "groupDevices(volumeGroup?.name)" in script
    assert 'Math.round(groupDevices(volumeGroup?.name)/inventory*100)' in script
    assert '"Toplam hacmin %"' in script
    assert '"Servis verisi yok"' in script
    assert 'groupDevices(volumeGroup?.name)} kay\\u0131tl\\u0131 cihaz' not in script
    assert "Kay\\u0131tl\\u0131 cihaz envanteri" not in table
    assert "esc(groupTemplate(row.name))" in script
    assert ".group-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))" in styles
    assert ".group-list-card.cards-mode .table-wrap{display:none}" in styles
    assert "@media(max-width:520px){.group-metrics" in styles
    assert "product-groups.js?v=20261028-product-groups-page-fill-1" in html
    assert "groupPageSize=20" in script
    assert 'id="groupPageSize" value="20"' in script
    assert "async function loadTableRows(table)" in script
    assert "offset<Number(first.count||0)" in script
    assert "offset=${offset}" in script
    assert 'function groupIconMarkup(name)' in script
    assert 'class="group-name-cell"' in script
    assert 'body[data-page="product-groups"] #groupTable td:nth-child(1) { width: 5%; }' in parity
    assert 'body[data-page="product-groups"] #groupTable td:nth-child(6) { width: 13%; }' in parity
    assert 'width: 205px;' in parity
    assert 'font-size: 18px;' in parity


def test_product_group_matched_fixture_capture_covers_populated_layout():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "productGroupsPopulatedCapture" in runner
    assert "product-groups-populated-1300x850.png" in runner
    assert 'metrics[2].includes("%42")' in runner


def test_product_group_rows_keep_desktop_id_order_and_number_format():
    script = (WEB / "product-groups.js").read_text(encoding="utf-8")

    assert '.sort((a,b)=>Number(a.id)-Number(b.id))' in script
    assert 'String((groupPage-1)*groupPageSize+index+1).padStart(2,"0")' in script
    assert 'const brandText=row=>String(row?.brand??row?.name??"").trim()' in script
    assert '.map(brandText).filter(Boolean)' in script
    assert '${linked.length} Marka${linked.length?` (' in script


def test_product_group_inventory_audit_covers_rows_beyond_api_page_limit():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "length:1004" in runner
    assert "groups.devicePageOffsets" in runner
    assert 'JSON.stringify(groups.devicePageOffsets) !== JSON.stringify([0,1000])' in runner
    assert 'groups.deviceInventoryText !== "1.004"' in runner

def test_product_group_delete_confirmation_is_cancelable_before_write():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "deleteConfirmationOpened,deleteCancelPreserved" in runner
    assert "!productGroupManagementWorkflow.deleteCancelPreserved" in runner
    assert "deleteFailureRetained" in runner
    assert "!productGroupManagementWorkflow.deleteFailureRetained" in runner
    assert "productGroupManagementWorkflow.calls.length !== 4" in runner
