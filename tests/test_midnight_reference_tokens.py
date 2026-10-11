from src.utils.theme_manager import ThemeManager
from src.utils._theme_color_utils import contrast_text


def test_reference_surface_levels_have_managed_fallbacks_for_every_theme(monkeypatch):
    from src.utils._theme_qss_transformer import ThemeQSSTransformer
    monkeypatch.setattr(ThemeManager, "_custom_accent_color", None)
    monkeypatch.setattr(ThemeManager, "_custom_text_color", None)
    midnight = ThemeManager.current_palette("Midnight Enterprise Slate")
    assert midnight["finance_surface_lowest"] == "#060E20"
    assert midnight["finance_surface_container"] == "#171F33"
    for theme in ThemeManager.DISPLAY_THEMES:
        palette = ThemeManager.current_palette(theme)
        configured = ThemeManager.get_theme_data(theme).get("palette", {})
        for token, fallback in ThemeManager.REFERENCE_PALETTE_FALLBACKS.items():
            assert palette[token] == configured.get(token, palette[fallback])
            assert ThemeManager.get_palette_color(theme, token) == palette[token]
            raw = "QFrame { background: @" + token + "; }"
            transformed = ThemeQSSTransformer.transform_qss(raw, palette, ThemeManager._light_fallback, ThemeManager.is_dark_theme(theme), midnight)
            assert "@" not in transformed
            assert "background: " + palette[token] in transformed


def test_full_midnight_design_name_resolves_to_existing_dark_palette():
    for name in ("Midnight Enterprise Slate", "midnight-enterprise-slate", "Midnight"):
        assert ThemeManager.normalize_theme_name(name) == "Koyu Mavi"
        assert ThemeManager.is_dark_theme(name)


def test_primary_foreground_token_uses_its_own_background(monkeypatch):
    monkeypatch.setattr(ThemeManager, "_custom_accent_color", None)
    monkeypatch.setattr(ThemeManager, "_custom_text_color", None)
    for name in ThemeManager.DISPLAY_THEMES:
        palette = ThemeManager.current_palette(name)
        expected = contrast_text(palette.get("finance_primary", palette["accent"]))
        assert palette["finance_primary_text"] == expected
        assert ThemeManager.get_palette_color(name, "finance_primary_text") == expected
        assert ThemeManager.get_palette_color(name, "finance_primary") == palette["finance_primary"]
        for foreground, background in ThemeManager.SOLID_FOREGROUND_TOKENS.items():
            configured = ThemeManager.get_theme_data(name).get("palette", {}).get(foreground)
            assert palette[foreground] == (configured or contrast_text(palette[background]))
            assert ThemeManager.get_palette_color(name, foreground) == palette[foreground]
    palette = ThemeManager.current_palette("AYEC")
    assert palette["finance_primary_text"] != palette["selection_text"]


def test_finance_breadcrumb_active_has_a_theme_fallback():
    from src.utils._theme_qss_transformer import ThemeQSSTransformer
    for name in ThemeManager.DISPLAY_THEMES:
        palette = ThemeManager.current_palette(name)
        transformed = ThemeQSSTransformer.transform_qss(
            "QLabel { color: @finance_breadcrumb_active; }",
            palette,
            ThemeManager._light_fallback,
            ThemeManager.is_dark_theme(name),
        )
        assert "color: " + palette["finance_breadcrumb_active"] in transformed
        assert "@" not in transformed


def test_semantic_foreground_survives_literal_repair_and_theme_transition():
    from src.utils._theme_qss_transformer import ThemeQSSTransformer
    raw = "QPushButton { background: @finance_primary; color: @finance_primary_text; } QLabel { color: @text_muted; }"
    for name in ThemeManager.DISPLAY_THEMES:
        palette = ThemeManager.current_palette(name)
        transformed = ThemeQSSTransformer.transform_qss(
            raw, palette, ThemeManager._light_fallback, ThemeManager.is_dark_theme(name),
            ThemeManager.current_palette("Koyu Mavi" if name == "AYEC" else "AYEC"))
        assert "color: " + palette["finance_primary_text"] in transformed
        assert "color: " + palette["text_muted"] in transformed
        assert "background: " + palette["finance_primary"] in transformed
        assert "@" not in transformed
        assert "__AYEC_THEME_TOKEN_" not in transformed


def test_reference_command_actions_have_distinct_theme_managed_solids():
    palette = ThemeManager.current_palette("Midnight Enterprise Slate")
    assert palette["finance_action_income"] == "#34D399"
    assert palette["finance_action_expense"] == "#F43F5E"
    assert palette["finance_action_collection"] == "#A5B4FC"
    assert palette["finance_action_expense"] != palette["danger"]
    for name in ThemeManager.DISPLAY_THEMES:
        palette = ThemeManager.current_palette(name)
        for key in ("finance_action_income", "finance_action_expense", "finance_action_collection"):
            assert ThemeManager.get_palette_color(name, key) == palette[key]
            configured = ThemeManager.get_theme_data(name).get("palette", {}).get(key + "_text")
            assert palette[key + "_text"] == (configured or contrast_text(palette[key]))


def test_solid_button_variants_use_background_specific_foreground(monkeypatch):
    from src.utils.design_system import DesignTokens
    from src.utils._theme_qss_transformer import ThemeQSSTransformer

    monkeypatch.setattr(ThemeManager, "_custom_accent_color", None)
    variants = {"primary": "accent", "success": "success", "destructive": "danger", "warning": "warning"}
    for name in ThemeManager.DISPLAY_THEMES:
        palette = ThemeManager.current_palette(name)
        for variant, background in variants.items():
            foreground = background + "_foreground"
            expected = contrast_text(palette[background])
            assert palette[foreground] == expected
            assert ThemeManager.get_palette_color(name, foreground) == expected
            transformed = ThemeQSSTransformer.transform_qss(
                DesignTokens.get_button_qss(variant), palette, ThemeManager._light_fallback,
                ThemeManager.is_dark_theme(name))
            assert "color: " + expected in transformed
            assert "@" not in transformed
