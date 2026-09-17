# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QEvent, QObject, QPropertyAnimation, QEasingCurve, QTimer, Qt
from PyQt6.QtGui import QColor, QPalette, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QLabel,
    QGraphicsOpacityEffect,
    QWidget,
    QAbstractButton,
    QLineEdit,
    QComboBox,
    QGroupBox,
    QTabWidget,
    QTextEdit,
    QTextBrowser,
    QPlainTextEdit,
    QTableWidget,
    QTableView,
    QListWidget,
    QTreeWidget,
    QTreeView,
    QMenu,
)
from src.utils.logger import logger


class _StyleChangeFilter(QObject):
    def eventFilter(self, obj, event):
        from src.utils.theme_manager import ThemeManager
        event_type = event.type()
        if (
            event_type in (QEvent.Type.Show, QEvent.Type.Polish)
            and isinstance(obj, (QTableView, QTreeView))
            and obj.selectionBehavior()
            != QAbstractItemView.SelectionBehavior.SelectRows
        ):
            obj.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows
            )
        if event_type == QEvent.Type.Show and isinstance(obj, QWidget):
            raw = getattr(obj, "_theme_raw_stylesheet", None)
            applied_generation = getattr(
                obj,
                "_theme_applied_generation",
                ThemeManager._theme_generation,
            )
            if (
                raw is not None
                and applied_generation != ThemeManager._theme_generation
            ):
                obj.setStyleSheet(raw)
        if getattr(ThemeManager, "_style_repair_in_progress", False):
            return False
        if (
            event_type in (QEvent.Type.Show, QEvent.Type.Polish)
            and not getattr(obj, "_theme_text_repair_done", False)
        ):
            ThemeManager._style_repair_in_progress = True
            try:
                if isinstance(obj, QWidget):
                    ThemeManager._repair_widget_texts(obj)
                    setattr(obj, "_theme_text_repair_done", True)
                obj.update()
            except Exception as e:
                logger.debug("Style repair filter failed: %s", e)
            finally:
                ThemeManager._style_repair_in_progress = False
        return False


class _ComboClickOpenFilter(QObject):
    @staticmethod
    def _find_parent_combo(widget):
        current = widget
        while current is not None:
            if isinstance(current, QComboBox):
                return current
            current = current.parent()
        return None

    def eventFilter(self, obj, event):
        from src.utils.theme_manager import ThemeManager
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        if getattr(event, "button", lambda: None)() != Qt.MouseButton.LeftButton:
            return False
        if not getattr(ThemeManager, "_combo_auto_popup_enabled", False):
            return False

        # combo_auto_popup ayarını kontrol et
        # Non-editable combos already open when clicked anywhere natively.
        # We only really need to handle editable combos or just let Qt do its thing.
        # However, to be safe and satisfy "click anywhere" aggressively:
        if isinstance(obj, QComboBox) and obj.isEnabled() and obj.isEditable():
            # Editable combobox: ayar kapalıysa doğal davranışa bırak
            try:
                # If it's already open, let native behavior close it
                if obj.view() and obj.view().isVisible():
                    return False
                obj.setFocus()
                QTimer.singleShot(0, obj.showPopup)
                return False
            except Exception as e:
                logger.debug("Combo popup open failed (combo): %s", e)
                return False

        # Editable combos: text-area click lands on inner QLineEdit.
        if isinstance(obj, QLineEdit) and obj.isEnabled():
            parent_combo = self._find_parent_combo(obj)
            if parent_combo and parent_combo.isEnabled():
                # Editable combobox: ayar kapalıysa doğal davranışa bırak
                if not parent_combo.isEditable():
                    return False
                try:
                    if parent_combo.view() and parent_combo.view().isVisible():
                        return False
                    parent_combo.setFocus()
                    QTimer.singleShot(0, parent_combo.showPopup)
                    return False
                except Exception as e:
                    logger.debug("Combo popup open failed (line edit): %s", e)
                    return False
        return False


