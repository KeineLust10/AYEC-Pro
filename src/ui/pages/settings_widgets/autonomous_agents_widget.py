from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss, tc, qc
from src.ui.widgets.animated_toggle import AnimatedToggle


class AgentScenarioGlyph(QWidget):
    """Small native vector glyph; colors follow the current theme tokens."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(28, 28)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tokens = ("finance_primary", "finance_secondary", "finance_secondary", "finance_tertiary", "finance_primary", "danger", "finance_primary")
        color = qc(tokens[self.kind])
        backdrop = qc(tokens[self.kind])
        backdrop.setAlpha(24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(backdrop)
        painter.drawRoundedRect(QRectF(0, 0, 28, 28), 4, 4)
        painter.setPen(QPen(color, 1.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        if self.kind == 0:
            path.moveTo(15, 5)
            for x, y in ((7, 15), (13, 15), (11, 23), (21, 11), (15, 11)):
                path.lineTo(x, y)
            path.closeSubpath()
        elif self.kind == 1:
            path.moveTo(6, 11)
            for x, y in ((10, 11), (15, 7), (15, 21), (10, 17), (6, 17)):
                path.lineTo(x, y)
            path.closeSubpath()
            painter.drawArc(12, 6, 11, 16, -60 * 16, 120 * 16)
        elif self.kind == 2:
            painter.drawRoundedRect(QRectF(6, 7, 16, 12), 4, 4)
            painter.drawLine(10, 19, 8, 22)
            painter.drawLine(8, 22, 14, 19)
        elif self.kind == 3:
            for x, height in ((7, 7), (12, 11), (17, 15)):
                painter.drawRect(x, 22 - height, 3, height)
        elif self.kind == 4:
            painter.drawLine(8, 20, 20, 8)
            painter.drawLine(8, 20, 13, 20)
            painter.drawLine(8, 20, 8, 15)
        elif self.kind == 5:
            path.moveTo(14, 5)
            path.lineTo(23, 22)
            path.lineTo(5, 22)
            path.closeSubpath()
            painter.drawLine(14, 11, 14, 16)
            painter.drawPoint(14, 19)
        else:
            painter.drawEllipse(10, 5, 8, 8)
            painter.drawRoundedRect(QRectF(7, 15, 14, 8), 4, 4)
        painter.drawPath(path)


class AutonomousAgentsWidget(QWidget):
    """Autonomous agent controls matching the Part 6 reference layout."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self._build_ui()
        self._refresh_runtime_status()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_runtime_status)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_runtime_status()
        if not self.status_timer.isActive():
            self.status_timer.start(5000)

    def hideEvent(self, event):
        self.status_timer.stop()
        super().hideEvent(event)

    def _card(self, title, body, parent_layout):
        card = QFrame()
        card.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border: 1px solid @border; border-radius: 10px; }"
        ))
        box = QVBoxLayout(card)
        box.setContentsMargins(18, 16, 18, 16)
        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss("color: @text; font-size: 15px; font-weight: 800; border: none;"))
        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setStyleSheet(theme_qss("color: @text_muted; border: none;"))
        box.addWidget(title_label)
        box.addWidget(body_label)
        parent_layout.addWidget(card)
        return box

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 18)
        root.setSpacing(10)
        header = QFrame()
        header.setObjectName("agentPageHeader")
        header.setStyleSheet(theme_qss("QFrame#agentPageHeader { background: transparent; border: none; }"))
        header.setFixedHeight(70)
        heading = QHBoxLayout(header)
        heading.setContentsMargins(0, 0, 0, 0)
        heading_text = QVBoxLayout()
        heading_text.setSpacing(2)
        category = QLabel("OTONOM S\u0130STEMLER")
        category.setStyleSheet(theme_qss("color: @finance_secondary; font-size: 9px; font-weight: 700; border: none; background: transparent;"))
        heading_text.addWidget(category)
        title = QLabel("Otonom Ajanlar & Entegrasyon Hub'\u0131")
        title.setStyleSheet(theme_qss("color: @text; font-size: 13px; font-weight: 800; border: none; background: transparent;"))
        heading_text.addWidget(title)
        subtitle = QLabel("Yapay zeka arka plan servisleri, otonom tetikleyiciler ve harici webhook a\u011f ge\u00e7itlerini y\u00f6netin.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none; background: transparent;"))
        heading_text.addWidget(subtitle)
        heading.addLayout(heading_text)
        heading.addStretch()
        restart = QPushButton("Servisleri Yeniden Baslat")
        restart.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        restart.clicked.connect(self._restart_services)
        self.restart_button = restart
        heading.addWidget(restart)
        new_agent = QPushButton("+ Yeni Ajan Tanimla")
        new_agent.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        new_agent.clicked.connect(self._open_agent_settings)
        self.new_agent_button = new_agent
        heading.addWidget(new_agent)
        root.addWidget(header)

        status_box = QFrame()
        status_box.setObjectName("agentRuntimeCard")
        status_box.setFixedHeight(164)
        status_box.setStyleSheet(theme_qss("QFrame#agentRuntimeCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        status = QVBoxLayout(status_box)
        status.setContentsMargins(18, 14, 18, 14)
        self.runtime_title = QLabel()
        status_title = self.runtime_title
        status_title.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 800; border: none;"))
        runtime_heading = QHBoxLayout()
        runtime_icon = QLabel("\u25a3")
        runtime_icon.setFixedSize(38, 38)
        runtime_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        runtime_icon.setStyleSheet(theme_qss("background: @finance_surface_alt; color: @finance_secondary; border: 1px solid @finance_secondary; border-radius: 8px; font-size: 20px;"))
        runtime_heading.addWidget(runtime_icon)
        runtime_heading.addWidget(status_title, 1)
        self.runtime_metrics = QLabel("CPU: -- / RAM: --\nDaemon PID: --")
        self.runtime_metrics.setFixedWidth(140)
        self.runtime_metrics.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.runtime_metrics.setStyleSheet(theme_qss("color: @finance_secondary; font-size: 10px; font-weight: 600; border: none;"))
        runtime_heading.addWidget(self.runtime_metrics)
        status.addLayout(runtime_heading)
        self.configured_count = QLabel()
        self.configured_count.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        status.addWidget(self.configured_count)
        states = QHBoxLayout()
        self.runtime_states = {}
        for key, name in (("voice", "Sesli Komut \u0130\u015fleme"), ("whatsapp", "WhatsApp Gateway"), ("customer", "Cari \u0130stihbarat"), ("tts", "TTS Ses Sentezi")):
            label = QLabel()
            label.setWordWrap(True)
            label.setStyleSheet(theme_qss("background: @finance_surface_alt; color: @text; padding: 8px; border: none; border-radius: 4px; font-size: 10px;"))
            self.runtime_states[key] = (name, label)
            states.addWidget(label)
        status.addLayout(states)
        body = QHBoxLayout()
        body.setSpacing(8)
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.addWidget(status_box)
        left_frame = QFrame()
        left_frame.setObjectName("agentScenariosCard")
        left_frame.setFixedHeight(527)
        left_frame.setStyleSheet(theme_qss("QFrame#agentScenariosCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        left = QVBoxLayout(left_frame)
        left.setContentsMargins(18, 16, 18, 16)
        left_title = QLabel("Otonom Tetikleyiciler & Senaryolar")
        left_title.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 800; border: none;"))
        title_row = QHBoxLayout()
        title_row.addWidget(left_title)
        title_row.addStretch()
        self.active_rules_label = QLabel()
        self.active_rules_label.setFixedWidth(100)
        self.active_rules_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.active_rules_label.setStyleSheet(theme_qss("color: @finance_primary; font-size: 11px; font-weight: 700; border: none;"))
        title_row.addWidget(self.active_rules_label)
        left.addLayout(title_row)
        left_body = QLabel("Sistem olaylar\u0131na kar\u015f\u0131 otomatik tepki verme yeteneklerini yap\u0131land\u0131r\u0131n.")
        left_body.setWordWrap(True)
        left_body.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        left.addWidget(left_body)
        scenarios = (
            ("agent_system_activation", "Sistemi Aktivasyon Otomasyonu", "Jarvis AI arka plan daemon servislerini otomatik ba\u015flat\u0131r."),
            ("agent_voice_feedback", "Sesli Geri Bildirim (TTS)", "Kritik i\u015flemler tamamland\u0131\u011f\u0131nda veya hata olu\u015ftu\u011funda sesli uyar\u0131 okur."),
            ("agent_whatsapp_reports", "Otomatik WhatsApp Kritik Raporlar", "G\u00fcn sonunda ve acil durumlarda y\u00f6neticiye rapor g\u00f6nderir."),
            ("agent_customer_intelligence", "Ak\u0131ll\u0131 M\u00fc\u015fteri \u0130stihbarat\u0131", "Servise gelen cihazlar\u0131n cari analizini otomatik \u00e7\u0131kar\u0131r."),
            ("agent_term_correction", "Teknik Terim D\u00fczeltme Motoru", "Sesli dikte esnas\u0131ndaki teknik terim hatalar\u0131n\u0131 d\u00fczeltir."),
            ("agent_error_reporting", "Sistem Hata Oto-Raporlay\u0131c\u0131", "Kritik exception loglar\u0131n\u0131 y\u00f6netici kayd\u0131na iletir."),
            ("assistant_fab_enabled", "Y\u00fczen Avatar Widget Kontrol\u00fc", "Sesli asistan g\u00f6rselini etkinlik durumuna g\u00f6re y\u00f6netir."),
        )
        self.scenario_toggles = {}
        for kind, (key, name, detail) in enumerate(scenarios):
            row = QFrame()
            row.setObjectName("agentScenarioRow")
            row.setFixedHeight(56)
            row.setStyleSheet(theme_qss("QFrame#agentScenarioRow { background: @finance_surface_alt; border: none; border-radius: 4px; }"))
            line = QHBoxLayout(row)
            line.setContentsMargins(10, 6, 10, 6)
            line.addWidget(AgentScenarioGlyph(kind, row))
            text = QVBoxLayout()
            text.setSpacing(2)
            name_label = QLabel(name)
            name_label.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 700; border: none;"))
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
            text.addWidget(name_label)
            text.addWidget(detail_label)
            line.addLayout(text, 1)
            toggle = AnimatedToggle(active_color=tc("success"))
            toggle.setFixedSize(34, 20)
            toggle.setProperty("activeThemeToken", "finance_secondary")
            toggle.setAccessibleName(name)
            self.scenario_toggles[key] = toggle
            enabled = True
            if key == "assistant_fab_enabled" and hasattr(self.db, "get_setting"):
                enabled = str(self.db.get_setting(key, "1")).strip().lower() not in {"0", "false", "no"}
            elif hasattr(self.db, "get_internal_setting"):
                enabled = str(self.db.get_internal_setting(key, "1")).strip().lower() not in {"0", "false", "no"}
            toggle.setChecked(enabled)
            toggle.toggled.connect(lambda checked, setting_key=key: self._save_toggle(setting_key, checked))
            line.addWidget(toggle)
            left.addWidget(row)
        left_column.addWidget(left_frame)
        body.addLayout(left_column, 2)
        right = QVBoxLayout()
        webhook_box = QFrame()
        webhook_box.setObjectName("agentWebhookCard")
        webhook_box.setStyleSheet(theme_qss("QFrame#agentWebhookCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        webhook_layout = QVBoxLayout(webhook_box)
        webhook_layout.setContentsMargins(18, 16, 18, 16)
        webhook_title = QLabel("UltraMsg Webhook")
        webhook_title.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 800; border: none;"))
        webhook_layout.addWidget(webhook_title)
        webhook_desc = QLabel("WhatsApp kurumsal bildirimleri ve m\u00fc\u015fteri etkile\u015fimleri i\u00e7in ana kanal k\u00f6pr\u00fcs\u00fc.")
        webhook_desc.setWordWrap(True)
        webhook_desc.setStyleSheet(theme_qss("color: @text_muted; border: none;"))
        webhook_layout.addWidget(webhook_desc)
        self.inp_ultra_instance = QLineEdit()
        self.inp_ultra_instance.setPlaceholderText("UltraMsg instance ID")
        self.inp_ultra_token = QLineEdit()
        self.inp_ultra_token.setPlaceholderText("API token secret")
        self.inp_ultra_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_ultra_phone = QLineEdit()
        self.inp_ultra_phone.setPlaceholderText("Yonetici WhatsApp numarasi")
        for field, label_text in ((self.inp_ultra_instance, "INSTANCE ID"), (self.inp_ultra_token, "API TOKEN SECRET"), (self.inp_ultra_phone, "Y\u00d6NET\u0130C\u0130 WHATSAPP NUMARASI")):
            label = QLabel(label_text)
            label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
            webhook_layout.addWidget(label)
            field.setStyleSheet(theme_qss("QLineEdit { background: @finance_surface_alt; color: @text; border: 1px solid @finance_outline; border-radius: 4px; padding: 4px 8px; min-height: 16px; font-size: 11px; }"))
            field.setFixedHeight(28)
            webhook_layout.addWidget(field)
        save_webhook = QPushButton("Webhook Ayarlarini Kaydet")
        save_webhook.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        save_webhook.clicked.connect(self._save_webhook_settings)
        self.save_webhook_button = save_webhook
        webhook_layout.addWidget(save_webhook)
        dispatcher_title = QLabel("Anl\u0131k Webhook Test G\u00f6ndericisi")
        dispatcher_title.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; border: none; padding-top: 8px;"))
        webhook_layout.addWidget(dispatcher_title)
        dispatcher_description = QLabel("UltraMsg a\u011f ge\u00e7idinin ayarlar\u0131n\u0131 yerel olarak do\u011frulay\u0131n.")
        dispatcher_description.setWordWrap(True)
        dispatcher_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none;"))
        webhook_layout.addWidget(dispatcher_description)
        right.addWidget(webhook_box)
        test_actions = QHBoxLayout()
        test_actions.setSpacing(8)
        send = QPushButton("Test Paketi G\u00f6nder")
        send.setToolTip("Yaln\u0131zca yerel ayar kontrol\u00fc yapar; a\u011f iste\u011fi veya mesaj g\u00f6ndermez.")
        self.validate_webhook_button = send
        send.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        send.clicked.connect(self._validate_webhook_settings)
        test_actions.addWidget(send, 1)
        logs = QPushButton("Loglar")
        self.btn_audit_log = logs
        logs.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        logs.clicked.connect(self._open_audit_log)
        test_actions.addWidget(logs)
        webhook_layout.addLayout(test_actions)
        metrics = QFrame()
        metrics.setObjectName("agentMetricsCard")
        metrics.setStyleSheet(theme_qss("QFrame#agentMetricsCard { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        metrics_layout = QVBoxLayout(metrics)
        metrics_layout.setContentsMargins(12, 10, 12, 10)
        for label_text, value_text in (
            ("Entegrasyon Kuyrugu", "-"),
            ("Webhook Basari Orani", "-"),
            ("Ortalama Yanit Gecikmesi", "-"),
        ):
            metric = QLabel(f"{label_text}                         {value_text}")
            metric.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; padding: 3px;"))
            metrics_layout.addWidget(metric)
        right.addWidget(metrics)
        right.addStretch()
        voice_features = QPushButton("Sesli Asistan \u00d6zellikleri")
        voice_features.setToolTip("Sesli asistan\u0131n form ve eri\u015filebilirlik yard\u0131mlar\u0131n\u0131 y\u00f6netin.")
        voice_features.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="md")))
        voice_features.clicked.connect(self._open_voice_feature_settings)
        self.voice_features_button = voice_features
        right.addWidget(voice_features, alignment=Qt.AlignmentFlag.AlignRight)
        body.addLayout(right, 1)
        root.addLayout(body)
        self._load_webhook_settings()

    def _open_voice_feature_settings(self):
        from src.services.voice_feature_settings import VoiceFeatureSettingsDialog

        dialog = VoiceFeatureSettingsDialog.create(self, self.db)
        dialog.exec()

    def _refresh_runtime_status(self):
        """Separate saved configuration from observed local worker state."""
        configured = sum(toggle.isChecked() for toggle in self.scenario_toggles.values())
        self.active_rules_label.setText(f"{configured} Kural Aktif")
        self.configured_count.setText(f"{configured}/{len(self.scenario_toggles)} Ayar Etkin - \u00c7al\u0131\u015fma durumu ayr\u0131 izlenir")
        assistant = getattr(self.main_window, "assistant", None)
        voice = getattr(assistant, "voice_assistant_thread", None)
        monitor = getattr(assistant, "assistant_monitor_worker", None)

        def running(worker):
            try:
                return bool(worker and worker.isRunning())
            except (AttributeError, RuntimeError):
                return False

        observed = running(voice) or running(monitor)
        state = "\u00c7ALI\u015eIYOR" if observed else ("HAZIR" if assistant else "DURUM ALINAMIYOR")
        self.runtime_title.setText(f"Jarvis Arka Plan Otonom Ajan\u0131   {state}")
        getter = getattr(self.db, "get_internal_setting", lambda _key, default="": default)
        configured_gateway = bool(getter("ultramsg_instance", "") and getter("ultramsg_token", ""))
        values = {
            "voice": ("\u00c7al\u0131\u015f\u0131yor" if running(voice) else "Durduruldu") if assistant else "-",
            "whatsapp": "Ayarland\u0131" if configured_gateway else "Ayarlanmam\u0131\u015f",
            "customer": "-",
            "tts": "-",
        }
        for key, (name, label) in self.runtime_states.items():
            label.setText(f"{name}\n{values[key]}")
            label.setToolTip("Yaln\u0131zca yerel durum / kay\u0131tl\u0131 ayarlar; ba\u011flant\u0131 testi yap\u0131lmad\u0131.")

    def _notify(self, message, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)

    def _save_toggle(self, key, checked):
        if key == "assistant_fab_enabled" and hasattr(self.db, "set_setting"):
            self.db.set_setting(key, "1" if checked else "0")
            if self.main_window is not None:
                self.main_window._assistant_fab_enabled = bool(checked)
                fab = getattr(self.main_window, "assistant_fab", None)
                if fab is not None:
                    page_index = int(getattr(self.main_window, "_current_page_index", -1))
                    fab.setVisible(bool(checked) and page_index not in {146, 147})
                    if checked and hasattr(self.main_window, "reposition_fab"):
                        self.main_window.reposition_fab()
        elif hasattr(self.db, "set_internal_setting"):
            self.db.set_internal_setting(key, "1" if checked else "0")
        self._refresh_runtime_status()
        self._notify("Otonom ajan ayari guncellendi.", "success")

    def _restart_services(self):
        if not self.main_window or not hasattr(self.main_window, "_ensure_assistant_manager"):
            self._notify("Asistan servis yoneticisi kullanilamiyor.", "warning")
            return
        assistant = self.main_window._ensure_assistant_manager()
        assistant.stop_voice_assistant()
        assistant.start_voice_assistant()
        assistant.run_assistant_monitoring()
        self._refresh_runtime_status()
        self._notify("Asistan servisleri yeniden baslatildi.", "success")

    def _open_agent_settings(self):
        parent = self.parentWidget()
        while parent is not None:
            if getattr(parent, "db", None) is self.db and hasattr(parent, "open_tab_by_key"):
                return parent.open_tab_by_key("voice_training")
            parent = parent.parentWidget()
        self._notify("Komut ve senaryo d\u00fczenleyicisi bu pencerede kullan\u0131lam\u0131yor.", "warning")
        return False

    def _open_audit_log(self):
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "sidebar") and hasattr(parent.sidebar, "items_map"):
                sidebar = parent.sidebar
                if hasattr(sidebar, "search_inp"):
                    sidebar.search_inp.clear()
                for row, mapped_id in enumerate(sidebar.items_map):
                    if mapped_id == 17:
                        sidebar.list_widget.setCurrentRow(row)
                        return True
                return False
            parent = parent.parentWidget()
        return False

    def _validate_webhook_settings(self):
        instance = ""
        token = ""
        if hasattr(self.db, "get_internal_setting"):
            instance = str(self.db.get_internal_setting("ultramsg_instance", "") or "")
            token = str(self.db.get_internal_setting("ultramsg_token", "") or "")
        if instance and token:
            self._notify("Test paketi haz\u0131r. Yerel ayarlar do\u011fruland\u0131; a\u011f testi veya mesaj g\u00f6nderimi yap\u0131lmad\u0131.", "info")
        else:
            self._notify("UltraMsg instance ve token bilgilerini tamamlayin.", "warning")

    def _load_webhook_settings(self):
        if not hasattr(self.db, "get_internal_setting"):
            return
        self.inp_ultra_instance.setText(str(self.db.get_internal_setting("ultramsg_instance", "") or ""))
        self.inp_ultra_token.setText(str(self.db.get_internal_setting("ultramsg_token", "") or ""))
        self.inp_ultra_phone.setText(str(self.db.get_internal_setting("ultramsg_phone", "") or ""))

    def _save_webhook_settings(self):
        if hasattr(self.db, "set_internal_setting"):
            self.db.set_internal_setting("ultramsg_instance", self.inp_ultra_instance.text().strip())
            self.db.set_internal_setting("ultramsg_token", self.inp_ultra_token.text().strip())
            self.db.set_internal_setting("ultramsg_phone", self.inp_ultra_phone.text().strip())
        self._refresh_runtime_status()
        self._notify("Webhook ayarlari kaydedildi.", "success")
