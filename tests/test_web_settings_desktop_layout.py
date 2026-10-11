from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_settings_desktop_uses_workspace_without_duplicate_page_heading():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="settings"] .content > .page-head > div:first-child {\n    display: none;' in styles
    assert 'body[data-page="settings"] .content > .page-head > .actions {\n    position: fixed;' in styles
    assert "left: calc(var(--sidebar) + 300px);" in styles


def test_settings_section_navigation_preserves_desktop_vertical_alignment():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="settings"] .settings-sidebar {\n    padding-top: 92px;' in styles


def test_theme_settings_render_desktop_controls_and_persist_setting_keys():
    script = (WEB / "settings-theme-reference.js").read_text(encoding="utf-8")
    for key in (
        "color_theme_full",
        "appearance_mode",
        "interface_scale_percent",
        "side_menu_label_mode",
        "custom_accent_color",
        "custom_text_color",
        "nav_mode",
    ):
        assert key in script
    assert 'desktopWrite("settings", { key, value })' in script
    assert 'id="themeScale" type="range"' in script
    assert "theme-appearance-panel" in script

def test_mobile_voice_search_control_has_visible_fallback_label():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert '.top-actions .global-search-voice::after' in styles
    assert 'content: "Voice";' in styles


def test_security_settings_hide_extra_password_status_copy():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="settings"] .security-reference [data-security-configured] { display: none; }' in styles


def test_settings_header_tracks_selected_desktop_section():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    wrapper = app[app.index("const ayecRenderSettingsBeforeSectionTitle"):]

    assert 'find(([id]) => id === settingsSection)' in wrapper
    assert '$("#pageTitle").textContent = selected[2]' in wrapper


def test_settings_navigation_keeps_selected_section_title():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    wrapper = app[app.index("const ayecNavigateBeforeSettingsSectionTitle"):]

    assert 'ayecNavigateBeforeSettingsSectionTitle(next)' in wrapper
    assert 'if (next === "settings" && selected)' in wrapper
    assert '$("#pageTitle").textContent = selected[2]' in wrapper


def test_mobile_settings_reuses_selected_title_without_duplicate_intro():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="settings"] .content > .page-head > div:first-child { display: none; }' in styles
    assert 'body[data-page="settings"] .content > .page-head { min-height: 0; margin: 0; gap: 0; }' in styles
