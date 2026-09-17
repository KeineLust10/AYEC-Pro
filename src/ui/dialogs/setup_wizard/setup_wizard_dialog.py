# -*- coding: utf-8 -*-

"""
AYEC Pro - İlk Kurulum Sihirbazı
Ultra Premium Dark Design  (v5.0.0)
Tek QGraphicsEffect kullanılmaz -> ComboBox popup sorunu yok.
"""

from PyQt6.QtWidgets import (
    QDialog as QtDialog, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame, QWidget, QScrollArea, QSizePolicy,
    QGraphicsOpacityEffect, QMessageBox,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtSlot, QPoint,
)
from PyQt6.QtGui import QColor, QPixmap, QLinearGradient, QPainter, QFont
from PyQt6.QtWidgets import QApplication
import os
from datetime import datetime

from .welcome_step      import WelcomeStep
from .company_info_step import CompanyInfoStep
from .admin_user_step   import AdminUserStep
from .basic_settings_step import BasicSettingsStep
from .completion_step   import CompletionStep
from src.ui.widgets.toast_notification import NotificationContainer
from src.utils.message_helper import show_error


# Renk Paleti — Modern Açık Tema
C = {
    "bg_deep":       "#F8FAFC",          # ana arka plan: çok açık gri
    "bg_card":       "#FFFFFF",          # içerik alanı: saf beyaz
    "bg_sidebar":    "#1E293B",          # sidebar: koyu lacivert (kontrast için)
    "sidebar_line":  "rgba(255,255,255,0.10)",
    "accent1":       "#6366F1",          # indigo-500
    "accent2":       "#4F46E5",          # indigo-600
    "accent3":       "#3B82F6",          # blue-500
    "accent_glow":   "rgba(99,102,241,0.20)",
    "success":       "#10B981",          # emerald
    "text_primary":  "#0F172A",          # içerik alanı koyu metin
    "text_secondary": "#475569",         # orta gri
    "text_muted":    "#94A3B8",          # açık gri
    "sidebar_text":  "#F1F5F9",          # sidebar birincil metin
    "sidebar_muted": "#94A3B8",          # sidebar ikincil metin
    "border":        "#E2E8F0",          # açık border
    "border_focus":  "#6366F1",
    "input_bg":      "#F8FAFC",
}

STEP_META = [
    ("01", "Hoş Geldiniz", "Başlangıç", "🏠"),
    ("02", "Şirket Bilgileri", "Kurumsal Kimlik", "🏢"),
    ("03", "Yönetici Hesabı", "Erişim Güvenliği", "🔐"),
    ("04", "Sistem Ayarları", "Yapılandırma", "⚙️"),
    ("05", "Tamamlandı", "Hazır!", "🚀"),
]


class SetupWizardDialog(QtDialog):
    """AYEC Pro Premium Setup Wizard"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_step = 0
        self.setup_data   = {}
        self._drag_pos    = None
        self._mail_workers = []          # GC koruması
        self._test_autofill_started = False
        self._init_ui()
        self._schedule_test_autofill_if_requested()

    # Setup
    def _init_ui(self):
        self.setWindowTitle("AYEC Pro - İlk Kurulum")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Tam ekran: birincil ekranın tüm alanını kullan
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)
        self.setFixedSize(screen_geo.width(), screen_geo.height())

        # Dış kap: sadece QFrame (shadow yok, ComboBox bozulur)
        self.base_frame = QFrame(self)
        self.base_frame.setObjectName("WizardBase")
        self.base_frame.setStyleSheet(f"""
            #WizardBase {{
                background-color: {C['bg_deep']};
                border-radius: 0px;
                border: none;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.base_frame)

        root = QHBoxLayout(self.base_frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_sidebar(root)
        self._build_content(root)

        # Toast
        self.toast_container = NotificationContainer(self)
        self.toast_container.resize(400, 600)
        self.toast_container.raise_()

        self._refresh_sidebar()
        self._restore_wizard_styles()

    def _restore_wizard_styles(self):
        """Restore literal wizard colors after the global theme patch has run."""
        widgets = [self, *self.findChildren(QWidget)]
        for widget in widgets:
            raw_style = getattr(widget, "_theme_raw_stylesheet", None)
            widget.setProperty("skipThemeTransform", True)
            if raw_style is not None:
                widget.setStyleSheet(raw_style)

    def _schedule_test_autofill_if_requested(self):
        flag_value = str(os.environ.get("AYEC_SETUP_AUTOFILL", "")).strip().lower()
        if flag_value not in {"1", "true", "yes", "on"}:
            return
        QTimer.singleShot(600, self._run_test_autofill_preview)

    def _run_test_autofill_preview(self):
        if self._test_autofill_started:
            return
        self._test_autofill_started = True
        try:
            self.show_toast("Test kurulum verileri dolduruluyor...", "info")
        except Exception:
            pass

        stamp = datetime.now().strftime("%d%H%M%S")
        company_step = self.steps[1]
        admin_step = self.steps[2]
        settings_step = self.steps[3]

        company_step.company_name.setText("AYEC Pro Servis")
        company_step.authorized_person.setText("Yönetici")
        company_step.phone.setText("05551234567")
        company_step.email.setText("")
        company_step.tax_office.setText("Vergi Dairesi")
        company_step.tax_number.setText("1234567890")
        company_step.address.setPlainText("Adres")

        admin_step.full_name.setText("Yönetici")
        admin_step.username.setText(f"yonetici")
        admin_step.email_field.setText("")
        admin_step.pw1.le.setText("Test1234!")
        admin_step.pw2.le.setText("Test1234!")

        currency_idx = settings_step.currency_combo.findText("TRY  -  Türk Lirası")
        if currency_idx >= 0:
            settings_step.currency_combo.setCurrentIndex(currency_idx)
        sector_idx = settings_step.sector_combo.findData("otomotiv")
        if sector_idx >= 0:
            settings_step.sector_combo.setCurrentIndex(sector_idx)
        for card in [settings_step.exc_card, settings_step.bak_card, settings_step.sms_card]:
            btn = card.grp.buttons()[0] if card.grp.buttons() else None
            if btn:
                btn.setChecked(True)

        self._advance_test_preview()

    def _advance_test_preview(self):
        if self.current_step >= len(STEP_META) - 1:
            self.show_toast("Test onizleme hazir. Son sayfadasiniz.", "success")
            return
        self.go_next()
        QTimer.singleShot(420, self._advance_test_preview)

    # ============================================================================
    #  SIDEBAR
    # ============================================================================
    def _build_sidebar(self, root):
        self.sidebar = QFrame()
        self.sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sidebar.setFixedWidth(300)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet(f"""
            #Sidebar {{
                background: qlineargradient(
                    x1:0,y1:0, x2:0,y2:1,
                    stop:0 #1E293B,
                    stop:1 #0F172A
                );
                border-right: 1px solid rgba(255,255,255,0.08);
            }}
        """)

        v = QVBoxLayout(self.sidebar)
        v.setContentsMargins(28, 36, 28, 32)
        v.setSpacing(0)

        # Logo
        logo_row = QFrame()
        logo_row.setStyleSheet("background:transparent;border:none;")
        logo_h = QHBoxLayout(logo_row)
        logo_h.setContentsMargins(0, 0, 0, 0)

        logo_icon = QLabel("⬡")
        logo_icon.setStyleSheet("""
            color: #818CF8;
            font-size: 34px;
            background: transparent;
            border: none;
        """)
        logo_h.addWidget(logo_icon)

        logo_txt = QVBoxLayout()
        lbl_brand = QLabel("AYEC Pro")
        lbl_brand.setStyleSheet(f"""
            color: {C['sidebar_text']};
            font-size: 20px;
            font-weight: 800;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)
        lbl_slogan = QLabel("Kurulum Sihirbazı")
        lbl_slogan.setStyleSheet(f"""
            color: {C['sidebar_muted']};
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
            background: transparent;
            border: none;
        """)
        logo_txt.addWidget(lbl_brand)
        logo_txt.addWidget(lbl_slogan)
        logo_h.addLayout(logo_txt)
        logo_h.addStretch()
        v.addWidget(logo_row)
        v.addSpacing(8)

        # Ayırıcı çizgi
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.08); border:none;")
        v.addWidget(line)
        v.addSpacing(28)

        self.lbl_progress = QLabel("0% Tamamlandı")
        self.lbl_progress.setStyleSheet(f"""
            color: {C['sidebar_muted']};
            font-size: 11px;
            letter-spacing: 1.5px;
            background: transparent;
            border: none;
            margin-bottom: 6px;
        """)
        v.addWidget(self.lbl_progress)

        self.progress_bar_bg = QFrame()
        self.progress_bar_bg.setFixedHeight(4)
        self.progress_bar_bg.setStyleSheet("""
            background: rgba(255,255,255,0.07);
            border-radius: 2px;
            border: none;
        """)
        pb_wrap = QVBoxLayout(self.progress_bar_bg)
        pb_wrap.setContentsMargins(0, 0, 0, 0)

        self.progress_fill = QFrame(self.progress_bar_bg)
        self.progress_fill.setFixedHeight(4)
        self.progress_fill.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #818CF8, stop:1 #60A5FA);
            border-radius: 2px;
            border: none;
        """)
        self.progress_fill.move(0, 0)
        self.progress_fill.show()
        v.addWidget(self.progress_bar_bg)
        v.addSpacing(28)

        # Adım Göstergeleri
        self.step_widgets = []
        for idx, (num, title, sub, _ico) in enumerate(STEP_META):
            w = self._make_step_widget(idx, num, title, sub)
            v.addWidget(w)
            self.step_widgets.append(w)
            if idx < len(STEP_META) - 1:
                # Dikey konnektör çizgisi
                conn = QFrame()
                conn.setFixedSize(2, 18)
                conn.setStyleSheet("background: rgba(255,255,255,0.06); border:none;")
                ch = QHBoxLayout()
                ch.setContentsMargins(34, 0, 0, 0)
                ch.addWidget(conn)
                ch.addStretch()
                wrap = QWidget()
                wrap.setLayout(ch)
                wrap.setStyleSheet("background:transparent;")
                v.addWidget(wrap)
                self.step_widgets.append(("connector", conn))

        v.addStretch()

        # Versiyon
        lbl_ver = QLabel("v5.0.0 · Premium Edition")
        lbl_ver.setStyleSheet(f"""
            color: {C['sidebar_muted']};
            font-size: 10px;
            background: transparent;
            border: none;
            letter-spacing: 1px;
        """)
        v.addWidget(lbl_ver)
        root.addWidget(self.sidebar)

    def _make_step_widget(self, idx, num, title, sub):
        """Tek adım satırı"""
        w = QFrame()
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        w.setObjectName(f"StepRow_{idx}")
        w.setFixedHeight(56)
        w.setStyleSheet("background:transparent; border:none;")

        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(14)

        # Çember
        circle = QLabel(num)
        circle.setObjectName(f"StepCircle_{idx}")
        circle.setFixedSize(36, 36)
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setStyleSheet(f"""
            background: rgba(255,255,255,0.08);
            color: {C['sidebar_muted']};
            border-radius: 18px;
            font-size: 11px;
            font-weight: 700;
            border: 1.5px solid rgba(255,255,255,0.12);
        """)
        h.addWidget(circle)

        # Metin
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setObjectName(f"StepTitle_{idx}")
        lbl_t.setStyleSheet(f"color:{C['sidebar_muted']}; font-size:13px; font-weight:600; background:transparent; border:none;")
        lbl_s = QLabel(sub)
        lbl_s.setObjectName(f"StepSub_{idx}")
        lbl_s.setStyleSheet(f"color:rgba(148,163,184,0.6); font-size:10px; background:transparent; border:none;")
        vbox.addWidget(lbl_t)
        vbox.addWidget(lbl_s)
        h.addLayout(vbox)
        h.addStretch()

        return w

    # ============================================================================
    #  CONTENT
    # ============================================================================
    def _build_content(self, root):
        self.content_wrap = QFrame()
        self.content_wrap.setObjectName("ContentWrap")
        self.content_wrap.setStyleSheet(f"""
            #ContentWrap {{
                background-color: {C['bg_deep']};
            }}
        """)

        cv = QVBoxLayout(self.content_wrap)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        # Top Bar
        self._build_topbar(cv)

        # Stack
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background:transparent; border:none; }
            QScrollBar:vertical {
                background: transparent; width: 6px; border:none;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.12);
                border-radius: 3px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background:transparent;")
        self.steps = [
            WelcomeStep(self),
            CompanyInfoStep(self),
            AdminUserStep(self),
            BasicSettingsStep(self),
            CompletionStep(self),
        ]
        for s in self.steps:
            self.stack.addWidget(s)

        scroll.setWidget(self.stack)
        cv.addWidget(scroll, 1)

        # Nav Bar
        self._build_navbar(cv)

        root.addWidget(self.content_wrap, 1)

    def _build_topbar(self, parent_layout):
        bar = QFrame()
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"""
            background: {C['bg_card']};
            border-bottom: 1px solid {C['border']};
        """)
        h = QHBoxLayout(bar)
        h.setContentsMargins(36, 0, 20, 0)

        # Adım başlığı
        self.lbl_step_title = QLabel("Hoş Geldiniz")
        self.lbl_step_title.setStyleSheet(f"""
            color: {C['text_primary']};
            font-size: 17px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        h.addWidget(self.lbl_step_title)
        h.addStretch()

        # Adım sayacı
        self.lbl_step_count = QLabel("Adım 1 / 5")
        self.lbl_step_count.setStyleSheet(f"""
            color: {C['text_secondary']};
            font-size: 12px;
            background: {C['bg_deep']};
            border: 1px solid {C['border']};
            border-radius: 20px;
            padding: 4px 14px;
        """)
        h.addWidget(self.lbl_step_count)
        h.addSpacing(16)

        # Pencere düğmeleri
        for txt, fn, hover in [("—", self.showMinimized, "#334155"),
                                ("✕", self.reject, "#EF4444")]:
            btn = QPushButton(txt)
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(fn)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C['text_secondary']};
                    border-radius: 8px; font-size: 13px; border: none;
                }}
                QPushButton:hover {{ background: {hover}; color: white; }}
            """)
            h.addWidget(btn)

        parent_layout.addWidget(bar)

    def _build_navbar(self, parent_layout):
        bar = QFrame()
        bar.setFixedHeight(84)
        bar.setStyleSheet(f"background:{C['bg_card']}; border-top: 1px solid {C['border']};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(36, 16, 36, 20)

        self.back_btn = QPushButton("← Geri")
        self.back_btn.setFixedSize(130, 44)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_deep']};
                color: {C['text_secondary']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: {C['border']};
                color: {C['text_primary']};
                border-color: #CBD5E1;
            }}
            QPushButton:disabled {{
                color: #CBD5E1;
                border-color: #E2E8F0;
            }}
        """)

        self.next_btn = QPushButton("Devam Et  →")
        self.next_btn.setFixedSize(175, 44)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self.go_next)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #6366F1, stop:1 #4F46E5);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4F46E5, stop:1 #4338CA);
            }}
            QPushButton:pressed {{
                background: #4338CA;
            }}
        """)

        h.addWidget(self.back_btn)
        h.addStretch()
        h.addWidget(self.next_btn)
        parent_layout.addWidget(bar)

    # ============================================================================
    #  SIDEBAR GÜNCELLEME
    # ============================================================================
    def _refresh_sidebar(self):
        step_index = 0
        for widget in self.step_widgets:
            if isinstance(widget, tuple):   # konnektör
                _, conn = widget
                is_before = step_index <= self.current_step
                conn.setStyleSheet(
                    "background: rgba(99,102,241,0.5); border:none;"
                    if is_before else
                    "background: rgba(0,0,0,0.10); border:none;"
                )
                continue

            idx = step_index
            step_index += 1

            is_active    = (idx == self.current_step)
            is_completed = (idx <  self.current_step)

            circle = widget.findChild(QLabel, f"StepCircle_{idx}")
            title  = widget.findChild(QLabel, f"StepTitle_{idx}")
            sub    = widget.findChild(QLabel, f"StepSub_{idx}")
            if not circle:
                continue

            if is_active:
                circle.setText(STEP_META[idx][3])   # emoji ikon
                circle.setStyleSheet("""
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #6366F1, stop:1 #4F46E5);
                    color: white; border-radius: 18px;
                    font-size: 16px; font-weight: 700;
                    border: none;
                """)
                title.setStyleSheet(f"color:#F1F5F9; font-size:13px; font-weight:700; background:transparent; border:none;")
                sub.setStyleSheet(f"color:#A5B4FC; font-size:10px; background:transparent; border:none;")
                # Aktif satır vurgusu
                widget.setStyleSheet("""
                    background: rgba(99,102,241,0.15);
                    border-radius: 12px; border: none;
                """)
            elif is_completed:
                circle.setText("✓")
                circle.setStyleSheet("""
                    background: rgba(16,185,129,0.15);
                    color: #10B981; border-radius: 18px;
                    font-size: 14px; font-weight: 800;
                    border: 1.5px solid rgba(16,185,129,0.4);
                """)
                title.setStyleSheet(f"color:#CBD5E1; font-size:13px; font-weight:600; background:transparent; border:none;")
                sub.setStyleSheet(f"color:rgba(148,163,184,0.6); font-size:10px; background:transparent; border:none;")
                widget.setStyleSheet("background:transparent; border:none;")
            else:
                circle.setText(STEP_META[idx][0])
                circle.setStyleSheet(f"""
                    background: rgba(255,255,255,0.08);
                    color: rgba(148,163,184,0.6); border-radius: 18px;
                    font-size: 11px; font-weight: 700;
                    border: 1.5px solid rgba(255,255,255,0.12);
                """)
                title.setStyleSheet(f"color:{C['sidebar_muted']}; font-size:13px; font-weight:600; background:transparent; border:none;")
                sub.setStyleSheet(f"color:rgba(148,163,184,0.5); font-size:10px; background:transparent; border:none;")
                widget.setStyleSheet("background:transparent; border:none;")

        # ?lerleme yüzdesi & bar
        pct = int(self.current_step / (len(STEP_META) - 1) * 100)
        self.lbl_progress.setText(f"%{pct} Tamamlandı")
        bar_w = max(4, int(self.progress_bar_bg.width() * pct / 100))
        self.progress_fill.resize(bar_w, 4)

        # Top bar metinleri
        self.lbl_step_title.setText(STEP_META[self.current_step][1])
        self.lbl_step_count.setText(f"Adım {self.current_step + 1} / {len(STEP_META)}")

    # ============================================================================
    #  NAVİGASYON
    # ============================================================================
    def go_next(self):
        step_w = self.steps[self.current_step]
        if hasattr(step_w, "validate") and not step_w.validate():
            return
        if hasattr(step_w, "get_data"):
            self.setup_data.update(step_w.get_data())

        if self.current_step == 3:
            legal_acceptance = self.setup_data.get("legal_acceptance", {})
            if legal_acceptance:
                self.setup_data.setdefault("basic_settings", {}).update(legal_acceptance)
                self.setup_data["basic_settings"]["terms_accepted_at"] = datetime.now().isoformat(timespec="seconds")

        # Autofill AdminUserStep fields using values from CompanyInfoStep
        if self.current_step == 1:  # CompanyInfoStep completed
            try:
                admin_step = self.steps[2]
                company_info = self.setup_data.get("company_info", {})
                auth_person = company_info.get("authorized_person", "").strip()
                comp_email = company_info.get("email", "").strip()
                
                if auth_person and not admin_step.full_name.text().strip():
                    admin_step.full_name.setText(auth_person)
                if comp_email and not admin_step.email_field.text().strip():
                    admin_step.email_field.setText(comp_email)
            except Exception as e:
                from src.utils.logger import logger
                logger.warning(f"Wizard auto-fill failed: {e}")

        if self.current_step == len(STEP_META) - 1:
            self._complete_setup()
        else:
            self._animate_transition(forward=True)

    def go_back(self):
        if self.current_step > 0:
            self._animate_transition(forward=False)

    def _animate_transition(self, forward: bool):
        """Hafif opacity fade geçişi"""
        current_w = self.steps[self.current_step]

        effect = QGraphicsOpacityEffect(current_w)
        current_w.setGraphicsEffect(effect)

        fade_out = QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(120)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutQuad)

        def _switch():
            self.current_step += 1 if forward else -1
            self.back_btn.setEnabled(self.current_step > 0)
            self.back_btn.setVisible(self.current_step > 0)

            # Son adım butonu
            if self.current_step == len(STEP_META) - 1:
                self.next_btn.setText("🚀  Kurulumu Tamamla")
                self.next_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #10B981, stop:1 #059669);
                        color: white; border: none; border-radius: 10px;
                        font-size: 14px; font-weight: 700;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #059669, stop:1 #047857);
                    }
                """)
            else:
                self.next_btn.setText("Devam Et  →")
                self.next_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #7C3AED, stop:1 #4F46E5);
                        color: white; border: none; border-radius: 10px;
                        font-size: 14px; font-weight: 700;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #6D28D9, stop:1 #4338CA);
                    }
                """)

            self.stack.setCurrentIndex(self.current_step)
            self._refresh_sidebar()

            # Fade in yeni
            new_w  = self.steps[self.current_step]
            eff2   = QGraphicsOpacityEffect(new_w)
            new_w.setGraphicsEffect(eff2)
            fade_in = QPropertyAnimation(eff2, b"opacity")
            fade_in.setDuration(180)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.InQuad)

            def _cleanup():
                new_w.setGraphicsEffect(None)

            fade_in.finished.connect(_cleanup)
            fade_in.start()
            self._anim_in = fade_in

        fade_out.finished.connect(_switch)
        fade_out.start()
        self._anim_out = fade_out

    # ============================================================================
    #  KURULUM TAMAMLA
    # ============================================================================
    def _complete_setup(self):
        try:
            self.next_btn.setEnabled(False)
            self.next_btn.setText("Kurulum Tamamlanıyor...")
            QApplication.processEvents()
            self.db.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            self.db.cursor.execute("CREATE TABLE IF NOT EXISTS internal_settings (key TEXT PRIMARY KEY, value TEXT)")
            self.db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_info (
                    company_name TEXT,
                    authorized_person TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    tax_office TEXT,
                    tax_number TEXT
                )
            """)
            if hasattr(self.db, "ensure_full_initialized"):
                self.db.ensure_full_initialized()
            c = self.setup_data.get("company_info", {})
            self.db.cursor.execute(
                "INSERT OR REPLACE INTO company_info "
                "(company_name, authorized_person, phone, email, address, tax_office, tax_number) "
                "VALUES (?,?,?,?,?,?,?)",
                (c.get("company_name"), c.get("authorized_person"),
                 c.get("phone"), c.get("email"),
                 c.get("address"), c.get("tax_office"), c.get("tax_number")),
            )
            company_settings = {
                "company_name": c.get("company_name") or "",
                "company_authorized_person": c.get("authorized_person") or "",
                "company_phone": c.get("phone") or "",
                "company_gsm": c.get("phone") or "",
                "company_email": c.get("email") or "",
                "company_address": c.get("address") or "",
                "company_tax_office": c.get("tax_office") or "",
                "company_tax_number": c.get("tax_number") or "",
                "installation_lat": c.get("installation_lat") or "",
                "installation_lng": c.get("installation_lng") or "",
                "installation_address": c.get("installation_address") or c.get("address") or "",
                "map_default_lat": c.get("installation_lat") or "",
                "map_default_lng": c.get("installation_lng") or "",
            }
            for setting_key, setting_value in company_settings.items():
                self.db.set_setting(setting_key, setting_value)
            if c.get("company_name") and not self.db.get_setting("site_title", ""):
                self.db.set_setting("site_title", c.get("company_name"))

            a = self.setup_data.get("admin_user", {})
            from src.utils.security_manager import SecurityManager
            pw_hash = SecurityManager.hash_password(a.get("password", ""))
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_name = (a.get("full_name") or "").strip()
            username = (a.get("username") or "").strip()
            email = (a.get("email") or "").strip() or None
            existing_tables = {
                row[0]
                for row in self.db.cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            personnel_cols = set(self.db._get_table_columns("personnel")) if hasattr(self.db, "_get_table_columns") and "personnel" in existing_tables else set()
            personnel_id = None
            personnel_row = None

            if "personnel" in existing_tables:
                self.db.cursor.execute(
                    "SELECT id FROM personnel WHERE username=?",
                    (username,),
                )
                personnel_row = self.db.cursor.fetchone()

            if personnel_row:
                try:
                    personnel_id = personnel_row["id"]
                except Exception:
                    personnel_id = personnel_row[0]
                personnel_updates = {
                    "name": full_name,
                    "password": pw_hash,
                    "role": "Yönetici",
                    "email": email,
                    "active": 1,
                    "created_at": created_at,
                }
                update_fields = [f"{col}=?" for col in personnel_updates if col in personnel_cols]
                update_values = [personnel_updates[col] for col in personnel_updates if col in personnel_cols]
                if update_fields:
                    self.db.cursor.execute(
                        f"UPDATE personnel SET {', '.join(update_fields)} WHERE id=?",
                        (*update_values, personnel_id),
                    )
            else:
                personnel_data = {
                    "name": full_name,
                    "username": username,
                    "password": pw_hash,
                    "role": "Yönetici",
                    "email": email,
                    "active": 1,
                    "created_at": created_at,
                }
                insert_cols = [col for col in personnel_data if col in personnel_cols]
                if insert_cols:
                    placeholders = ",".join(["?"] * len(insert_cols))
                    self.db.cursor.execute(
                        f"INSERT INTO personnel ({', '.join(insert_cols)}) VALUES ({placeholders})",
                        tuple(personnel_data[col] for col in insert_cols),
                    )
                    personnel_id = self.db.cursor.lastrowid
                else:
                    personnel_id = None

            user_cols = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") and "users" in existing_tables else set()
            user_data = {
                "username": username,
                "password": pw_hash,
                "email": email,
                "role": "Yönetici",
                "created_at": created_at,
                "full_name": full_name,
                "name": full_name,
                "personnel_id": personnel_id,
                "active": 1,
                "is_active": 1,
                "interface_edit_access": 1,
            }
            if "permissions" in user_cols:
                user_data["permissions"] = '{"mode":"all"}'

            existing_user = None
            if "users" in existing_tables:
                existing_user = self.db.cursor.execute(
                    "SELECT id FROM users WHERE username=?",
                    (username,),
                ).fetchone()
            if existing_user:
                try:
                    existing_user_id = existing_user["id"]
                except Exception:
                    existing_user_id = existing_user[0]
                update_fields = [f"{col}=?" for col in user_data if col in user_cols and col != "username"]
                update_values = [user_data[col] for col in user_data if col in user_cols and col != "username"]
                if update_fields:
                    self.db.cursor.execute(
                        f"UPDATE users SET {', '.join(update_fields)} WHERE id=?",
                        (*update_values, existing_user_id),
                    )
            elif "users" in existing_tables:
                insert_cols = [col for col in user_data if col in user_cols]
                if insert_cols:
                    placeholders = ",".join(["?"] * len(insert_cols))
                    self.db.cursor.execute(
                        f"INSERT INTO users ({', '.join(insert_cols)}) VALUES ({placeholders})",
                        tuple(user_data[col] for col in insert_cols),
                    )

            s = self.setup_data.get("basic_settings", {})
            for k, v in [
                ("currency",            s.get("currency",            s.get("default_currency", "TRY"))),
                ("default_currency",    s.get("default_currency",    s.get("currency", "TRY"))),
                ("current_sector",      s.get("current_sector",      "teknik_servis")),
                ("device_business_profiles", s.get("device_business_profiles", "bilgisayar")),
                ("auto_exchange_update", str(s.get("auto_exchange_update", True))),
                ("auto_backup",          str(s.get("auto_backup",         True))),
                ("sms_notifications",    str(s.get("sms_notifications",  False))),
                ("terms_version",        s.get("terms_version", "2026.09")),
                ("terms_accepted_at",    s.get("terms_accepted_at", "")),
                ("terms_accepted",       str(s.get("terms_accepted", False))),
                ("backup_responsibility_acknowledged", str(s.get("backup_responsibility_acknowledged", False))),
                ("privacy_notice_read",  str(s.get("privacy_notice_read", False))),
                ("marketing_opt_in",     str(s.get("marketing_opt_in", False))),
            ]:
                self.db.cursor.execute(
                    "INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (k, v)
                )

            self.db.cursor.execute(
                "INSERT OR REPLACE INTO settings (key,value) VALUES ('setup_completed','true')"
            )
            selected_sector = s.get("current_sector", "teknik_servis")
            try:
                self.db.create_internal_settings_table()
            except Exception:
                pass

            try:
                self.db.set_internal_setting("current_sector", selected_sector)
                self.db.set_internal_setting(
                    "device_business_profiles",
                    s.get("device_business_profiles", "bilgisayar"),
                )
                self.db.set_internal_setting("setup_completed", "true")
            except Exception:
                try:
                    self.db.cursor.execute("CREATE TABLE IF NOT EXISTS internal_settings (key TEXT PRIMARY KEY, value TEXT)")
                    self.db.cursor.execute(
                        "INSERT OR REPLACE INTO internal_settings (key, value) VALUES (?, ?)",
                        ("current_sector", selected_sector),
                    )
                    self.db.cursor.execute(
                        "INSERT OR REPLACE INTO internal_settings (key, value) VALUES (?, ?)",
                        ("device_business_profiles", s.get("device_business_profiles", "bilgisayar")),
                    )
                    self.db.cursor.execute(
                        "INSERT OR REPLACE INTO internal_settings (key, value) VALUES (?, ?)",
                        ("setup_completed", "true"),
                    )
                except Exception:
                    pass

            self.db.conn.commit()

            # E-posta gönder
            try:
                self._send_welcome_emails()
            except Exception:
                pass

            QApplication.processEvents()
            self.done(QtDialog.DialogCode.Accepted)
            self.close()

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.next_btn.setEnabled(True)
            self.next_btn.setText("🚀  Kurulumu Tamamla")
            show_error(self, "Kurulum Hatası", f"Kurulum tamamlanamadı:\n{e}")

    def _send_welcome_emails(self):
        """Kurulum tamamlandıktan sonra müşteriye hoş geldin ve yöneticiye bildirim maili gönder."""
        try:
            from src.utils.mail_manager import send_registration_emails_async
            c = self.setup_data.get("company_info", {})
            a = self.setup_data.get("admin_user",   {})
            b = self.setup_data.get("basic_settings", {})

            reg_data = {
                "company_name": c.get("company_name"),
                "full_name": a.get("full_name") or c.get("authorized_person"),
                "email": a.get("email") or c.get("email"),
                "phone": c.get("phone"),
                "purpose": b.get("current_sector", "teknik_servis"),
                "license": "Yeni Kurulum"
            }
            send_registration_emails_async(reg_data, db=self.db)
        except Exception as e:
            from src.utils.logger import logger
            logger.warning(f"Setup welcome email error: {e}")

        try:
            from src.utils.mail_manager import MailWorker
            c = self.setup_data.get("company_info", {})
            a = self.setup_data.get("admin_user",   {})

            company = c.get("company_name", "Şirketiniz")
            name    = a.get("full_name", "Yönetici")
            uname   = a.get("username",     "admin")
            emails  = list({
                e for e in [c.get("email",""), a.get("email","")]
                if e and "@" in e
            })

            html = f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head><meta charset="UTF-8">
            <style>
              body{{font-family:'Segoe UI',Arial,sans-serif;background:#0A0C14;margin:0;padding:0;}}
              .wrap{{max-width:580px;margin:30px auto;background:#10131C;border-radius:16px;
                     overflow:hidden;border:1px solid rgba(124,58,237,0.25);}}
              .header{{background:linear-gradient(135deg,#7C3AED,#4F46E5);padding:40px 36px;text-align:center;}}
              .header h1{{color:#fff;margin:0;font-size:26px;font-weight:800;letter-spacing:1px;}}
              .header p{{color:rgba(255,255,255,0.75);margin:8px 0 0;font-size:14px;}}
              .body{{padding:36px;}}
              .greeting{{color:#F1F5F9;font-size:17px;font-weight:600;margin-bottom:20px;}}
              .card{{background:#181C28;border-radius:12px;padding:20px 24px;
                     border:1px solid rgba(255,255,255,0.06);margin:20px 0;}}
              .card-title{{color:#818CF8;font-size:12px;font-weight:700;
                           letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;}}
              .row{{display:flex;justify-content:space-between;
                    border-bottom:1px solid rgba(255,255,255,0.05);padding:8px 0;}}
              .row:last-child{{border-bottom:none;}}
              .row-label{{color:#64748B;font-size:13px;}}
              .row-value{{color:#F1F5F9;font-size:13px;font-weight:600;}}
              .badge{{display:inline-block;background:rgba(16,185,129,0.15);
                      color:#10B981;border-radius:20px;padding:4px 14px;
                      font-size:12px;font-weight:700;border:1px solid rgba(16,185,129,0.3);}}
              .footer{{text-align:center;padding:24px 36px;
                       border-top:1px solid rgba(255,255,255,0.05);}}
              .footer p{{color:#475569;font-size:12px;margin:4px 0;}}
              .footer a{{color:#818CF8;text-decoration:none;}}
            </style>
            </head>
            <body>
            <div class="wrap">
              <div class="header">
                <h1>⬡ AYEC Pro</h1>
                <p>Kurulumunuz başarıyla tamamlandı 🎉</p>
              </div>
              <div class="body">
                <p class="greeting">Merhaba, {name}!</p>
                <p style="color:#94A3B8;font-size:14px;line-height:1.7;">
                  <strong style="color:#F1F5F9;">{company}</strong> için
                  AYEC Pro kurulumunuz tamamlandı. Sisteminiz kullanıma hazır.
                </p>
                <div class="card">
                  <div class="card-title">Şirket Bilgileri</div>
                  <div class="row"><span class="row-label">Şirket Adı</span>
                    <span class="row-value">{company}</span></div>
                  <div class="row"><span class="row-label">Yetkili Kişi</span>
                    <span class="row-value">{c.get('authorized_person','—')}</span></div>
                  <div class="row"><span class="row-label">Telefon</span>
                    <span class="row-value">{c.get('phone','—')}</span></div>
                  <div class="row"><span class="row-label">E-posta</span>
                    <span class="row-value">{c.get('email','—')}</span></div>
                </div>
                <div class="card">
                  <div class="card-title">Yönetici Hesabı</div>
                  <div class="row"><span class="row-label">Ad Soyad</span>
                    <span class="row-value">{name}</span></div>
                  <div class="row"><span class="row-label">Kullanıcı Adı</span>
                    <span class="row-value">{uname}</span></div>
                  <div class="row"><span class="row-label">Durum</span>
                    <span class="row-value"><span class="badge">✓ Aktif</span></span></div>
                </div>
                <div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);
                            border-radius:10px;padding:14px 18px;margin-top:20px;">
                  <p style="color:#FBBF24;font-size:13px;font-weight:600;margin:0;">
                    ⚠️ Güvenlik Hatırlatması
                  </p>
                  <p style="color:#94A3B8;font-size:12px;margin:6px 0 0;">
                    Kullanıcı adı ve şifrenizi güvenli bir yerde saklayın.
                    Bu bilgileri asla başkalarıyla paylaşmayın.
                  </p>
                </div>
              </div>
              <div class="footer">
                <p>Bu e-posta AYEC Pro kurulum sihirbazı tarafından gönderilmiştir.</p>
                <p>Sorularınız için: <a href="mailto:destek@ayecpro.com">destek@ayecpro.com</a></p>
              </div>
            </div>
            </body></html>
            """

            for email in emails:
                worker = MailWorker(
                    recipient=email,
                    subject=f"🎉 AYEC Pro Kurulumunuz Tamamlandı — {company}",
                    body=html,
                    is_html=True,
                    db=self.db,
                )
                worker.finished.connect(self._on_mail_result)
                worker.start()
                self._mail_workers.append(worker)

        except Exception as e:
            from src.utils.logger import logger
            logger.warning(f"Setup welcome email error: {e}")

    @pyqtSlot(bool, str)
    def _on_mail_result(self, success, msg):
        if success:
            self.show_toast("📧 Hoş geldin e-postası gönderildi", "success")
        else:
            from src.utils.logger import logger
            logger.warning(f"Welcome mail send failed: {msg}")

    # ============================================================================
    #  TOAST
    # ============================================================================
    def show_toast(self, message: str, kind: str = "info"):
        try:
            if hasattr(self, "toast_container"):
                self.toast_container.show_notification(message, kind)
        except Exception:
            pass

    # ============================================================================
    #  PENCERE TAŞIMA
    # ============================================================================
    def mousePressEvent(self, e):
        pass   # Tam ekran modda sürükleme devre dışı

    def mouseMoveEvent(self, e):
        pass

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def resizeEvent(self, e):
        if hasattr(self, "base_frame"):
            self.base_frame.resize(self.width(), self.height())
        if hasattr(self, "toast_container"):
            self.toast_container.move(self.width() - 430, self.height() - 80)
        if hasattr(self, "progress_bar_bg"):
            pct = int(self.current_step / (len(STEP_META) - 1) * 100)
            bar_w = max(4, int(self.progress_bar_bg.width() * pct / 100))
            self.progress_fill.resize(bar_w, 4)
        super().resizeEvent(e)

