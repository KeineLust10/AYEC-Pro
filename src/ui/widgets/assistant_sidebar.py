# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QGraphicsDropShadowEffect, QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QLinearGradient, QBrush
import threading
import os
import re
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from src.ui.widgets.modern_dialog import ModernDialog
try:
    from src.utils.ai_service import AIService
except Exception:
    AIService = None

class AIQueryThread(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, ai_service, question):
        super().__init__()
        self.ai_service = ai_service
        self.question = question
        self.db_name = getattr(getattr(ai_service, "db", None), "_db_name", None) if ai_service else None
        self.api_keys = list(getattr(ai_service, "api_keys", []) or []) if ai_service else []
        self.model_id = getattr(ai_service, "model_id", "gemini-3.6-flash") if ai_service else "gemini-3.6-flash"
        
    def run(self):
        db = None
        service = self.ai_service
        try:
            if self.db_name and AIService is not None:
                from src.database import Database
                db = Database(self.db_name, init_mode="connection_only")
                service = AIService(db, model_name=self.model_id)
                if self.api_keys:
                    service.api_keys = self.api_keys
                    service._setup_client()
            result = service.get_smart_response(self.question) if service else {"success": False, "answer": "AI service unavailable"}
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass
        self.finished.emit(result)

class AssistantMessage(QFrame):
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
        self.label.setStyleSheet(theme_qss("border: none; background: transparent; font-size: 13px; line-height: 1.4;"))
        
        if is_ai:
            container.setStyleSheet(theme_qss("""
                QFrame {
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 18px;
                    border-bottom-left-radius: 4px;
                }
                QLabel { color: @text; }
            """))
            self.layout.addWidget(container)
            self.layout.addStretch()
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0,0,0,15))
            shadow.setOffset(0, 2)
            container.setGraphicsEffect(shadow)
        else:
            container.setStyleSheet(theme_qss("""
                QFrame {
                    background-color: @accent;
                    border-radius: 18px;
                    border-bottom-right-radius: 4px;
                }
                QLabel { color: @selection_text; }
            """))
            self.layout.addWidget(container)
            self.layout.setContentsMargins(40, 5, 0, 5) # Align Right
        
        c_layout.addWidget(self.label)

class AssistantSidebarDialog(ModernDialog):
    closed = pyqtSignal()
    data_changed = pyqtSignal()
    
    def __init__(self, db, parent=None, ai_service=None):
        super().__init__(title="AYEC Pro", parent=parent, width=450, height=700)
        self.db = db
        self.ai_service = ai_service
        self.tts_engine = None
        self.query_thread = None
        self.set_footer_visible(False)
        self.setFixedSize(450, 700)
        self.voice_enabled = self.db.get_setting("asistan_voice_enabled", "1") == "1"
        self.setup_ui()
        
    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Main Container with Glass Effect ---
        self.container = QFrame()
        self.container.setObjectName("mainContainer")
        self.container.setStyleSheet(theme_qss("""
            QFrame#mainContainer {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 20px;
            }
        """))
        
        # Shadow for pop-up feel
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        layout.addWidget(self.container)
        
        # --- Header ---
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: 1px solid @surface_alt;
            }
        """))
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        # Title
        title = QLabel("AYEC Pro")
        title.setStyleSheet(theme_qss("""
            font-family: 'Segoe UI', sans-serif, 'Segoe UI Emoji';
            font-size: 18px;
            font-weight: 700;
            color: @text;
        """))
        
        # Close Button
        close_btn = QPushButton("")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                border: none;
                border-radius: 16px;
                color: @text_muted;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: @surface_alt;
                color: @danger;
            }
        """))
        
        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(close_btn)
        
        container_layout.addWidget(header)
        
        # --- Chat Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("AssistantChatScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(theme_qss("""
            QScrollArea#AssistantChatScroll { border: none; background: transparent; }
            QScrollArea#AssistantChatScroll QWidget { background: transparent; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: @border;
                border-radius: 3px;
            }
        """))
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch()  # Messages start from bottom or stack upwards
        
        self.scroll_area.setWidget(self.scroll_content)
        container_layout.addWidget(self.scroll_area)
        
        # --- Input Area ---
        input_frame = QFrame()
        input_frame.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-top: 1px solid @surface_alt;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """))
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 15, 20, 15)
        input_layout.setSpacing(10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Bir şeyler sorun...")
        self.input_field.setFixedHeight(45)
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setStyleSheet(theme_qss("""
            QLineEdit {
                border: 2px solid @border;
                border-radius: 12px;
                padding: 0 15px;
                font-size: 14px;
                color: @text;
                background-color: @surface_alt;
            }
            QLineEdit:focus {
                border-color: @accent;
                background-color: @surface;
            }
        """))
        
        send_btn = QPushButton("")
        send_btn.setFixedSize(45, 45)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self.send_message)
        send_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                border: none;
                border-radius: 12px;
                color: @selection_text;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)
        
        container_layout.addWidget(input_frame)
        
        # Initial greeting
        self.add_message("Merhaba! Ben AYEC Pro. Size nasıl yardımcı olabilirim", is_ai=True)

    def speak(self, text):
        """Metni sesli olarak okur (Türkçe)."""
        if not text: return
        try:
            if not self.tts_engine:
                try:
                    import pyttsx3
                    from src.utils.asistan_motoru import _select_turkish_pyttsx3_voice
                except Exception:
                    pyttsx3 = None
                    _select_turkish_pyttsx3_voice = None
                if not pyttsx3:
                    return
                self.tts_engine = pyttsx3.init()
                # Türkçe ses seçimi (merkezi fonksiyon)
                if _select_turkish_pyttsx3_voice:
                    _select_turkish_pyttsx3_voice(self.tts_engine)

            if self.tts_engine:
                # Run in separate thread to avoid freezing UI
                threading.Thread(target=lambda: self._tts_run(text), daemon=True).start()
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def _tts_run(self, text):
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception:
            pass

    def add_message(self, text, is_ai=True):
        msg = AssistantMessage(text, is_ai=is_ai)
        # Add before the stretch item
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, msg)
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
        
        # --- VOICE FEEDBACK ---
        if is_ai and self.voice_enabled and text:
            # Strip markdown for cleaner TTS
            clean_text = re.sub(r'[*_#`]', '', text)
            self.speak(clean_text)

    def scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.add_message(text, is_ai=False)
        self.input_field.clear()
        
        # Simulate AI thinking or process
        QTimer.singleShot(500, lambda: self.process_query(text))
        
    def process_query(self, text):
        normalized = re.sub(r"\s+", " ", str(text or "").strip().casefold())
        builtin_actions = (
            (("finans ozeti", "finansal ozet", "mali ozet", "kasa ozeti"),
             "accounting_summary", "Finansal ozeti aciyorum."),
            (("stok ozeti", "stok durumu", "stok listesi"),
             "stock_summary", "Stok ozetini aciyorum."),
            (("randevular", "randevu listesi"),
             "check_appointments", "Randevulari aciyorum."),
        )
        for phrases, action, reply in builtin_actions:
            if any(phrase in normalized for phrase in phrases):
                manager = None
                window = self.parentWidget()
                if window is not None:
                    ensure_manager = getattr(window, "_ensure_assistant_manager", None)
                    manager = ensure_manager() if callable(ensure_manager) else getattr(window, "assistant_manager", None)
                if manager is not None:
                    try:
                        manager.aksiyon_merkezi(action, "")
                        self.add_message(reply, is_ai=True)
                        return
                    except Exception as exc:
                        logger.warning("Assistant action failed: %s", exc)
                break

        # Placeholder for actual AI processing
        # Ensure we have ai_service
        if not self.ai_service:
            try:
                self.ai_service = AIService()
            except Exception:
                pass
        
        if self.ai_service:
             # Use thread for processing if needed, for now simple placeholder response
             # self.query_thread = AIQueryThread(self.ai_service, text)
             # ...
             pass
        
        # Fallback simple response for now to prove UI works
        self.add_message("Bu özellik şu anda geliştirme aşamasında.", is_ai=True)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
