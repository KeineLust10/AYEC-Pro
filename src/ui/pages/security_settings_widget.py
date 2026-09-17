# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QGroupBox, QFrame, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon, QAction
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.input_validator import InputValidator
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.dialogs.security_confirm_dialog import SecurityConfirmDialog
from src.utils.theme_colors import theme_qss
from src.utils.password_security import hash_password, validate_new_password



class SecuritySettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """
    Yeniden Tasarlanmış Güvenlik Sekmesi:
    - Toggle Switchli Modern Tasarım
    - Uygulama Giriş Güvenliği
    - Teknisyen Paneli Koruması
    - Yönetici Şifresi ve Kurtarma (Gizli Soru)
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.validator = InputValidator()
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel("🛡️")
        icon_lbl.setStyleSheet("font-size: 32px;")
        title = QLabel("Güvenlik ve Erişim Kontrolü")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        header.addWidget(icon_lbl)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        info_lbl = QLabel("Uygulamanızın ve kritik bölümlerin erişim güvenliğini buradan yönetebilirsiniz.")
        info_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11pt; margin-bottom: 10px;"))
        layout.addWidget(info_lbl)

        # 1. App Lock Card
        self.card1 = self.create_toggle_card(
            "Uygulama Giriş Güvenliği", 
            "Program açılışında şifre sorulsun.",
            "app_lock_container"
        )
        layout.addWidget(self.card1)

        # 2. Tech Panel Card
        self.card2 = self.create_toggle_card(
            "Teknisyen Paneli Koruması", 
            "Teknisyen paneline girişte özel şifre istensin.",
            "tech_lock_container"
        )
        layout.addWidget(self.card2)

        # 2.5 Auto Login Card
        self.card_auto_login = self.create_auto_login_card()
        layout.addWidget(self.card_auto_login)

        
        # 3. Admin & Recovery Card
        self.card3 = QFrame()
        self.card3.setStyleSheet(theme_qss("background-color: @surface; border: 1px solid @border; border-radius: 8px;"))
        l3 = QVBoxLayout(self.card3)
        l3.setContentsMargins(20, 20, 20, 20)
        l3.setSpacing(15)
        
        l3.addWidget(self.make_title("🔑 Yönetici Şifresi ve Kurtarma", "Kritik işlemler ve şifre sıfırlama için."))
        
        # Admin Pass
        h_admin = QHBoxLayout()
        h_admin.addWidget(QLabel("Yönetici Şifresi:"))
        self.inp_admin_pass = QLineEdit()
        self.inp_admin_pass.setPlaceholderText("Yeni admin şifresi belirle...")
        self.inp_admin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_admin_pass.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; background:@surface_alt; color:@text;"))
        h_admin.addWidget(self.inp_admin_pass)
        l3.addLayout(h_admin)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(theme_qss("background-color: @border;"))
        l3.addWidget(line)
        
        # Recovery Section
        rec_lbl = QLabel("❓ Şifre Kurtarma (Gizli Soru)")
        rec_lbl.setStyleSheet(theme_qss("font-weight: bold; color: @text;"))
        l3.addWidget(rec_lbl)
        
        rec_info = QLabel("Şifrenizi unutursanız bu soruya vereceğiniz yanıtla sıfırlayabilirsiniz.")
        rec_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 9pt; font-style: italic;"))
        l3.addWidget(rec_info)
        
        grid_rec = QVBoxLayout()
        
        self.cmb_question = QComboBox()
        self.cmb_question.addItems([
            "Özel Soru Belirle...",
            "İlk evcil hayvanınızın adı nedir",
            "İlkokul öğretmeninizin adı nedir",
            "Doğduğunuz şehir neresi",
            "Annenizin kızlık soyadı nedir",
            "En sevdiğiniz yemek nedir"
        ])
        self.cmb_question.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; background:@surface_alt; color:@text;"))
        self.cmb_question.currentIndexChanged.connect(self.on_question_change)
        grid_rec.addWidget(self.cmb_question)
        
        self.inp_custom_question = QLineEdit()
        self.inp_custom_question.setPlaceholderText("Kendi gizli sorunuzu yazın...")
        self.inp_custom_question.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; background:@surface_alt; color:@text;"))
        self.inp_custom_question.hide()
        grid_rec.addWidget(self.inp_custom_question)
        
        self.inp_answer = QLineEdit()
        self.inp_answer.setPlaceholderText("Yanıtınız...")
        self.inp_answer.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_answer.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; background:@surface_alt; color:@text;"))
        grid_rec.addWidget(self.inp_answer)
        
        l3.addLayout(grid_rec)
        
        layout.addWidget(self.card3)
        
        # Save Button
        btn_save = QPushButton("AYARLARI KAYDET")
        btn_save.setFixedHeight(50)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton { background-color: @success; color: @selection_text; border-radius: 8px; font-weight: bold; font-size: 12pt; }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)
        
        layout.addStretch()

    def _wire_ui_signals(self):
        self.toggle_auto_login.toggled.connect(self._on_ui_widget_changed)

    def create_toggle_card(self, title, subtitle, container_id):
        card = QFrame()
        card.setStyleSheet(theme_qss("background-color: @surface; border: 1px solid @border; border-radius: 8px;"))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header Row
        h_row = QHBoxLayout()
        
        titles_lay = QVBoxLayout()
        titles_lay.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t.setStyleSheet(theme_qss("color: @text; border: none;"))
        s = QLabel(subtitle)
        s.setStyleSheet(theme_qss("color: @text_muted; font-size: 9pt; border: none;"))
        titles_lay.addWidget(t)
        titles_lay.addWidget(s)
        
        h_row.addLayout(titles_lay)
        h_row.addStretch()
        
        # Toggle
        toggle = AnimatedToggle()
        toggle.setFixedSize(60, 40)
        setattr(self, f"toggle_{container_id}", toggle) # Save reference
        toggle.stateChanged.connect(lambda s: self.toggle_container(s, container_id))
        h_row.addWidget(toggle)
        
        layout.addLayout(h_row)
        
        # Content Container
        container = QWidget()
        container.setObjectName(container_id)
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 15, 0, 0)
        
        lbl_pass = QLabel("Giriş Şifresi:")
        inp_pass = QLineEdit()
        inp_pass.setPlaceholderText("Yeni şifre belirle...")
        inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        inp_pass.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; background:@surface_alt; color:@text;"))
        
        # Reference Save
        setattr(self, f"inp_{container_id}", inp_pass)
        
        c_layout.addWidget(lbl_pass)
        c_layout.addWidget(inp_pass)
        
        layout.addWidget(container)
        
        return card

    def create_auto_login_card(self):
        """Otomatik giriş toggle kartı"""
        card = QFrame()
        card.setStyleSheet(theme_qss("background-color: @surface; border: 1px solid @border; border-radius: 8px;"))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        h_row = QHBoxLayout()
        
        titles_lay = QVBoxLayout()
        titles_lay.setSpacing(2)
        t = QLabel("Otomatik Giriş")
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t.setStyleSheet(theme_qss("color: @text; border: none;"))
        s = QLabel("Program açılışında kullanıcı adı ve şifre sormadan otomatik giriş yap.")
        s.setStyleSheet(theme_qss("color: @text_muted; font-size: 9pt; border: none;"))
        titles_lay.addWidget(t)
        titles_lay.addWidget(s)
        
        h_row.addLayout(titles_lay)
        h_row.addStretch()
        
        self.toggle_auto_login = AnimatedToggle()
        self.toggle_auto_login.setFixedSize(60, 40)
        # We don't connect directly to stateChanged for logic yet to avoid double trigger on load
        self.toggle_auto_login.clicked.connect(self.on_auto_login_clicked)
        h_row.addWidget(self.toggle_auto_login)
        
        layout.addLayout(h_row)
        return card

    def on_auto_login_clicked(self):
        """Otomatik giriş toggle edildiğinde şifre sor"""
        current_state = self.toggle_auto_login.isChecked()
        
        # Dialoğu aç
        dialog = SecurityConfirmDialog(self.db, 
                                     title="Güvenlik Onayı", 
                                     message=f"Otomatik girişi {'aktifleştirmek' if current_state else 'devre dışı bırakmak'} için yönetici şifresini giriniz.",
                                     parent=self.window())
        
        if dialog.exec() == SecurityConfirmDialog.Accepted:
            # Şifre doğru, işlemi gerçekleştir
            self.set_auto_login_db(current_state)
            show_success(self.window(), f"Otomatik giriş {'aktif edildi' if current_state else 'devre dışı bırakıldı'}.")
        else:
            # İptal edildi veya şifre yanlış, toggle'ı geri al
            self.toggle_auto_login.blockSignals(True)
            self.toggle_auto_login.setChecked(not current_state)
            self.toggle_auto_login.blockSignals(False)

    def set_auto_login_db(self, enabled):
        """Veritabanında otomatik giriş ayarını güncelle (Genellikle admin kullanıcısı için)"""
        try:
            # Basitlik için 'admin' kullanıcısının auto_login ayarını güncelliyoruz
            self.db.cursor.execute("UPDATE users SET auto_login=? WHERE username='admin'", (1 if enabled else 0,))
            self.db.conn.commit()
            
            # Eğer kapatılıyorsa token'ı da silebiliriz (opsiyonel ama güvenli)
            if not enabled:
                from src.utils.auth_manager import AuthManager
                auth = AuthManager(self.db)
                auth.clear_token()
        except Exception as e:
            import logging
            logging.getLogger("AYECProLogger").error("Auto-login update error: %s", e)


    def make_title(self, text, sub):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(2)
        t = QLabel(text)
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t.setStyleSheet(theme_qss("color: @text; border: none;"))
        s = QLabel(sub)
        s.setStyleSheet(theme_qss("color: @text_muted; font-size: 9pt; border: none;"))
        l.addWidget(t)
        l.addWidget(s)
        return w

    def toggle_container(self, state, container_id):
        # We can enable/disable input or hide it
        # Getting the input widget via stored reference
        inp = getattr(self, f"inp_{container_id}", None)
        if inp:
            enabled = bool(state)
            inp.setEnabled(enabled)
            if not enabled:
                inp.clear() # Optional: clear when disabled

    def on_question_change(self, index):
        if index == 0:
            self.inp_custom_question.show()
            self.inp_custom_question.setFocus()
        else:
            self.inp_custom_question.hide()

    def load_data(self):
        # App Lock
        is_app_active = self.db.get_setting("app_lock_active", "0") == "1"
        self.toggle_app_lock_container.setChecked(is_app_active)
        self.inp_app_lock_container.setEnabled(is_app_active)

        is_tech_active = self.db.get_setting("tech_lock_active", "0") == "1"
        self.toggle_tech_lock_container.setChecked(is_tech_active)
        self.inp_tech_lock_container.setEnabled(is_tech_active)

        # Auto Login
        self.db.cursor.execute("SELECT auto_login FROM users WHERE username = 'admin'")
        row = self.db.cursor.fetchone()
        is_auto_login = row[0] == 1 if row else False
        self.toggle_auto_login.blockSignals(True)
        self.toggle_auto_login.setChecked(is_auto_login)
        self.toggle_auto_login.blockSignals(False)

        
        # Recovery
        q_text = self.db.get_setting("security_question", "")
        # Try to find in combo
        idx = self.cmb_question.findText(q_text)
        if idx > 0:
            self.cmb_question.setCurrentIndex(idx)
        elif q_text:
            self.cmb_question.setCurrentIndex(0)
            self.inp_custom_question.setText(q_text)
            self.inp_custom_question.show()
            
        # Answer is secret, don't show

    def save_settings(self):
        # App Lock
        app_active = self.toggle_app_lock_container.isChecked()
        app_pass = self.inp_app_lock_container.text().strip()
        
        current_app_pass = self.db.get_setting("app_password", "")
        
        if app_active:
            if app_pass:
                if len(app_pass) < 4:
                    show_error(self.window(), "Uygulama şifresi en az 4 karakter olmalıdır.")
                    return
                self.db.set_setting("app_password", app_pass)
            elif not current_app_pass:
                show_warning(self.window(), "Aktifleştirmek için lütfen bir Uygulama Şifresi belirleyin.")
                return
        
        self.db.set_setting("app_lock_active", "1" if app_active else "0")
        
        # Tech Lock
        tech_active = self.toggle_tech_lock_container.isChecked()
        tech_pass = self.inp_tech_lock_container.text().strip()
        current_tech_pass = self.db.get_setting("tech_password", "")
        
        if tech_active:
            if tech_pass:
                if len(tech_pass) < 4:
                    show_error(self.window(), "Teknisyen şifresi en az 4 karakter olmalıdır.")
                    return
                self.db.set_setting("tech_password", tech_pass)
            elif not current_tech_pass:
                show_warning(self.window(), "Aktifleştirmek için lütfen bir Teknisyen Şifresi belirleyin.")
                return
                
        self.db.set_setting("tech_lock_active", "1" if tech_active else "0")
        
        # Admin Pass
        admin_pass = self.inp_admin_pass.text().strip()
        if admin_pass:
             password_error = validate_new_password(admin_pass)
             if password_error:
                 show_error(self.window(), password_error)
                 return
             if len(admin_pass) < 4:
                show_error(self.window(), "Yönetici şifresi en az 4 karakter olmalıdır.")
                return
             self.db.set_setting("admin_pass", hash_password(admin_pass))
             
        # Recovery Info
        if self.cmb_question.currentIndex() == 0:
            question = self.inp_custom_question.text().strip()
        else:
            question = self.cmb_question.currentText()
            
        answer = self.inp_answer.text().strip()
        
        if question and answer:
            self.db.set_setting("security_question", question)
            # Simple hash for answer or plain if simple recovery needed 
            # Better hash it.
            import hashlib
            ans_hash = hashlib.sha256(answer.lower().encode()).hexdigest()
            self.db.set_setting("security_answer_hash", ans_hash)
            
        elif (question and not answer) or (answer and not question):
             show_warning(self.window(), "Gizli soru ve yanıtı birlikte girilmelidir.")
             return

        show_success(self.window(), "Güvenlik ayarları başarıyla güncellendi! ✅")
        
        # Clear sensitive inputs
        self.inp_app_lock_container.clear()
        self.inp_tech_lock_container.clear()
        self.inp_admin_pass.clear()
        self.inp_answer.clear()
