from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_brand_service_counts_load_complete_device_results():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("async function loadBrandsReference")
    end = app.index("\n}", start)
    block = app[start:end]

    assert 'loadAllDesktopTableData("devices",{q:row.brand||""})' in block
    assert 'devices?limit=500' not in block


def test_brand_management_table_uses_shared_readable_web_type_scale():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    stylesheet = (WEB / "styles.css").read_text(encoding="utf-8")

    assert re.search(r'href="styles\.css\?v=[^"]+"', html)
    assert 'body[data-page="brands"] .brands-reference-table table{font-size:12px}' in stylesheet
    assert 'body[data-page="brands"] .brands-reference-table td{font-size:12px}' in stylesheet
    assert 'body[data-page="brands"] .brands-count{font-size:12px}' in stylesheet
    assert 'body[data-page="brands"] .brands-reference-footer{font-size:12px}' in stylesheet

