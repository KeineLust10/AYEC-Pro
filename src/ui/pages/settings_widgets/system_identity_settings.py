# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.animated_toggle import AnimatedToggle as ToggleSwitch
from src.utils.design_system import DesignTokens
from src.utils.language_manager import LanguageManager
from src.utils.path_helper import PathHelper
from src.utils.role_utils import is_admin_role
from src.utils.system_config import SYSTEM_MODES, SystemConfig
from src.utils.theme_colors import tc, theme_qss
from src.utils.toast_notification import show_error, show_success


class SystemIdentitySettingsWidget(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.lang = LanguageManager()
        current_user = getattr(main_window, "current_user", {}) if main_window else {}
        self._can_change_sector = main_window is None or is_admin_role(
            dict(current_user or {}).get("role")
        )
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setObjectName("SystemIdentitySettingsRoot")
        self.setStyleSheet(
            theme_qss(
                """
                QWidget#SystemIdentitySettingsRoot { color: @text; background: transparent; }
                QWidget#SystemIdentitySettingsRoot QGroupBox { color: @text; }
                QWidget#SystemIdentitySettingsRoot QGroupBox::title { color: @text; subcontrol-origin: margin; left: 12px; padding: 0 4px; }
                QWidget#SystemIdentitySettingsRoot QLabel { color: @text; background: transparent; }
                QWidget#SystemIdentitySettingsRoot QComboBox {
                    background-color: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 6px;
                    padding: 6px 8px;
                }
                """
            )
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("⚙️ Sistem Kimliği & Modüler Yapı")
        title.setStyleSheet(theme_qss("font-size: 20px; font-weight: bold; color: @text;"))
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setSpacing(20)

        self._build_sector_group()
        self._build_modules_group()
        self._build_features_group()
        self._build_system_info_group()
        self._build_startup_group()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_save = QPushButton("💾 Değişiklikleri Uygula ve Kaydet")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success")))
        btn_save.setFixedHeight(45)
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)

    def _build_sector_group(self):
        group_sector = QGroupBox("1. Sektörel Kimlik (Master Switch)")
        group_sector.setStyleSheet(theme_qss("font-weight: bold; padding-top: 20px;"))
        sector_layout = QVBoxLayout(group_sector)

        self.cmb_sector = QComboBox()
        self.cmb_sector.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        for key, mode in SYSTEM_MODES.items():
            self.cmb_sector.addItem(f"{mode['icon']} {mode['display_name']}", key)
        self.cmb_sector.currentIndexChanged.connect(self.on_sector_changed)
        self.cmb_sector.setEnabled(self._can_change_sector)
        if not self._can_change_sector:
            self.cmb_sector.setToolTip(
                "Sekt\u00f6r de\u011fi\u015fikli\u011fi i\u00e7in firma y\u00f6neticisi yetkisi gerekir."
            )

        sector_layout.addWidget(QLabel("Ana çalışma modu:"))
        sector_layout.addWidget(self.cmb_sector)

        self.lbl_warning = QLabel("⚠️ Dikkat: Sektör değişikliği menü yapısını ve etiketleri yeniden düzenler.")
        self.lbl_warning.setStyleSheet(theme_qss("color: @warning; font-style: italic; font-size: 11px;"))
        sector_layout.addWidget(self.lbl_warning)

        sector_layout.addWidget(QLabel("Cihaz katalog is kollari:"))
        self.device_profile_checks = {}
        profile_row = QHBoxLayout()
        for profile_id, label in (
            ("bilgisayar", "Bilgisayar"),
            ("cep_telefonu", "Cep Telefonu"),
            ("akilli_ev", "Akilli Ev"),
        ):
            checkbox = QCheckBox(label)
            checkbox.setChecked(profile_id == "bilgisayar")
            self.device_profile_checks[profile_id] = checkbox
            profile_row.addWidget(checkbox)
        profile_row.addStretch()
        sector_layout.addLayout(profile_row)

        profile_hint = QLabel(
            "Secilen kataloglar Yeni Servis Kaydi ve Yeni Cihaz Ekle alanlarini filtreler."
        )
        profile_hint.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        sector_layout.addWidget(profile_hint)

        self.container_layout.addWidget(group_sector)

    def _build_modules_group(self):
        group_modules = QGroupBox("2. Modül Paketleri (Toggle Switch)")
        group_modules.setStyleSheet(theme_qss("font-weight: bold; padding-top: 20px;"))
        self.module_layout = QGridLayout(group_modules)

        self.module_toggles = {}
        modules = [
            ("operations", "🔧 Servis & Operasyon Yönetimi"),
            ("finance", "💰 Finans & Banka Yönetimi"),
            ("stock", "📦 Stok & Depo Takibi"),
            ("projects", "🏗️ Proje / İş Takibi"),
            ("crm", "🤝 Müşteri İlişkileri (CRM)"),
            ("personnel", "👥 Personel & Bordro"),
            ("asistan", "🤖 Sesli Asistan & Kısayollar"),
        ]

        for i, (key, label) in enumerate(modules):
            row, col = divmod(i, 2)
            toggle = ToggleSwitch(active_color=tc("success"))
            self.module_toggles[key] = toggle
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("font-weight: normal;"))

            line = QHBoxLayout()
            line.addWidget(lbl)
            line.addStretch()
            line.addWidget(toggle)
            self.module_layout.addLayout(line, row, col)

        self.container_layout.addWidget(group_modules)

    def _build_features_group(self):
        group_features = QGroupBox("3. Özellik Bazlı Kontroller")
        group_features.setStyleSheet(theme_qss("font-weight: bold; padding-top: 20px;"))
        self.feature_layout = QGridLayout(group_features)

        self.feature_toggles = {}
        features = [
            ("wizard_upload", "📎 Sihirbazda dosya yükleme"),
            ("iban_verify", "✅ Otomatik IBAN doğrulama"),
            ("voice_alerts", "🔊 Sesli uyarılar"),
            ("scheduled_alerts", "📅 Zaman ayarlı duyurular"),
            ("usage_guides", "📖 Kullanım kılavuzu sekmeleri"),
        ]

        for i, (key, label) in enumerate(features):
            row, col = divmod(i, 2)
            toggle = ToggleSwitch(active_color=tc("accent"))
            self.feature_toggles[key] = toggle
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("font-weight: normal;"))

            line = QHBoxLayout()
            line.addWidget(lbl)
            line.addStretch()
            line.addWidget(toggle)
            self.feature_layout.addLayout(line, row, col)

        self.container_layout.addWidget(group_features)

    def _table_has_column(self, table_name, column_name):
        try:
            if hasattr(self.db, "_get_table_columns"):
                return column_name in set(self.db._get_table_columns(table_name) or [])
        except Exception:
            pass
        return False

    def _safe_scalar(self, query, params=(), default=0):
        try:
            row = self.db.cursor.execute(query, params).fetchone()
            return row[0] if row else default
        except Exception:
            return default

    def _build_system_info_group(self):
        group_system_info = QGroupBox("4. Sistem ve Veritabani Bilgileri")
        group_system_info.setStyleSheet(theme_qss("font-weight: bold; padding-top: 20px;"))
        system_info_layout = QVBoxLayout(group_system_info)

        import os
        db_path = PathHelper.get_db_path()
        db_exists = os.path.exists(db_path)
        db_size = os.path.getsize(db_path) / (1024 * 1024) if db_exists else 0

        parts_count = 0
        movements_count = 0
        accounting_stock_count = 0
        try:
            if db_exists and self.db:
                parts_where = "WHERE COALESCE(is_deleted, 0)=0" if self._table_has_column("parts", "is_deleted") else ""
                parts_count = int(self._safe_scalar(f"SELECT COUNT(*) FROM parts {parts_where}", default=0) or 0)
                movements_count = int(self._safe_scalar("SELECT COUNT(*) FROM stock_movements", default=0) or 0)
                accounting_stock_count = int(
                    self._safe_scalar(
                        "SELECT COUNT(*) FROM accounting WHERE COALESCE(description, '') LIKE '%Stok%'",
                        default=0,
                    ) or 0
                )
        except Exception:
            pass

        info_style = (
            "font-weight: normal; color: @text_muted; font-size: 12px; "
            "padding: 5px; background: @surface_alt; border-radius: 4px; margin: 2px 0;"
        )

        entries = [
            f"📂 Veritabanı yolu: <b>{db_path}</b>",
            f"{'✅' if db_exists else '❌'} Durum: {'Mevcut' if db_exists else 'Bulunamadı'}",
            f"💾 Dosya boyutu: <b>{db_size:.2f} MB</b>",
            f"📦 Toplam ürün/parça: <b>{parts_count}</b>",
            f"📊 Stok hareketleri: <b>{movements_count}</b>",
            f"💰 Stok muhasebe kayıtları: <b>{accounting_stock_count}</b>",
        ]

        for text in entries:
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(theme_qss(info_style))
            system_info_layout.addWidget(lbl)

        btn_copy_path = QPushButton("📋 Veritabanı yolunu kopyala")
        btn_copy_path.setStyleSheet(
            theme_qss(
                "background-color: @accent; color: @selection_text; padding: 8px; "
                "border-radius: 4px; font-weight: 600; font-size: 12px; border: none;"
            )
        )
        btn_copy_path.setFixedHeight(36)
        btn_copy_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_path.clicked.connect(lambda: self.copy_db_path(db_path))
        system_info_layout.addWidget(btn_copy_path)

        btn_open_folder = QPushButton("📁 Veritabanı klasörünü aç")
        btn_open_folder.setStyleSheet(
            theme_qss(
                "background-color: @success; color: @selection_text; padding: 8px; "
                "border-radius: 4px; font-weight: 600; font-size: 12px; border: none;"
            )
        )
        btn_open_folder.setFixedHeight(36)
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.clicked.connect(lambda: self.open_db_folder(db_path))
        system_info_layout.addWidget(btn_open_folder)

        is_frozen_fn = getattr(PathHelper, "_is_frozen", None)
        is_frozen = bool(is_frozen_fn()) if callable(is_frozen_fn) else False
        mode_text = "🔒 Frozen (Yüklü Uygulama)" if is_frozen else "🐍 Development (Geliştirme Modu)"
        lbl_mode = QLabel(f"⚙️ Yükleme modu: <b>{mode_text}</b>")
        lbl_mode.setTextFormat(Qt.TextFormat.RichText)
        lbl_mode.setStyleSheet(theme_qss(info_style))
        system_info_layout.addWidget(lbl_mode)

        self.container_layout.addWidget(group_system_info)

    def _build_startup_group(self):
        group_startup = QGroupBox("5. Başlangıç ve Kısayol Ayarları")
        group_startup.setStyleSheet(theme_qss("font-weight: bold; padding-top: 20px;"))
        startup_layout = QVBoxLayout(group_startup)

        line = QHBoxLayout()
        lbl_startup = QLabel("Windows başlangıcında otomatik çalıştır")
        lbl_startup.setStyleSheet(theme_qss("font-weight: normal;"))
        self.toggle_startup = ToggleSwitch(active_color=tc("primary"))

        if self.main_window and hasattr(self.main_window, "is_in_windows_startup"):
            self.toggle_startup.setChecked(self.main_window.is_in_windows_startup())
            self.toggle_startup.toggled.connect(self.main_window.toggle_windows_startup)

        line.addWidget(lbl_startup)
        line.addStretch()
        line.addWidget(self.toggle_startup)
        startup_layout.addLayout(line)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        btn_desktop = QPushButton("Masaüstü kısayolu oluştur")
        btn_desktop.setStyleSheet(
            theme_qss(
                "background-color: @surface_alt; color: @text; padding: 8px; border-radius: 4px; "
                "font-weight: normal; border: 1px solid @border;"
            )
        )
        btn_desktop.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.main_window and hasattr(self.main_window, "create_desktop_shortcut"):
            btn_desktop.clicked.connect(
                lambda: show_success(self, "Başarılı", "Masaüstü kısayolu oluşturuldu.")
                if self.main_window.create_desktop_shortcut()
                else None
            )

        btn_start_menu = QPushButton("Başlangıç menüsü kısayolu oluştur")
        btn_start_menu.setStyleSheet(
            theme_qss(
                "background-color: @surface_alt; color: @text; padding: 8px; border-radius: 4px; "
                "font-weight: normal; border: 1px solid @border;"
            )
        )
        btn_start_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.main_window and hasattr(self.main_window, "create_start_menu_shortcut"):
            btn_start_menu.clicked.connect(
                lambda: show_success(self, "Başarılı", "Başlangıç menüsü kısayolu oluşturuldu.")
                if self.main_window.create_start_menu_shortcut()
                else None
            )

        buttons.addWidget(btn_desktop)
        buttons.addWidget(btn_start_menu)
        buttons.addStretch()
        startup_layout.addLayout(buttons)

        self.container_layout.addWidget(group_startup)

    def on_sector_changed(self, index):
        sector_key = self.cmb_sector.currentData()
        mode = SYSTEM_MODES[sector_key]
        for key, toggle in self.module_toggles.items():
            toggle.setChecked(key in mode["active_modules"])

    def load_settings(self):
        sec = SystemConfig.get_current_sector(self.db)
        idx = self.cmb_sector.findData(sec)
        if idx >= 0:
            self.cmb_sector.setCurrentIndex(idx)

        default_modules = set(SystemConfig.get_default_active_modules(sec))
        for key, toggle in self.module_toggles.items():
            val = self.db.get_internal_setting(
                f"module_{key}_active",
                "1" if key in default_modules else "0",
            )
            toggle.setChecked(val == "1")

        for key, toggle in self.feature_toggles.items():
            val = self.db.get_internal_setting(f"feature_{key}_active", "1")
            toggle.setChecked(val == "1")

        raw_profiles = self.db.get_internal_setting("device_business_profiles", "bilgisayar")
        selected_profiles = {
            item.strip() for item in str(raw_profiles or "").split(",") if item.strip()
        }
        for profile_id, checkbox in self.device_profile_checks.items():
            checkbox.setChecked(profile_id in selected_profiles)

    def save_settings(self):
        sector_key = SystemConfig.normalize_sector(self.cmb_sector.currentData())
        current_sector = SystemConfig.get_current_sector(self.db)
        if sector_key != current_sector and not self._can_change_sector:
            self.load_settings()
            show_error(
                self,
                "Sekt\u00f6r de\u011fi\u015fikli\u011fi i\u00e7in firma y\u00f6neticisi yetkisi gerekir.",
            )
            return
        sector_changed = sector_key != current_sector

        mode_data = SYSTEM_MODES[sector_key]
        for l_key, l_val in mode_data.get("labels", {}).items():
            self.lang.update_label(l_key, l_val)

        for key, toggle in self.module_toggles.items():
            self.db.set_internal_setting(f"module_{key}_active", "1" if toggle.isChecked() else "0")

        for key, toggle in self.feature_toggles.items():
            self.db.set_internal_setting(f"feature_{key}_active", "1" if toggle.isChecked() else "0")

        selected_profiles = [
            profile_id for profile_id, checkbox in self.device_profile_checks.items()
            if checkbox.isChecked()
        ]
        if not selected_profiles:
            selected_profiles = ["bilgisayar"]
            self.device_profile_checks["bilgisayar"].setChecked(True)
        self.db.set_internal_setting("device_business_profiles", ",".join(selected_profiles))

        show_success(self, "Sistem Yapılandırması Güncellendi", "Değişiklikler anında uygulandı.")

        if self.main_window:
            if sector_changed and hasattr(self.main_window, "apply_sector_change"):
                self.main_window.apply_sector_change(sector_key)
            elif hasattr(self.main_window, "refresh_side_menu"):
                if sector_changed:
                    self.db.set_internal_setting("current_sector", sector_key)
                self.main_window.refresh_side_menu()
            self.lang.labels_updated.emit()
        else:
            self.db.set_internal_setting("current_sector", sector_key)

    def copy_db_path(self, db_path):
        try:
            from PyQt6.QtWidgets import QApplication

            QApplication.clipboard().setText(db_path)
            show_success(self, "Kopyalandı", f"Veritabanı yolu panoya kopyalandı:\n{db_path}")
        except Exception as e:
            show_error(self, f"Kopyalama hatası: {str(e)}")

    def open_db_folder(self, db_path):
        try:
            import os
            import platform
            import subprocess

            folder_path = os.path.dirname(db_path)

            if platform.system() == "Windows":
                subprocess.Popen(["explorer", "/select,", db_path])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])

            show_success(self, "Klasör Açıldı", f"Veritabanı klasörü açıldı:\n{folder_path}")
        except Exception as e:
            show_error(self, f"Klasör açma hatası: {str(e)}")
