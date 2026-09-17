# -*- coding: utf-8 -*-

"""
AI Assistant Page - Offline Mode
Modern chat interface for local knowledge base search.
"""

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.utils.ai_service import AIService
from src.utils.theme_colors import theme_qss


class AIQueryThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, ai_service, question, context=None):
        super().__init__()
        self.ai_service = ai_service
        self.question = question
        self.context = context
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


class AIAssistantPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.ai_service = AIService(db)
        self.query_thread = None
        self.faq = {
            "stok": "Stok Ekleme:\n1. Stok Yonetimi sayfasina gidin\n2. Yeni parca ekleyin\n3. Bilgileri doldurun\n4. Kaydedin",
            "musteri": "Musteri Kaydi:\n1. Musteri Islemleri sayfasina gidin\n2. Yeni musteri ekleyin\n3. Ad, telefon ve e-posta bilgilerini girin\n4. Kaydedin",
            "servis": "Servis Takibi:\n1. Servis Operasyon Panosu'nu acin\n2. Kartlari durumlara gore takip edin\n3. Kart detayina tiklayin\n4. Islemleri kaydedin",
            "randevu": "Randevu Olusturma:\n1. Randevu sayfasina gidin\n2. Yeni randevu olusturun\n3. Musteri, tarih ve saat secin\n4. Kaydedin",
            "rapor": "Rapor Alma:\n1. Raporlar sayfasina gidin\n2. Tarih araligini secin\n3. Rapor turunu belirleyin\n4. PDF veya Excel alin",
            "yedek": "Yedekleme:\n1. Ayarlar sayfasina gidin\n2. Yedekle butonuna basin\n3. Yedek dosyasi olusturulur\n4. backups klasorunde saklanir",
        }
        self.setup_ui()
        self.apply_theme_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 50, 40, 50)
        layout.setSpacing(30)

        header = QHBoxLayout()
        title_vbox = QVBoxLayout()

        self.title_label = QLabel("Bilgi Asistanı")
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.subtitle_label = QLabel("YEREL BİLGİ BANKASINDA ARAMA YAPIN")
        self.subtitle_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        title_vbox.addWidget(self.title_label)
        title_vbox.addWidget(self.subtitle_label)
        header.addLayout(title_vbox)

        self.lbl_ai_status = QLabel()
        header.addWidget(self.lbl_ai_status)
        header.addStretch()
        layout.addLayout(header)

        self.welcome_frame = QFrame()
        self.welcome_frame.setObjectName("Card")
        welcome_layout = QVBoxLayout(self.welcome_frame)

        self.welcome_title = QLabel("Nasıl yardımcı olabilirim?")
        self.welcome_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.welcome_text = QLabel(
            "Aşağıdaki önerilen sorulardan birini seçebilir veya kendi sorunuzu yazabilirsiniz."
        )
        self.welcome_text.setFont(QFont("Segoe UI", 11))
        self.welcome_text.setWordWrap(True)

        welcome_layout.addWidget(self.welcome_title)
        welcome_layout.addWidget(self.welcome_text)
        layout.addWidget(self.welcome_frame)

        self.suggestions_label = QLabel("ÖNERİLEN SORULAR")
        self.suggestions_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.suggestions_label)

        suggestions_grid = QGridLayout()
        suggestions_grid.setSpacing(10)
        self.suggestion_buttons = []
        suggested_questions = [
            ("Stok nasıl eklenir", "stok"),
            ("Müşteri kaydı nasıl yapılır", "musteri"),
            ("Servis takibi nasıl çalışır", "servis"),
            ("Randevu nasıl oluşturulur", "randevu"),
            ("Rapor nasıl alınır", "rapor"),
            ("Yedekleme nasıl yapılır", "yedek"),
        ]
        for i, (question, key) in enumerate(suggested_questions):
            btn = QPushButton(question)
            btn.setObjectName("SuggestionChip")
            btn.setFont(QFont("Segoe UI", 10))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.show_answer(k))
            suggestions_grid.addWidget(btn, i // 2, i % 2)
            self.suggestion_buttons.append(btn)
        layout.addLayout(suggestions_grid)

        self.search_label = QLabel("VEYA KENDİ SORUNUZU YAZIN")
        self.search_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.search_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Sorunuzu buraya yazın...")
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.setFixedHeight(50)
        self.search_input.returnPressed.connect(self.search_question)

        self.btn_search = QPushButton("Ara")
        self.btn_search.setObjectName("Primary")
        self.btn_search.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_search.setFixedHeight(50)
        self.btn_search.setFixedWidth(120)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self.search_question)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)

        self.answer_label = QLabel("CEVAP")
        self.answer_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.answer_label)

        self.answer_area = QTextEdit()
        self.answer_area.setReadOnly(True)
        self.answer_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.answer_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.answer_area.setPlaceholderText("Bir soru seçin veya yazın, cevabı burada göreceksiniz...")
        layout.addWidget(self.answer_area)
        layout.addStretch()

    def apply_theme_styles(self):
        self.setStyleSheet(theme_qss("background: @window;"))
        self.title_label.setStyleSheet(theme_qss("letter-spacing: -0.5px; color: @text;"))
        self.subtitle_label.setStyleSheet(theme_qss("color: @text_muted; letter-spacing: 2px;"))
        self.welcome_frame.setStyleSheet(
            theme_qss(
                """
                #Card {
                    background: @surface;
                    border: 2px solid @accent;
                    border-radius: 16px;
                    padding: 30px;
                }
                """
            )
        )
        self.welcome_title.setStyleSheet(theme_qss("color: @text;"))
        self.welcome_text.setStyleSheet(theme_qss("color: @text_muted;"))
        self.suggestions_label.setStyleSheet(theme_qss("color: @text_muted; letter-spacing: 1px;"))
        for btn in self.suggestion_buttons:
            btn.setStyleSheet(
                theme_qss(
                    """
                    QPushButton#SuggestionChip {
                        background: @surface;
                        border: 2px solid @border;
                        border-radius: 20px;
                        padding: 12px 20px;
                        text-align: left;
                        color: @text;
                    }
                    QPushButton#SuggestionChip:hover {
                        background: @surface_alt;
                        border-color: @accent;
                        color: @accent;
                    }
                    """
                )
            )
        self.search_label.setStyleSheet(theme_qss("color: @text_muted; letter-spacing: 1px;"))
        self.search_input.setStyleSheet(
            theme_qss(
                """
                QLineEdit {
                    border: 2px solid @border;
                    border-radius: 25px;
                    padding: 0 20px;
                    background: @surface;
                    color: @text;
                }
                QLineEdit::placeholder {
                    color: @text_muted;
                }
                QLineEdit:focus {
                    border-color: @accent;
                }
                """
            )
        )
        self.btn_search.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background: @accent;
                    color: @selection_text;
                    border: none;
                    border-radius: 25px;
                    font-weight: 700;
                    padding: 0 18px;
                }
                QPushButton:hover {
                    background: @accent_hover;
                }
                """
            )
        )
        self.answer_label.setStyleSheet(theme_qss("color: @text_muted; letter-spacing: 1px;"))
        self.answer_area.setStyleSheet(
            theme_qss(
                """
                QTextEdit {
                    background: @surface;
                    border: 2px solid @border;
                    border-radius: 12px;
                    padding: 20px;
                    color: @text;
                    line-height: 1.6;
                }
                """
            )
        )
        self.update_connection_status()

    def refresh_theme(self):
        self.apply_theme_styles()

    def show_answer(self, key):
        if key in self.faq:
            self.answer_area.setPlainText(self.faq[key])
        else:
            self.answer_area.setPlainText("Bu konu hakkinda bilgi bulunamadi.")

    def search_question(self):
        question = self.search_input.text().strip()
        if not question:
            return

        question_lower = question.lower()
        for key, answer in self.faq.items():
            if key in question_lower:
                self.answer_area.setPlainText(f"Hizli Cevap:\n\n{answer}")
                return

        self.query_ai(question)

    def query_ai(self, question, context=None):
        self.answer_area.setPlainText("Bilgi bankasi taraniyor...\n\nLutfen bekleyin...")
        self.search_input.setEnabled(False)
        self.query_thread = AIQueryThread(self.ai_service, question, context)
        self.query_thread.finished.connect(self.on_ai_response)
        self.query_thread.start()

    def on_ai_response(self, result):
        self.search_input.setEnabled(True)
        if result.get("success"):
            self.answer_area.setPlainText(f"Asistan:\n\n{result.get('answer', '')}")
        else:
            self.answer_area.setPlainText(f"Hata:\n\n{result.get('error', 'Bilinmeyen hata')}")

    def update_connection_status(self):
        if hasattr(self, "ai_service"):
            api_key = self.db.get_setting("gemini_api_key", "")
            if api_key:
                self.ai_service.setup_gemini(api_key)
                if self.ai_service.is_configured:
                    self.lbl_ai_status.setText("Jarvis Cevrimici")
                    self.lbl_ai_status.setStyleSheet(
                        theme_qss(
                            "color: @success; padding: 8px 16px; background: @surface_alt; border-radius: 20px; border: 1px solid @success;"
                        )
                    )
                    return

        self.lbl_ai_status.setText("Cevrimdisi Mod (Yerel)")
        self.lbl_ai_status.setStyleSheet(
            theme_qss(
                "color: @text_muted; padding: 8px 16px; background: @surface_alt; border-radius: 20px; border: 1px solid @border;"
            )
        )
