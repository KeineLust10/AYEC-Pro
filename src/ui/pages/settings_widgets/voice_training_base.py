# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QPushButton, QCheckBox,
                             QFrame, QListWidgetItem, QApplication,
                             QTimeEdit)
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QFont
import json
import os
import subprocess
import sys
from src.utils.theme_colors import theme_qss, tc
from src.utils.path_helper import PathHelper
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.design_system import DesignTokens
from src.ui.dialogs.modern_input_dialog import ModernInputDialog
from src.utils.logger import logger
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.page_config import PAGE_MAPPING, PAGE_NAMES



class VoiceTrainingWidget(QWidget):
    """
    Sesli Komut Eğitimi Sayfası
    - Senaryo Ekle/Sil
    - Tetikleyici Kelime Ekle/Sil
    - JSON Yönetimi (GUI tabanlı)
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.config_path = os.path.join(PathHelper.get_app_data_dir(), "asistan_ayarlari.json")
        self.data = {}
        self.current_scenario_name = ""
        self.last_healthcheck_result = None
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def _default_scenarios(self):
        scenarios = {
            "Finansal Özet": {
                "triggers": ["finans özet", "mali durum özeti", "kasa özeti"],
                "action": {"type": "builtin", "name": "accounting_summary"},
            },
            "Stoklara %10 Zam": {
                "triggers": ["stoklara yüzde 10 zam yap", "stoklara %10 zam yap", "fiyatlara yüzde 10 zam yap"],
                "action": {"type": "builtin", "name": "apply_zam"},
            },
            "Kritik Stoklar": {
                "triggers": ["kritik stokları listele", "kritik stoklar", "eksik stoklar"],
                "action": {"type": "builtin", "name": "list_critical_stock"},
            },
            "Teknisyen Paneli": {
                "triggers": ["teknisyen panelini aç", "teknisyen paneli", "panel aç"],
                "action": {"type": "builtin", "name": "panel_ac"},
            },
            "Yeni Servis Aç": {
                "triggers": ["yeni servis aç", "servis kaydı oluştur", "servis formunu aç"],
                "action": {"type": "builtin", "name": "servis_ac"},
            },
            "Bugünkü Randevular": {
                "triggers": ["bugünkü randevular", "randevularımı söyle", "bugün randevum var mı"],
                "action": {"type": "builtin", "name": "check_appointments"},
            },
            "Stok Özeti": {
                "triggers": ["stok özeti", "envanter özeti", "stok durum özeti"],
                "action": {"type": "builtin", "name": "stock_summary"},
            },
            "Yönetici Özeti": {
                "triggers": ["yönetici özeti", "bugün ne oldu", "günlük yönetici özeti"],
                "action": {"type": "builtin", "name": "managerial_summary"},
            },
            "Gelişmiş Finansal Özet": {
                "triggers": ["gelişmiş finansal özet", "nakit akış özeti", "vade özetini söyle"],
                "action": {"type": "builtin", "name": "financial_summary"},
            },
            "Müşteri 360": {
                "triggers": ["müşteri 360 aç", "müşteri cari hesap", "müşteri detaylarını aç"],
                "action": {"type": "builtin", "name": "customer_360"},
            },
            "Cihaz Durumu Sorgu": {
                "triggers": ["cihaz durumu sorgula", "cihaz durumu", "servis durumu sorgula"],
                "action": {"type": "builtin", "name": "device_status_query"},
            },
            "İndirim Tavsiyesi": {
                "triggers": ["indirim tavsiyesi ver", "müşteri için indirim tavsiyesi", "indirim önerisi"],
                "action": {"type": "builtin", "name": "discount_advice"},
            },
            "Borç Özeti": {
                "triggers": ["borç özeti", "kredi borç özeti", "borç durumunu söyle"],
                "action": {"type": "builtin", "name": "loan_summary"},
            },
            "Çek Senet Özeti": {
                "triggers": ["çek senet özeti", "çek senet portföyü", "çek senetleri aç"],
                "action": {"type": "builtin", "name": "check_summary"},
            },
            "Stok Karşılaştırma": {
                "triggers": ["stok karşılaştırma yap", "stok karşılaştırma", "hangi stok daha fazla"],
                "action": {"type": "builtin", "name": "stock_comparison"},
            },
            "Sesli Not Ekle": {
                "triggers": ["not ekle", "not al", "notu al", "sesli not al", "hızlı not ekle"],
                "action": {"type": "builtin", "name": "add_quick_note_voice"},
            },
            "Sesli Hatırlatıcı Ekle": {
                "triggers": ["hatırlatıcı ekle", "sesli hatırlatıcı kur", "yarın için hatırlatıcı ekle"],
                "action": {"type": "builtin", "name": "add_reminder_voice"},
            },
            "Gün Kapanış Özeti": {
                "triggers": ["gün kapanış özeti", "günü kapat", "akşam özetini ver"],
                "action": {"type": "builtin", "name": "closing_routine"},
            },
            "Musteri Borc Durumu": {
                "triggers": [
                    "borclu musterileri soyle",
                    "musteri borc durumunu soyle",
                    "kimlerin borcu var",
                ],
                "action": {"type": "builtin", "name": "customer_debt_summary"},
            },
            "Servis Is Yuku": {
                "triggers": [
                    "servis is yukunu soyle",
                    "kac cihaz bekliyor",
                    "servis durum ozeti",
                ],
                "action": {"type": "builtin", "name": "service_workload_summary"},
            },
            "Simdi Senkronize Et": {
                "triggers": [
                    "simdi senkronize et",
                    "senkronizasyon yap",
                    "verileri sunucuyla esitle",
                ],
                "action": {"type": "builtin", "name": "sync_now"},
            },
            "Asistan Yetenekleri": {
                "triggers": [
                    "neler yapabilirsin",
                    "hangi komutlari biliyorsun",
                    "bana nasil yardim edebilirsin",
                ],
                "action": {"type": "builtin", "name": "assistant_help"},
            },
            "Genel Bakış": {
                "triggers": ["genel bakış aç", "dashboard aç", "ana ekranı aç"],
                "action": {"type": "page", "index": 40},
            },
            "Stok Sayfası": {
                "triggers": ["stok sayfasını aç", "stok ekranını aç", "envanteri aç"],
                "action": {"type": "page", "index": 50},
            },
            "Müşteri Listesi": {
                "triggers": ["müşteri listesini aç", "müşterileri aç", "müşteri ekranını aç"],
                "action": {"type": "page", "index": 21},
            },
            "Satış Ekranı": {
                "triggers": ["satış ekranını aç", "satış işlemini aç", "yeni satış aç"],
                "action": {"type": "page", "index": 150},
            },
        }
        linked_pages = {
            int(config["action"]["index"])
            for config in scenarios.values()
            if config.get("action", {}).get("type") == "page"
        }
        for page_id, page_name in sorted(PAGE_NAMES.items()):
            if int(page_id) not in PAGE_MAPPING or int(page_id) in linked_pages:
                continue
            label = str(page_name or "").strip()
            if not label:
                continue
            scenario_name = f"{label} Sayfas\u0131"
            voice_label = label.casefold()
            scenarios[scenario_name] = {
                "triggers": [
                    f"{voice_label} a\u00e7",
                    f"{voice_label} sayfas\u0131n\u0131 a\u00e7",
                    f"{voice_label} ekran\u0131na git",
                ],
                "action": {"type": "page", "index": int(page_id)},
            }
        return scenarios

    def _build_stat_card(self, title, value, accent):
        card = QFrame()
        card.setStyleSheet(theme_qss(
            f"""
            QFrame {{
                background: @surface;
                border: 1px solid @border;
                border-left: 4px solid {accent};
                border-radius: 14px;
            }}
            """
        ))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        value_lbl = QLabel(value)
        value_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        value_lbl.setStyleSheet(theme_qss("color: @text;"))
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 600;"))
        title_lbl.setWordWrap(True)

        layout.addWidget(value_lbl)
        layout.addWidget(title_lbl)
        return card

    def _recommended_commands(self):
        return [
            "Asistan finans özet",
            "Asistan gelişmiş finansal özet",
            "Asistan kritik stokları listele",
            "Asistan stok özeti",
            "Asistan stoklara yüzde on zam yap",
            "Asistan yeni servis aç",
            "Asistan bugünkü randevular",
            "Asistan sezer ipek müşteri 360 aç",
            "Asistan sezer ipek cihaz durumu sorgula",
            "Asistan sezer ipek için indirim tavsiyesi ver",
            "Asistan toplantı notu al yarın müşteriyi ara",
            "Asistan yarın saat 14:30 için ödeme hatırlatıcı ekle",
            "Asistan gün kapanış özeti",
        ]

    def copy_recommended_commands(self):
        text = "\n".join(self._recommended_commands())
        QApplication.clipboard().setText(text)
        show_success(self.main_window or self, "Önerilen komutlar panoya kopyalandı.")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 18)
        layout.setSpacing(14)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        summary_row.addWidget(self._build_stat_card("Hazır komut şablonları", "10 gömülü senaryo", tc("accent")))
        summary_row.addWidget(self._build_stat_card("Tetikleme mantığı", "Uyanma adı + en uzun eşleşme", tc("success")))
        summary_row.addWidget(self._build_stat_card("Düzenleme davranışı", "Anında kaydet, isterse sil", tc("warning")))
        layout.addLayout(summary_row)

        command_card = QFrame()
        command_card.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 16px; }"))
        command_layout = QVBoxLayout(command_card)
        command_layout.setContentsMargins(18, 18, 18, 18)
        command_layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_text = QVBoxLayout()
        lbl_commands = QLabel("Sesli Senaryo Merkezi")
        lbl_commands.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_commands.setStyleSheet(theme_qss("color: @text;"))
        lbl_commands_info = QLabel("Senaryolar sayfada dağınık görünmez. Ekleme, düzenleme ve test işlemleri modern pencereden yapılır.")
        lbl_commands_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 600;"))
        lbl_commands_info.setWordWrap(True)
        title_text.addWidget(lbl_commands)
        title_text.addWidget(lbl_commands_info)
        title_row.addLayout(title_text, 1)
        self.lbl_active_scenario = QLabel("Aktif senaryo: Henüz seçilmedi")
        self.lbl_active_scenario.setStyleSheet(theme_qss("QLabel { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 10px; padding: 8px 12px; font-weight: 700; }"))
        title_row.addWidget(self.lbl_active_scenario, alignment=Qt.AlignmentFlag.AlignTop)
        command_layout.addLayout(title_row)

        self.lbl_scenario_meta = QLabel("Hazır senaryoları yükleyebilir, eski kayıtları düzeltebilir ve aktif komutu anında simüle edebilirsiniz.")
        self.lbl_scenario_meta.setWordWrap(True)
        self.lbl_scenario_meta.setStyleSheet(theme_qss("QLabel { background: @surface_alt; color: @text_muted; border: 1px solid @border; border-radius: 10px; padding: 10px 12px; font-size: 11px; font-weight: 600; }"))
        command_layout.addWidget(self.lbl_scenario_meta)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)
        self.btn_open_scenarios = QPushButton("🧩 Senaryoları Yönet")
        self.btn_open_scenarios.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_open_scenarios.clicked.connect(self.open_scenario_manager)
        self.btn_add_scen = QPushButton("➕ Senaryo Ekle")
        self.btn_add_scen.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_add_scen.clicked.connect(self.open_new_scenario_dialog)
        self.btn_load_defaults = QPushButton("Hazır Senaryoları Yükle")
        self.btn_load_defaults.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_load_defaults.clicked.connect(self.load_default_scenarios)
        self.btn_fix_legacy = QPushButton("Eski Senaryoları Düzelt")
        self.btn_fix_legacy.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_fix_legacy.clicked.connect(self.repair_legacy_scenarios)
        self.btn_test_scenario = QPushButton("🎙️ Aktif Senaryoyu Test Et")
        self.btn_test_scenario.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_test_scenario.clicked.connect(self.test_active_scenario)
        self.btn_healthcheck = QPushButton("🩺 Sağlık Testi Çalıştır")
        self.btn_healthcheck.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_healthcheck.clicked.connect(self.run_healthcheck)
        quick_row.addWidget(self.btn_open_scenarios)
        quick_row.addWidget(self.btn_add_scen)
        quick_row.addWidget(self.btn_load_defaults)
        quick_row.addWidget(self.btn_fix_legacy)
        quick_row.addWidget(self.btn_test_scenario)
        quick_row.addWidget(self.btn_healthcheck)
        command_layout.addLayout(quick_row)

        self.lbl_test_result = QLabel("Son test sonucu: Henüz çalıştırılmadı")
        self.lbl_test_result.setWordWrap(True)
        self.lbl_test_result.setStyleSheet(theme_qss(
            """
            QLabel {
                background: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            """
        ))
        command_layout.addWidget(self.lbl_test_result)
        self.btn_healthcheck_details = QPushButton("Detayları Gör")
        self.btn_healthcheck_details.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_healthcheck_details.clicked.connect(self.open_healthcheck_details)
        self.btn_healthcheck_details.setVisible(False)
        command_layout.addWidget(self.btn_healthcheck_details, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(command_card)

        suggested_card = QFrame()
        suggested_card.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 16px; }"))
        suggested_layout = QVBoxLayout(suggested_card)
        suggested_layout.setContentsMargins(18, 18, 18, 18)
        suggested_layout.setSpacing(12)

        suggested_head = QHBoxLayout()
        suggested_title = QLabel("Önerilen En Güçlü Komutlar")
        suggested_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        suggested_title.setStyleSheet(theme_qss("color: @text;"))
        suggested_info = QLabel("Günlük operasyonda en çok zaman kazandıran hazır sesli komutlar.")
        suggested_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 600;"))
        suggested_info.setWordWrap(True)
        suggested_text_col = QVBoxLayout()
        suggested_text_col.addWidget(suggested_title)
        suggested_text_col.addWidget(suggested_info)
        suggested_head.addLayout(suggested_text_col, 1)
        self.btn_copy_recommended = QPushButton("Kopyala")
        self.btn_copy_recommended.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_copy_recommended.clicked.connect(self.copy_recommended_commands)
        suggested_head.addWidget(self.btn_copy_recommended, alignment=Qt.AlignmentFlag.AlignTop)
        suggested_layout.addLayout(suggested_head)

        self.list_recommended_commands = QListWidget()
        self.list_recommended_commands.setStyleSheet(theme_qss(
            """
            QListWidget {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 8px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 8px 10px;
                margin: 2px 0;
                border-radius: 8px;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background: @accent_soft;
                color: @text;
            }
            """
        ))
        self.list_recommended_commands.setMinimumHeight(240)
        self.list_recommended_commands.setMaximumHeight(280)
        for command in self._recommended_commands():
            self.list_recommended_commands.addItem(QListWidgetItem(f"• {command}"))
        suggested_layout.addWidget(self.list_recommended_commands)
        layout.addWidget(suggested_card)
        
        # ===== SCHEDULED ALERTS SECTION =====
        schedule_card = QFrame()
        schedule_card.setStyleSheet(theme_qss(
            """
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 16px;
            }
            """
        ))
        schedule_layout = QVBoxLayout(schedule_card)
        schedule_layout.setContentsMargins(20, 20, 20, 20)
        schedule_layout.setSpacing(16)
        lbl_schedule = QLabel("Zamanlanmış Uyarılar")
        lbl_schedule.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_schedule.setStyleSheet(theme_qss("color: @text;"))
        schedule_layout.addWidget(lbl_schedule)
        schedule_info = QLabel("Aşağıdaki uyarı saatlerini ve aktiflik durumlarını yönetin.")
        schedule_info.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; font-size: 12px;"))
        schedule_info.setWordWrap(True)
        schedule_layout.addWidget(schedule_info)
        
        # Kredi Uyarısı
        row_loan = QHBoxLayout()
        row_loan.setSpacing(18)
        lbl_loan = QLabel("Kredi Taksit")
        lbl_loan.setStyleSheet(theme_qss("color: @text; font-weight: 600; min-width: 140px;"))
        row_loan.addWidget(lbl_loan)
        
        self.time_loan = QTimeEdit()
        self.time_loan.setDisplayFormat("HH:mm")
        self.time_loan.setTime(QTime(11, 0))
        self.time_loan.setFixedHeight(40)
        self.time_loan.setFixedWidth(120)
        self.time_loan.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row_loan.addWidget(self.time_loan)
        
        self.chk_loan_enabled = AnimatedToggle(active_color=tc("accent"))
        self.chk_loan_enabled.setChecked(True)
        row_loan.addWidget(self.chk_loan_enabled)
        row_loan.addStretch()
        schedule_layout.addLayout(row_loan)
        
        # Çek Uyarısı
        row_check = QHBoxLayout()
        row_check.setSpacing(18)
        lbl_check = QLabel("Çek / Senet")
        lbl_check.setStyleSheet(theme_qss("color: @text; font-weight: 600; min-width: 140px;"))
        row_check.addWidget(lbl_check)
        
        self.time_check = QTimeEdit()
        self.time_check.setDisplayFormat("HH:mm")
        self.time_check.setTime(QTime(11, 30))
        self.time_check.setFixedHeight(40)
        self.time_check.setFixedWidth(120)
        self.time_check.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row_check.addWidget(self.time_check)
        
        self.chk_check_enabled = AnimatedToggle(active_color=tc("accent"))
        self.chk_check_enabled.setChecked(True)
        row_check.addWidget(self.chk_check_enabled)
        row_check.addStretch()
        schedule_layout.addLayout(row_check)
        
        # Kritik Stok Uyarısı
        row_stock = QHBoxLayout()
        row_stock.setSpacing(18)
        lbl_stock = QLabel("Kritik Stok")
        lbl_stock.setStyleSheet(theme_qss("color: @text; font-weight: 600; min-width: 140px;"))
        row_stock.addWidget(lbl_stock)
        
        self.time_stock = QTimeEdit()
        self.time_stock.setDisplayFormat("HH:mm")
        self.time_stock.setTime(QTime(15, 0))
        self.time_stock.setFixedHeight(40)
        self.time_stock.setFixedWidth(120)
        self.time_stock.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row_stock.addWidget(self.time_stock)
        
        self.chk_stock_enabled = AnimatedToggle(active_color=tc("accent"))
        self.chk_stock_enabled.setChecked(True)
        row_stock.addWidget(self.chk_stock_enabled)
        row_stock.addStretch()
        schedule_layout.addLayout(row_stock)
        
        # ===== QUIET HOURS (DND) SECTION =====
        dnd_card = QFrame()
        dnd_card.setStyleSheet(theme_qss(
            """
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 16px;
            }
            """
        ))
        dnd_layout = QVBoxLayout(dnd_card)
        dnd_layout.setContentsMargins(20, 20, 20, 20)
        dnd_layout.setSpacing(16)
        lbl_dnd = QLabel("Sessiz Saatler")
        lbl_dnd.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_dnd.setStyleSheet(theme_qss("color: @text;"))
        dnd_layout.addWidget(lbl_dnd)
        dnd_info = QLabel("Bildirimlerin susturulacağı saat aralığını belirleyin.")
        dnd_info.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; font-size: 12px;"))
        dnd_info.setWordWrap(True)
        dnd_layout.addWidget(dnd_info)
        
        row_dnd = QHBoxLayout()
        row_dnd.setSpacing(18)
        lbl_start = QLabel("Başlangıç")
        lbl_start.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; min-width: 100px;"))
        row_dnd.addWidget(lbl_start)
        
        self.time_dnd_start = QTimeEdit()
        self.time_dnd_start.setDisplayFormat("HH:mm")
        self.time_dnd_start.setTime(QTime(19, 0))
        self.time_dnd_start.setFixedHeight(40)
        self.time_dnd_start.setFixedWidth(120)
        self.time_dnd_start.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row_dnd.addWidget(self.time_dnd_start)
        
        row_dnd.addSpacing(20)
        
        lbl_end = QLabel("Bitiş")
        lbl_end.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; min-width: 100px;"))
        row_dnd.addWidget(lbl_end)
        
        self.time_dnd_end = QTimeEdit()
        self.time_dnd_end.setDisplayFormat("HH:mm")
        self.time_dnd_end.setTime(QTime(8, 30))
        self.time_dnd_end.setFixedHeight(40)
        self.time_dnd_end.setFixedWidth(120)
        self.time_dnd_end.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        row_dnd.addWidget(self.time_dnd_end)
        row_dnd.addStretch()
        dnd_layout.addLayout(row_dnd)
        
        # Kritik override checkbox
        row_critical = QHBoxLayout()
        row_critical.setSpacing(12)
        self.chk_critical_override = QCheckBox("Kritik uyarılarda sessiz modu yoksay")
        self.chk_critical_override.setStyleSheet(theme_qss(
            """
            QCheckBox {
                color: @text_muted;
                font-weight: 600;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 2px solid @border;
                background: @surface;
            }
            QCheckBox::indicator:checked {
                background: @accent;
                border-color: @accent;
            }
            """
        ))
        self.chk_critical_override.setChecked(False)
        row_critical.addWidget(self.chk_critical_override)
        row_critical.addStretch()
        dnd_layout.addLayout(row_critical)
        
        # Load scheduled alerts settings
        self._load_scheduled_alerts()
        
        # Save Button
        self.btn_save = QPushButton("💾 TÜM EĞİTİMİ KAYDET")
        self.btn_save.setFixedHeight(50)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="lg")))
        self.btn_save.clicked.connect(self.save_data)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(schedule_card, 2)
        cards_row.addWidget(dnd_card, 1)
        layout.addLayout(cards_row)
        layout.addWidget(self.btn_save)

    def _wire_ui_signals(self):
        self.chk_loan_enabled.toggled.connect(self.save_data)
        self.chk_check_enabled.toggled.connect(self.save_data)
        self.chk_stock_enabled.toggled.connect(self.save_data)
        self.chk_critical_override.stateChanged.connect(self.save_data)

    def load_data(self):
        path = self.config_path
        if not os.path.exists(path):
            legacy = os.path.join(os.getcwd(), "asistan_ayarlari.json")
            if os.path.exists(legacy):
                path = legacy
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {}

        original_snapshot = json.dumps(self.data, ensure_ascii=False, sort_keys=True) if isinstance(self.data, dict) else ""
        self.data = self._normalize_data(self.data)
        self.data = self._sanitize_data(self.data)
        if not self.data:
            self.data = self._normalize_data(self._default_scenarios())
            self._persist_voice_data()
        elif json.dumps(self.data, ensure_ascii=False, sort_keys=True) != original_snapshot:
            self._persist_voice_data()
        self._sync_active_scenario()

    def _normalize_data(self, raw):
        if not isinstance(raw, dict):
            return {}
        normalized = {}
        for key, val in raw.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if isinstance(val, list):
                normalized[key] = {"triggers": [str(x).strip().lower() for x in val if str(x).strip()]}
            elif isinstance(val, dict):
                triggers = val.get("triggers")
                if triggers is None:
                    triggers = val.get("kelimeler")
                if not isinstance(triggers, list):
                    triggers = []
                action = val.get("action") if isinstance(val.get("action"), dict) else None
                normalized[key] = {"triggers": [str(x).strip().lower() for x in triggers if str(x).strip()]}
                if action:
                    try:
                        if action.get("type") == "page_search":
                            action = {"type": "page", "index": action.get("index"), "auto_search": True}
                    except Exception:
                        pass
                    normalized[key]["action"] = action
            else:
                continue
        return normalized

    def _sanitize_data(self, data):
        defaults = self._default_scenarios()
        sanitized = {}
        keyword_map = {
            "finans": {"type": "builtin", "name": "accounting_summary"},
            "mali": {"type": "builtin", "name": "accounting_summary"},
            "zam": {"type": "builtin", "name": "apply_zam"},
            "kritik stok": {"type": "builtin", "name": "list_critical_stock"},
            "teknisyen": {"type": "builtin", "name": "panel_ac"},
            "müşteri 360": {"type": "builtin", "name": "customer_360"},
        }
        for name, cfg in (data or {}).items():
            item = {"triggers": list(cfg.get("triggers", []))}
            action = cfg.get("action") if isinstance(cfg.get("action"), dict) else None
            haystack = " ".join([name.lower()] + [str(t).lower() for t in item["triggers"]])
            if action:
                item["action"] = action
            if not action:
                for keyword, fixed_action in keyword_map.items():
                    if keyword in haystack:
                        item["action"] = fixed_action.copy()
                        break
            if name in defaults and not item.get("action"):
                item["action"] = defaults[name]["action"].copy()
            sanitized[name] = item
        for name, cfg in defaults.items():
            if name not in sanitized:
                sanitized[name] = {
                    "triggers": list(cfg["triggers"]),
                    "action": cfg["action"].copy(),
                }
        return sanitized

    def _init_action_options(self, combo):
        combo.clear()
        options = [("Ba\u011flant\u0131 Yok (Sadece Komut)", None)]

        options.append(("\U0001f6e0\ufe0f A\u00e7: Teknisyen Paneli", {"type": "builtin", "name": "panel_ac"}))
        options.append(("\U0001f4cb A\u00e7: Yeni Servis", {"type": "builtin", "name": "servis_ac"}))
        options.append(("\U0001f4ca \u00d6zel Fonksiyon: Finansal \u00d6zet", {"type": "builtin", "name": "accounting_summary"}))
        options.append(("\U0001f4c8 \u00d6zel Fonksiyon: Geli\u015fmi\u015f Finansal \u00d6zet", {"type": "builtin", "name": "financial_summary"}))
        options.append(("\U0001f4b8 \u00d6zel Fonksiyon: Stoklara %10 Zam", {"type": "builtin", "name": "apply_zam"}))
        options.append(("\u2714\ufe0f \u00d6zel Fonksiyon: Sesli Onay (Evet)", {"type": "builtin", "name": "confirm_yes"}))
        options.append(("\u274c \u00d6zel Fonksiyon: Sesli Onay (Hay\u0131r)", {"type": "builtin", "name": "confirm_no"}))
        options.append(("\U0001f4c5 \u00d6zel Fonksiyon: Bug\u00fcnk\u00fc Randevular", {"type": "builtin", "name": "check_appointments"}))
        options.append(("\U0001f50a \u00d6zel Fonksiyon: Kritik Stoklar\u0131 Listele", {"type": "builtin", "name": "list_critical_stock"}))
        options.append(("\U0001f4e6 \u00d6zel Fonksiyon: Stok \u00d6zeti", {"type": "builtin", "name": "stock_summary"}))
        options.append(("\u23f0 \u00d6zel Fonksiyon: Sesli Hat\u0131rlat\u0131c\u0131 Ekle", {"type": "builtin", "name": "add_reminder_voice"}))
        options.append(("\U0001f4dd \u00d6zel Fonksiyon: Sesli Not Al", {"type": "builtin", "name": "add_quick_note_voice"}))
        options.append(("\U0001f9ed \u00d6zel Fonksiyon: Y\u00f6netici \u00d6zeti", {"type": "builtin", "name": "managerial_summary"}))
        options.append(("\U0001f527 \u00d6zel Fonksiyon: Cihaz Durumu Sorgula", {"type": "builtin", "name": "device_status_query"}))
        options.append(("\U0001f305 \u00d6zel Fonksiyon: G\u00fcnayd\u0131n Rutini", {"type": "builtin", "name": "greeting_routine"}))
        options.append(("\U0001f319 \u00d6zel Fonksiyon: Kapan\u0131\u015f Rutini", {"type": "builtin", "name": "closing_routine"}))
        options.append(("\U0001f3f7\ufe0f \u00d6zel Fonksiyon: Stok Kar\u015f\u0131la\u015ft\u0131rma", {"type": "builtin", "name": "stock_comparison"}))
        options.append(("\U0001f464 \u00d6zel Fonksiyon: M\u00fc\u015fteri 360", {"type": "builtin", "name": "customer_360"}))
        options.append(("\U0001f4ac \u00d6zel Fonksiyon: \u0130ndirim Tavsiyesi", {"type": "builtin", "name": "discount_advice"}))
        options.append(("\U0001f4b3 \u00d6zel Fonksiyon: Bor\u00e7 \u00d6zeti", {"type": "builtin", "name": "loan_summary"}))
        options.append(("\U0001f9fe \u00d6zel Fonksiyon: \u00c7ek Senet \u00d6zeti", {"type": "builtin", "name": "check_summary"}))
        options.append(("Musteri Borc Durumu", {"type": "builtin", "name": "customer_debt_summary"}))
        options.append(("Servis Is Yuku", {"type": "builtin", "name": "service_workload_summary"}))
        options.append(("Simdi Senkronize Et", {"type": "builtin", "name": "sync_now"}))
        options.append(("Asistan Yetenekleri", {"type": "builtin", "name": "assistant_help"}))

        nav_items = None
        try:
            if self.main_window and hasattr(self.main_window, "get_navigation_map"):
                nav_items = self.main_window.get_navigation_map()
        except Exception:
            nav_items = None

        if nav_items:
            for item in nav_items:
                try:
                    idx = int(item.get("index"))
                    lbl = str(item.get("label") or f"Sayfa {idx}")
                    options.append((f"📄 Sayfa Aç: {lbl}", {"type": "page", "index": idx}))
                except Exception:
                    continue
        else:
            fallback = sorted(PAGE_NAMES.items())
            for idx, lbl in fallback:
                options.append((f"📄 Sayfa Aç: {lbl}", {"type": "page", "index": idx}))

        for label, action in options:
            combo.addItem(label)
            payload = "" if action is None else json.dumps(action, ensure_ascii=False, sort_keys=True)
            combo.setItemData(combo.count() - 1, payload, Qt.ItemDataRole.UserRole)

    def open_scenario_manager(self):
        from .voice_scenario_editor import VoiceScenarioEditorDialog
        dlg = VoiceScenarioEditorDialog(self)
        dlg.exec()
        self._sync_active_scenario()

    def open_new_scenario_dialog(self):
        text, ok = ModernInputDialog.get_text(self.main_window or self, "Yeni Senaryo", "Senaryo adı:")
        if ok and text:
            self.add_scenario(text)
            self.current_scenario_name = text
            self._sync_active_scenario()
            self.open_scenario_manager()

    def add_scenario(self, preset_name=None):
        text = preset_name
        ok = True
        if text is None:
            text, ok = ModernInputDialog.get_text(self.main_window or self, "Yeni Senaryo", "Senaryo adı:")
        if ok and text:
            if text in self.data:
                show_warning(self.main_window or self, "Bu senaryo zaten var.")
                return
            self.data[text] = {"triggers": []}
            self.current_scenario_name = text
            self._sync_active_scenario()
            self._persist_voice_data()

    def delete_scenario(self):
        if self.current_scenario_name:
            self.delete_scenario_by_name(self.current_scenario_name)

    def delete_scenario_by_name(self, key):
        if not key or key not in self.data:
            return
        del self.data[key]
        if self.current_scenario_name == key:
            self.current_scenario_name = next(iter(sorted(self.data.keys())), "")
        self._sync_active_scenario()
        self._persist_voice_data()

    def add_trigger(self):
        if self.current_scenario_name:
            self.add_trigger_to_scenario(self.current_scenario_name, "")

    def add_trigger_to_scenario(self, scenario, trigger_text):
        if not scenario:
            show_warning(self.main_window or self, "Önce bir senaryo seçiniz.")
            return
        text = str(trigger_text or "").strip().lower()
        if not text:
            return
        cfg = self.data.get(scenario)
        if not isinstance(cfg, dict):
            cfg = {"triggers": []}
            self.data[scenario] = cfg
        triggers = cfg.get("triggers")
        if not isinstance(triggers, list):
            triggers = []
            cfg["triggers"] = triggers
        if text not in triggers:
            triggers.append(text)
            self.current_scenario_name = scenario
            self._sync_active_scenario()
            self._persist_voice_data()
        else:
            show_warning(self.main_window or self, "Bu kelime zaten ekli.")

    def delete_trigger(self):
        return

    def delete_trigger_from_scenario(self, scenario, trigger):
        cfg = self.data.get(scenario)
        triggers = cfg.get("triggers") if isinstance(cfg, dict) else None
        if isinstance(triggers, list) and trigger in triggers:
            triggers.remove(trigger)
            self.current_scenario_name = scenario
            self._sync_active_scenario()
            self._persist_voice_data()

    def set_scenario_action(self, scenario, payload, auto_search=False):
        if not scenario:
            return
        cfg = self.data.get(scenario)
        if not isinstance(cfg, dict):
            cfg = {"triggers": []}
            self.data[scenario] = cfg
        if not payload:
            cfg.pop("action", None)
        else:
            try:
                action = json.loads(payload)
                if isinstance(action, dict):
                    if action.get("type") == "page":
                        action["auto_search"] = bool(auto_search)
                    cfg["action"] = action
                else:
                    cfg.pop("action", None)
            except Exception:
                cfg.pop("action", None)
        self.current_scenario_name = scenario
        self._sync_active_scenario()
        self._persist_voice_data()

    def _sync_active_scenario(self):
        if not self.data:
            self.lbl_active_scenario.setText("Aktif senaryo: Henüz seçilmedi")
            return
        if not self.current_scenario_name or self.current_scenario_name not in self.data:
            self.current_scenario_name = sorted(self.data.keys())[0]
        cfg = self.data.get(self.current_scenario_name, {})
        trigger_count = len(cfg.get("triggers", [])) if isinstance(cfg, dict) else 0
        action = cfg.get("action") if isinstance(cfg, dict) else None
        action_text = "Bağlantı yok"
        if isinstance(action, dict):
            if action.get("type") == "builtin":
                action_text = action.get("name", "builtin")
            elif action.get("type") == "page":
                action_text = f"Sayfa {action.get('index')}"
        self.lbl_active_scenario.setText(f"Aktif senaryo: {self.current_scenario_name}")
        self.lbl_scenario_meta.setText(f"{self.current_scenario_name}: {trigger_count} tetikleyici, işlem: {action_text}. Düzenleme için modern pencereyi açabilirsiniz.")

    def _load_scheduled_alerts(self):
        """Zamanlanmış uyarıları ve DND ayarlarını yükle"""
        try:
            alerts = self.db.get_all_scheduled_alerts()
            
            for row in alerts:
                alert = dict(row)
                alert_type = alert['alert_type']
                trigger_time = alert['trigger_time']  # 'HH:mm'
                is_enabled = bool(alert.get('is_enabled', 1))
                
                hour, minute = map(int, trigger_time.split(':'))
                qt_time = QTime(hour, minute)
                
                if alert_type == 'loan_reminder':
                    self.time_loan.setTime(qt_time)
                    self.chk_loan_enabled.setChecked(is_enabled)
                elif alert_type == 'check_reminder':
                    self.time_check.setTime(qt_time)
                    self.chk_check_enabled.setChecked(is_enabled)
                elif alert_type == 'stock_critical':
                    self.time_stock.setTime(qt_time)
                    self.chk_stock_enabled.setChecked(is_enabled)
        except Exception as e:
            logger.error(f"Error loading scheduled alerts: {e}")
        
        # Load DND settings
        try:
            dnd_start = self.db.get_setting('quiet_hours_start', '19:00')
            dnd_end = self.db.get_setting('quiet_hours_end', '08:30')
            critical_override = self.db.get_setting('critical_override_dnd', '0') == '1'
            
            hour, minute = map(int, dnd_start.split(':'))
            self.time_dnd_start.setTime(QTime(hour, minute))
            
            hour, minute = map(int, dnd_end.split(':'))
            self.time_dnd_end.setTime(QTime(hour, minute))
            
            self.chk_critical_override.setChecked(critical_override)
        except Exception as e:
            logger.error(f"Error loading DND settings: {e}")
    
    def _save_scheduled_alerts(self):
        """Zamanlanmış uyarıları ve DND ayarlarını kaydet"""
        # Save scheduled alerts
        try:
            loan_time = self.time_loan.time().toString("HH:mm")
            check_time = self.time_check.time().toString("HH:mm")
            stock_time = self.time_stock.time().toString("HH:mm")
            
            self.db.update_scheduled_alert('loan_reminder', 
                trigger_time=loan_time, 
                is_enabled=self.chk_loan_enabled.isChecked())
            
            self.db.update_scheduled_alert('check_reminder', 
                trigger_time=check_time, 
                is_enabled=self.chk_check_enabled.isChecked())
            
            self.db.update_scheduled_alert('stock_critical', 
                trigger_time=stock_time, 
                is_enabled=self.chk_stock_enabled.isChecked())
        except Exception as e:
            logger.error(f"Error saving scheduled alerts: {e}")
        
        # Save DND settings
        try:
            dnd_start = self.time_dnd_start.time().toString("HH:mm")
            dnd_end = self.time_dnd_end.time().toString("HH:mm")
            
            self.db.set_setting('quiet_hours_start', dnd_start)
            self.db.set_setting('quiet_hours_end', dnd_end)
            self.db.set_setting('critical_override_dnd', '1' if self.chk_critical_override.isChecked() else '0')
        except Exception as e:
            logger.error(f"Error saving DND settings: {e}")

    def save_data(self):
        try:
            self._persist_voice_data()
            
            # Save scheduled alerts too
            self._save_scheduled_alerts()
            
            show_success(self.main_window or self, "Eğitim verileri ve zamanlanmış uyarılar kaydedildi.")
        except Exception as e:
            show_error(self.main_window or self, f"Kaydetme hatası: {e}")

    def _persist_voice_data(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def load_default_scenarios(self):
        defaults = self._default_scenarios()
        added = 0
        for name, payload in defaults.items():
            if name not in self.data:
                self.data[name] = payload
                added += 1
        self.data = self._normalize_data(self.data)
        self.data = self._sanitize_data(self.data)
        self._sync_active_scenario()
        self._persist_voice_data()
        if added:
            show_success(self.main_window or self, f"{added} hazır senaryo eklendi.")
        else:
            show_warning(self.main_window or self, "Hazır senaryolar zaten ekli.")

    def repair_legacy_scenarios(self):
        before = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        self.data = self._sanitize_data(self._normalize_data(self.data))
        defaults = self._default_scenarios()
        for name, payload in defaults.items():
            if name not in self.data:
                self.data[name] = payload
        after = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        self._persist_voice_data()
        self._sync_active_scenario()
        if before != after:
            show_success(self.main_window or self, "Eski senaryolar temizlenip doğru varsayılanlarla hizalandı.")
        else:
            show_warning(self.main_window or self, "Düzeltilecek eski senaryo bulunmadı.")

    def test_active_scenario(self):
        if not self.current_scenario_name or self.current_scenario_name not in self.data:
            show_warning(self.main_window or self, "Önce bir senaryo seçin veya ekleyin.")
            return
        from src.utils.asistan_motoru import BulutAsistan
        assistant = BulutAsistan()
        wake_words = assistant._get_wake_words()
        wake_word = wake_words[0] if wake_words else "asistan"
        sample, ok = ModernInputDialog.get_text(
            self.main_window or self,
            "Aktif Senaryoyu Test Et",
            f"Komutu tam cümle olarak yazın. Örn: {wake_word} finans özet",
            f"{wake_word} "
        )
        if not ok or not str(sample).strip():
            return
        result = {}

        def _capture(action, payload):
            result["action"] = action
            result["payload"] = payload

        assistant.tetik_sinyali.connect(_capture)
        assistant.komut_coz(sample)
        if result:
            self.lbl_test_result.setText(
                f"Son test sonucu: {sample}\nAksiyon: {result['action']}\nParametre: {result.get('payload', '') or '-'}"
            )
            show_success(self.main_window or self, f"Tetiklendi: {result['action']} | Parametre: {result.get('payload', '')}")
        else:
            self.lbl_test_result.setText(f"Son test sonucu: {sample}\nAksiyon: Tetiklenmedi\nParametre: -")
            show_warning(self.main_window or self, "Komut tetiklenmedi. Uyanma adı ve tetikleyicileri kontrol edin.")

    def run_healthcheck(self):
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
            script_path = os.path.join(project_root, "scripts", "voice_scenario_healthcheck.py")
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=25,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            if result.returncode != 0:
                self.lbl_test_result.setText(f"Sağlık testi başarısız.\nÇıkış kodu: {result.returncode}\nHata: {stderr or stdout or '-'}")
                show_error(self.main_window or self, "Sağlık testi çalıştırılamadı.")
                return

            json_start = stdout.find("{")
            if json_start < 0:
                self.lbl_test_result.setText(f"Sağlık testi çıktısı okunamadı.\nÇıktı: {stdout or '-'}")
                show_warning(self.main_window or self, "Sağlık testi çıktısı çözümlenemedi.")
                return

            data = json.loads(stdout[json_start:])
            self.last_healthcheck_result = data
            total = len(data.get("scenario_results", []))
            passed = sum(1 for item in data.get("scenario_results", []) if item.get("ok"))
            db_total = len(data.get("db_dependency_results", []))
            db_passed = sum(1 for item in data.get("db_dependency_results", []) if item.get("ok"))
            wake_word = data.get("wake_word", "-")
            overall_ok = bool(data.get("overall_ok"))
            status = "Başarılı" if overall_ok else "Sorun Var"
            self.lbl_test_result.setText(
                f"Sağlık testi: {status}\n"
                f"Uyanma adı: {wake_word}\n"
                f"Senaryo testi: {passed}/{total}\n"
                f"Bağımlılık testi: {db_passed}/{db_total}"
            )
            self.btn_healthcheck_details.setVisible(True)
            if overall_ok:
                show_success(self.main_window or self, f"Sesli asistan sağlık testi başarılı: {passed}/{total}")
            else:
                failed = [item.get("phrase", item.get("name", "?")) for item in data.get("scenario_results", []) if not item.get("ok")]
                failed += [item.get("name", "?") for item in data.get("db_dependency_results", []) if not item.get("ok")]
                show_warning(self.main_window or self, f"Sağlık testinde sorun bulundu: {', '.join(failed[:4])}")
        except Exception as e:
            logger.error(f"Voice healthcheck run error: {e}")
            self.last_healthcheck_result = None
            self.lbl_test_result.setText(f"Sağlık testi sırasında hata oluştu:\n{e}")
            self.btn_healthcheck_details.setVisible(False)
            show_error(self.main_window or self, f"Sağlık testi hatası: {e}")

    def open_healthcheck_details(self):
        if not self.last_healthcheck_result:
            show_warning(self.main_window or self, "Önce sağlık testini çalıştırın.")
            return
        from .voice_healthcheck_dialog import VoiceHealthcheckResultDialog
        dlg = VoiceHealthcheckResultDialog(self.main_window or self, self.last_healthcheck_result)
        dlg.exec()
