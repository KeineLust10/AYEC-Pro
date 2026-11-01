from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_support_desktop_type_and_inner_margins_match_native_reference():
    stylesheet = (ROOT / "Web_Arayuzu" / "web" / "support-reference.css").read_text(encoding="utf-8")
    index = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")

    assert 'font-family:"Segoe UI",sans-serif' in stylesheet
    assert ".support-contact{display:grid;gap:25px;padding:14px 18px 28px 32px}" in stylesheet
    assert "min-height:182px" in stylesheet
    assert "font-size:37px" in stylesheet
    assert "font-size:17px;line-height:1.2" in stylesheet
    assert "font-size:29px" in stylesheet
    assert ".support-action-card strong{font-size:20px;line-height:1.3}" in stylesheet
    assert ".support-action-card small{color:var(--muted,#9ca3b4);font-size:16px;line-height:1.25}" in stylesheet
    assert "support-reference.css?v=20261026-support-type-parity-3" in index


def test_support_mobile_type_overrides_stay_compact():
    stylesheet = (ROOT / "Web_Arayuzu" / "web" / "support-reference.css").read_text(encoding="utf-8")

    assert ".support-hero h2{font-size:23px}" in stylesheet
    assert ".support-phone{font-size:19px;white-space:normal}" in stylesheet
    assert ".support-contact{gap:14px;padding:10px 0 20px}" in stylesheet

def test_offscreen_support_audit_checks_desktop_contact_destinations_and_safe_targets():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert '"https://wa.me/905348781047"' in audit
    assert '"mailto:destek@ayecpro.com"' in audit
    assert '"https://www.teamviewer.com"' in audit
    assert 'support.targets' in audit
    assert 'support.rels' in audit

\n