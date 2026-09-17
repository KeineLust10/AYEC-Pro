# -*- coding: utf-8 -*-
import re
from pathlib import Path

THEME_DIR = Path(__file__).resolve().parents[1] / "themes"

THEME_ALIASES = {
    "AYEC": "AYEC",
    "Bulut": "Koyu Mavi",
    "Nord": "Koyu Mavi",
    "Forest": "Forest",
    "Neon": "Koyu Mavi",
    "Terra": "AYEC",
    "Sakura": "Koyu Mavi",
    "Sunset": "Forest",
    "Midnight": "Koyu Mavi",
    "Ocean": "Koyu Mavi",
    "Ocaen": "Koyu Mavi",
    "Lavender": "Koyu Mavi",
    "Levander": "Koyu Mavi",
    "Koyu Mavi": "Koyu Mavi",
    "Koyu Tema": "Koyu Mavi",
    "Koyu Mavi - Koyu Tema": "Koyu Mavi",
}

THEME_FILES = {
    "AYEC": {"json": "light_theme.json", "qss": "light_theme.qss"},
    "Koyu Mavi": {"json": "dark_blue_theme.json", "qss": "dark_blue_theme.qss"},
    "Forest": {"json": "forest_theme.json", "qss": "forest_theme.qss"},
}

THEMES = {name: {} for name in THEME_FILES}
DISPLAY_THEMES = ["AYEC", "Koyu Mavi", "Forest"]
DARK_THEMES = {"Koyu Mavi", "Forest"}

COLOR_TOKEN_RE = re.compile(
    r"(#[A-Fa-f0-9]{3,8}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|\bwhite\b|\bblack\b)",
    re.IGNORECASE,
)
BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
DECL_RE = re.compile(r"([\w\-]+)\s*:\s*([^;{}]+)(?:;|\s*$)")
TOKEN_REF_RE = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")
UNSUPPORTED_QSS_DECL_RE = re.compile(
    r"\s*(?:letter-spacing|text-transform|line-height|opacity|box-shadow|backdrop-filter|filter|"
    r"transition(?:-[\w-]+)?|transform|cursor|bg-color|text-decoration|aspect-ratio|user-select)\s*:\s*[^;{}]+;?",
    re.IGNORECASE,
)
MOJIBAKE_HINT_RE = re.compile(r"([\u00C3\u00C4\u00C5\u00E2\u00C2].)")

NEUTRAL_HEX_RE = re.compile(
    r"#(?:fff(?:fff)?|000(?:000)?|f[0-9a-f]{5}|e[0-9a-f]{5}|d[0-9a-f]{5}|c[0-9a-f]{5}|"
    r"[0-4][0-9a-f]{5}|[5-9a-f][0-9a-f]{1,5})\b",
    re.IGNORECASE,
)

VIVID_PALETTE_KEYS = {
    "accent", "accent_hover", "accent_pressed", "selection_bg",
    "danger", "danger_bg", "success", "warning", "warning_bg",
}

SAFE_REMAP_KEYS = {
    "window", "surface", "surface_alt", "border",
    "disabled_bg", "text", "text_muted", "disabled_text",
    "button_text", "selection_text",
}
