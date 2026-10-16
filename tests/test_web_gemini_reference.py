from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gemini_reference_page_wires_settings_and_actions():
    app_js = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'settingsSection === "ai-settings"' in app_js
    assert 'data-gemini-setting="gemini_api_key"' in app_js
    assert 'data-gemini-range="gemini_max_output_tokens"' in app_js
    assert 'data-gemini-range="gemini_temperature"' in app_js
    assert 'data-gemini-setting="gemini_sensitive_data_masking"' in app_js
    assert 'data-gemini-setting="gemini_zero_downtime_rotation"' in app_js
    assert 'data-gemini-setting="gemini_smart_token_compression"' in app_js
    assert 'data-gemini-setting="gemini_cost_limit_protection"' in app_js
    assert 'data-gemini-setting="gemini_auto_load_shedding"' in app_js
    assert "data-gemini-save" in app_js
    assert "data-gemini-export" in app_js


def test_gemini_reference_styles_include_compact_and_mobile_layouts():
    css = (ROOT / "Web_Arayuzu" / "web" / "gemini-reference.css").read_text(encoding="utf-8")
    index = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'href="gemini-reference.css?v=20261012-1"' in index
    assert "@media (max-width: 1050px)" in css
    assert "@media (max-width: 560px)" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
