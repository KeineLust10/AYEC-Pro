# -*- coding: utf-8 -*-

import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.utils.toast_notification import show_error, show_info, show_warning
from src.utils.logger import logger
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import ToastManager


class NewServiceDialogMediaMixin:
    def _apply_reference_dark_skin(self):
        """Apply the service-accept reference palette only inside this dialog."""
        token_map = {
            "@finance_surface_high": "#182238",
            "@finance_surface_alt": "#131b2c",
            "@finance_surface": "#0e1320",
            "@finance_canvas": "#06090e",
            "@finance_outline": "#222f4c",
            "@finance_text_muted": "#94a3b8",
            "@finance_text": "#e2e8f0",
            "@finance_primary_text": "#ffffff",
            "@finance_primary": "#2563eb",
            "@finance_secondary": "#10b981",
            "@finance_tertiary": "#f472b6",
            "@finance_success_bg": "#052e2b",
            "@finance_warning_bg": "#4c1d32",
            "@finance_active_bg": "#1e3a5f",
            "@surface_high": "#182238",
            "@surface_alt": "#131b2c",
            "@surface": "#0e1320",
            "@window": "#06090e",
            "@text_muted": "#94a3b8",
            "@text": "#e2e8f0",
            "@border": "#222f4c",
            "@selection_bg": "#1d4ed8",
            "@selection_text": "#ffffff",
            "@accent_soft": "#1e293b",
            "@accent_hover": "#1d4ed8",
            "@accent_pressed": "#1e40af",
            "@accent": "#3b82f6",
            "@success": "#10b981",
            "@warning_bg": "#4c1d32",
            "@warning": "#f59e0b",
            "@danger": "#fb7185",
            "@disabled_bg": "#182238",
            "@disabled_text": "#64748b",
            "@primary": "#3b82f6",
        }
        color_map = (
            ("#EEF3F9", "#06090e"),
            ("#F4F6FB", "#06090e"),
            ("#F7F8FC", "#0a0e17"),
            ("#E3EBF5", "#131b2c"),
            ("#F8F9FD", "#131b2c"),
            ("#D4E0EE", "#182238"),
            ("#EEF2F7", "#182238"),
            ("#DCE6F1", "#182238"),
            ("#C6D3E2", "#222f4c"),
            ("#D8E0EB", "#222f4c"),
            ("#E5EAF2", "#222f4c"),
            ("#607189", "#94a3b8"),
            ("#172033", "#e2e8f0"),
            ("#1F2937", "#e2e8f0"),
            ("#111827", "#e2e8f0"),
            ("#0F172A", "#cbd5e1"),
            ("#DCE8FB", "#1e293b"),
            ("#CFE0FB", "#1d4ed8"),
            ("#D7F6E7", "#052e2b"),
            ("#FCE1E7", "#4c1d32"),
            ("#F3F4F8", "#131b2c"),
            ("#ECEFF5", "#182238"),
            ("#F8FAFC", "#131b2c"),
            ("#E1E6F0", "#222f4c"),
            ("#D6DDE9", "#182238"),
            ("#9AA4B2", "#64748b"),
        )
        widgets = [self, *self.findChildren(QWidget)]
        for widget in widgets:
            stylesheet = widget.styleSheet()
            if not stylesheet:
                continue
            if isinstance(widget, (QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton)):
                widget_font = widget.font()
                widget_font.setFamily("Segoe UI")
                widget.setFont(widget_font)
            updated = stylesheet
            for token in sorted(token_map, key=len, reverse=True):
                updated = updated.replace(token, token_map[token])
            for light, dark in color_map:
                updated = updated.replace(light, dark).replace(light.lower(), dark.lower())
            if isinstance(widget, QLineEdit):
                updated += "QLineEdit{background:rgb(248,250,252);color:rgb(51,65,85);}"
            elif isinstance(widget, QTextEdit):
                updated += "QTextEdit{background:rgb(248,250,252);color:rgb(51,65,85);}"
            elif isinstance(widget, QComboBox):
                updated += (
                    "QComboBox{background:rgb(248,250,252);color:rgb(51,65,85);"
                    "selection-background-color:rgb(37,99,235);selection-color:rgb(248,251,255);}"
                )
            if updated != stylesheet:
                widget.setProperty("skipThemeTransform", True)
                widget.setStyleSheet(updated)

    def _apply_dialog_contrast_guard(self):
        self.setStyleSheet(
            theme_qss(
                "QLabel{color:@text;} "
                "QLineEdit,QTextEdit,QComboBox,QAbstractSpinBox{color:@text;background:@surface;border:1px solid @border;} "
                "QComboBox QAbstractItemView{color:@text;background:@surface;selection-background-color:@selection_bg;selection-color:@selection_text;}"
            )
        )

    def _photos_table_exists(self):
        try:
            self.db.cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='photos' LIMIT 1")
            return self.db.cursor.fetchone() is not None
        except Exception:
            return False
    
    def _refresh_photo_table(self):
        """Fotoğraf sayısı butonunu güncelle."""
        count = len(self.photo_paths)
        if hasattr(self, "btn_photo_count"):
            if count > 0:
                self.btn_photo_count.setText(f"{count} Dosya Seçildi (Görmek İçin Tıkla)")
                self.btn_photo_count.setVisible(True)
            else:
                self.btn_photo_count.setVisible(False)
        self._update_reference_photo_preview()

    def _update_reference_photo_preview(self):
        layout = getattr(self, "reference_photo_preview_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not self.photo_paths:
            empty_slot = QPushButton("\u25a7\n\u00d6n Kasa")
            empty_slot.setAccessibleName("\u00d6n Kasa foto\u011fraf\u0131 ekle")
            empty_slot.setFixedSize(70, 70)
            empty_slot.setStyleSheet(theme_qss(
                "QPushButton { background: @surface; color: @text_muted; border: 1px solid @border; "
                "border-radius: 8px; font-size: 10px; } QPushButton:hover { border-color: @accent; }"
            ))
            empty_slot.clicked.connect(self.upload_photo)
            layout.addWidget(empty_slot)
        for index, path in enumerate(self.photo_paths[:5]):
            tile = QFrame()
            tile.setFixedSize(60, 60)
            tile.setStyleSheet(theme_qss(
                "QFrame { background: @surface; border: 1px solid @border; border-radius: 7px; }"
            ))
            tile_layout = QGridLayout(tile)
            tile_layout.setContentsMargins(2, 2, 2, 2)
            preview = QLabel()
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                preview.setPixmap(pixmap.scaled(
                    54, 54, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            else:
                preview.setText("IMG")
                preview.setStyleSheet(theme_qss("color: @text_muted; border: none; background: transparent;"))
            tile_layout.addWidget(preview, 0, 0)
            remove_button = QPushButton("x")
            remove_button.setFixedSize(16, 16)
            remove_button.setStyleSheet(
                "QPushButton { background: #0b1220; color: #fb7185; border: 1px solid #334155; "
                "border-radius: 8px; padding: 0; font-size: 9px; font-weight: 700; }"
            )
            remove_button.clicked.connect(lambda _checked=False, i=index: self._remove_photo(i))
            tile_layout.addWidget(remove_button, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            layout.addWidget(tile)
        if len(self.photo_paths) < 5:
            add_button = QPushButton("+\nEkle")
            add_button.setFixedSize(70, 70)
            add_button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface; color: @text_muted; border: 1px dashed @border; "
                "border-radius: 7px; font-size: 10px; } QPushButton:hover { border-color: @accent; color: @text; }"
            ))
            add_button.clicked.connect(self.upload_photo)
            layout.addWidget(add_button)
        if not self.photo_paths:
            hint = QLabel(
                "Teslim an\u0131nda cihaz\u0131n fiziksel kusurlar\u0131n\u0131 belgelemek "
                "m\u00fc\u015fteri ihtilaflar\u0131n\u0131 \u00f6nler."
            )
            hint.setWordWrap(True)
            hint.setStyleSheet(theme_qss(
                "color: @text_muted; font-size: 11px; font-style: italic; border: none; background: transparent;"
            ))
            layout.addWidget(hint, 1)
        layout.addStretch(1)
    
    def _create_photo_item_widget(self, idx, path):
        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border-radius: 12px;
            }
        """))
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setMinimumSize(44, 44)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @text;
                color: @surface_alt;
                border: 1px solid @text;
                border-radius: 10px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: @text; }
        """))
        btn_close.clicked.connect(lambda _=False, i=idx: self._remove_photo(i))
        top_row.addWidget(btn_close)
        v.addLayout(top_row)

        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img.setFixedSize(220, 140)
        if os.path.exists(path):
            pix = QPixmap(path).scaled(220, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img.setPixmap(pix)
        img.setCursor(Qt.CursorShape.PointingHandCursor)
        img.mousePressEvent = lambda _e, p=path: self._open_photo_preview(p)
        v.addWidget(img)

        label_text = self.photo_labels[idx] if idx < len(self.photo_labels) else ""
        inp_label = QLineEdit(label_text)
        inp_label.setPlaceholderText("Etiket (örn: Ekran Kırığı)")
        inp_label.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        inp_label.editingFinished.connect(lambda i=idx, inp=inp_label: self._update_photo_label(i, inp.text()))
        v.addWidget(inp_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setMinimumHeight(44)
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_cancel.clicked.connect(self._cancel_photo_changes)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("Tamam")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setMinimumHeight(44)
        btn_ok.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_ok.clicked.connect(self._confirm_photo_changes)
        btn_row.addWidget(btn_ok)
        v.addLayout(btn_row)
        return card
    
    def _open_photo_gallery(self):
        """Seçilen fotoğrafları galeri dialog'unda göster."""
        if not self.photo_paths:
            return
        from PyQt6.QtWidgets import QScrollArea, QGridLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Seçilen Fotoğraflar ({len(self.photo_paths)})")
        dlg.setMinimumSize(600, 400)
        dlg.setStyleSheet(theme_qss("QDialog { background: @surface; }"))
        main_lay = QVBoxLayout(dlg)
        main_lay.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)

        for i, path in enumerate(self.photo_paths):
            card = QFrame()
            card.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 8px; }"))
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 8, 8, 8)
            cl.setSpacing(4)
            img = QLabel()
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img.setFixedSize(160, 120)
            if os.path.exists(path):
                pix = QPixmap(path).scaled(160, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img.setPixmap(pix)
            img.setCursor(Qt.CursorShape.PointingHandCursor)
            img.mousePressEvent = lambda _e, p=path: self._open_photo_preview(p)
            cl.addWidget(img)
            lbl_text = self.photo_labels[i] if i < len(self.photo_labels) and self.photo_labels[i] else os.path.basename(path)
            lbl = QLabel(lbl_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
            lbl.setWordWrap(True)
            cl.addWidget(lbl)
            # Sil butonu
            btn_del = QPushButton("Kaldır")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(theme_qss("QPushButton { background: transparent; color: @text_muted; border: none; font-size: 11px; } QPushButton:hover { color: #EF4444; }"))
            btn_del.clicked.connect(lambda _=False, idx=i, d=dlg: (self._remove_photo(idx), d.close(), self._open_photo_gallery()))
            cl.addWidget(btn_del)
            grid.addWidget(card, i // 3, i % 3)

        scroll.setWidget(container)
        main_lay.addWidget(scroll)
        btn_close = QPushButton("Kapat")
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_close.clicked.connect(dlg.close)
        main_lay.addWidget(btn_close)
        dlg.exec()

    def _open_photo_preview(self, path):
        if not os.path.exists(path):
            ToastManager.warning(self, "Görsel bulunamadı.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Fotoğraf Önizleme")
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            width = min(int(geo.width() * 0.9), 1400)
            height = min(int(geo.height() * 0.85), 950)
        else:
            width, height = 1200, 900
        dlg.setFixedSize(width, height)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        target_w = max(width - 32, 200)
        target_h = max(height - 32, 200)
        pix = QPixmap(path).scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(pix)
        layout.addWidget(lbl, 1)
        dlg.exec()

    def _update_photo_button(self):
        count = len(self.photo_paths)
        if not self.is_automotive:
            summary = (
                f"{count} g\u00f6rsel se\u00e7ildi\nEklemek veya kald\u0131rmak i\u00e7in a\u015fa\u011f\u0131daki \u00f6nizlemeleri kullan\u0131n"
                if count
                else "Hen\u00fcz g\u00f6rsel se\u00e7ilmedi \u00b7 PNG, JPG"
            )
            title = "Foto\u011fraf Y\u00fcklemek \u0130\u00e7in T\u0131klay\u0131n veya S\u00fcr\u00fckleyin"
            self.btn_photo.setText(title + "\n" + summary)
            self.btn_photo.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface; color: @text; border: 1px dashed @finance_outline; border-radius: 6px; font-size: 11px; padding: 8px; }"
                "QPushButton:hover { background: @finance_surface_alt; border-color: @finance_primary; }"))
            return
        label = "Dosya" if count == 1 else "Dosya"
        if count:
            self.btn_photo.setText(f"📸 {count} {label} Seçildi (Görmek için Tıkla)")
            self.btn_photo.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @surface_alt; border: 2px solid @success; border-radius: 8px;
                    color: @success; font-weight: bold; font-size: 13px;
                }
            """))
        else:
            self.btn_photo.setText("📷 Fotoğraf Yükle")
            self.btn_photo.setStyleSheet(theme_qss("""
                QPushButton {
                    background: @surface; border: 1px solid @border; border-radius: 8px; font-weight: 600; color: @text;
                }
                QPushButton:hover { background: @surface_alt; }
            """))

    def _snapshot_photo_state(self):
        self.photo_snapshot_paths = list(self.photo_paths)
        self.photo_snapshot_labels = list(self.photo_labels)

    def _update_photo_label(self, idx, text):
        while len(self.photo_labels) < len(self.photo_paths):
            self.photo_labels.append("")
        if 0 <= idx < len(self.photo_labels):
            self.photo_labels[idx] = text

    def _remove_photo(self, idx):
        if idx < 0 or idx >= len(self.photo_paths):
            return
        self.photo_paths.pop(idx)
        if idx < len(self.photo_labels):
            self.photo_labels.pop(idx)
        self.photo_path = self.photo_paths[0] if self.photo_paths else ""
        self._refresh_photo_table()
        self._update_photo_button()

    def _cancel_photo_changes(self):
        self.photo_paths = list(self.photo_snapshot_paths)
        self.photo_labels = list(self.photo_snapshot_labels)
        self.photo_path = self.photo_paths[0] if self.photo_paths else ""
        self._refresh_photo_table()
        self._update_photo_button()
        ToastManager.info(self, "Değişiklikler geri alındı.")

    def _confirm_photo_changes(self):
        self._snapshot_photo_state()
        self._update_photo_button()
        ToastManager.success(self, "Değişiklikler kaydedildi.")

    def _sync_photos_table(self, tracking_no):
        if not tracking_no:
            return
        if not self._photos_table_exists():
            return
        try:
            self.db.cursor.execute("DELETE FROM photos WHERE tracking_no=? AND stage=?", (tracking_no, "Giriş"))
            for idx, path in enumerate(self.photo_paths):
                label = self.photo_labels[idx] if idx < len(self.photo_labels) else ""
                self.db.add_photo(tracking_no, path, label, "Giriş")
        except Exception as e:
            logger.debug(f"_sync_photos_table fallback used: {e}")

    def upload_photo(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, 'Fotoğraf Seç', '', "Resim Dosyaları (*.jpg *.png *.jpeg)")
        if file_paths:
            self._add_selected_photos(file_paths)

    def _add_selected_photos(self, file_paths):
        accepted = [
            path for path in file_paths
            if str(path).lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        merged_paths = list(self.photo_paths)
        for path in accepted:
            if path not in merged_paths:
                merged_paths.append(path)
        if len(merged_paths) > 5:
            ToastManager.warning(self, "En fazla 5 fotograf ekleyebilirsiniz.")
        merged_paths = merged_paths[:5]
        if merged_paths == self.photo_paths:
            return
        self._snapshot_photo_state()
        prev_labels = {p: self.photo_labels[i] for i, p in enumerate(self.photo_paths) if i < len(self.photo_labels)}
        self.photo_paths = merged_paths
        self.photo_labels = [prev_labels.get(p, "") for p in self.photo_paths]
        self.photo_path = self.photo_paths[0] if self.photo_paths else ""
        self._refresh_photo_table()
        self._update_photo_button()
        ToastManager.success(self, f"{len(self.photo_paths)} g\u00f6rsel ba\u015far\u0131yla eklendi.")

    def _collect_selected_accessories(self):
        acc_list = []
        for acc_name, chk in self.accessory_checkboxes.items():
            if chk.isChecked():
                acc_list.append(acc_name)
        return ", ".join(acc_list)

    def _sync_accessories_for_existing(self):
        if not self.device_data:
            return
        try:
            accessories = self._collect_selected_accessories()
            self.db.cursor.execute("UPDATE devices SET accessories=? WHERE id=?", (accessories, self.device_data[0]))
            self.db.conn.commit()
        except Exception as e:
            logger.warning(f"Accessory sync error: {e}")

    def _handle_accessory_toggle_changed(self, checked):
        if getattr(self, "_restoring_reference_form", False):
            return
        self._sync_accessories_for_existing()

    def _refresh_customer_list_if_loaded(self):
        try:
            win = self.window()
        except Exception:
            return
        try:
            pages = getattr(win, "pages", None)
            if isinstance(pages, dict) and 21 in pages:
                page = pages.get(21)
                if page and hasattr(page, "load_data"):
                    page.load_data()
                    return
        except Exception as e:
            logger.debug(f"_refresh_customer_list_if_loaded pages path failed: {e}")
        try:
            content_area = getattr(win, "content_area", None)
            if content_area and hasattr(content_area, "currentWidget"):
                page = content_area.currentWidget()
                if page and hasattr(page, "load_data") and page.__class__.__name__ == "CustomersPage":
                    page.load_data()
        except Exception as e:
            logger.debug(f"_refresh_customer_list_if_loaded current widget path failed: {e}")


