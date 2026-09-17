# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, 
                             QFormLayout, QFrame, QScrollArea, QWidget, QFileDialog,
                             QRadioButton, QButtonGroup, QDoubleSpinBox)
from src.utils.toast_notification import show_success, show_error, show_warning
from PyQt6.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG
from datetime import datetime, timedelta
import random
import os
import importlib.util

from src.ui.widgets.pattern_lock import PatternLockWidget
from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
from src.utils.ai_service import AIService
import threading

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.utils.design_system import DesignTokens
from src.utils.validators import Validators
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger


class AddDeviceDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, customer_name=None, device_data=None):
        super().__init__("Yeni Servis Kayd\u0131 Olu\u015ftur", parent, width=1400, height=900)
        self.db = db
        self.device_data = device_data
        self._editing_tracking_no = self._device_value(device_data, "tracking_no")
        try:
            self.db.create_device_brands_table()
        except Exception as exc:
            logger.debug("Device catalog initialization skipped: %s", exc)
        self.selected_customer_id = None
        self.photo_path = ""
        self.ai_service = AIService(db)
        self.setup_content()
        if device_data:
            self._load_device_data(device_data)
        elif customer_name:
            self.inp_name.setText(str(customer_name))

    @staticmethod
    def _device_value(device_data, key, default=""):
        if not device_data:
            return default
        if isinstance(device_data, dict):
            return device_data.get(key, default)
        try:
            if key in device_data.keys():
                return device_data[key]
        except (AttributeError, IndexError, KeyError, TypeError):
            pass
        return default

    def _load_device_data(self, device_data):
        self.setWindowTitle("Servis Kaydini Duzenle")
        self.inp_name.setText(str(self._device_value(device_data, "customer_name") or ""))
        self.inp_tckn.setText(str(self._device_value(device_data, "customer_tax_id") or ""))
        self.inp_contact.setText(str(self._device_value(device_data, "customer_contact") or ""))
        self.inp_delivered_by.setText(str(self._device_value(device_data, "delivered_by_name") or ""))
        self.inp_delivered_phone.setText(str(self._device_value(device_data, "delivered_by_phone") or ""))
        self.combo_type.setCurrentText(str(self._device_value(device_data, "device_type") or ""))
        self._load_catalog_brands(self.combo_type.currentText(), preserve_current=False)
        self.inp_brand.setCurrentText(str(self._device_value(device_data, "device_brand") or ""))
        self._load_catalog_models(self.combo_type.currentText(), self.inp_brand.currentText(), preserve_current=False)
        self.inp_model.setCurrentText(str(self._device_value(device_data, "device_model") or ""))
        self.inp_serial.setText(
            str(self._device_value(device_data, "serial_no") or self._device_value(device_data, "imei") or "")
        )
        self.txt_desc.setPlainText(str(self._device_value(device_data, "fault_description") or ""))
        self.combo_urgency.setCurrentText(str(self._device_value(device_data, "urgency", "Normal") or "Normal"))
        self.spin_cost.setValue(float(self._device_value(device_data, "cost_price", 0) or 0))
        self.photo_path = str(self._device_value(device_data, "photo_path") or "")
        if self.photo_path:
            self.lbl_photo.setText(os.path.basename(self.photo_path))

    def _enabled_device_profiles(self):
        try:
            raw = self.db.get_internal_setting("device_business_profiles", "")
        except Exception:
            raw = ""
        allowed = {"bilgisayar", "cep_telefonu", "akilli_ev"}
        profiles = [item.strip() for item in str(raw or "").split(",") if item.strip() in allowed]
        return profiles or ["bilgisayar"]

    def _catalog_device_types(self):
        try:
            rows = self.db.get_device_model_catalog(profiles=self._enabled_device_profiles())
            items = [str(row[1]).strip() for row in rows if row[1]]
            if items:
                priority = []
                for profile in self._enabled_device_profiles():
                    priority.extend(
                        {
                            "bilgisayar": ["Laptop", "Masa\u00fcst\u00fc PC", "Monit\u00f6r"],
                            "cep_telefonu": ["Cep Telefonu", "Tablet", "Ak\u0131ll\u0131 Saat"],
                            "akilli_ev": ["Ak\u0131ll\u0131 Ev Merkezi", "Ak\u0131ll\u0131 Priz", "Ak\u0131ll\u0131 Kamera"],
                        }.get(profile, [])
                    )
                return list(dict.fromkeys(priority + items)) + ["Di\u011fer"]
        except Exception as exc:
            logger.debug("Device catalog type lookup failed: %s", exc)
        return ["Laptop", "Masa\u00fcst\u00fc PC", "Di\u011fer"]

    def _load_catalog_brands(self, device_type, preserve_current=True):
        current = self.inp_brand.currentText().strip() if preserve_current else ""
        brands = []
        try:
            rows = self.db.get_device_model_catalog(
                profiles=self._enabled_device_profiles(), device_type=device_type
            )
            brands = sorted({str(row[2]).strip() for row in rows if row[2]}, key=str.casefold)
        except Exception as exc:
            logger.debug("Device catalog brand lookup failed: %s", exc)
        self.inp_brand.blockSignals(True)
        self.inp_brand.clear()
        self.inp_brand.addItems(brands)
        if current:
            self.inp_brand.setCurrentText(current)
        self.inp_brand.blockSignals(False)
        self._load_catalog_models(device_type, self.inp_brand.currentText(), preserve_current=False)

    def _load_catalog_models(self, device_type, brand, preserve_current=True):
        current = self.inp_model.currentText().strip() if preserve_current else ""
        models = []
        try:
            rows = self.db.get_device_model_catalog(
                profiles=self._enabled_device_profiles(), device_type=device_type, brand=brand
            )
            models = sorted({str(row[3]).strip() for row in rows if row[3]}, key=str.casefold)
        except Exception as exc:
            logger.debug("Device catalog model lookup failed: %s", exc)
        self.inp_model.blockSignals(True)
        self.inp_model.clear()
        self.inp_model.addItems(models)
        if current:
            self.inp_model.setCurrentText(current)
        self.inp_model.blockSignals(False)

    def setup_content(self):
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(20)
        
        # --- Left Panel (Scrollable Forms) ---
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setStyleSheet(theme_qss("background: transparent;"))
        
        left_content = QWidget()
        left_vbox = QVBoxLayout(left_content)
        left_vbox.setContentsMargins(0, 0, 10, 0)
        left_vbox.setSpacing(25)
        
        # 1. Müşteri Bilgileri
        grp_cust = QFrame()
        grp_cust.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        gl = QVBoxLayout(grp_cust)
        gl.setContentsMargins(20, 20, 20, 20)
        
        lt = QLabel("👤 MÜŞTERİ BİLGİLERİ")
        lt.setStyleSheet(theme_qss("font-weight: 800; color: @text; border: none; font-size: 13px;"))
        gl.addWidget(lt)
        
        btn_find = QPushButton("🔍 Kayıtlı Müşteri Seç")
        btn_find.setFixedHeight(45)
        btn_find.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_find.clicked.connect(self.open_customer_select)
        gl.addWidget(btn_find)
        
        self.lbl_selected_customer = QLabel("Durum: Yeni Müşteri Kaydı")
        self.lbl_selected_customer.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        gl.addWidget(self.lbl_selected_customer)
        
        # Form Alanları
        self.form_lay = QFormLayout()
        self.form_lay.setSpacing(15)
        
        self.inp_name = ValidatedLineEdit("Ad Soyad veya Firma Adı", validator_func=Validators.is_not_empty)
        self.inp_tckn = ValidatedLineEdit("TCKN / Vergi No")
        self.inp_delivered_by = ValidatedLineEdit(
            "Cihaz\u0131 teslim eden ki\u015fi"
        )
        self.inp_delivered_phone = ValidatedLineEdit(
            "Teslim eden ileti\u015fim numaras\u0131"
        )
        self.inp_contact = ValidatedLineEdit("Telefon Numarası", validator_func=Validators.is_phone)
        
        self.form_lay.addRow("Müşteri Adı:", self.inp_name)
        self.form_lay.addRow("Kimlik/Vergi No:", self.inp_tckn)
        self.form_lay.addRow("İletişim Tel:", self.inp_contact)
        self.form_lay.addRow("Teslim Eden:", self.inp_delivered_by)
        self.form_lay.addRow("Teslim Eden Tel:", self.inp_delivered_phone)
        gl.addLayout(self.form_lay)
        
        self.inp_name.editingFinished.connect(lambda: self.trigger_customer_intelligence(self.inp_name.text()))
        left_vbox.addWidget(grp_cust)

        # 2. Cihaz Bilgileri
        grp_dev = QFrame()
        grp_dev.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        dl = QVBoxLayout(grp_dev)
        dl.setContentsMargins(20, 20, 20, 20)
        
        dt = QLabel("📱 CİHAZ BİLGİLERİ")
        dt.setStyleSheet(theme_qss("font-weight: 800; color: @text; border: none; font-size: 13px;"))
        dl.addWidget(dt)
        
        df = QFormLayout()
        df.setSpacing(15)
        self.combo_type = ModernComboBox(items=self._catalog_device_types())
        self.inp_brand = ValidatedLineEdit("Marka (Örn: Apple, Samsung)")
        self.inp_model = ValidatedLineEdit("Model (Örn: iPhone 13 Pro)")
        self.inp_brand = ModernComboBox()
        self.inp_brand.setEditable(True)
        self.inp_model = ModernComboBox()
        self.inp_model.setEditable(True)
        self.inp_model.setPlaceholderText("Model secin veya yazin")
        self.inp_serial = ValidatedLineEdit("Seri / IMEI")
        self.combo_type.currentTextChanged.connect(
            lambda value: self._load_catalog_brands(value, preserve_current=False)
        )
        self.inp_brand.currentTextChanged.connect(
            lambda value: self._load_catalog_models(
                self.combo_type.currentText(), value, preserve_current=False
            )
        )
        self._load_catalog_brands(self.combo_type.currentText(), preserve_current=False)
        
        df.addRow("Cihaz Türü:", self.combo_type)
        df.addRow("Marka:", self.inp_brand)
        df.addRow("Model:", self.inp_model)
        df.addRow("Seri / IMEI:", self.inp_serial)
        dl.addLayout(df)
        left_vbox.addWidget(grp_dev)
        
        # 3. Arıza ve Durum
        grp_fix = QFrame()
        grp_fix.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        fl = QVBoxLayout(grp_fix)
        fl.setContentsMargins(20, 20, 20, 20)
        
        ft = QLabel("🛠️ ARIZA & SERVİS DETAYLARI")
        ft.setStyleSheet(theme_qss("font-weight: 800; color: @text; border: none; font-size: 13px;"))
        fl.addWidget(ft)
        
        ff = QFormLayout()
        ff.setSpacing(15)
        
        self.txt_desc = QTextEdit()
        self.txt_desc.setFixedHeight(120)
        self.txt_desc.setPlaceholderText("Arıza detaylarını buraya yazın veya mikrofonla anlatın...")
        self.txt_desc.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        
        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(45, 45)
        self.btn_mic.setToolTip("Jarvis'e Anlat (Sesli Not)")
        self.btn_mic.setStyleSheet(theme_qss("""
            QPushButton {{ 
                background: @surface; 
                color: @accent; 
                border: 2px solid @accent; 
                border-radius: 22px; 
                font-size: 20px; 
            }}
            QPushButton:hover {{ 
                background: @accent; 
                color: @selection_text; 
            }}
        """))
        self.btn_mic.clicked.connect(self.start_voice_note)
        
        desc_h = QHBoxLayout()
        desc_h.addWidget(self.txt_desc)
        desc_h.addWidget(self.btn_mic)
        
        self.combo_urgency = ModernComboBox(items=["Düşük", "Normal", "Yüksek", "Kritik"])
        self.combo_urgency.setCurrentText("Normal")
        
        self.spin_cost = QDoubleSpinBox()
        self.spin_cost.setRange(0, 50000)
        self.spin_cost.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=CurrencyHelper.get_code(self.db))}")
        self.spin_cost.setFixedHeight(45)
        DesignTokens.apply_spinbox_styles(self.spin_cost)

        # Currency Chips
        _dc_chip_sty = theme_qss('''
            QRadioButton {
                background: @surface_alt;
                color: @text_muted;
                padding: 5px 12px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid @border;
            }
            QRadioButton::indicator {
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
                image: none;
            }
            QRadioButton:checked { background: @accent; color: @selection_text; border: 1px solid @accent; }
            QRadioButton:!checked:hover { background: @surface; color: @text; }
        ''')
        self.cost_btn_try = QRadioButton(CurrencyHelper.get_symbol(currency_code="TRY"))
        self.cost_btn_usd = QRadioButton("$")
        self.cost_btn_eur = QRadioButton("€")
        self.cost_btn_grp = QButtonGroup(self)
        self.cost_btn_grp.addButton(self.cost_btn_try, 1)
        self.cost_btn_grp.addButton(self.cost_btn_usd, 2)
        self.cost_btn_grp.addButton(self.cost_btn_eur, 3)
        for _b in [self.cost_btn_try, self.cost_btn_usd, self.cost_btn_eur]:
            _b.setStyleSheet(_dc_chip_sty)
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cost_btn_try.setChecked(True)
        def _dc_suffix():
            _s = "$" if self.cost_btn_usd.isChecked() else "€" if self.cost_btn_eur.isChecked() else CurrencyHelper.get_symbol(currency_code="TRY")
            self.spin_cost.setSuffix(f" {_s}")
        self.cost_btn_try.toggled.connect(_dc_suffix)
        self.cost_btn_usd.toggled.connect(_dc_suffix)
        self.cost_btn_eur.toggled.connect(_dc_suffix)

        cost_h = QHBoxLayout()
        cost_h.addWidget(self.spin_cost)
        cost_h.addWidget(self.cost_btn_try)
        cost_h.addWidget(self.cost_btn_usd)
        cost_h.addWidget(self.cost_btn_eur)
        
        ff.addRow("Arıza Tanımı:", desc_h)
        ff.addRow("Öncelik:", self.combo_urgency)
        ff.addRow("Tahmini Tutar:", cost_h)
        fl.addLayout(ff)
        left_vbox.addStretch(1)
        
        left_scroll.setWidget(left_content)
        main_h_layout.addWidget(left_scroll, 48)
        
        # --- Right Panel (Service Details, Pattern & Photo) ---
        right_panel = QWidget()
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(10, 0, 0, 0)
        rl.setSpacing(16)

        rl.addWidget(grp_fix)
        rl.addStretch(1)
        
        # Pattern Lock
        p_card = QFrame()
        p_card.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        p_lay = QVBoxLayout(p_card)
        self.pattern_widget = PatternLockWidget()
        btn_pattern = QPushButton("Desen Kilidi")
        btn_pattern.setFixedHeight(42)
        btn_pattern.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pattern.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_pattern.clicked.connect(self.open_pattern_lock_dialog)
        p_lay.addWidget(btn_pattern)
        rl.addWidget(p_card)
        
        # Photo
        photo_card = QFrame()
        photo_card.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        photo_lay = QVBoxLayout(photo_card)
        photo_lay.addWidget(QLabel("📸 CİHAZ GÖRSELİ"), alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.btn_photo = QPushButton("📁 Fotoğraf Yükle")
        self.btn_photo.setFixedHeight(50)
        self.btn_photo.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_photo.clicked.connect(self.select_photo)
        photo_lay.addWidget(self.btn_photo)
        
        self.lbl_photo = QLabel("Henüz görsel seçilmedi")
        self.lbl_photo.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-style: italic;"))
        self.lbl_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_lay.addWidget(self.lbl_photo)
        rl.addWidget(photo_card)
        
        rl.addStretch()
        main_h_layout.addWidget(right_panel, 52)
        
        self.add_layout(main_h_layout)
        
        # Footer Buttons
        self.add_cancel_button()
        self.add_button("Temizle", "secondary", self.clear_form)
        self.add_button("💾 KAYDI TAMAMLA VE FİŞ OLUŞTUR", "primary", self.save_device)

    def clear_form(self):
        self.inp_name.clear()
        self.inp_contact.clear()
        self.inp_delivered_by.clear()
        self.inp_delivered_phone.clear()
        self.inp_tckn.clear()
        self.inp_brand.clear()
        self.inp_model.clear()
        self._load_catalog_brands(self.combo_type.currentText(), preserve_current=False)
        self.inp_serial.clear()
        self.txt_desc.clear()
        self.pattern_widget.clear_pattern()
        self.photo_path = ""
        self.lbl_photo.setText("Henüz görsel seçilmedi")
        self.selected_customer_id = None
        self.lbl_selected_customer.setText("Durum: Yeni Müşteri Kaydı")


    def open_pattern_lock_dialog(self):
        dialog = ModernDialog("Desen Kilidi", self, width=380, height=450)
        dialog.set_footer_visible(False)
        layout = dialog.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        title = QLabel("Desen Kilidi")
        title.setStyleSheet(theme_qss("font-size: 16px; font-weight: 800; color: @text;"))
        layout.addWidget(title)

        editor = PatternLockWidget()
        editor.set_pattern(self.pattern_widget.get_pattern())
        layout.addWidget(editor, alignment=Qt.AlignmentFlag.AlignCenter)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_button = QPushButton("Iptal")
        cancel_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        cancel_button.clicked.connect(dialog.reject)
        save_button = QPushButton("Kaydet")
        save_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        save_button.clicked.connect(dialog.accept)
        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pattern_widget.set_pattern(editor.get_pattern())

    def open_customer_select(self):
        dialog = CustomerSelectDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_customer:
            c = dialog.selected_customer
            self.selected_customer_id = c[0]
            self.inp_name.setText(c[1])
            self.inp_contact.setText(c[2])
            self.inp_delivered_by.setText(c[1])
            self.inp_delivered_phone.setText(c[2])
            self.inp_tckn.setText(c[5])
            self.lbl_selected_customer.setText(f"Durum: Kayıtlı Müşteri ({c[1]})")
            self.trigger_customer_intelligence(c[1])

    def check_contact_for_intel(self):
        tel = self.inp_contact.text().strip()
        if len(tel) >= 10:
            customers = self.db.search_customers(tel)
            if customers:
                self.inp_name.setText(customers[0][1])
                self.trigger_customer_intelligence(customers[0][1])

    voice_finished_signal = pyqtSignal(str)
    voice_error_signal = pyqtSignal(str)

    def trigger_customer_intelligence(self, name):
        if not name or len(name) < 3:
            return
        if self.db.get_setting("jarvis_intel_enabled", "1") != "1":
            return
        
        def run_intel():
            history = self.db.get_customer_history_summary(name)
            if history:
                insight = self.ai_service.generate_customer_insight(history)
                if insight:
                    if self.parent() and hasattr(self.parent(), 'jarvis_sidebar'):
                        # UI updates should be queued in main thread
                        QMetaObject.invokeMethod(self.parent().jarvis_sidebar, "add_message", 
                                                 Qt.QueuedConnection, Q_ARG(str, insight), Q_ARG(bool, True))
                        
                    # Ayrıca dialog içinde bir bildirim göster
                    from src.ui.widgets.jarvis_toast import JarvisToast
                    # Note: We need a QWidget parent for toast, self should work
                    try:
                        toast = JarvisToast(self.parent() or self, "JARVIS İSTİHBARAT", insight)
                        toast.show_toast()
                    except Exception as toast_err:
                        logger.warning(f"AddDeviceDialog intelligence toast failed: {toast_err}")

        threading.Thread(target=run_intel, daemon=True).start()

    def start_voice_note(self):
        """Sesli not işlemini kilitlemeden başlatır"""
        # 0. Check PyAudio
        if not importlib.util.find_spec("speech_recognition") or not importlib.util.find_spec("pyaudio"):
             show_error(self, "Ses modülü (PyAudio) eksik. Lütfen 'pip install pyaudio' kurunuz.")
             return

        # 1. Görsel Geri Bildirim
        self.btn_mic.setStyleSheet("background: #e74c3c; color: white; border: 2px solid #c0392b; border-radius: 20px; font-size: 18px;")
        self.txt_desc.setPlaceholderText("Jarvis sizi dinliyor... (Konuşun)")
        self.btn_mic.setEnabled(False)
        
        try:
            # 2. İşçiyi (Worker) başlat
            from src.utils.voice_worker import VoiceWorker
            self.voice_thread = VoiceWorker(self.ai_service)
            
            # 3. Sonuçlar gelince ne yapılacağını söyle
            self.voice_thread.text_received.connect(self.on_voice_finished)
            self.voice_thread.error_occurred.connect(self.on_voice_error)
            
            # 4. Arka planda çalıştır
            self.voice_thread.start()
        except Exception as e:
             self.on_voice_error(str(e))

    def on_voice_finished(self, text):
        """Ses başarıyla alındığında çalışır (Main Thread)"""
        self.btn_mic.setEnabled(True)
        self.btn_mic.setStyleSheet("background: #1E293B; color: #F59E0B; border: 2px solid #F59E0B; border-radius: 20px; font-size: 18px;")
        
        # AI Refine
        refine_enabled = self.db.get_setting("jarvis_voice_refine_enabled", "1") == "1"
        if refine_enabled:
            self.txt_desc.setPlaceholderText("Jarvis notunuzu düzenliyor...")
            
            def refine():
                refined = self.ai_service.refine_technical_note(text)
                # UI Update safe way
                QMetaObject.invokeMethod(self.txt_desc, "setText", Qt.QueuedConnection, Q_ARG(str, refined))
            
            threading.Thread(target=refine, daemon=True).start()
        else:
            self.txt_desc.setText(text)

    def on_voice_error(self, err_msg):
        """Hata durumunda çalışır (Main Thread)"""
        self.btn_mic.setEnabled(True)
        self.btn_mic.setStyleSheet("background: #1E293B; color: #F59E0B; border: 2px solid #F59E0B; border-radius: 20px; font-size: 18px;")
        self.txt_desc.setPlaceholderText(f"Hata: {err_msg}")
        show_warning(self, "Ses Hatası", err_msg)

    def toggle_customer_fields(self):
        pass # We use universal fields now for cleaner UI

    def select_photo(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Fotoğraf Seç', '', 'Images (*.jpg *.png)')
        if fname:
            self.photo_path = fname
            self.lbl_photo.setText(f"Seçildi: {os.path.basename(fname)}")

    def save_device(self):
        if not self.inp_name.text() or not self.inp_contact.text():
            show_error(self, "Lütfen müşteri adı ve iletişim bilgilerini giriniz.")
            return
            
        tracking_no = self._editing_tracking_no or f"TRK{random.randint(100000, 999999)}"
        data = {
            "tracking_no": tracking_no,
            "customer_name": self.inp_name.text(),
            "device_brand": self.inp_brand.currentText(),
            "device_model": self.inp_model.currentText(),
            "serial_no": self.inp_serial.text(),
            "fault_category": self.combo_type.currentText(),
            "urgency": self.combo_urgency.currentText(),
            "status": self._device_value(self.device_data, "status", "Bekliyor"),
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "estimated_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "device_type": self.combo_type.currentText(),
            "imei": self.inp_serial.text(),
            "pattern_lock": self.pattern_widget.get_pattern(),
            "customer_type": "Bireysel",
            "customer_tax_id": self.inp_tckn.text(),
            "customer_contact": self.inp_contact.text(),
            "delivered_by_name": (
                self.inp_delivered_by.text().strip()
                or self.inp_name.text().strip()
            ),
            "delivered_by_phone": (
                self.inp_delivered_phone.text().strip()
                or self.inp_contact.text().strip()
            ),
            "fault_description": self.txt_desc.toPlainText(),
            "photo_path": self.photo_path,
            "priority": self.combo_urgency.currentText(),
            "technician": "Atanmadı",
            "warranty_end_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "cost_price": self.spin_cost.value(),
            "internal_notes": ""
        }
        
        if self._editing_tracking_no:
            try:
                self.db.cursor.execute("PRAGMA table_info(devices)")
                columns = {row[1] for row in (self.db.cursor.fetchall() or [])}
                updates = [
                    (key, value)
                    for key, value in data.items()
                    if key in columns and key != "tracking_no"
                ]
                if not updates:
                    raise RuntimeError("No editable device fields are available")
                clause = ", ".join(f"{key}=?" for key, _ in updates)
                self.db.cursor.execute(
                    f"UPDATE devices SET {clause} WHERE tracking_no=?",
                    tuple(value for _, value in updates) + (self._editing_tracking_no,),
                )
                self.db.conn.commit()
                show_success(self, "Servis kaydi guncellendi.")
                self.accept()
                return
            except Exception as exc:
                logger.error("Compact service edit failed: %s", exc)
                show_error(self, f"Servis kaydi guncellenemedi: {exc}")
                return

        if self.db.add_device(data):
            show_success(self, f"Servis kaydı oluşturuldu! Takip No: {tracking_no}")
            self.accept()
        else:
            show_error(self, "Veritabanı hatası oluştu.")

    def _wire_ui_signals(self):
        self.combo_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.combo_urgency.currentIndexChanged.connect(self._on_ui_widget_changed)
