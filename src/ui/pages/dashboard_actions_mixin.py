# -*- coding: utf-8 -*-

import webbrowser
from urllib.parse import quote

from PyQt6.QtCore import QUrl, QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QMenu,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QWidget,
    QTableWidgetItem,
    QApplication,
)

from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.ui.dialogs.tahsilat_dialog import TahsilatDialog
from src.utils.pdf_manager import PDFManagerQt
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_error, show_success, show_warning
from src.utils.logger import logger
from src.utils.role_utils import is_admin_role
from src.utils.system_config import SystemConfig, SYSTEM_MODES
from src.utils.status_utils import normalize_device_status
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.page_ids import PageIds
from src.ui.pages.dashboard_widgets.stat_card import StatCard
from src.ui.pages.dashboard_widgets.status_badge import StatusBadge
from src.ui.pages.dashboard_widgets.action_widget import ActionWidget


class DashboardActionsMixin:
    def _update_recent_empty_state(self):
        if hasattr(self, "recent_empty_state") and hasattr(self, "table"):
            has_rows = self.table.rowCount() > 0
            self.table.setVisible(has_rows)
            self.recent_empty_state.setVisible(not has_rows)

    def _is_automotive(self):
        """🆕 Otomotiv sektöründe olup olmadığını kontrol et (Plugin aware)"""
        try:
            # Önce plugin system'den kontrol et
            if hasattr(self, "sector_manager") and self.sector_manager:
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            # Fallback: eski yöntem
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def open_service_form_shortcut(self):
        try:
            if self._is_automotive():
                if self.main_window and hasattr(self.main_window, "switch_page"):
                    self.main_window.switch_page(PageIds.VEHICLE_MAINTENANCE)

                    def _open_vehicle_card():
                        try:
                            page = None
                            if hasattr(self.main_window, "get_page"):
                                page = self.main_window.get_page(
                                    PageIds.VEHICLE_MAINTENANCE
                                )
                            if page and hasattr(page, "open_new_card"):
                                page.open_new_card()
                        except Exception as inner_e:
                            self.notify(f"Araç kartı açılamadı: {inner_e}", "error")

                    QTimer.singleShot(150, _open_vehicle_card)
                    return

            self.open_new_service_dialog()
        except Exception as e:
            self.notify(f"Kısayol açılamadı: {e}", "error")

    def open_new_service_dialog(self):
        QTimer.singleShot(0, self._open_new_service_dialog_deferred)

    def _open_new_service_dialog_deferred(self):
        try:
            from src.ui.dialogs.new_service_dialog import NewServiceDialog

            dlg = NewServiceDialog(
                self.db, self, sector_manager=getattr(self, "sector_manager", None)
            )
            if dlg.exec():
                self.refresh_data()
                self.notify("Yeni servis kaydı oluşturuldu.", "success")
        except Exception as e:
            self.notify(f"Kayıt ekranı açılamadı: {e}", "error")

    def open_new_customer_dialog(self):
        QTimer.singleShot(0, self._open_new_customer_dialog_deferred)

    def _open_new_customer_dialog_deferred(self):
        try:
            from src.ui.dialogs.add_customer_dialog import AddCustomerDialog

            dlg = AddCustomerDialog(
                self.db, self, sector_manager=getattr(self, "sector_manager", None)
            )
            if dlg.exec():
                if hasattr(self, "refresh_data"):
                    self.refresh_data()
                if self.main_window and hasattr(
                    self.main_window, "refresh_loaded_page"
                ):
                    self.main_window.refresh_loaded_page(21)
                self.notify("Yeni müşteri kaydı oluşturuldu.", "success")
        except Exception as e:
            self.notify(f"Müşteri ekranı hatası: {e}", "error")

    def on_table_double_click(self, row, column):
        """Müşteri ismine (col 1) çift tıklandığında 360, diğerlerinde düzenleme"""
        if row < 0:
            return
        if getattr(self, "_dashboard_double_click_busy", False):
            return
        self._dashboard_double_click_busy = True

        item_id = self.table.item(row, 0)
        if not item_id:
            self._dashboard_double_click_busy = False
            return

        tracking_no = item_id.text()

        try:
            if column == 1:  # Müşteri Sütunu
                item_cust = self.table.item(row, 1)
                customer_name = item_cust.text() if item_cust else ""
                self.open_customer_360_dialog(customer_name)
            elif column == 2:
                self.open_technician_panel(tracking_no)
            else:
                self.open_edit_dialog(tracking_no)
        finally:
            # Aynı satırda hızlı ardışık çift tıklama ile panelin iki kez açılmasını engelle.
            QTimer.singleShot(
                250, lambda: setattr(self, "_dashboard_double_click_busy", False)
            )

    def open_customer_360_dialog(self, customer_name, tracking_no=None):
        QTimer.singleShot(
            0,
            lambda: self._open_customer_360_dialog_deferred(customer_name, tracking_no),
        )

    def _open_customer_360_dialog_deferred(self, customer_name, tracking_no=None):
        # Müşteri ID'sini bul
        customer_id = None
        try:
            # 1. İsimden dene
            self.db.cursor.execute(
                "SELECT id FROM customers WHERE name=?", (customer_name,)
            )
            row = self.db.cursor.fetchone()
            if row:
                customer_id = row[0]
            elif tracking_no:
                # 2. Takip numarasından dene
                self.db.cursor.execute(
                    "SELECT customer_id FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                    (tracking_no,),
                )
                row = self.db.cursor.fetchone()
                if row:
                    customer_id = row[0]
        except Exception as e:
            logger.error(f"Customer ID lookup error: {e}")

        if customer_id:
            from src.ui.dialogs.customer_360_dialog import Customer360Dialog

            # Fix: Pass correct parent (self.main_window or self, Customer360Dialog expects parent as last arg usually)
            # Checking Customer360Dialog init: (self, db, customer_id, customer_name, parent=None)
            dlg = Customer360Dialog(
                self.db,
                customer_id,
                customer_name,
                self.main_window,
                sector_manager=getattr(self, "sector_manager", None),
            )
            dlg.exec()
        else:
            self.notify(f"'{customer_name}' için müşteri kaydı bulunamadı.", "warning")

    def open_context_menu(self, position):
        """Tablo için sağ tık menüsü"""
        if not is_context_menu_enabled(self.db, page_id=40):
            return

        menu = QMenu()
        menu.setStyleSheet(
            theme_qss("""
            QMenu {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 10px 25px;
                color: @text;
                font-size: 13px;
                font-weight: 500;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: @accent;
                color: @selection_text;
            }
            QMenu::separator {
                height: 1px;
                background-color: @surface_alt;
                margin: 4px 10px;
            }
        """)
        )

        # Seçili satırı al
        row = self.table.currentRow()
        if row == -1:
            return

        tracking_no = self.table.item(row, 0).text()
        customer_name = self.table.item(row, 1).text()

        # Kullan?c? rol?n? ana pencereden al
        role = "Personel"
        if (
            hasattr(self.main_window, "user_data")
            and self.main_window.user_data is not None
        ):
            user_data = self.main_window.user_data
            try:
                if isinstance(user_data, dict):
                    role = user_data.get("role", role)
                elif isinstance(user_data, (list, tuple)) and len(user_data) > 3:
                    role = user_data[3]
            except Exception:
                role = role

        # --- Men? ??eleri ---

        # 1. Teknisyen Paneli (NEW)
        action_tech = menu.addAction("🛠️  Teknisyen Paneli")
        action_tech.triggered.connect(lambda: self.open_technician_panel(tracking_no))

        # 2. Detay/Düzenle
        if self.db.check_permission(role, "update_status"):
            action_service = menu.addAction("📝  Servis Formu")
            action_service.triggered.connect(lambda: self.open_edit_dialog(tracking_no))
            action_edit = menu.addAction("✏️  Düzenle")
            action_edit.triggered.connect(lambda: self.open_edit_dialog(tracking_no))

            # Submenu for Status
            status_menu = menu.addMenu("🔄  Durumu Değiştir")
            status_menu.setStyleSheet(theme_qss(menu.styleSheet()))
            # Harmonized Statuses from Kanban
            for st in [
                "Bekliyor",
                "Tamirde",
                "Parça Bekliyor",
                "Test Sürecinde",
                "Hazır",
                "Teslim Edildi",
                "İptal",
            ]:
                a = status_menu.addAction(st)
                a.triggered.connect(lambda ch, s=st: self.change_status(tracking_no, s))

            menu.addSeparator()
            action_close = menu.addAction("✅  İşlemi Kapat")
            action_close.triggered.connect(
                lambda: self.quick_close_service(tracking_no)
            )

        menu.addSeparator()

        # 3. Customer 360 (NEW)
        action_360 = menu.addAction("📊  Müşteri 360° Karne")
        action_360.triggered.connect(
            lambda: self.open_customer_360_dialog(customer_name, tracking_no)
        )

        # 4. İletişim
        action_cust = menu.addAction("👤  Müşteri Bilgileri")
        action_cust.triggered.connect(
            lambda: self.open_context_menu_action("customer", tracking_no)
        )

        if self.db.check_permission(role, "add_transaction") or is_admin_role(role):
            action_sms = menu.addAction("💬  SMS Gönder")
            action_sms.triggered.connect(
                lambda: self.open_context_menu_action("sms", tracking_no)
            )

            action_wa = menu.addAction("📞  WhatsApp")
            action_wa.triggered.connect(
                lambda: self.open_context_menu_action("whatsapp", tracking_no)
            )

        menu.addSeparator()

        # 5. Ek İşlemler (Table Buttons match)
        action_pay = menu.addAction("💳  Ödeme Al")
        action_pay.triggered.connect(
            lambda: self.open_context_menu_action("payment", tracking_no)
        )

        action_photo = menu.addAction("🖼️  Fotoğraflar / Medya")
        action_photo.triggered.connect(
            lambda: self.open_context_menu_action("photos", tracking_no)
        )

        action_barcode = menu.addAction("🏷️  Barkod Yazdır")
        action_barcode.triggered.connect(lambda: self.print_service(tracking_no))

        # 6. Çıktı & Arşiv
        if is_admin_role(role):
            menu.addSeparator()
            action_delete = menu.addAction("🗑️  Sil")
            action_delete.triggered.connect(lambda: self.delete_service(tracking_no))

        menu.exec(self.table.viewport().mapToGlobal(position))

    def open_technician_panel(self, tracking_no):
        """Bir cihaz i?in teknisyen panelini a?."""
        if getattr(self, "_opening_technician_panel", False):
            return
        self._opening_technician_panel = True
        QTimer.singleShot(0, lambda: self._open_technician_panel_deferred(tracking_no))

    def _open_technician_panel_deferred(self, tracking_no):
        from src.ui.dialogs.technician_panel import TechnicianPanel

        try:
            cur = self.db.conn.cursor()
            cur.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            )
            row = cur.fetchone()
            if row:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                dialog = TechnicianPanel(
                    self.db,
                    row,
                    self.main_window,
                    sector_manager=getattr(self, "sector_manager", None),
                )
                QApplication.restoreOverrideCursor()
                dialog.exec()
                self.refresh_data()
                self._refresh_service_board()
            else:
                self.notify(f"Servis kaydı bulunamadı: {tracking_no}", "warning")
        except Exception as e:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            self.notify(f"Panel açılırken hata: {e}", "error")
        finally:
            self._opening_technician_panel = False

    def _refresh_service_board(self):
        try:
            if hasattr(self.main_window, "page_service_board") and hasattr(
                self.main_window.page_service_board, "refresh_data"
            ):
                self.main_window.page_service_board.refresh_data()
                return
            if hasattr(self.main_window, "service_board_page") and hasattr(
                self.main_window.service_board_page, "refresh_data"
            ):
                self.main_window.service_board_page.refresh_data()
                return
            if hasattr(self.main_window, "get_page"):
                page = self.main_window.get_page(41)
                if hasattr(page, "refresh_data"):
                    page.refresh_data()
        except Exception as e:
            logger.debug(f"Service board refresh skipped: {e}")

    def change_status(self, tracking_no, new_status=None):
        """Servis durumunu değiştir (Parametre varsa direkt, yoksa dialog ile)"""
        if new_status:
            try:
                if new_status == "Teslim Edildi":
                    self.notify(
                        "Teslim edildi işlemini teknisyen panelinden tahsilat ile tamamlayın.",
                        "info",
                    )
                    self.open_technician_panel(tracking_no)
                    return
                self.db.update_status(tracking_no, new_status)
                self.audit_logger.log_action(
                    "devices",
                    "UPDATE",
                    f"Takip No: {tracking_no} için durum '{new_status}' olarak güncellendi.",
                )
                self.refresh_data()
                self._refresh_service_board()
                self.notify(f"Durum güncellendi: {new_status}", "success")
            except Exception as e:
                self.notify(f"Hata: {e}", "error")
        else:
            try:
                statuses = [
                    "Bekliyor",
                    "Tamirde",
                    "Parça Bekliyor",
                    "Test Sürecinde",
                    "Hazır",
                    "Teslim Edildi",
                    "İptal",
                ]
                from src.ui.dialogs.modern_select_dialog import ModernSelectDialog

                item, ok = ModernSelectDialog.get_item(
                    self,
                    "🔄 Durum Değiştir",
                    f"Takip No: {tracking_no}\n\nYeni durumu seçiniz:",
                    statuses,
                    0,
                )
                if ok and item:
                    self.change_status(tracking_no, item)
            except Exception as e:
                self.notify(f"Durum güncelleme hatası: {e}", "error")

    def print_barcode(self, tracking_no):
        try:
            from PyQt6.QtGui import QTextDocument
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from src.utils.date_utils import format_datetime_turkish
            from datetime import datetime

            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            ).fetchone()
            if not row:
                self.notify("Cihaz bulunamadı!", "error")
                return

            doc = QTextDocument()
            html = f"""
            <div style="font-family: 'Segoe UI', sans-serif; padding: 20px; background-color: white; color: black;">
                <h2 style="color: #0E5C9A; border-bottom: 2px solid #0E5C9A; padding-bottom: 10px;">SERVIS KAYIT FISI</h2>
                <table style="width: 100%; margin-top: 20px; color: black;">
                    <tr><td style="padding: 5px;"><b>Takip No:</b></td><td>{tracking_no}</td></tr>
                    <tr><td style="padding: 5px;"><b>Müşteri:</b></td><td>{row["customer_name"] or "-"}</td></tr>
                    <tr><td style="padding: 5px;"><b>Cihaz:</b></td><td>{row["device_brand"] or ""} {row["device_model"] or ""}</td></tr>
                    <tr><td style="padding: 5px;"><b>Seri No:</b></td><td>{row["serial_no"] or "-"}</td></tr>
                    <tr><td style="padding: 5px;"><b>Arıza:</b></td><td>{row["fault_description"] or "-"}</td></tr>
                    <tr><td style="padding: 5px;"><b>Tarih:</b></td><td>{format_datetime_turkish(datetime.now())}</td></tr>
                </table>
                <div style="margin-top: 40px; text-align: center; border-top: 1px dashed lightgray; padding-top: 20px; color: black;">
                    <p>Güveniniz için teşekkür ederiz.</p>
                </div>
            </div>
            """
            doc.setHtml(html)

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)

            if dialog.exec():
                doc.print(printer)
                self.notify("Yazdırma işlemi başlatıldı.", "success")
        except Exception as e:
            self.notify(f"Yazdırma hatası: {e}", "error")

    def delete_service(self, tracking_no):
        try:
            # SimpleConfirmDialog is imported at top level
            dialog = SimpleConfirmDialog(
                parent=self,
                title="Onay",
                text=f"{tracking_no} nolu kaydı SİLMEK istediğinize emin misiniz\nBu işlem geri alınamaz.",
            )

            from PyQt6.QtWidgets import QDialog

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if self.db.delete_device(tracking_no):
                    self.audit_logger.log_action(
                        "devices",
                        "DELETE",
                        f"Barkod/Takip No: {tracking_no} olan cihaz kaydı silindi.",
                    )
                    self.refresh_data()
                    self.notify("Kayıt başarıyla silindi.", "success")
                else:
                    self.notify("Silme işlemi başarısız.", "error")
        except TypeError as e:
            # Fallback for argument mismatch (if old version persists in memory, this won't help much but good for logging)
            logger.error(f"Dialog init error: {e}")
            self.notify(f"Dialog hatası: {e}", "error")
        except Exception as e:
            self.notify(f"Silme hatası: {e}", "error")

    def apply_filter(self, category):
        """Apply status filter to the table"""
        self.current_filter_category = category

        # Update title/UI to reflect filter
        titles = {
            "all": "Son İşlemler (Tümü)",
            "active": "Son İşlemler (Tamirde/Aktif)",
            "done": "Son İşlemler (Tamamlananlar)",
            "waiting": "Son İşlemler (Bekleyenler)",
            "today": "Son İşlemler (Bugün Gelenler)",
            "delivered_today": "Son İşlemler (Bugün Teslim Edilenler)",
            "pending_approval": "Son İşlemler (Onay Bekleyenler)",
        }
        self.lbl_table_title.setText(titles.get(category, "Son İşlemler"))

        self.update_filter_buttons_style()
        self.populate_table()

    def update_filter_buttons_style(self):
        if not hasattr(self, "filter_buttons"):
            return

        for key, btn in self.filter_buttons.items():
            # Base style consistent with ActionButton but allowing overrides
            base_style = """
                QPushButton {
                    border-radius: 12px;
                    text-align: left;
                    padding-left: 15px;
                    font-weight: 600;
                    font-size: 13px;
                }
            """

            if key == self.current_filter_category:
                # Active: Blue bg, White text
                btn.setStyleSheet(
                    theme_qss(
                        base_style
                        + """
                    QPushButton {
                        background-color: @accent;
                        color: @selection_text;
                        border: 1px solid @accent;
                    }
                    QPushButton:hover {
                        background-color: @accent_hover;
                    }
                """
                    )
                )
            else:
                # Inactive: White bg, Gray text
                btn.setStyleSheet(
                    theme_qss(
                        base_style
                        + """
                    QPushButton {
                        background-color: @surface;
                        color: @text;
                        border: 1px solid @border;
                    }
                    QPushButton:hover {
                        background-color: @surface_alt;
                        color: @accent;
                        border: 1px solid @border;
                    }
                """
                    )
                )

    def _get_devices_columns(self):
        cols = getattr(self, "_devices_columns_cache", None)
        if cols is not None:
            return cols
        try:
            self.db.cursor.execute("PRAGMA table_info(devices)")
            rows = self.db.cursor.fetchall() or []
            cols = {r[1] for r in rows if len(r) > 1}
        except Exception:
            cols = set()
        self._devices_columns_cache = cols
        return cols

    def refresh_data(self):
        try:
            # Her yenilemede filtreyi sıfırla — "Son İşlemler" tüm durumları göstersin
            self.current_filter_category = "all"
            if hasattr(self, "lbl_table_title"):
                self.lbl_table_title.setText("Son İşlemler")

            if hasattr(self, "apply_theme_styles"):
                self.apply_theme_styles()
            if hasattr(self, "update_filter_buttons_style"):
                self.update_filter_buttons_style()

            self._refresh_today_appointments()

            # Insight strip güncelle
            try:
                self._refresh_insight_strip()
            except Exception as e:
                logger.debug(f"Dashboard insight strip refresh failed: {e}")

            try:
                summary = (
                    self.db.get_summary_data()
                    if hasattr(self.db, "get_summary_data")
                    else {}
                )
            except Exception:
                summary = {}
            critical_stock = summary.get("critical_stock_count", 0)
            self._pending_critical_stock_count = int(critical_stock or 0)

            self.populate_table()
            if hasattr(self, "_speak_morning_greeting"):
                QTimer.singleShot(1200, self._speak_morning_greeting)
        except Exception as e:
            logger.error(
                f"Dashboard refresh_data fatal guard caught: {e}", exc_info=True
            )
            try:
                self.show_error_state(e)
            except Exception as inner_e:
                logger.error(f"Dashboard show_error_state failed: {inner_e}")

    def create_financial_summary(self, parent_layout):
        """Legacy stub — artık kullanılmıyor."""
        pass

    def _refresh_insight_strip(self):
        """Insight kartlarını DB verisiyle günceller."""
        if not hasattr(self, "_perf_card"):
            return

        try:
            summary = (
                self.db.get_summary_data()
                if hasattr(self.db, "get_summary_data")
                else {}
            )
        except Exception:
            summary = {}

        # Kart 1: Günlük Performans
        try:
            pending = int(summary.get("pending_count", 0) or 0)
            delivered = int(summary.get("delivered_today", 0) or 0)
            total = pending + delivered
            if total > 0:
                pct = int(delivered / total * 100)
                perf_text = f"%{pct} Teslim"
                self._perf_card["sub"].setText(
                    f"{delivered}/{total} iş bugün teslim edildi"
                )
            else:
                pct = 0
                perf_text = "İşlem yok"
                self._perf_card["sub"].setText("Bugün kayıt bulunmuyor")
            self._perf_card["main"].setText(perf_text)
        except Exception:
            pass

        # Kart 2: Kuyruk
        try:
            waiting = int(summary.get("waiting_count", 0) or 0)
            active = int(summary.get("active_count", 0) or 0)
            # completed_jobs = tüm teslim edilenler (bugünkü değil toplam)
            done = int(summary.get("completed_jobs", 0) or 0)
            self._queue_card["main"].setText(f"{waiting} · {active} · {done}")
            self._queue_card["sub"].setText("Bekleyen · Aktif · Teslim")
        except Exception:
            pass

        # Kart 3: Bugünkü Tahsilat
        try:
            from src.utils.finance_manager import FinanceManager
            from src.utils.currency_helper import CurrencyHelper

            fm = FinanceManager(self.db)
            fdata = fm.get_financial_summary("today") or {}
            hot_cash = float(fdata.get("hot_cash", 0) or 0)
            rev_txt = CurrencyHelper.format_try_for_display(
                hot_cash, db=self.db, include_try_reference=False
            )
            self._revenue_card["main"].setText(rev_txt)
        except Exception:
            pass

        # Kart 4: AI ipucu (pasif tetikleyici — sadece asistan varsa)
        try:
            if (
                getattr(self.main_window, "assistant_sidebar", None)
                and self.main_window.assistant_sidebar.ai_service
            ):
                if not (
                    getattr(self, "analysis_worker", None)
                    and self.analysis_worker.isRunning()
                ):
                    self.analysis_worker = AssistantAnalysisWorker(
                        self.main_window.assistant_sidebar.ai_service, self.db, self
                    )
                    self.analysis_worker.finished.connect(
                        self._on_insight_analysis_done
                    )
                    self.analysis_worker.start()
        except Exception:
            pass

    def _on_insight_analysis_done(self, text):
        if text and hasattr(self, "_tip_card"):
            self._tip_card["main"].setText(text)
        try:
            if self.analysis_worker:
                self.analysis_worker.deleteLater()
        except Exception:
            pass
        self.analysis_worker = None

    def closeEvent(self, event):
        try:
            if (
                getattr(self, "analysis_worker", None)
                and self.analysis_worker.isRunning()
            ):
                try:
                    self.analysis_worker.requestInterruption()
                except Exception:
                    pass
                if not self.analysis_worker.wait(2000):
                    try:
                        self.analysis_worker.terminate()
                    except Exception:
                        pass
                    self.analysis_worker.wait(1000)
        except Exception:
            pass
        super().closeEvent(event)

    def populate_table(self):
        if not hasattr(self, "table"):
            return
        self.table.setRowCount(0)
        self._update_recent_empty_state()

        # Determine query based on filter
        cols = self._get_devices_columns()
        base_cols = [
            "tracking_no",
            "customer_name",
            "device_brand",
            "device_model",
            "status",
        ]
        if "approval_status" in cols:
            base_cols.append("approval_status")
        if "entry_date" in cols:
            base_cols.append("entry_date")
        selected_list = [c for c in base_cols if c in cols]
        if not selected_list:
            selected_list = ["tracking_no", "customer_name", "status"]
        select_cols = ", ".join(selected_list)
        idx_map = {name: i for i, name in enumerate(selected_list)}

        query = "SELECT {select_cols} FROM devices ".format(select_cols=select_cols)
        where_clauses = []
        params = []

        if "is_archived" in cols:
            where_clauses.append("COALESCE(is_archived, 0) = 0")
        if "is_deleted" in cols:
            where_clauses.append("COALESCE(is_deleted, 0) = 0")

        if False and self.current_filter_category == "active":
            where_clauses.append(
                "status IN ('Tamirde', 'Parça Bekliyor', 'Serviste', 'Test Sürecinde', 'İşleme Alınacak')"
            )
        elif False and self.current_filter_category == "done":
            where_clauses.append(
                "status IN ('Teslim Edildi', 'Hazır', 'Bitti', 'Tamir Edildi')"
            )
        elif False and self.current_filter_category == "waiting":
            where_clauses.append("status = 'Bekliyor'")
        elif self.current_filter_category == "today":
            if "entry_date" in cols:
                today = QDate.currentDate().toString("dd.MM.yyyy")
                where_clauses.append("entry_date LIKE ?")
                params.append(f"%{today}%")
        elif self.current_filter_category == "delivered_today":
            where_clauses.append("status IN ('Teslim Edildi', 'Teslim')")
            if "exit_date" in cols:
                from PyQt6.QtCore import QDate

                today_db = QDate.currentDate().toString("yyyy-MM-dd")
                where_clauses.append("exit_date = ?")
                params.append(today_db)
        elif self.current_filter_category == "pending_approval":
            where_clauses.append(
                "status IN ('Onay Bekliyor', 'Onay Bekleyen', 'Parça Bekliyor')"
            )
        else:
            where_clauses.append(
                "COALESCE(status, '') NOT IN ('Teslim Edildi', 'Teslim', 'Bitti', 'Tamir Edildi')"
            )

        if (
            self.current_filter_category == "pending_approval"
            and "approval_status" in cols
            and where_clauses
        ):
            where_clauses[-1] = (
                "("
                + where_clauses[-1]
                + " OR COALESCE(approval_status, '') IN ('Musteri Onayi Bekliyor', 'Beklemede', 'Bekleme'))"
            )

        if where_clauses:
            query += "WHERE " + " AND ".join(where_clauses) + " "

        # Use ID DESC for reliable 'newest first' sorting as date string format may vary
        query += " ORDER BY id DESC"

        try:
            self.db.cursor.execute(query, params)
            services = self.db.cursor.fetchall()
        except Exception as e:
            logger.error(f"Filter query error: {e}")
            services = []

        filtered_services = []
        for service in services:
            try:
                raw_status = str(service[idx_map.get("status", 0)] or "").strip()
                normalized_status = normalize_device_status(raw_status)
                approval_status = (
                    str(service[idx_map.get("approval_status", -1)] or "").strip()
                    if "approval_status" in idx_map
                    else ""
                )
                if (
                    approval_status
                    in {"Musteri Onayi Bekliyor", "Beklemede", "Bekleme"}
                    and "Onay" not in raw_status
                ):
                    raw_status = f"{raw_status} Onay".strip()
            except Exception:
                raw_status = ""
                normalized_status = ""
                approval_status = ""

            if self.current_filter_category == "active" and normalized_status not in {
                "Tamirde",
                "Parça Bekliyor",
                "Test Sürecinde",
            }:
                continue
            if self.current_filter_category == "done" and normalized_status not in {
                "Teslim Edildi",
                "Hazır",
            }:
                continue
            if (
                self.current_filter_category == "waiting"
                and normalized_status != "Bekliyor"
            ):
                continue
            if (
                self.current_filter_category == "pending_approval"
                and normalized_status not in {"Parça Bekliyor", "Test Sürecinde"}
                and "Onay" not in raw_status
            ):
                continue
            filtered_services.append(service)

        for row_idx, service in enumerate(filtered_services):
            self.table.insertRow(row_idx)

            tracking_no = (
                str(service[idx_map.get("tracking_no", 0)] or "") if service else ""
            )
            customer = (
                str(service[idx_map.get("customer_name", 0)] or "") if service else ""
            )
            brand = (
                str(service[idx_map.get("device_brand", 0)] or "") if service else ""
            )
            model = (
                str(service[idx_map.get("device_model", 0)] or "") if service else ""
            )
            device = f"{brand} {model}".strip()
            status = str(service[idx_map.get("status", 0)] or "") if service else ""

            # 1. Takip No
            item_track = QTableWidgetItem(tracking_no)
            item_track.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            item_track.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
            self.table.setItem(row_idx, 0, item_track)

            # 2. Müşteri
            item_cust = QTableWidgetItem(customer)
            item_cust.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
            self.table.setItem(row_idx, 1, item_cust)

            # 3. Cihaz
            item_device = QTableWidgetItem(device)
            item_device.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
            self.table.setItem(row_idx, 2, item_device)

            # 4. Durum (Renkli Kutu - Kanban ile tam uyumlu)
            normalized_status = normalize_device_status(status.strip())

            # Kanban get_kanban_colors() ile birebir aynı renkler
            STATUS_DISPLAY = {
                "Bekliyor": ("BEKLİYOR", "#F59E0B"),  # amber  - Kanban col 1
                "Tamirde": ("TAMİRDE", "#2563EB"),  # blue   - Kanban col 2
                "Parça Bekliyor": (
                    "PARÇA BEKLİYOR",
                    "#D97706",
                ),  # orange - Kanban col 3
                "Test Sürecinde": ("TEST / ONAY", "#0EA5E9"),  # sky    - Kanban col 4
                "Teslim Edildi": ("TESLİM EDİLDİ", "#10B981"),  # green  - Kanban col 5
                "İptal": ("İPTAL EDİLDİ", "#EF4444"),  # red    - Kanban col 6
            }

            disp_text, bg_color = STATUS_DISPLAY.get(
                normalized_status, (status.upper() or "?", "#6B7280")
            )
            text_color = "#FFFFFF"

            lbl_status = QLabel(disp_text)
            lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_status.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    font-weight: bold;
                    font-size: 11px;
                    border-radius: 4px;
                    margin: 2px;
                    padding: 2px 4px;
                }}
            """)
            self.table.setCellWidget(row_idx, 3, lbl_status)

            # 5. İşlemler (7'li Buton Grubu)
            action_widget = ActionWidget(tracking_no, self)
            self.table.setCellWidget(row_idx, 4, action_widget)

        self._update_recent_empty_state()

    def open_context_menu_action(self, action_type, tracking_no):
        """ActionWidget tarafından çağrılan yardımcı metod"""
        if action_type in {"sms", "photos", "payment"}:
            QTimer.singleShot(
                0,
                lambda: self._open_context_menu_action_deferred(
                    action_type, tracking_no
                ),
            )
            return

        self._open_context_menu_action_deferred(action_type, tracking_no)

    def _open_context_menu_action_deferred(self, action_type, tracking_no):
        """Ağır aksiyonları menü etkileşiminden ayırmak için deferred çalıştırılır."""
        if action_type == "info":
            # Just show a quick info dialog or toast
            self.notify(f"Cihaz: {tracking_no}", "info")

        elif action_type == "customer":
            try:
                row = self.db.cursor.execute(
                    "SELECT customer_id FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                    (tracking_no,),
                ).fetchone()
                if row and row["customer_id"]:
                    self.main_window.open_customer_360_by_id(row["customer_id"])
                else:
                    self.main_window.on_menu_click(21)
            except Exception as e:
                self.notify(f"Müşteri açılırken hata: {str(e)}", "error")

        elif action_type == "sms":
            # Open SMS Dialog
            try:
                # Need customer name and phone
                row = self.db.cursor.execute(
                    "SELECT customer_name, customer_contact FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                    (tracking_no,),
                ).fetchone()
                if row:
                    from src.ui.dialogs.send_sms_dialog import SendSMSDialog

                    dlg = SendSMSDialog(
                        self.db,
                        self,
                        row["customer_name"],
                        row["customer_contact"],
                        tracking_no,
                    )
                    dlg.exec()
                else:
                    self.notify("Müşteri bilgisi bulunamadı.", "warning")
            except Exception as e:
                self.notify(f"SMS ekranı açılamadı: {e}", "error")

        elif action_type == "photos":
            # Open Photo Manager
            try:
                dlg = PhotoGalleryDialog(self.db, tracking_no, self)
                dlg.exec()
            except ImportError:
                self.notify("Galeri modülü yüklenemedi.", "error")
            except Exception as e:
                self.notify(f"Galeri hatası: {e}", "error")

        elif action_type == "whatsapp":
            self.db.cursor.execute(
                "SELECT customer_name, customer_contact FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            )
            res = self.db.cursor.fetchone()
            if res:
                customer_name = res["customer_name"] or "Müşteri"
                phone = "".join(
                    ch for ch in str(res["customer_contact"] or "") if ch.isdigit()
                )
                if phone.startswith("0"):
                    phone = phone[1:]
                if len(phone) == 10:
                    phone = f"90{phone}"
                if not phone:
                    self.notify("Telefon numarası bulunamadı.", "warning")
                    return
                message = quote(
                    f"Merhaba {customer_name}, servis kaydınız hakkında sizinle iletişime geçiyoruz."
                )
                webbrowser.open(f"https://wa.me/{phone}?text={message}")
            else:
                self.notify("Telefon numarası bulunamadı.", "warning")
        elif action_type == "payment":
            try:
                try:
                    row = self.db.cursor.execute(
                        "SELECT customer_id, customer_name, customer_contact, customer_email FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                        (tracking_no,),
                    ).fetchone()
                except Exception:
                    row = self.db.cursor.execute(
                        "SELECT customer_id, customer_name, customer_contact FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                        (tracking_no,),
                    ).fetchone()
                if not row:
                    self.notify("Müşteri bilgisi bulunamadı.", "warning")
                    return
                customer_id = row["customer_id"]
                name = row["customer_name"] or ""
                phone = row["customer_contact"] or ""
                email = (
                    row["customer_email"]
                    if hasattr(row, "keys") and "customer_email" in row.keys()
                    else ""
                )
                if customer_id:
                    c_row = self.db.cursor.execute(
                        "SELECT id, name, phone, email FROM customers WHERE id=?",
                        (customer_id,),
                    ).fetchone()
                    if c_row:
                        customer = {
                            "id": c_row["id"],
                            "name": c_row["name"],
                            "phone": c_row["phone"],
                            "email": c_row["email"],
                        }
                    else:
                        customer = {
                            "id": customer_id,
                            "name": name,
                            "phone": phone,
                            "email": email,
                        }
                else:
                    customer = {"id": 0, "name": name, "phone": phone, "email": email}
                dlg = TahsilatDialog(self, self.db, customer)
                dlg.exec()
            except Exception as e:
                self.notify(f"Tahsilat ekranı açılamadı: {e}", "error")

    def open_add_stock_dialog(self):
        QTimer.singleShot(0, self._open_add_stock_dialog_deferred)

    def _open_add_stock_dialog_deferred(self):
        try:
            from src.ui.dialogs.add_stock_dialog import AddStockDialog

            try:
                dlg = AddStockDialog(self.db, parent=self)
            except TypeError:
                dlg = AddStockDialog(self.db)
                if hasattr(dlg, "setParent"):
                    dlg.setParent(self)
            if dlg.exec():
                self.notify("Yeni ürün/stok eklendi.", "success")
        except Exception as e:
            self.notify(f"Stok penceresi açılamadı: {e}", "error")

    def open_edit_dialog(self, tracking_no):
        QTimer.singleShot(0, lambda: self._open_edit_dialog_deferred(tracking_no))

    def _open_edit_dialog_deferred(self, tracking_no):
        # Fetch device data
        try:
            self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            )
            device = self.db.cursor.fetchone()
            if device:
                from src.ui.dialogs.new_service_dialog import NewServiceDialog

                dlg = NewServiceDialog(
                    self.db,
                    self,
                    device_data=device,
                    sector_manager=getattr(self, "sector_manager", None),
                )
                if dlg.exec():
                    self.refresh_data()

            else:
                show_warning(self, "Kayıt bulunamadı.")
        except Exception as e:
            logger.error(f"Edit error: {e}")
            show_error(self, f"Düzeltme hatası: {e}")

    def print_service(self, tracking_no):
        """Barkod etiketi (Label) yazdır (50mm x 30mm)"""
        try:
            self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            )
            device = self.db.cursor.fetchone()

            if device:
                # Use PDFManager to create label
                pm = PDFManagerQt(self.db)
                success, path = pm.create_device_label(device)

                if success:
                    self.notify(f"Barkod etiketi oluşturuldu: {path}", "success")
                else:
                    self.notify(f"Etiket oluşturulamadı: {path}", "error")
            else:
                show_warning(self, "Servis kaydı bulunamadı.")
        except Exception as e:
            show_error(self, f"Yazdırma hatası: {e}")

    def perform_web_search(self):
        query = self.search_inp.text().strip()
        if not query:
            return

        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

        if QWebEngineView:
            from src.ui.widgets.premium_dialog import PremiumDialog

            dlg = PremiumDialog(f"Web Arama: {query}", self)
            dlg.resize(1200, 850)

            # Use body_layout from PremiumDialog
            web = QWebEngineView()
            web.load(QUrl(url))
            web.setStyleSheet(theme_qss("border-radius: 10px;"))
            dlg.body_layout.addWidget(web)

            self.notify(f"'{query}' araması yapılıyor...", "info")
            dlg.exec()
        else:
            self.notify(f"'{query}' araması tarayıcıda açılıyor...", "info")
            webbrowser.open(url)

    def quick_close_service(self, tracking_no):
        """Hızlı servis kapatma/teslim etme"""
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        from PyQt6.QtWidgets import QDialog

        dlg = SimpleConfirmDialog(
            self,
            "İşlemi Kapat",
            f"#{tracking_no} numaralı servis işlemini kapatıp teslim edildi olarak işaretlemek istiyor musunuz",
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.notify(
                    "Teslim edildi işlemini teknisyen panelinden tahsilat ile tamamlayın.",
                    "info",
                )
                self.open_technician_panel(tracking_no)
            except Exception as e:
                show_error(self, f"Teknisyen paneli açılamadı: {e}")
