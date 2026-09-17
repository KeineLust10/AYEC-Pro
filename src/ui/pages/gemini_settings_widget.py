# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QSlider, QSpinBox, 
                             QGroupBox, QFormLayout, QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QAction
try:
    from google import genai
    HAS_GEMINI = True
except Exception:
    HAS_GEMINI = False
    genai = None

from src.utils.message_helper import show_success, show_error, show_info, show_warning
from src.utils.ai_service import (
    DEFAULT_GEMINI_MODEL,
    RECOMMENDED_GEMINI_MODELS,
    normalize_gemini_model,
)


class GeminiSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """
    Jarvis (Gemini) Ayarları Widget'ı
    - API Key Yönetimi
    - Model Seçimi
    - Parametre Ayarları
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        header = QHBoxLayout()
        title_lbl = QLabel("🤖 Gemini AI (Jarvis) Ayarları")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #2c3e50;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Info Box
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #e8f8f5; border: 1px solid #d1f2eb; border-radius: 6px; padding: 15px;")
        info_layout = QVBoxLayout(info_frame)
        info_lbl = QLabel("Google Gemini API anahtarınızı girerek yapay zeka özelliklerini (Jarvis) aktif edebilirsiniz.")
        info_lbl.setStyleSheet("color: #16a085;")
        info_lbl.setWordWrap(True)
        info_layout.addWidget(info_lbl)
        if not HAS_GEMINI:
            warn_lbl = QLabel("⚠️ UYARI: 'google-genai' kütüphanesi yüklü değil! Jarvis özellikleri çalışmayacaktır.\nKurulum için terminalde: pip install google-genai")
            warn_lbl.setStyleSheet("color: red; font-weight: bold;")
            warn_lbl.setWordWrap(True)
            info_layout.addWidget(warn_lbl)
            
        layout.addWidget(info_frame)

        # Form Area
        form_group = QGroupBox("Bağlantı Ayarları")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(15)

        # API Key
        self.inp_api_key = QLineEdit()
        self.inp_api_key.setPlaceholderText("AIzaSy...")
        self.inp_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_api_key.setMinimumWidth(300)
        
        # Toggle Password Visibility
        toggle_btn = QPushButton("👁")
        toggle_btn.setFixedWidth(40)
        toggle_btn.setCheckable(True)
        toggle_btn.toggled.connect(lambda checked: self.inp_api_key.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password))
        
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.inp_api_key)
        key_layout.addWidget(toggle_btn)
        
        form_layout.addRow("API Anahtarı:", key_layout)

        # Model Selector
        self.combo_model = QComboBox()
        self.combo_model.addItems(list(RECOMMENDED_GEMINI_MODELS))
        form_layout.addRow("Model Seçimi:", self.combo_model)

        # Parameters
        self.slider_temp = QSlider(Qt.Orientation.Horizontal)
        self.slider_temp.setRange(0, 100) # 0.0 to 1.0 (div by 100)
        self.slider_temp.setValue(70)
        self.lbl_temp_val = QLabel("0.7")
        self.slider_temp.valueChanged.connect(lambda v: self.lbl_temp_val.setText(str(v/100.0)))
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.slider_temp)
        temp_layout.addWidget(self.lbl_temp_val)
        
        form_layout.addRow("Yaratıcılık (Temperature):", temp_layout)

        layout.addWidget(form_group)

        # Actions
        btn_layout = QHBoxLayout()
        
        self.btn_test = QPushButton("Bağlantıyı Test Et")
        self.btn_test.setStyleSheet("""
            background-color: #95a5a6; color: white; padding: 10px; border-radius: 5px; font-weight: bold;
        """)
        self.btn_test.clicked.connect(self.test_connection)
        
        self.btn_save = QPushButton("Ayarları Kaydet")
        self.btn_save.setStyleSheet("""
            background-color: #27ae60; color: white; padding: 10px; border-radius: 5px; font-weight: bold;
        """)
        self.btn_save.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(self.btn_test)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        layout.addStretch()

    def _wire_ui_signals(self):
        self.combo_model.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_settings(self):
        api_key = self.db.get_setting("gemini_api_key", "")
        model = normalize_gemini_model(
            self.db.get_setting("gemini_model", DEFAULT_GEMINI_MODEL)
        )
        temperature = float(self.db.get_setting("gemini_temperature", "0.7"))
        
        self.inp_api_key.setText(api_key)
        
        idx = self.combo_model.findText(model)
        if idx >= 0: self.combo_model.setCurrentIndex(idx)
        
        self.slider_temp.setValue(int(temperature * 100))
        self.lbl_temp_val.setText(str(temperature))

    def save_settings(self):
        api_key = self.inp_api_key.text().strip()
        model = self.combo_model.currentText()
        temperature = self.slider_temp.value() / 100.0
        
        try:
            self.db.set_setting("gemini_api_key", api_key)
            self.db.set_setting("gemini_model", model)
            self.db.set_setting("gemini_temperature", str(temperature))
            
            show_success(self, "Kaydedildi", "Ayarlar başarıyla kaydedildi.")
            
        except Exception as e:
            show_error(self, "Hata", f"Kaydetme hatası: {e}")

    def test_connection(self):
        api_key = self.inp_api_key.text().strip()
        if not api_key:
            show_warning(self, "Uyarı", "Lütfen önce API anahtarı girin.")
            return

        self.btn_test.setText("Test Ediliyor...")
        self.btn_test.setEnabled(False)
        self.repaint()

        try:
            if not HAS_GEMINI:
                raise ImportError("'google-genai' kütüphanesi eksik.")
                
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.combo_model.currentText(),
                contents="Hello, reply with 'OK'."
            )
            
            if response and response.text:
                show_success(self, "Başarılı", "Bağlantı başarılı! Gemini yanıt verdi.")
            else:
                show_error(self, "Hata", "Yanıt alınamadı.")
                
        except Exception as e:
            show_error(self, "Bağlantı Hatası", str(e))
        finally:
            self.btn_test.setText("Bağlantıyı Test Et")
            self.btn_test.setEnabled(True)
