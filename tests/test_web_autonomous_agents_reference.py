from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_autonomous_agents_uses_shared_settings_and_reference_controls():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function renderAutonomousAgentsSettings(){")
    end = app.index("function settingBody(s){", start)
    view = app[start:end]

    for key in (
        "agent_system_activation",
        "agent_voice_feedback",
        "agent_whatsapp_reports",
        "agent_customer_intelligence",
        "agent_term_correction",
        "agent_error_reporting",
        "assistant_fab_enabled",
        "ultramsg_instance",
        "ultramsg_token",
        "ultramsg_phone",
    ):
        assert key in view
    assert 'settingsSection==="autonomous-agents"' in app
    assert "Test Paketi G\\u00f6nder" in view
    assert "function saveAutonomousSettings()" in view
    assert "function testAutonomousSettings()" in view
    assert "Ag testi veya mesaj gonderimi yapilmadi" in view


def test_web_autonomous_agents_css_has_tablet_and_mobile_layouts():
    css = (ROOT / "Web_Arayuzu" / "web" / "autonomous-reference.css").read_text(encoding="utf-8")
    html = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")

    assert "@media(max-width:760px)" in css
    assert "@media(max-width:420px)" in css
    assert "grid-template-columns:minmax(0,1fr)" in css
    assert "autonomous-reference.css" in html
