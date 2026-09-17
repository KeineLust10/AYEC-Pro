# -*- coding: utf-8 -*-

import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.toast_notification import show_error, show_info, show_warning
from src.utils.logger import logger
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import ToastManager


class NewServiceDialogMediaMixin:
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
            self._snapshot_photo_state()
            prev_labels = {p: self.photo_labels[i] for i, p in enumerate(self.photo_paths) if i < len(self.photo_labels)}
            self.photo_paths = list(file_paths)
            self.photo_labels = [prev_labels.get(p, "") for p in self.photo_paths]
            self.photo_path = self.photo_paths[0] if self.photo_paths else ""
            self._refresh_photo_table()
            self._update_photo_button()
            ToastManager.success(self, f"{len(self.photo_paths)} görsel başarıyla eklendi. 📸")

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


