# -*- coding: utf-8 -*-
import re
from PyQt6.QtGui import QColor
from ._theme_constants import (
    COLOR_TOKEN_RE,
    BLOCK_RE,
    DECL_RE,
    TOKEN_REF_RE,
    UNSUPPORTED_QSS_DECL_RE,
    SAFE_REMAP_KEYS,
)
from ._theme_color_utils import is_vivid_color, is_neutral_value
from src.utils.logger import logger


class ThemeQSSTransformer:
    """Transforms QSS with current palette colors."""
    @staticmethod
    def sanitize_qss(qss_text):
        if not qss_text:
            return qss_text
        return UNSUPPORTED_QSS_DECL_RE.sub("", qss_text)

    @staticmethod
    def _replace_color_tokens(value, target_hex):
        if not value or "qlineargradient" in value.lower() or "qradialgradient" in value.lower():
            return value
        return COLOR_TOKEN_RE.sub(target_hex, value)

    @staticmethod
    def _resolve_palette_token(token, current_palette, light_fallback):
        aliases = {
            "bg": "window",
            "background": "window",
            "fg": "text",
            "foreground": "text",
            "card": "surface",
            "panel": "surface",
            "input_bg": "surface",
            "muted": "text_muted",
            "hover": "hover_bg",
            "primary": "accent",
            "primary_hover": "accent_hover",
            "primary_pressed": "accent_pressed",
        }
        key = aliases.get(token, token)
        value = current_palette.get(key)
        if value:
            return str(value)

        if token.endswith("_hover"):
            base = aliases.get(token[:-6], token[:-6])
            return str(
                current_palette.get(base)
                or current_palette.get("accent_hover")
                or current_palette.get("selection_bg")
                or light_fallback("selection_bg", "#3B82F6")
            )
        if token.endswith("_pressed"):
            base = aliases.get(token[:-8], token[:-8])
            return str(
                current_palette.get(base)
                or current_palette.get("accent_pressed")
                or current_palette.get("selection_bg")
                or light_fallback("selection_bg", "#3B82F6")
            )
        if token.endswith("_bg"):
            return str(current_palette.get("surface_alt") or light_fallback("surface_alt", "#E5E7EB"))
        if token.endswith("_text") or token.endswith("_color"):
            return str(current_palette.get("text") or light_fallback("text", "#111827"))

        logger.warning(f"Unknown QSS theme token '@{token}' resolved to text color")
        return str(current_palette.get("text") or light_fallback("text", "#111827"))

    @classmethod
    def _map_decl_color(cls, selector, prop, value, current_palette, light_fallback):
        prop_l = prop.lower()
        sel = selector.lower()

        if "transparent" in value.lower() or "none" in value.lower():
            return value

        if "selection-background-color" in prop_l:
            return cls._replace_color_tokens(value, current_palette.get("selection_bg", light_fallback("selection_bg")))
        if "selection-color" in prop_l:
            return cls._replace_color_tokens(value, current_palette.get("selection_text", light_fallback("selection_text")))
        if prop_l == "color":
            if not is_neutral_value(value):
                return value
            if "qpushbutton" in sel:
                if ":disabled" in sel:
                    return cls._replace_color_tokens(value, current_palette.get("disabled_text", light_fallback("disabled_text")))
                if ":pressed" in sel or ":checked" in sel or ":selected" in sel:
                    return cls._replace_color_tokens(value, current_palette.get("selection_text", light_fallback("selection_text")))
                return cls._replace_color_tokens(value, current_palette.get("button_text", light_fallback("text")))
            if ":disabled" in sel:
                return cls._replace_color_tokens(value, current_palette.get("disabled_text", light_fallback("disabled_text")))
            return cls._replace_color_tokens(value, current_palette.get("text", light_fallback("text")))

        if "border" in prop_l:
            if not is_neutral_value(value):
                return value
            return cls._replace_color_tokens(value, current_palette.get("border", light_fallback("border")))

        if "background" in prop_l:
            if not is_neutral_value(value):
                return value
            if "qpushbutton" in sel:
                if ":disabled" in sel:
                    return cls._replace_color_tokens(value, current_palette.get("disabled_bg", light_fallback("disabled_bg")))
                return value

            if "qcombobox" in sel and "qabstractitemview::item:selected" in sel:
                return cls._replace_color_tokens(value, current_palette.get("selection_bg", light_fallback("selection_bg")))
            if "qcombobox" in sel and "qabstractitemview::item:hover" in sel:
                return cls._replace_color_tokens(value, current_palette.get("surface_alt", light_fallback("surface_alt")))
            if "qcombobox::drop-down:hover" in sel:
                return cls._replace_color_tokens(value, current_palette.get("selection_bg", light_fallback("selection_bg")))
            if "qcombobox::drop-down" in sel:
                return cls._replace_color_tokens(value, current_palette.get("surface_alt", light_fallback("surface_alt")))
            if "qcombobox:hover" in sel:
                return cls._replace_color_tokens(value, current_palette.get("surface_alt", light_fallback("surface_alt")))

            if "qlineedit" in sel or "qtextedit" in sel or "qcombobox" in sel:
                return cls._replace_color_tokens(value, current_palette.get("surface", light_fallback("surface")))

            if "qmenubar" in sel or "qstatusbar" in sel or "qheaderview" in sel:
                return cls._replace_color_tokens(value, current_palette.get("surface_alt", light_fallback("surface_alt")))

            if "qscrollbar" in sel:
                return cls._replace_color_tokens(value, current_palette.get("disabled_bg", light_fallback("disabled_bg")))

            return cls._replace_color_tokens(value, current_palette.get("surface", light_fallback("surface")))

        return value

    @classmethod
    def remap_qss_declarations(cls, qss_text, current_palette, light_fallback):
        if not qss_text:
            return qss_text

        rebuilt = []
        last_end = 0

        for match in BLOCK_RE.finditer(qss_text):
            rebuilt.append(qss_text[last_end:match.start()])
            selector = match.group(1)
            body = match.group(2)
            last_end = match.end()

            body_out = []
            body_last = 0
            for decl in DECL_RE.finditer(body):
                body_out.append(body[body_last:decl.start()])
                prop = decl.group(1)
                value = decl.group(2)
                try:
                    mapped = cls._map_decl_color(selector, prop, value, current_palette, light_fallback)
                except Exception:
                    mapped = value
                body_out.append(f"{prop}: {mapped};")
                body_last = decl.end()

            body_out.append(body[body_last:])
            # Restore the braces that BLOCK_RE matched but did not capture in groups
            rebuilt.append(f"{selector}{{{''.join(body_out)}}}")

        rebuilt.append(qss_text[last_end:])
        return "".join(rebuilt)

    @classmethod
    def remap_palette_literals(cls, qss_text, old_palette, new_palette):
        if not qss_text or not old_palette:
            return qss_text
        pairs = []

        for key, old_val in old_palette.items():
            if key not in SAFE_REMAP_KEYS:
                continue
            new_val = new_palette.get(key)
            if not old_val or not new_val:
                continue
            if str(old_val).lower() == str(new_val).lower():
                continue
            if is_vivid_color(str(old_val)):
                continue
            pairs.append((str(old_val), str(new_val)))

        if not pairs:
            return qss_text
        txt = qss_text
        for old, new in sorted(pairs, key=lambda item: len(item[0]), reverse=True):
            txt = re.sub(re.escape(old), new, txt, flags=re.IGNORECASE)
        return txt

    @classmethod
    def harmonize_literal_neutrals(cls, qss_text, current_palette, is_dark_theme):
        if not qss_text:
            return qss_text
        p = current_palette
        txt = qss_text

        if is_dark_theme:
            _surface = p.get("surface", "#2D2D2D")
            _window = p.get("window", "#1E1E1E")
            _text = p.get("text", "#E5E7EB")
            _surface_alt = p.get("surface_alt", "#3C3C3C")
            _border = p.get("border", "#4A4A4A")
            _disabled_bg = p.get("disabled_bg", "#374151")
            _text_muted = p.get("text_muted", "#9CA3AF")
            if not is_vivid_color(_surface):
                txt = re.sub(r"\bwhite\b", _surface, txt, flags=re.IGNORECASE)
            if not is_vivid_color(_text):
                txt = re.sub(r"\bblack\b", _text, txt, flags=re.IGNORECASE)
            replacements = {
                "#FFFFFF": _surface,
                "#FFF":    _surface,
                "#FAFAFA": _window,
                "#F9FAFB": _window,
                "#F7F8FA": _window,
                "#F7F8FC": _window,
                "#F3F4F6": _window,
                "#F5F5F5": _surface_alt,
                "#F3F4F8": _surface_alt,
                "#E5E7EB": _surface_alt,
                "#ECEFF5": _surface_alt,
                "#E8E8E8": _surface_alt,
                "#E5EAF2": _border,
                "#D1D5DB": _border,
                "#C9CDD3": _border,
                "#B8C0CC": _border,
                "#AEB4BD": _border,
                "#D6DDE9": _border,
                "#D6D6D6": _border,
                "#111827": _text,
                "#1F2937": _text,
                "#64748B": _text_muted,
                "#F8FAFC": _window,
                "#F1F5F9": _surface_alt,
                "#F4F7FB": _window,
                "#E9EEF6": _surface_alt,
                "#CAD5E3": _border,
                "#E5EBF3": _disabled_bg,
                "#EEF3F9": _surface_alt,
                "#172033": _text,
                "#5E6B82": _text_muted,
                "#8A96A8": _text_muted,
                "#FFF7FB": _window,
                "#FCEFF6": _surface_alt,
                "#EFCFE1": _border,
                "#F5EAF0": _disabled_bg,
                "#FDF0F7": _surface_alt,
                "#3A2331": _text,
                "#7B5A70": _text_muted,
                "#B495A6": _text_muted,
                "#FFF8F2": _window,
                "#FFFDFB": _surface,
                "#FFF0E8": _surface_alt,
                "#F7E9DE": _surface_alt,
                "#E3CBB9": _border,
                "#F0E6DF": _disabled_bg,
                "#3D2C24": _text,
                "#7A6052": _text_muted,
                "#AE9587": _text_muted,
                "#F0F8FF": _window,
                "#E1F2FF": _surface_alt,
                "#B0D4EE": _border,
                "#D6EEF8": _disabled_bg,
                "#E8F5FF": _surface_alt,
                "#1A3A5C": _text,
                "#4A7AA0": _text_muted,
                "#7AAFC8": _text_muted,
                "#F9F5FF": _window,
                "#F0E8FF": _surface_alt,
                "#D9C8F5": _border,
                "#EDE5FF": _disabled_bg,
                "#F5EFFF": _surface_alt,
                "#2D1E52": _text,
                "#6E4D9E": _text_muted,
                "#9B8ABF": _text_muted,
            }
        else:
            _window = p.get("window", "#FFFFFF")
            _surface = p.get("surface", "#F5F5F5")
            _text = p.get("text", "#1F2937")
            _surface_alt = p.get("surface_alt", "#E8E8E8")
            _border = p.get("border", "#D6D6D6")
            _disabled_bg = p.get("disabled_bg", "#ECEFF5")
            _text_muted = p.get("text_muted", "#6B7280")
            if not is_vivid_color(_window):
                txt = re.sub(r"\bwhite\b", _window, txt, flags=re.IGNORECASE)
            if not is_vivid_color(_text):
                txt = re.sub(r"\bblack\b", _text, txt, flags=re.IGNORECASE)
            replacements = {
                "#1E1E1E": _window,
                "#2D2D2D": _surface,
                "#3C3C3C": _surface_alt,
                "#4A4A4A": _border,
                "#374151": _disabled_bg,
                "#1F2937": _text,
                "#6B7280": _text_muted,
                "#0C1410": _window,
                "#121C17": _surface,
                "#1A2922": _surface_alt,
                "#2D4A3E": _border,
                "#15221C": _disabled_bg,
                "#ECFDF5": _text,
                "#A7F3D0": _text_muted,
                "#4D7C68": _text_muted,
                "#0A0A12": _window,
                "#141422": _surface,
                "#1D1D33": _surface_alt,
                "#34376A": _border,
                "#1A1A2B": _disabled_bg,
                "#1A1A2E": _surface_alt,
                "#0F172A": _window,
                "#1E293B": _surface,
                "#253347": _surface_alt,
                "#475569": _border,
                "#1F2A3D": _disabled_bg,
                "#334155": _surface_alt,
                "#E2E8F0": _text,
                "#94A3B8": _text_muted,
                "#64748B": _text_muted,
                "#111827": _text,
                "#172033": _text,
                "#1A0A14": _window,
                "#241018": _surface,
                "#2E1820": _surface_alt,
                "#5C2E3C": _border,
                "#200E18": _disabled_bg,
                "#FFE4D6": _text,
                "#D4A0A0": _text_muted,
                "#080C1A": _window,
                "#0F1428": _surface,
                "#161E38": _surface_alt,
                "#2A3660": _border,
                "#0F1328": _disabled_bg,
                "#E0E8FF": _text,
                "#8892CC": _text_muted,
            }

        for old, new in replacements.items():
            if is_vivid_color(new):
                continue
            txt = re.sub(re.escape(old), new, txt, flags=re.IGNORECASE)
        return txt

    @classmethod
    def transform_qss(cls, qss_text, current_palette, light_fallback, is_dark_theme, old_palette=None):
        if not qss_text:
            return qss_text
        # 1. Sanitize (remove cursor, outline etc.)
        out = cls.sanitize_qss(qss_text)
        
        # 2. Resolve all @tokens first. This is crucial so that subsequent logic 
        # sees actual colors instead of token strings.
        out = TOKEN_REF_RE.sub(
            lambda m: cls._resolve_palette_token(m.group(1), current_palette, light_fallback),
            out,
        )
        
        # 3. Harmonize literals (e.g. #FFFFFF -> theme neutral)
        out = cls.harmonize_literal_neutrals(out, current_palette, is_dark_theme)
        
        # 4. Smart remapping based on QSS context (selectors/props)
        out = cls.remap_qss_declarations(out, current_palette, light_fallback)
        
        # 5. Delta remapping if transitioning from old palette
        if old_palette:
            out = cls.remap_palette_literals(out, old_palette, current_palette)
            
        # Final pass of sanitization to catch any artifacts
        return cls.sanitize_qss(out)
