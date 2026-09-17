# -*- coding: utf-8 -*-


import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect, QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QLinearGradient, QBrush
import pyttsx3
import threading
import logging
from src.utils.ai_service import AIService
from src.ui.widgets.modern_dialog import ModernDialog

logger = logging.getLogger("AYECProLogger")

class AIQueryThread(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, ai_service, question):
        super().__init__()
        self.ai_service = ai_service
        self.question = question
        self.db_name = getattr(getattr(ai_service, "db", None), "_db_name", None)
        self.api_keys = list(getattr(ai_service, "api_keys", []) or [])
        self.model_id = getattr(ai_service, "model_id", "gemini-3.6-flash")
        
    def run(self):
        db = None
        service = self.ai_service
        try:
            if self.db_name:
                from src.database import Database
                db = Database(self.db_name, init_mode="connection_only")
                service = AIService(db, model_name=self.model_id)
                if self.api_keys:
                    service.api_keys = self.api_keys
                    service._setup_client()
            result = service.get_smart_response(self.question)
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass
        self.finished.emit(result)

class JarvisMessage(QFrame):
    def __init__(self, text, is_ai=True, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        
        container = QFrame()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(15, 12, 15, 12)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setStyleSheet("border: none; background: transparent; font-size: 13px; line-height: 1.4;")
        
        if is_ai:
            container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 18px;
                    border-bottom-left-radius: 4px;
                }
                QLabel { color: #1e293b; }
            """)
            self.layout.addWidget(container)
            self.layout.addStretch()
            self.layout.setContentsMargins(0, 5, 40, 5) # Align Left
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0,0,0,15))
            shadow.setOffset(0, 2)
            container.setGraphicsEffect(shadow)
        else:
            container.setStyleSheet("""
                QFrame {
                    background-color: #3b82f6;
                    border-radius: 18px;
                    border-bottom-right-radius: 4px;
                }
                QLabel { color: white; }
            """)
            self.layout.addWidget(container)
            self.layout.setContentsMargins(40, 5, 0, 5) # Align Right
        
        c_layout.addWidget(self.label)

class JarvisAssistantDialog(ModernDialog):
    closed = pyqtSignal()
    data_changed = pyqtSignal()
    
    def __init__(self, db, parent=None):
        super().__init__(title="JARVIS CORE", parent=parent, width=450, height=700)
        self.db = db
        self.ai_service = None
        self.tts_engine = None
        self.query_thread = None
        self.set_footer_visible(False)
        self.setFixedSize(450, 700)
        self.voice_enabled = self.db.get_setting("jarvis_voice_enabled", "0") == "1"
        self.setup_ui()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
        
    def delayed_init(self):
        try:
            self.ai_service = AIService(self.db)
        except Exception as e:
            logger.error("AI service init failed: %s", e)
            self.ai_service = None
        logger.info("Jarvis service initialized.")

    def setup_ui(self):
        # Translucent Background Container
        self.main_layout = self.content_layout
        self.main_layout.setContentsMargins(10, 20, 10, 20) # Floating effect margins
        
        # --- THE REAL VISUAL BOX ---
        self.box = QFrame()
        self.box.setObjectName("JarvisBox")
        self.box.setStyleSheet("""
            QFrame#JarvisBox {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 28px;
            }
        """)
        
        # Shadow for box
        box_shadow = QGraphicsDropShadowEffect()
        box_shadow.setBlurRadius(30)
        box_shadow.setColor(QColor(0,0,0,60))
        box_shadow.setOffset(0, 10)
        self.box.setGraphicsEffect(box_shadow)
        
        self.main_layout.addWidget(self.box)
        
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.setSpacing(0)
        
        # --- HEADER ---
        self.header = QFrame()
        self.header.setFixedHeight(80)
        self.header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                border-top-left-radius: 28px;
                border-top-right-radius: 28px;
                border-bottom: 1px solid #334155;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(25, 0, 20, 0)
        
        # Status Pulse Icon
        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #10b981; font-size: 16px; background: transparent;")
        header_layout.addWidget(self.status_icon)
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("JARVIS CORE")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white; border: none; background: transparent;")
        
        lbl_sub = QLabel("Advanced System Assistant")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet("color: #94a3b8; border: none; background: transparent;")
        
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        header_layout.addLayout(title_vbox)
        
        header_layout.addStretch()
        
        # Actions
        self.btn_voice = QPushButton("🔊" if self.voice_enabled else "🔇")
        self.btn_voice.setFixedSize(36, 36)
        self.btn_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voice.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1);
                border: none;
                border-radius: 18px;
                font-size: 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); }
        """)
        self.btn_voice.clicked.connect(self.toggle_voice)
        header_layout.addWidget(self.btn_voice)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 18px;
            }
            QPushButton:hover { background: #ef4444; color: white; }
        """)
        self.btn_close.clicked.connect(self.close)
        header_layout.addWidget(self.btn_close)
        
        box_layout.addWidget(self.header)
        
        # --- CHAT AREA ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(10)
        
        self.scroll.setWidget(self.chat_container)
        box_layout.addWidget(self.scroll, 1)
        
        # --- INPUT AREA ---
        self.footer = QFrame()
        self.footer.setFixedHeight(100)
        self.footer.setStyleSheet("""
            QFrame {
                background: white;
                border-bottom-left-radius: 28px;
                border-bottom-right-radius: 28px;
                border-top: 1px solid #f1f5f9;
            }
        """)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(20, 15, 20, 15)
        footer_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Jarvis'e bir talimat verin...")
        self.input_field.setFixedHeight(50)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 25px;
                padding: 0 20px;
                font-size: 13px;
                color: #1e293b;
            }
            QLineEdit:focus { border-color: #3b82f6; background-color: white; }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        footer_layout.addWidget(self.input_field)
        
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(50, 50)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn_send.clicked.connect(self.send_message)
        footer_layout.addWidget(self.btn_send)
        
        box_layout.addWidget(self.footer)
        
        # Initial Message
        self.add_message("<b>Sistem Çevrimiçi.</b><br>Size nasıl yardımcı olabilirim?", True)

    @pyqtSlot(str, bool)
    def add_message(self, text, is_ai=True):
        msg = JarvisMessage(text, is_ai)
        self.chat_layout.addWidget(msg)
        QTimer.singleShot(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def send_message(self):
        text = self.input_field.text().strip()
        if not text: return
        self.add_message(text, False)
        self.input_field.clear()
        self.process_query(text)

    def process_query(self, query):
        if self.ai_service is None:
            self.delayed_init()
            if self.ai_service is None:
                self.add_message("Hata: AI Servisi başlatılamadı.", True)
                return

        if not self.ai_service.is_configured:
            api_key = self.db.get_setting("gemini_api_key", "")
            if api_key: self.ai_service.setup_gemini(api_key)
            if not self.ai_service.is_configured:
                self.add_message("Gemini API anahtarı eksik. Ayarlardan yapılandırın.", True)
                return
        
        self.loading = QLabel("Düşünüyorum...")
        self.loading.setStyleSheet("color: #64748b; font-style: italic; margin-left: 20px;")
        self.chat_layout.addWidget(self.loading)
        
        self.query_thread = AIQueryThread(self.ai_service, query)
        self.query_thread.finished.connect(self.on_ai_response)
        self.query_thread.start()

    def on_ai_response(self, result):
        if hasattr(self, 'loading'): self.loading.deleteLater()
        if result['success']:
            self.add_message(result['answer'], True)
            self.data_changed.emit()
            if self.voice_enabled: self.speak(result['answer'])
        else:
            self.add_message(f"<span style='color:red'>Hata: {result['answer']}</span>", True)

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        self.db.set_setting("jarvis_voice_enabled", "1" if self.voice_enabled else "0")
        self.btn_voice.setText("🔊" if self.voice_enabled else "🔇")

    def speak(self, text):
        if not self.tts_engine: return
        clean_text = text.replace("<br>", " ").replace("<b>", "").replace("</b>", "")
        threading.Thread(target=lambda: (self.tts_engine.say(clean_text), self.tts_engine.runAndWait()), daemon=True).start()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
