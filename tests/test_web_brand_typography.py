from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_brand_management_table_uses_shared_readable_web_type_scale():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    stylesheet = (WEB / "styles.css").read_text(encoding="utf-8")

    assert re.search(r'href="styles\.css\?v=[^"]+"', html)
    assert 'body[data-page="brands"] .brands-reference-table table{font-size:12px}' in stylesheet
    assert 'body[data-page="brands"] .brands-reference-table td{font-size:12px}' in stylesheet
    assert 'body[data-page="brands"] .brands-count{font-size:12px}' in stylesheet
    assert 'body[data-page="brands"] .brands-reference-footer{font-size:12px}' in stylesheet

