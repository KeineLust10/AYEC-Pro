# -*- coding: utf-8 -*-

"""
Wizard Page 1: Device visuals and accessories.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QPushButton,
    QFrame,
    QGroupBox,
    QDialog,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath

from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.pattern_lock import PatternLockWidget
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from src.utils.design_system import DesignTokens
from src.utils.system_config import SystemConfig
from src.utils.automotive_defaults import AUTOMOTIVE_ACCESSORY_CATEGORY, AUTOMOTIVE_PRESET
from src.utils.technical_service_profiles import (
    build_profile_category,
    get_profile_labels,
    normalize_technical_service_profile,
)

import os


class TechnicianWizardPage1(QWidget):
    """Page 1: Device visuals and delivered accessories."""

    def __init__(self, db, tracking_no, device_dict, parent=None, sector_manager=None):
        super().__init__(parent)
        self.db = db
        self.sector_manager = sector_manager
        self.tracking_no = tracking_no
        self.device_dict = device_dict
        self.accessory_toggles = {}
        self.pattern_str = device_dict.get("pattern_lock", "")
        self.photo_path_str = device_dict.get("photo_path", "")
        self.accessories_str = device_dict.get("accessories", "")
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 2)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        content_h = QHBoxLayout()
        content_h.setContentsMargins(0, 0, 0, 0)
        content_h.setSpacing(12)
        content_h.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.accessories_group = self.create_accessories_section()
        self.accessories_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        content_h.addWidget(self.accessories_group, 38)

        self.pattern_group = None
        if not self._is_automotive():
            self.pattern_button = QPushButton("Desen Kilidi")
            self.pattern_button.setFixedHeight(30)
            self.pattern_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.pattern_button.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("secondary", size="sm"))
            )
            self.pattern_button.clicked.connect(self.open_pattern_lock_dialog)
            pattern_action = QHBoxLayout()
            pattern_action.setContentsMargins(0, 0, 0, 0)
            pattern_action.addWidget(self.pattern_button)
            pattern_action.addStretch()
            main_layout.addLayout(pattern_action)

        self.photo_group = self.create_photo_section()
        self.photo_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        content_h.addWidget(self.photo_group, 48 if self._is_automotive() else 32)

        main_layout.addLayout(content_h)

    def _is_automotive(self):
        try:
            parent_dialog = self.parent()
            if parent_dialog and hasattr(parent_dialog, "_is_automotive"):
                return bool(parent_dialog._is_automotive())
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _technical_service_profile(self):
        parent_dialog = self.parent()
        if parent_dialog and hasattr(parent_dialog, "get_technical_service_profile"):
            return parent_dialog.get_technical_service_profile()
        return normalize_technical_service_profile(self.device_dict.get("device_type"))

    def _accessory_category(self):
        if self._is_automotive():
            return AUTOMOTIVE_ACCESSORY_CATEGORY
        return build_profile_category(self._technical_service_profile(), "Aksesuar")

    def _accessory_group_title(self):
        if self._is_automotive():
            return "Ara\u00e7 Kabul / Teslim Ekipman\u0131"
        return f"{self._technical_service_profile()} Yan\u0131nda Gelenler"

    def _is_classic_appearance(self):
        parent_dialog = self.parent()
        return bool(
            parent_dialog
            and hasattr(parent_dialog, "_is_classic_appearance")
            and parent_dialog._is_classic_appearance()
        )

    def _classic_group_qss(self):
        return """
            QGroupBox {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                margin-top: 12px;
                padding: 18px 8px 8px 8px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 4px;
                background: #FFFFFF;
                color: #111827;
            }
            QGroupBox QWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QGroupBox QLabel {
                background: transparent;
                color: #111827;
                border: none;
            }
        """

    def _group_qss(self):
        if self._is_classic_appearance():
            return self._classic_group_qss()
        return theme_qss(
            f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid {DesignTokens.BORDER};
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: {DesignTokens.FOREGROUND};
            }}
            """
        )

    def create_accessories_section(self):
        category = self._accessory_category()
        group = QGroupBox("Bilgisayar Yan\u0131nda Gelen Aksesuarlar")
        if self._is_automotive():
            group.setTitle("Ara\u00e7 Kabul / Teslim Ekipman\u0131")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 11, QFont.Weight.Bold))
        group.setStyleSheet(self._group_qss())

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(2)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        saved_accs = [
            s.strip().upper()
            for s in (self.accessories_str or "").split(",")
            if s.strip()
        ]

        try:
            acc_list = self.db.get_fast_notes(category) or []
            if not acc_list:
                acc_list_old = self.db.get_quick_notes("accessories_notes") or []
                acc_list = []
                for item in acc_list_old:
                    is_active = False
                    try:
                        if int(item[3]) == 1:
                            is_active = True
                    except Exception:
                        pass
                    if not is_active and len(item) > 4:
                        try:
                            is_active = int(item[4]) == 1
                        except Exception:
                            is_active = False
                    if is_active:
                        acc_list.append((0, category, item[2], 1, 0))
            active_acc = []
            for item in acc_list:
                try:
                    if isinstance(item, dict):
                        is_active = int(item.get("is_active", 1)) == 1
                        label = str(item.get("label", "")).strip()
                    elif hasattr(item, "keys"):
                        is_active = int(item["is_active"]) == 1 if "is_active" in item.keys() else True
                        label = str(item["label"]).strip() if "label" in item.keys() else str(item[2]).strip()
                    else:
                        is_active = int(item[3]) == 1
                        label = str(item[2]).strip()
                except Exception:
                    is_active = False
                    label = ""
                if is_active and label:
                    active_acc.append((0, category, label, 1, 0))
        except Exception as e:
            logger.error("TechnicianWizardPage1 accessories load error: %s", e)
            active_acc = []

        if not active_acc:
            active_acc = [
                (0, "Aksesuar", name, 1, 0)
                for name in ["G\u00fc\u00e7 Adapt\u00f6r\u00fc", "\u015earj Kablosu", "HDMI / G\u00f6r\u00fcnt\u00fc Kablosu", "Mouse", "Klavye", "Ta\u015f\u0131ma \u00c7antas\u0131"]
            ]

        if self._is_automotive():
            active_acc = [(0, category, name, 1, 0) for name in AUTOMOTIVE_PRESET[AUTOMOTIVE_ACCESSORY_CATEGORY]]

        row = 0
        col = 0
        for item in active_acc:
            name = str(item[2]).strip()
            if not name:
                continue
            toggle_widget = self.create_toggle_item(name, name.upper() in saved_accs)
            grid.addWidget(toggle_widget, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        layout.addLayout(grid)
        return group

    def reload_accessories(self):
        if not hasattr(self, "accessories_group"):
            return
        layout = self.accessories_group.layout()
        if layout is None:
            return

        self.accessories_group.setTitle(self._accessory_group_title())
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

        self.accessory_toggles = {}
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        saved_accs = [s.strip().upper() for s in (self.accessories_str or "").split(",") if s.strip()]
        labels = (
            list(AUTOMOTIVE_PRESET[AUTOMOTIVE_ACCESSORY_CATEGORY])
            if self._is_automotive()
            else list(get_profile_labels(self._technical_service_profile(), "Aksesuar"))
        )

        row = 0
        col = 0
        for label in labels:
            toggle_widget = self.create_toggle_item(label, label.upper() in saved_accs)
            grid.addWidget(toggle_widget, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        layout.addLayout(grid)

    def create_toggle_item(self, text, checked=False):
        container = QWidget()
        container.setObjectName("ClassicAccessoryToggleItem")
        container.setFixedHeight(34)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if self._is_classic_appearance():
            container.setStyleSheet("""
                QWidget#ClassicAccessoryToggleItem {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #D1D5DB;
                    border-radius: 0px;
                }
                QWidget#ClassicAccessoryToggleItem QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
            """)
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(6, 3, 6, 3)
        h_layout.setSpacing(6)

        toggle = AnimatedToggle()
        toggle.setFixedSize(46, 24)
        toggle.setChecked(checked)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setAccessibleName(f"aksesuar_toggle_{text.lower().replace(' ', '_')}")

        label = QLabel(text)
        label.setFont(QFont(DesignTokens.FONT_FAMILY, 10))
        label.setStyleSheet(
            "color: #111827; background: transparent; border: none;"
            if self._is_classic_appearance()
            else theme_qss(
                f"color: {DesignTokens.FOREGROUND}; background: transparent; border: none;"
            )
        )
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        label.mousePressEvent = lambda event, t=toggle: t.toggle()
        label.setAccessibleName(f"aksesuar_etiket_{text.lower().replace(' ', '_')}")

        h_layout.addWidget(toggle)
        h_layout.addWidget(label)
        h_layout.addStretch()

        self.accessory_toggles[text] = toggle
        return container

    def create_pattern_lock_section(self):
        group = QGroupBox("G\u00fcvenlik Deseni")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 11, QFont.Weight.Bold))
        group.setStyleSheet(self._group_qss())

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(2)

        pattern_widget = PatternLockWidget()
        if self.pattern_str:
            pattern_widget.set_pattern(self.pattern_str)
        pattern_widget.setReadOnly(True)
        self.pattern_widget = pattern_widget
        layout.addWidget(pattern_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        return group

    def open_pattern_lock_dialog(self):
        dialog = ModernDialog("Desen Kilidi", self, width=360, height=430)
        dialog.set_footer_visible(False)
        layout = dialog.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        title = QLabel("Desen Kilidi")
        title.setStyleSheet(theme_qss("font-size: 16px; font-weight: 800; color: @text;"))
        layout.addWidget(title)

        pattern_widget = PatternLockWidget()
        if self.pattern_str:
            pattern_widget.set_pattern(self.pattern_str)
        pattern_widget.setReadOnly(True)
        layout.addWidget(pattern_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        close_button = QPushButton("Kapat")
        close_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def create_photo_section(self):
        group = QGroupBox("Cihaz G\u00f6rselleri")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 11, QFont.Weight.Bold))
        group.setStyleSheet(self._group_qss())

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        self.photos_grid = QGridLayout()
        self.photos_grid.setContentsMargins(0, 0, 0, 0)
        self.photos_grid.setHorizontalSpacing(6)
        self.photos_grid.setVerticalSpacing(6)
        self._rebuild_gallery_grid()
        layout.addLayout(self.photos_grid)

        btn_gallery = QPushButton("Galeriyi A\u00e7")
        btn_gallery.setMinimumWidth(240)
        btn_gallery.setFixedHeight(36)
        btn_gallery.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.DemiBold))
        btn_gallery.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        btn_gallery.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gallery.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_gallery.clicked.connect(self.open_gallery)
        layout.addWidget(btn_gallery)
        return group

    def _rebuild_gallery_grid(self):
        if not hasattr(self, "photos_grid"):
            return
        while self.photos_grid.count():
            child = self.photos_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        photo_paths = self._get_photo_paths()
        thumb_size = 50
        for index in range(6):
            thumb = self._create_gallery_thumb(
                photo_paths[index] if index < len(photo_paths) else "",
                thumb_size,
            )
            self.photos_grid.addWidget(thumb, index // 3, index % 3)

    def _get_photo_paths(self):
        paths = []
        if self.tracking_no and hasattr(self.db, "get_photos"):
            try:
                for row in (self.db.get_photos(self.tracking_no) or []):
                    path = str((row[1] if len(row) > 1 else "") or "").strip()
                    if path and path not in paths and os.path.exists(path):
                        paths.append(path)
            except Exception:
                pass
        raw_paths = self.device_dict.get("photo_paths", "") or ""
        if raw_paths:
            for path in [p.strip() for p in str(raw_paths).split(",") if p.strip()]:
                if path and path not in paths:
                    paths.append(path)
        if self.photo_path_str:
            single = str(self.photo_path_str).strip()
            if single and single not in paths:
                paths.insert(0, single)
        return [path for path in paths if os.path.exists(path)][:6]

    def _create_gallery_thumb(self, path, size):
        frame = QFrame()
        frame.setFixedSize(size, size)
        if self._is_classic_appearance():
            frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #B8C0CC; border-radius: 0px; }")
        else:
            frame.setStyleSheet(
                theme_qss(
                    """
                    QFrame {
                        background: @surface_alt;
                        border: 1px solid @border;
                        border-radius: 10px;
                    }
                    """
                )
            )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if path and os.path.exists(path):
            pixmap = QPixmap(path).scaled(
                size - 4,
                size - 4,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            rounded = QPixmap(size - 4, size - 4)
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            clip = QPainterPath()
            clip.addRoundedRect(0, 0, size - 4, size - 4, 8, 8)
            painter.setClipPath(clip)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            label.setPixmap(rounded)
        else:
            label.setText("\U0001f5bc")
            label.setStyleSheet(
                theme_qss(
                    "color: @text_muted; font-size: 18px; border: none; background: transparent;"
                )
            )
        layout.addWidget(label)
        return frame

    def apply_classic_styles(self):
        if not self._is_classic_appearance():
            return
        self.setProperty("skipThemeTransform", False)
        self.setStyleSheet("QWidget { background: #F3F4F6; color: #111827; } QLabel { background: transparent; color: #111827; border: none; }")
        for group in self.findChildren(QGroupBox):
            group.setProperty("skipThemeTransform", False)
            group.setStyleSheet(self._classic_group_qss())
        for item in self.findChildren(QWidget, "ClassicAccessoryToggleItem"):
            item.setProperty("skipThemeTransform", False)
            item.setStyleSheet("""
                QWidget#ClassicAccessoryToggleItem {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #D1D5DB;
                    border-radius: 0px;
                }
                QWidget#ClassicAccessoryToggleItem QLabel {
                    background: transparent;
                    color: #111827;
                    border: none;
                }
            """)
        for label in self.findChildren(QLabel):
            label.setProperty("skipThemeTransform", False)
            label.setStyleSheet("color: #111827; background: transparent; border: none;")
        for frame in self.findChildren(QFrame):
            frame.setProperty("skipThemeTransform", False)
            frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #B8C0CC; border-radius: 0px; }")
        for button in self.findChildren(QPushButton):
            button.setProperty("skipThemeTransform", False)
            button.setStyleSheet("""
                QPushButton {
                    background: #2F7DEB;
                    color: #FFFFFF;
                    border: 1px solid #1D5FB8;
                    border-radius: 2px;
                    padding: 5px 10px;
                    font-weight: 700;
                }
                QPushButton:hover { background: #2469C9; }
            """)
        if hasattr(self, "pattern_widget"):
            self.pattern_widget.update()

    def open_gallery(self):
        try:
            from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog

            dlg = PhotoGalleryDialog(self.db, self.tracking_no, self)
            dlg.exec()
            try:
                merged_paths = []
                if hasattr(self.db, "get_photos"):
                    for photo_row in (self.db.get_photos(self.tracking_no) or []):
                        photo_path = str((photo_row[1] if len(photo_row) > 1 else "") or "").strip()
                        if photo_path and os.path.exists(photo_path) and photo_path not in merged_paths:
                            merged_paths.append(photo_path)
                self.db.cursor.execute(
                    "SELECT photo_path, photo_paths FROM devices WHERE tracking_no=?",
                    (self.tracking_no,),
                )
                row = self.db.cursor.fetchone()
                if row:
                    self.photo_path_str = row[0] or ""
                    self.device_dict["photo_path"] = row[0] or ""
                    for legacy_path in [p.strip() for p in str(row[1] or "").split(",") if p.strip()]:
                        if legacy_path and os.path.exists(legacy_path) and legacy_path not in merged_paths:
                            merged_paths.append(legacy_path)
                if merged_paths:
                    self.device_dict["photo_paths"] = ",".join(merged_paths)
                    if not self.photo_path_str:
                        self.photo_path_str = merged_paths[0]
                        self.device_dict["photo_path"] = merged_paths[0]
                self._rebuild_gallery_grid()
            except Exception:
                pass
        except Exception as e:
            from src.utils.toast_notification import show_error

            show_error(self, f"Galeri a\u00e7\u0131lamad\u0131: {e}")

    def get_data(self):
        accessories = []
        for name, toggle in self.accessory_toggles.items():
            if toggle.isChecked():
                accessories.append(name)

        return {
            "accessories": ",".join(accessories),
            "pattern_lock": self.pattern_str,
            "photo_path": self.photo_path_str,
        }
