from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_company_logo_preview_uses_csp_safe_load_and_error_listeners():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'id="companyLogoPreview"' in app
    assert 'onload="this.nextElementSibling.hidden=true"' not in app
    assert 'onerror="this.hidden=true"' not in app
    assert 'document.addEventListener("load",handleCompanyLogoPreview,true)' in app
    assert 'document.addEventListener("error",handleCompanyLogoPreview,true)' in app
