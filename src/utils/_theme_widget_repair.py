# -*- coding: utf-8 -*-
import re
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QLabel,
    QAbstractButton,
    QLineEdit,
    QComboBox,
    QGroupBox,
    QTabWidget,
    QTextEdit,
    QTextBrowser,
    QPlainTextEdit,
    QMenu,
)
from ._theme_constants import MOJIBAKE_HINT_RE
from src.utils.logger import logger


def _fix_mojibake_text(text):
    if not text or not isinstance(text, str):
        return text
    if not MOJIBAKE_HINT_RE.search(text):
        return text

    best = text
    best_score = len(MOJIBAKE_HINT_RE.findall(text))

    try:
        from ftfy import fix_text
        cand = fix_text(text)
        score = len(MOJIBAKE_HINT_RE.findall(cand))
        if score < best_score and cand.strip():
            best = cand
            best_score = score
    except Exception as e:
        logger.debug("ftfy fix_text failed: %s", e)

    for enc in ("cp1254", "cp1252", "latin-1"):
        try:
            # Repair only reversible encodings; never discard valid UI characters.
            cand = best.encode(enc).decode("utf-8")
        except Exception:
            continue
        score = len(MOJIBAKE_HINT_RE.findall(cand))
        if score < best_score and cand.strip():
            best = cand
            best_score = score
    return best


def repair_widget_texts(w):
    try:
        if isinstance(w, QLabel):
            t = w.text()
            ft = _fix_mojibake_text(t)
            if ft != t:
                w.setText(ft)
        elif isinstance(w, QAbstractButton):
            t = w.text()
            ft = _fix_mojibake_text(t)
            if ft != t:
                w.setText(ft)
        elif isinstance(w, QLineEdit):
            p = w.placeholderText()
            fp = _fix_mojibake_text(p)
            if fp != p:
                w.setPlaceholderText(fp)
        elif isinstance(w, QTextEdit):
            p = w.placeholderText()
            fp = _fix_mojibake_text(p)
            if fp != p:
                w.setPlaceholderText(fp)
        elif isinstance(w, QTextBrowser):
            ht = w.toHtml()
            fht = _fix_mojibake_text(ht)
            if fht != ht:
                w.setHtml(fht)
        elif isinstance(w, QPlainTextEdit):
            p = w.placeholderText()
            fp = _fix_mojibake_text(p)
            if fp != p:
                w.setPlaceholderText(fp)
        elif isinstance(w, QComboBox):
            p = w.placeholderText()
            fp = _fix_mojibake_text(p)
            if fp != p:
                w.setPlaceholderText(fp)
            for i in range(w.count()):
                txt = w.itemText(i)
                ftxt = _fix_mojibake_text(txt)
                if ftxt != txt:
                    w.setItemText(i, ftxt)
        elif isinstance(w, QGroupBox):
            t = w.title()
            ft = _fix_mojibake_text(t)
            if ft != t:
                w.setTitle(ft)
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                t = w.tabText(i)
                ft = _fix_mojibake_text(t)
                if ft != t:
                    w.setTabText(i, ft)
        elif isinstance(w, QMenu):
            t = w.title()
            ft = _fix_mojibake_text(t)
            if ft != t:
                w.setTitle(ft)

        if hasattr(w, "actions"):
            try:
                for act in w.actions():
                    if not isinstance(act, QAction):
                        continue
                    at = act.text()
                    fat = _fix_mojibake_text(at)
                    if fat != at:
                        act.setText(fat)
            except Exception as e:
                logger.debug("Action text repair failed: %s", e)
        t = w.windowTitle()
        ft = _fix_mojibake_text(t)
        if ft != t:
            w.setWindowTitle(ft)
    except Exception as e:
        logger.debug("Widget text repair failed: %s", e)

