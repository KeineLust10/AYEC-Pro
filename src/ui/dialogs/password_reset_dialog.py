import hashlib

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.message_helper import show_error, show_info, show_warning
from src.utils.theme_colors import theme_qss
from src.utils.password_security import hash_password, validate_new_password


class PasswordResetDialog(ModernDialog):
    def __init__(self, db, parent=None):
        super().__init__(title="Guvenli Sifre Sifirlama", parent=parent, width=400, height=350)
        self.db = db
        self.current_username = None
        self.secret_answer_hash = None
        self.attempts = 0
        self.max_attempts = 3
        self.set_footer_visible(False)
        self.setStyleSheet(
            theme_qss(
                """
                QDialog { background-color: @surface; }
                QLineEdit {
                    padding: 10px; border: 1px solid @border; border-radius: 6px; font-size: 14px;
                }
                QLineEdit:focus { border: 1px solid @accent; }
                QLabel { color: @text; font-size: 14px; }
                QPushButton {
                    background-color: @accent; color: @selection_text; border: none; border-radius: 6px;
                    padding: 10px; font-weight: bold; font-size: 14px;
                }
                QPushButton:hover { background-color: @accent_hover; }
                QPushButton:disabled { background-color: @surface_alt; }
                """
            )
        )

        self.layout = self.content_layout
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(15)
        self.init_ui()

    def init_ui(self):
        lbl_head = QLabel("Sifremi Unuttum")
        lbl_head.setStyleSheet(theme_qss("font-size: 20px; font-weight: 800; color: @text;"))
        self.layout.addWidget(lbl_head, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stack = QVBoxLayout()
        self.layout.addLayout(self.stack)
        self.create_step_1()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def create_step_1(self):
        self.clear_layout(self.stack)
        lbl = QLabel("Lutfen kullanici adinizi giriniz:")
        self.inp_user = QLineEdit()
        self.inp_user.setPlaceholderText("Kullanici Adi")
        self.inp_user.setFocus()

        btn = QPushButton("Devam Et")
        btn.clicked.connect(self.verify_user)

        self.stack.addWidget(lbl)
        self.stack.addWidget(self.inp_user)
        self.stack.addWidget(btn)
        self.stack.addStretch()

    def verify_user(self):
        username = self.inp_user.text().strip()
        if not username:
            return

        try:
            self.db.cursor.execute(
                "SELECT secret_question, secret_answer FROM users WHERE username=?",
                (username,),
            )
            row = self.db.cursor.fetchone()
            if row:
                question, answer = row[0], row[1]
                if not question or not answer:
                    show_warning(
                        self,
                        "Hata",
                        "Bu hesap için güvenlik sorusu tanımlanmamış.\nLütfen yönetici ile iletişime geçin.",
                    )
                    return
                self.current_username = username
                self.current_answer = answer
                self.create_step_2(question)
            else:
                show_warning(self, "Hata", "Kullanıcı bulunamadı.")
        except Exception as exc:
            show_error(self, "Sistem Hatası", f"Veritabanı hatası: {exc}")

    def create_step_2(self, question):
        self.clear_layout(self.stack)

        lbl_info = QLabel(f"Kullanici: <b>{self.current_username}</b>")
        lbl_q = QLabel("SISTEM GUVENLIK SORUSU:")
        lbl_q.setStyleSheet(theme_qss("font-size: 11px; color: @text_muted; font-weight: bold;"))

        lbl_question = QLabel(question)
        lbl_question.setStyleSheet(
            theme_qss(
                "background: @surface_alt; padding: 15px; border-radius: 8px; font-weight: bold; color: @text; border: 1px solid @border;"
            )
        )
        lbl_question.setWordWrap(True)

        self.inp_ans = QLineEdit()
        self.inp_ans.setPlaceholderText("Cevabiniz...")
        self.inp_ans.setFocus()

        btn = QPushButton("Dogrula")
        btn.clicked.connect(self.verify_answer)

        self.lbl_attempts = QLabel(f"Kalan Hakkiniz: {self.max_attempts}")
        self.lbl_attempts.setStyleSheet(theme_qss("color: @danger; font-size: 12px;"))

        self.stack.addWidget(lbl_info)
        self.stack.addSpacing(10)
        self.stack.addWidget(lbl_q)
        self.stack.addWidget(lbl_question)
        self.stack.addWidget(self.inp_ans)
        self.stack.addWidget(self.lbl_attempts)
        self.stack.addWidget(btn)
        self.stack.addStretch()

    def verify_answer(self):
        answer = self.inp_ans.text().strip()
        stored = str(self.current_answer or "").strip()
        normalized = answer.lower()
        hashed = hashlib.sha256(normalized.encode()).hexdigest()
        is_hash = len(stored) == 64 and all(c in "0123456789abcdef" for c in stored.lower())

        if (is_hash and hashed == stored.lower()) or (not is_hash and normalized == stored.lower()):
            self.create_step_3()
            return

        self.attempts += 1
        remaining = self.max_attempts - self.attempts
        self.lbl_attempts.setText(f"Kalan Hakkiniz: {remaining}")
        if remaining <= 0:
            show_error(
                self,
                "Engellendi",
                "Çok fazla hatalı giriş yaptınız.\nPanel güvenlik nedeniyle kilitlendi.",
            )
            self.reject()
            return
        show_warning(self, "Hata", "Yanlış cevap.")

    def create_step_3(self):
        self.clear_layout(self.stack)

        lbl = QLabel("Kimlik dogrulandi. Yeni sifrenizi belirleyin.")
        lbl.setStyleSheet(theme_qss("color: @success; font-weight: bold;"))

        self.inp_p1 = QLineEdit()
        self.inp_p1.setPlaceholderText("Yeni Sifre")
        self.inp_p1.setEchoMode(QLineEdit.EchoMode.Password)

        self.inp_p2 = QLineEdit()
        self.inp_p2.setPlaceholderText("Yeni Sifre (Tekrar)")
        self.inp_p2.setEchoMode(QLineEdit.EchoMode.Password)

        btn = QPushButton("Sifreyi Guncelle")
        btn.setStyleSheet(
            theme_qss(
                "background-color: @success; color: @selection_text; font-weight: bold; padding: 12px; border-radius: 6px;"
            )
        )
        btn.clicked.connect(self.reset_password)

        self.stack.addWidget(lbl)
        self.stack.addWidget(self.inp_p1)
        self.stack.addWidget(self.inp_p2)
        self.stack.addWidget(btn)
        self.stack.addStretch()

    def reset_password(self):
        p1 = self.inp_p1.text()
        p2 = self.inp_p2.text()

        if not p1:
            show_warning(self, "Hata", "Şifre boş olamaz.")
            return
        if p1 != p2:
            show_warning(self, "Hata", "Şifreler eşleşmiyor.")
            return

        password_error = validate_new_password(p1)
        if password_error:
            show_warning(self, "Password", password_error)
            return

        try:
            hashed_pw = hash_password(p1)
            self.db.cursor.execute(
                "UPDATE users SET password=?, must_change_password=0, "
                "password_updated_at=datetime('now') WHERE username=?",
                (hashed_pw, self.current_username),
            )
            self.db.conn.commit()
            show_info(
                self,
                "Başarılı",
                "Şifreniz başarıyla güncellendi.\nYeni şifrenizle giriş yapabilirsiniz.",
            )
            self.accept()
        except Exception as exc:
            self.db.conn.rollback()
            show_error(self, "Hata", f"Güncelleme hatası: {exc}")
