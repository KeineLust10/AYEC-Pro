# -*- coding: utf-8 -*-

"""
Quick Notes Editor Dialog
Allows managing fast_notes (Technician Panel & Service Dialog macros)
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QWidget, QMessageBox, QAbstractItemView, QFrame,
                             QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import ToastManager
from src.utils.logger import logger
from src.utils.system_config import SystemConfig
from src.utils.automotive_defaults import (
    AUTOMOTIVE_CATEGORIES,
    AUTOMOTIVE_PRESET,
    ensure_automotive_fast_notes,
)
from src.utils.technical_service_profiles import (
    DEFAULT_TECHNICAL_SERVICE_PROFILE,
    TECHNICAL_SERVICE_BASE_CATEGORIES,
    TECHNICAL_SERVICE_PROFILE_ORDER,
    TECHNICAL_SERVICE_PROFILE_PRESETS,
    build_profile_category,
    get_profile_labels,
    normalize_technical_service_profile,
)

PROFILE_PRESETS = {
    "Cep Telefonu": {
        "Arıza Hızlı Seçimi": ["EKRAN KIRIK", "SIVI TEMAS", "BATARYA ŞİŞİK", "ŞARJ ALMIYOR", "KAPANDI AÇILMIYOR", "KAMERA SORUNU", "SES GELMİYOR", "MİKROFON ÇALIŞMIYOR"],
        "Aksesuar": ["SIM Kart", "SD Kart", "Kılıf", "Şarj Aleti", "Kutu", "Kablo"],
        "İşlem Detayı": ["CİHAZ YAPILDI", "İADE EDİLDİ", "FİYAT ONAYI BEKLİYOR", "PARÇA BEKLİYOR", "TEST EDİLİYOR"],
        "Gizli Not": ["TEST OK", "VIP MÜŞTERİ", "RİSKLİ CİHAZ", "ACİL İŞLEM"],
    },
    "Bilgisayar": {
        "Arıza Hızlı Seçimi": ["GÖRÜNTÜ YOK", "AÇILMIYOR", "ŞARJ OLMUYOR", "ISINMA / FAN SESİ", "YAVAŞ ÇALIŞIYOR", "MAVİ EKRAN", "KLAVYE ÇALIŞMIYOR", "PORT / SOKET SORUNU"],
        "Aksesuar": ["Güç Adaptörü", "Şarj Kablosu", "HDMI / Görüntü Kablosu", "Mouse", "Klavye", "Taşıma Çantası"],
        "İşlem Detayı": ["FORMAT ATILDI", "PARÇA DEĞİŞTİ", "TEMİZLİK YAPILDI", "TEST EDİLİYOR", "ONAY BEKLİYOR"],
        "Gizli Not": ["TEST OK", "VERİ YEDEKLENDİ", "SIVI TEMASI ŞÜPHELİ", "ACİL TESLİM"],
    },
    "Güvenlik Sistemleri": {
        "Arıza Hızlı Seçimi": ["KAMERA GÖRÜNTÜ VERMİYOR", "KAYIT YOK", "ADAPTÖR ARIZASI", "NETWORK BAĞLANTISI YOK", "DISK HATASI", "GECE GÖRÜŞÜ ÇALIŞMIYOR"],
        "Aksesuar": ["Adaptör", "Montaj Ayağı", "BNC / PoE Kablo", "Kumanda", "Sensör", "Kurulum Notu"],
        "İşlem Detayı": ["MONTAJ YAPILDI", "KAYIT CİHAZI TEST EDİLDİ", "KEŞİF BEKLİYOR", "PARÇA BEKLİYOR", "UZAK BAĞLANTI AYARLANDI"],
        "Gizli Not": ["ŞİFRE PAYLAŞILDI", "SAHA TESTİ GEREKİYOR", "KABLOLAMA KONTROL EDİLECEK", "ACİL SAHA ÇIKIŞI"],
    },
}
PROFILE_PRESETS["Otomotiv"] = AUTOMOTIVE_PRESET
PROFILE_PRESETS.update(TECHNICAL_SERVICE_PROFILE_PRESETS)



class QuickNotesEditor(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, initial_category="Arıza Notu"):
        self.db = db
        self.sector_manager = None
        super().__init__("Hızlı Notlar / Makrolar Düzenleyici", parent, width=1200, height=850)
        self._tune_header_icons()
        self._force_automotive_categories = self._is_automotive()
        
        self.categories = ["Arıza Notu", "Arıza Hızlı Seçimi", "İşlem Detayı", "Gizli Not", "Aksesuar", "Cihaz Testi"]
        self.current_category = initial_category if initial_category in self.categories else "Arıza Notu"
        
        self.setup_content()
        self.load_data()

    def __init__(self, db, parent=None, initial_category="Arıza Hızlı Seçimi", sector_manager=None, profile_name=None):
        self.db = db
        self.sector_manager = sector_manager
        self.profile_name = normalize_technical_service_profile(profile_name)
        super().__init__("Hızlı Notlar / Makrolar Düzenleyici", parent, width=1200, height=850)
        self._tune_header_icons()
        self._force_automotive_categories = self._is_automotive()
        if self._force_automotive_categories:
            ensure_automotive_fast_notes(self.db)

        self.categories = list(TECHNICAL_SERVICE_BASE_CATEGORIES)
        self.current_category = initial_category if initial_category in self.categories else "Arıza Hızlı Seçimi"

        self.setup_content()
        self.load_data()

    def _is_automotive(self):
        try:
            if self.sector_manager and getattr(self.sector_manager, "get_current_plugin", None):
                plugin = self.sector_manager.get_current_plugin()
                if plugin:
                    return plugin.sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _effective_category(self, category=None):
        current = category or self.current_category
        if self._force_automotive_categories:
            return current
        return build_profile_category(self.profile_name, current)
         
    def setup_content(self):
        # Header Controls
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(20, 10, 20, 10)
        
        lbl_cat = QLabel("Kategori:")
        lbl_cat.setFont(QFont(DesignTokens.FONT_FAMILY, 11, QFont.Weight.Bold))
        if getattr(self, "_force_automotive_categories", False):
            self.categories = list(AUTOMOTIVE_CATEGORIES)
            if self.current_category not in self.categories:
                self.current_category = self.categories[0]
        else:
            self.categories = list(TECHNICAL_SERVICE_BASE_CATEGORIES)
            if self.current_category not in self.categories:
                self.current_category = self.categories[0]
        
        self.cmb_category = ModernComboBox(items=self.categories)
        self.cmb_category.setCurrentText(self.current_category)
        self.cmb_category.currentTextChanged.connect(self._on_category_changed)
        self.cmb_category.setFixedWidth(250)
        
        control_layout.addWidget(lbl_cat)
        control_layout.addWidget(self.cmb_category)
        profile_items = ["Otomotiv"] if getattr(self, "_force_automotive_categories", False) else list(TECHNICAL_SERVICE_PROFILE_ORDER)
        self.cmb_profile = ModernComboBox(items=profile_items)
        self.cmb_profile.setFixedWidth(190)
        if getattr(self, "_force_automotive_categories", False):
            self.cmb_profile.clear()
            self.cmb_profile.addItem("Otomotiv")
        else:
            self.cmb_profile.setCurrentText(self.profile_name)
            self.cmb_profile.currentTextChanged.connect(self._on_profile_changed)
        self.btn_apply_profile = QPushButton("Profil Uygula")
        self.btn_apply_profile.setFixedSize(120, 40)
        self.btn_apply_profile.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_apply_profile.clicked.connect(self.apply_profile_preset)
        control_layout.addWidget(self.cmb_profile)
        control_layout.addWidget(self.btn_apply_profile)
        control_layout.addStretch()
        
        # Add New Section
        self.inp_new_note = ValidatedLineEdit("Yeni not ekle...")
        self.inp_new_note.setPlaceholderText("Yeni not/etiket ismi...")
        self.btn_add = QPushButton(" + Ekle")
        self.btn_add.setFixedSize(100, 40)
        self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_add.clicked.connect(self.add_note)
        
        control_layout.addWidget(self.inp_new_note)
        control_layout.addWidget(self.btn_add)
        
        self.content_layout.addLayout(control_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["S\u0131ra", "Etiket / Not", "Durum", "\u0130\u015flem"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss() + """
            QTableWidget {
                background: @surface;
                color: @text;
                gridline-color: @border;
                font-size: 13px;
            }
            QHeaderView::section {
                background: @surface_alt;
                color: @text;
                font-weight: 800;
                padding: 8px;
            }
            QTableWidget::item {
                color: @text;
                padding: 6px;
            }
            QTableWidget::item:alternate {
                background: @surface_alt;
            }
        """))
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection) # Disable row selection for clearer inline editing
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setMinimumHeight(420)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.content_layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self._add_footer_hint()
        
        # Standard Buttons
        self.btn_close = QPushButton("Kapat")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setFixedSize(120, 45)
        self.btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.btn_close)

    def _tune_header_icons(self):
        if hasattr(self, "logo_label"):
            self.logo_label.setFixedSize(28, 28)
            pix = self.logo_label.pixmap()
            if pix:
                self.logo_label.setPixmap(pix.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            else:
                self.logo_label.setStyleSheet(theme_qss("color: @text; font-weight: bold; border: 1px solid @text; border-radius: 14px;"))

    def _add_footer_hint(self):
        lbl_hint = QLabel()
        lbl_hint.setText("Not: De\u011fi\u015fiklikler an\u0131nda kaydedilir. S\u0131ray\u0131 de\u011fi\u015ftirmek i\u00e7in 'S\u0131ra' s\u00fctununu d\u00fczenleyebilirsiniz.")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet(theme_qss("color: @text; font-size: 12px;"))
        self.footer_layout.addWidget(lbl_hint)
        
    def _on_category_changed(self, text):
        self.current_category = text
        self.load_data()

    def _on_profile_changed(self, text):
        new_profile = normalize_technical_service_profile(text)
        if new_profile == self.profile_name:
            return
        self.profile_name = new_profile
        self.load_data()
        
    def _wire_ui_signals(self):
        self.cmb_category.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_profile.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_data(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        notes = self.db.get_fast_notes(self._effective_category())
        
        for row_idx, note in enumerate(notes):
            self.table.insertRow(row_idx)
            if isinstance(note, dict):
                note_id = note.get('id')
                label = note.get('label', '')
                is_active = note.get('is_active', 0)
                order = note.get('display_order') or 0
            else:
                note_id = note[0] if len(note) > 0 else None
                label = note[2] if len(note) > 2 else ""
                is_active = note[3] if len(note) > 3 else 0
                order = note[4] if len(note) > 4 else row_idx
            self.table.setRowHeight(row_idx, 55)
            
            # 1. Order (Editable Int) — note_id stored in UserRole for real-time save
            item_order = QTableWidgetItem(str(order))
            item_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_order.setData(Qt.ItemDataRole.UserRole, note_id)
            self.table.setItem(row_idx, 0, item_order)

            # 2. Label (Editable) — note_id stored in UserRole for real-time save
            item_label = QTableWidgetItem(str(label))
            item_label.setData(Qt.ItemDataRole.UserRole, note_id)
            self.table.setItem(row_idx, 1, item_label)
            
            # 3. Active Toggle
            toggle_widget = QFrame()
            toggle_widget.setStyleSheet(theme_qss("QFrame { background: transparent; border: none; }"))
            t_layout = QHBoxLayout(toggle_widget)
            t_layout.setContentsMargins(0, 0, 10, 0)
            t_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            toggle = AnimatedToggle()
            toggle.setFixedSize(38, 20)
            toggle.setChecked(bool(is_active))
            toggle.toggled.connect(lambda c, nid=note_id: self.update_status(nid, c))
            t_layout.addWidget(toggle)
            self.table.setCellWidget(row_idx, 2, toggle_widget)
            
            # 4. Delete Button
            btn_del = QPushButton("Sil")
            btn_del.setFixedSize(60, 26)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive")))
            btn_del.clicked.connect(lambda _, nid=note_id: self.delete_note(nid))
            
            check_widget = QFrame()
            check_widget.setStyleSheet(theme_qss("QFrame { background: transparent; border: none; }"))
            c_layout = QHBoxLayout(check_widget)
            c_layout.setContentsMargins(0, 0, 10, 0)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c_layout.addWidget(btn_del)
            self.table.setCellWidget(row_idx, 3, check_widget)
        self._fit_table_height()
        self.table.blockSignals(False)

    def _fit_table_height(self):
        """Dikey scroll yerine tabloyu mevcut satır sayısına göre boyutlandır."""
        header_h = self.table.horizontalHeader().height() or 40
        rows_h = sum(self.table.rowHeight(r) or 55 for r in range(self.table.rowCount()))
        total_h = header_h + rows_h + (self.table.frameWidth() * 2) + 8
        self.table.setMinimumHeight(420)
        self.table.setMaximumHeight(max(420, min(total_h, 640)))

    def add_note(self):
        text = self.inp_new_note.text().strip()
        if not text:
            ToastManager.warning(self, "Lütfen not metni giriniz.")
            return
            
        try:
            # Default order = max order + 1
            existing = self.db.get_fast_notes(self._effective_category())
            normalized_orders = []
            for n in existing:
                if isinstance(n, dict):
                    normalized_orders.append(n.get('display_order') or 0)
                elif len(n) > 4:
                    normalized_orders.append(n[4] or 0)
                else:
                    normalized_orders.append(0)
            max_order = max(normalized_orders) if normalized_orders else -1
            
            self.db.add_fast_note(self._effective_category(), text, 1, max_order + 1)
            self.inp_new_note.clear()
            self.load_data()
            ToastManager.success(self, "Eklendi.")
        except Exception as e:
            ToastManager.error(self, f"Hata: {e}")

    def apply_profile_preset(self):
        profile_name = self.cmb_profile.currentText().strip()
        if not getattr(self, "_force_automotive_categories", False):
            self.profile_name = normalize_technical_service_profile(profile_name)
        preset = PROFILE_PRESETS.get(profile_name)
        if not preset:
            ToastManager.warning(self, "Profil bulunamadı.")
            return
        try:
            for category, labels in preset.items():
                effective_category = category if getattr(self, "_force_automotive_categories", False) else build_profile_category(self.profile_name, category)
                self.db.cursor.execute("DELETE FROM fast_notes WHERE category=?", (effective_category,))
                for idx, label in enumerate(labels):
                    self.db.cursor.execute(
                        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                        (effective_category, label, 1, idx),
                    )
            self.db.conn.commit()
            self.load_data()
            ToastManager.success(self, f"{profile_name} profili uygulandı.")
        except Exception as e:
            ToastManager.error(self, f"Profil uygulanamadı: {e}")

    def update_status(self, note_id, is_active):
        try:
            self.db.cursor.execute(
                "UPDATE fast_notes SET is_active=? WHERE id=?",
                (1 if is_active else 0, note_id)
            )
            self.db.conn.commit()
        except Exception as e:
            logger.error(f"Quick note status update error: {e}")

    def delete_note(self, note_id):
        dlg = ModernConfirmDialog("Onay", "Bu notu silmek istediğinize emin misiniz", self, confirm_text="Sil", cancel_text="İptal", destructive=True)
        if dlg.exec():
            try:
                self.db.delete_fast_note(note_id)
                self.load_data()
                ToastManager.success(self, "Not silindi.")
            except Exception as e:
                ToastManager.error(self, f"Silinemedi: {e}")
                
    def closeEvent(self, event):
        # Save any inline edits to Order or Label before closing
        self.save_table_changes()
        super().closeEvent(event)
        
    def save_table_changes(self):
        # Gerçek zamanlı kayıt on_item_changed ile yapılıyor — bu metod artık boş
        pass

    def on_item_changed(self, item):
        """Sıra veya etiket hücresi düzenlendiğinde anında DB'ye kaydet."""
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return
        col = item.column()
        try:
            if col == 0:  # Sıra
                val = int(item.text() or 0)
                self.db.cursor.execute(
                    "UPDATE fast_notes SET display_order=? WHERE id=?", (val, note_id)
                )
                self.db.conn.commit()
            elif col == 1:  # Etiket
                val = item.text().strip()
                if val:
                    self.db.cursor.execute(
                        "UPDATE fast_notes SET label=? WHERE id=?", (val, note_id)
                    )
                    self.db.conn.commit()
        except Exception as e:
            logger.error(f"QuickNotes real-time save error: {e}")
