# -*- coding: utf-8 -*-

from datetime import datetime
from PyQt6.QtWidgets import QDialog
from src.ui.components.modern_dialog import ModernDialog
from src.ui.components.message_box import ModernMessage
from src.ui.dialogs.password_prompt_dialog import PasswordPromptDialog
from src.utils.auth_manager import AuthManager
from src.utils.currency_helper import CurrencyHelper
from src.utils.message_helper import show_question
from src.utils.theme_colors import theme_qss

class AccountingFiscalMixin:
    def _legacy_handle_fiscal_rollover(self):
        fiscal_service = getattr(self.main_window, "fiscal_service", None)
        if not fiscal_service:
            ModernMessage.show_error(self, "Mali yıl servisi başlatılamadı.", "Servis Hatası")
            return

        snapshot = fiscal_service.get_status_snapshot()
        reply = show_question(
            self,
            "Yeni Mali Yıla Geçiş",
            "Manuel mali yıl devir işlemi başlatılsın mı?\n\n"
            f"Planlı devir tarihi: {snapshot.get('rollover_date', '-')}\n"
            f"Planlı reset tarihi: {snapshot.get('reset_date', '-')}\n"
            f"Son devir: {snapshot.get('last_rollover', '-')}\n"
            f"Son durum: {snapshot.get('last_status', '-')}\n\n"
            "Bu işlem mevcut veritabanını arşivler ve yalnızca devir anında yeni mali yılı açar.",
        )
        if int(reply) != 16384:
            return

        current_user = getattr(self.main_window, "current_user", {}) or {}
        username = current_user.get("username", "Kullanıcı")
        full_name = current_user.get("name") or current_user.get("full_name") or username
        pwd_dialog = PasswordPromptDialog(username, full_name, self)
        if pwd_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        auth_manager = AuthManager(self.db)
        auth_manager.current_user = current_user
        if not auth_manager.verify_action_password(pwd_dialog.password_value):
            ModernMessage.show_error(self, "Hatalı kullanıcı şifresi. Mali yıl devri iptal edildi.", "Şifre Hatası")
            return

        result = fiscal_service.trigger_manual_rollover()
        if not result.get("ok"):
            archive_name = result.get("archive_name") or "-"
            detail = result.get("error", "Bilinmeyen hata")
            if archive_name != "-":
                detail = f"{detail}\n\nOluşan arşiv: {archive_name}"
            ModernMessage.show_error(self, f"Manuel mali yıl devri başarısız: {detail}", "Mali Yıl Hatası")
            self.populate_fiscal_year_selector()
            self.refresh_data()
            return

        snapshot = result.get("snapshot", {})
        archive_name = result.get("archive_name") or "oluşturulamadı"
        ModernMessage.show_info(
            self,
            "Manuel mali yıl devir işlemi tamamlandı.\n\n"
            f"Arşiv: {archive_name}\n"
            f"Aktif mali yıl: {snapshot.get('fiscal_year_start', '-')}\n"
            f"Bir sonraki planlı devir: {snapshot.get('rollover_date', '-')}",
            "Mali Yıl Devri",
        )
        self.populate_fiscal_year_selector()
        self.refresh_data()

    def handle_fiscal_rollover(self):
        """Run the protected fiscal rollover wizard."""
        fiscal_service = getattr(self.main_window, "fiscal_service", None)
        if not fiscal_service:
            ModernMessage.show_error(
                self, "Mali yil servisi baslatilamadi.", "Servis Hatasi"
            )
            return

        from src.ui.dialogs.fiscal_rollover_wizard import FiscalRolloverWizard

        wizard = FiscalRolloverWizard(fiscal_service, self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        if not wizard.is_accountant_approved():
            return

        current_user = getattr(self.main_window, "current_user", {}) or {}
        username = current_user.get("username", "Kullanici")
        full_name = current_user.get("name") or current_user.get("full_name") or username
        password_dialog = PasswordPromptDialog(username, full_name, self)
        if password_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        auth_manager = AuthManager(self.db)
        auth_manager.current_user = current_user
        if not auth_manager.verify_action_password(password_dialog.password_value):
            ModernMessage.show_error(
                self,
                "Hatali kullanici sifresi. Mali yil devri iptal edildi.",
                "Sifre Hatasi",
            )
            return

        result = fiscal_service.trigger_manual_rollover(
            selections=wizard.selected_options(), approved_by=username
        )
        if not result.get("ok"):
            archive_name = result.get("archive_name") or "-"
            detail = result.get("error", "Bilinmeyen hata")
            if archive_name != "-":
                detail = f"{detail}\n\nOlusan arsiv: {archive_name}"
            ModernMessage.show_error(
                self,
                f"Manuel mali yil devri basarisiz: {detail}",
                "Mali Yil Hatasi",
            )
            self.populate_fiscal_year_selector()
            self.refresh_data()
            return

        snapshot = result.get("snapshot", {})
        archive_name = result.get("archive_name") or "olusturulamadi"
        ModernMessage.show_info(
            self,
            "Manuel mali yil devir islemi tamamlandi.\n\n"
            f"Arsiv: {archive_name}\n"
            f"Aktif mali yil: {snapshot.get('fiscal_year_start', '-')}\n"
            f"Bir sonraki planli devir: {snapshot.get('rollover_date', '-')}",
            "Mali Yil Devri",
        )
        self.populate_fiscal_year_selector()
        self.refresh_data()

    def show_fiscal_opening_report(self):
        fiscal_service = getattr(self.main_window, "fiscal_service", None)
        report = fiscal_service.get_last_opening_report() if fiscal_service else {}
        if not report:
            ModernMessage.show_info(self, "Kayıtlı bir yılbaşı açılış raporu bulunamadı.\nÖnce mali yıl devri çalışmış olmalı.", "Yılbaşı Raporu")
            return
        message = (
            f"Açılış Tarihi: {report.get('opening_date', '-')}\n"
            f"Arşiv: {report.get('archive_name', '-')}\n"
            f"Oluşan Açılış Fişi: {report.get('opening_count', 0)}\n\n"
            f"Banka Devri: {report.get('bank_count', 0)} hesap | "
            f"{CurrencyHelper.format_try_for_display(report.get('bank_total_try', 0), db=self.db, include_try_reference=False)}\n"
            f"Cari Alacak Devri: {CurrencyHelper.format_try_for_display(report.get('receivable_total_try', 0), db=self.db, include_try_reference=False)}\n"
            f"Müşteri Avans Devri: {CurrencyHelper.format_try_for_display(report.get('advance_total_try', 0), db=self.db, include_try_reference=False)}\n\n"
            f"Sonraki Planlı Devir: {report.get('next_rollover_date', '-')}"
        )
        ModernMessage.show_info(self, message, "Yılbaşı Başlangıç Raporu")

    def populate_fiscal_year_selector(self):
        try:
            fiscal_start = str(self.db.get_internal_setting("fiscal_year_start", "") or "").strip()
            current_year = int((fiscal_start or str(datetime.now().year))[:4])
            if current_year > datetime.now().year:
                current_year = datetime.now().year
        except Exception:
            current_year = datetime.now().year
        current_archive = ""
        if getattr(self.main_window, "is_archive_mode", False):
            db_path = str(getattr(getattr(self.main_window, "db", None), "_db_path", "") or "")
            if "archive_" in db_path.lower():
                current_archive = db_path.split("\\")[-1]

        self.cmb_fiscal_year.blockSignals(True)
        self.cmb_fiscal_year.clear()
        self.cmb_fiscal_year.addItem(f"Canlı ({current_year})", ("live", current_year, ""))
        archives = []
        if hasattr(self.main_window, "get_available_archives"):
            try: archives = self.main_window.get_available_archives() or []
            except Exception: archives = []
        selected_index = 0
        for archive in archives:
            year_text = archive.replace("archive_", "").replace(".db", "")
            label = f"Mali Yıl {year_text}" if year_text.isdigit() else archive
            self.cmb_fiscal_year.addItem(label, ("archive", year_text, archive))
            if archive == current_archive:
                selected_index = self.cmb_fiscal_year.count() - 1
        self.cmb_fiscal_year.setCurrentIndex(selected_index)
        self.cmb_fiscal_year.blockSignals(False)

    def handle_fiscal_year_changed(self, _index):
        payload = self.cmb_fiscal_year.currentData()
        if not payload: return
        mode, _year, archive_name = payload
        is_archive = getattr(self.main_window, "is_archive_mode", False)
        if mode == "live":
            if is_archive and hasattr(self.main_window, "return_to_active_database"):
                if self.main_window.return_to_active_database():
                    self.update_archive_button()
                    self.refresh_data()
            return
        if archive_name and hasattr(self.main_window, "load_archived_database"):
            current_db_path = str(getattr(getattr(self.main_window, "db", None), "_db_path", "") or "")
            if archive_name.lower() in current_db_path.lower(): return
            if self.main_window.load_archived_database(archive_name):
                self.update_archive_button()
                self.refresh_data()

    def update_archive_button(self):
        is_archive = getattr(self.main_window, "is_archive_mode", False)
        if is_archive:
            self.btn_archive.setText("Canlı Sisteme Dön")
            self.btn_archive.setStyleSheet(theme_qss("background: @danger; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: 700; border: 1px solid @danger;"))
        else:
            self.btn_archive.setText("Arşiv (Geçmiş)")
            self.btn_archive.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border-radius: 8px; padding: 10px 20px; font-weight: 700; border: 1px solid @border;"))
        self.populate_fiscal_year_selector()

    def handle_archive_action(self):
        is_archive = getattr(self.main_window, "is_archive_mode", False)
        if is_archive:
            if hasattr(self.main_window, "return_to_active_database"):
                if self.main_window.return_to_active_database():
                    self.update_archive_button()
                    self.refresh_data()
        else:
            if hasattr(self.main_window, "get_available_archives"):
                archives = self.main_window.get_available_archives()
                if not archives:
                    ModernMessage.show_warning(self, "Kayıtlı hiçbir geçmiş yıl arşivi bulunamadı.", "Geçmiş Arşiv Bulunamadı")
                    return
                from src.ui.pages.accounting_page import ArchiveSelectionDialog
                dlg = ArchiveSelectionDialog(self, archives)
                if dlg.exec():
                    if dlg.selected_archive and self.main_window.load_archived_database(dlg.selected_archive):
                        self.update_archive_button()
                        self.refresh_data()
