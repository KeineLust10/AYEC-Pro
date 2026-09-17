# -*- coding: utf-8 -*-
"""Runtime guards for Turkish mojibake in UI text.

Some legacy source strings and stored records were decoded with the wrong
codepage. This module keeps visible Qt text readable while the remaining
source/data cleanup is done incrementally.
"""

from __future__ import annotations

from typing import Any


_DIRECT_REPLACEMENTS = {
    "Ç": "Ç",
    "ç": "ç",
    "Ü": "Ü",
    "ü": "ü",
    "Ö": "Ö",
    "ö": "ö",
    "İ": "İ",
    "ı": "ı",
    "\u00c5\u017e": "Ş",
    "\u00c5\u0178": "ş",
    "Ş": "Ş",
    "ş": "ş",
    "\u00c4\u017e": "Ğ",
    "\u00c4\u0178": "ğ",
    "Ğ": "Ğ",
    "ğ": "ğ",
    "İ": "İ",
    "ı": "ı",
    "\u00c5\u0178": "ş",
    "\u00c5\u017e": "Ş",
    "\u00c4\u0178": "ğ",
    "\u00c4\u017e": "Ğ",
    "ü": "ü",
    "Ü": "Ü",
    "ö": "ö",
    "Ö": "Ö",
    "ç": "ç",
    "Ç": "Ç",
    "–": "-",
    "—": "-",
    "—": "-",
    "–": "-",
    "…": "...",
    "'": "'",
    "'": "'",
    "\"": "\"",
    "\ufffd": '"',
    "•": "•",
    "→": "->",
    "←": "<-",
    "✓": "✓",
    "✔": "✓",
    "✏": "✏",
    "✕": "×",
    "➕": "+",
    "\u00e2\u0161\u00a1": "⚡",
    "✨": "✨",
    "⏳": "⏳",
    "⬆️": "↑",
    "⊞": "⊞",
    "️": "",
    "📢": "📢",
    "📊": "📊",
    "📄": "📄",
    "📂": "📂",
    "📎": "📎",
    "📅": "📅",
    "💾": "💾",
    "💡": "💡",
    "💬": "💬",
    "🔄": "🔄",
    "🔧": "🔧",
    "🔑": "🔑",
    "🗑": "🗑",
    "🗂": "🗂",
    "🚀": "🚀",
    "🛒": "🛒",
    "🎨": "🎨",
    "🎉": "🎉",
}

_QUESTION_MARK_REPLACEMENTS = {
    "Satış": "Satış",
    "satış": "satış",
    "Şablon": "Şablon",
    "?ifre": "Şifre",
    "?irket": "Şirket",
    "?deme": "Ödeme",
    "?ncelik": "Öncelik",
    "?cerik": "İçerik",
    "?ptal": "İptal",
    "?slem": "İşlem",
    "Ürün": "Ürün",
    "?rün": "Ürün",
    "yüklen": "yüklen",
    "göster": "göster",
    "se?": "seç",
}


def _decode_once(value: str, encoding: str) -> str:
    try:
        return value.encode(encoding, errors="strict").decode("utf-8", errors="strict")
    except Exception:
        return value


def fix_mojibake(value: Any) -> Any:
    """Return a readable Turkish string when common mojibake is detected."""
    if not isinstance(value, str) or not value:
        return value

    text = value
    for _ in range(3):
        before = text
        for bad, good in _DIRECT_REPLACEMENTS.items():
            text = text.replace(bad, good)
        # These repair common UTF-8 bytes read as Windows/Latin code pages.
        text = _decode_once(text, "cp1252")
        text = _decode_once(text, "latin1")
        for bad, good in _DIRECT_REPLACEMENTS.items():
            text = text.replace(bad, good)
        if text == before:
            break

    for bad, good in _QUESTION_MARK_REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text


def install_qt_text_sanitizer() -> bool:
    """Patch common Qt text setters so visible strings are sanitized once."""
    try:
        from PyQt6.QtGui import QAction
        from PyQt6.QtWidgets import (
            QComboBox,
            QGroupBox,
            QLabel,
            QLineEdit,
            QMenu,
            QPlainTextEdit,
            QPushButton,
            QTabWidget,
            QTableWidget,
            QTextEdit,
            QWidget,
        )
    except Exception:
        return False

    if getattr(QWidget, "_ayec_mojibake_sanitizer_installed", False):
        return False

    def patch_method(cls: Any, name: str, text_arg_index: int = 0) -> None:
        original = getattr(cls, name, None)
        if original is None or getattr(original, "_ayec_patched", False):
            return

        def wrapper(self, *args, **kwargs):
            args = list(args)
            if len(args) > text_arg_index:
                args[text_arg_index] = fix_mojibake(args[text_arg_index])
            return original(self, *args, **kwargs)

        wrapper._ayec_patched = True
        setattr(cls, name, wrapper)

    for cls in (QLabel, QPushButton, QGroupBox, QAction, QWidget):
        patch_method(cls, "setText" if cls is not QWidget else "setWindowTitle")
    for cls in (QLabel, QPushButton, QGroupBox, QLineEdit, QTextEdit, QPlainTextEdit, QWidget):
        patch_method(cls, "setToolTip")
    for cls in (QLineEdit, QTextEdit, QPlainTextEdit):
        patch_method(cls, "setPlaceholderText")

    original_add_item = QComboBox.addItem
    if not getattr(original_add_item, "_ayec_patched", False):

        def add_item(self, *args, **kwargs):
            args = list(args)
            if args:
                if isinstance(args[0], str):
                    args[0] = fix_mojibake(args[0])
                elif len(args) > 1 and isinstance(args[1], str):
                    args[1] = fix_mojibake(args[1])
            return original_add_item(self, *args, **kwargs)

        add_item._ayec_patched = True
        QComboBox.addItem = add_item

    original_add_items = QComboBox.addItems
    if not getattr(original_add_items, "_ayec_patched", False):

        def add_items(self, texts):
            return original_add_items(self, [fix_mojibake(text) for text in texts])

        add_items._ayec_patched = True
        QComboBox.addItems = add_items

    original_set_item_text = QComboBox.setItemText
    if not getattr(original_set_item_text, "_ayec_patched", False):

        def set_item_text(self, index, text):
            return original_set_item_text(self, index, fix_mojibake(text))

        set_item_text._ayec_patched = True
        QComboBox.setItemText = set_item_text

    original_add_tab = QTabWidget.addTab
    if not getattr(original_add_tab, "_ayec_patched", False):

        def add_tab(self, *args, **kwargs):
            args = list(args)
            if args and isinstance(args[-1], str):
                args[-1] = fix_mojibake(args[-1])
            return original_add_tab(self, *args, **kwargs)

        add_tab._ayec_patched = True
        QTabWidget.addTab = add_tab

    original_set_tab_text = QTabWidget.setTabText
    if not getattr(original_set_tab_text, "_ayec_patched", False):

        def set_tab_text(self, index, text):
            return original_set_tab_text(self, index, fix_mojibake(text))

        set_tab_text._ayec_patched = True
        QTabWidget.setTabText = set_tab_text

    original_headers = QTableWidget.setHorizontalHeaderLabels
    if not getattr(original_headers, "_ayec_patched", False):

        def set_headers(self, labels):
            return original_headers(self, [fix_mojibake(label) for label in labels])

        set_headers._ayec_patched = True
        QTableWidget.setHorizontalHeaderLabels = set_headers

    original_set_item = QTableWidget.setItem
    if not getattr(original_set_item, "_ayec_patched", False):

        def set_item(self, row, column, item):
            try:
                item.setText(fix_mojibake(item.text()))
                item.setToolTip(fix_mojibake(item.toolTip()))
            except Exception:
                pass
            return original_set_item(self, row, column, item)

        set_item._ayec_patched = True
        QTableWidget.setItem = set_item

    original_menu_add_action = QMenu.addAction
    if not getattr(original_menu_add_action, "_ayec_patched", False):

        def menu_add_action(self, *args, **kwargs):
            args = list(args)
            if args:
                if isinstance(args[0], str):
                    args[0] = fix_mojibake(args[0])
                elif len(args) > 1 and isinstance(args[1], str):
                    args[1] = fix_mojibake(args[1])
            return original_menu_add_action(self, *args, **kwargs)

        menu_add_action._ayec_patched = True
        QMenu.addAction = menu_add_action

    QWidget._ayec_mojibake_sanitizer_installed = True
    return True
