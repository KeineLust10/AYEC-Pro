# -*- coding: utf-8 -*-

import webbrowser
from datetime import datetime
from urllib.parse import quote
from PyQt6.QtCore import QTimer, QDate
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMenu
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger

class DashboardFuncMixin:
    def _emit_financial_data_changed(self):
        main_window = getattr(self, "main_window", None) or self.window()
        if main_window and hasattr(main_window, "financial_data_changed"):
            try:
                main_window.financial_data_changed.emit()
            except Exception:
                pass

    def _announce_payment_received(self):
        self.notify("\u00d6deme al\u0131nd\u0131.", "success")
        try:
            from src.utils.asistan_motoru import sesli_cevap_ver_async
            sesli_cevap_ver_async("\u00d6deme al\u0131nd\u0131.")
        except Exception:
            pass

    def change_status(self, tracking_no, new_status=None):
        if new_status:
            try:
                saved = self.db.update_status(tracking_no, new_status)
                if not saved:
                    raise RuntimeError("Durum veritaban\u0131na kaydedilemedi")
                if hasattr(self, "audit_logger"):
                    self.audit_logger.log_action("devices", "UPDATE", f"Takip No: {tracking_no} için durum '{new_status}' olarak güncellendi.")
                self.refresh_data()
                if hasattr(self, "_refresh_service_board"): self._refresh_service_board()
                self.notify(f"Durum güncellendi: {new_status}", "success")
            except Exception as e: self.notify(f"Hata: {e}", "error")
        else:
            try:
                statuses = ["Bekliyor", "Tamirde", "Parça Bekliyor", "Test Sürecinde", "Hazır", "Teslim Edildi", "İptal"]
                from src.ui.dialogs.modern_select_dialog import ModernSelectDialog
                item, ok = ModernSelectDialog.get_item(self, "Durum Değiştir", f"Takip No: {tracking_no}\n\nYeni durumu seçiniz:", statuses, 0)
                if ok and item: self.change_status(tracking_no, item)
            except Exception as e: self.notify(f"Durum güncelleme hatası: {e}", "error")

    def print_service(self, tracking_no):
        """Show compact receipt and label choices for a service row."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { padding: 5px; } QMenu::item { padding: 8px 24px; }"
        )
        actions = [
            ("K\u0131sa Fi\u015f", self.print_short_receipt),
            ("Detayl\u0131 Fi\u015f Yazd\u0131r", self.print_detailed_receipt),
            ("Kargo Fi\u015fi", self.print_cargo_receipt),
            ("Etiket A", self._print_service_label_a),
            ("Etiket B", self._print_service_label_b),
            ("Yazd\u0131r", self.print_service_form),
        ]
        for label, callback in actions:
            action = menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, fn=callback: fn(tracking_no)
            )
        menu.exec(QCursor.pos())

    def _print_service_label_a(self, tracking_no):
        """Create label A with the selected printer profile dimensions."""
        try:
            from src.utils.pdf_manager import PDFManagerQt

            device = self.db.get_device_by_tracking_no(tracking_no) if hasattr(self.db, "get_device_by_tracking_no") else None
            if not device:
                cur = self.db.cursor.execute("SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,))
                device = cur.fetchone()
            if device:
                options = self._get_service_print_options(
                    "label_a",
                    "Etiket A Yazd\u0131rma Ayarlar\u0131",
                )
                if not options:
                    return
                pm = PDFManagerQt(self.db)
                pm._suppress_service_open = options.direct_print
                success, path = pm.create_device_label(
                    device,
                    width_mm=options.label_width_mm,
                    height_mm=options.label_height_mm,
                )
                if success:
                    self._complete_service_print(
                        path,
                        options,
                        "Barkod etiketi olu\u015fturuldu",
                    )
                else:
                    self.notify(f"Etiket olu\u015fturulamad\u0131: {path}", "error")
            else:
                self.notify("Servis kayd\u0131 bulunamad\u0131.", "warning")
        except Exception as e:
            self.notify(f"Yazd\u0131rma hatas\u0131: {e}", "error")

    def _print_service_label_b(self, tracking_no):
        """Create the compact company-branded PDF label."""
        try:
            from src.utils.pdf_manager import PDFManagerQt

            device = self.db.get_device_by_tracking_no(tracking_no) if hasattr(self.db, "get_device_by_tracking_no") else None
            if not device:
                cur = self.db.cursor.execute("SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,))
                device = cur.fetchone()
            if device:
                options = self._get_service_print_options(
                    "label_b",
                    "Etiket B Yazd\u0131rma Ayarlar\u0131",
                )
                if not options:
                    return
                pdf = PDFManagerQt(self.db)
                pdf._suppress_service_open = options.direct_print
                success, path = pdf.create_device_label_b(
                    device,
                    width_mm=options.label_width_mm,
                    height_mm=options.label_height_mm,
                )
                if success:
                    self._complete_service_print(
                        path,
                        options,
                        "Cihaz etiketi B olu\u015fturuldu",
                    )
                else:
                    self.notify(f"Etiket olu\u015fturulamad\u0131: {path}", "error")
            else:
                self.notify("Servis kayd\u0131 bulunamad\u0131.", "warning")
        except Exception as exc:
            self.notify(f"Yazd\u0131rma hatas\u0131: {exc}", "error")

    def print_service_zpl(self, tracking_no):
        try:
            from src.utils.pdf_manager import PDFManagerQt

            device = (
                self.db.get_device_by_tracking_no(tracking_no)
                if hasattr(self.db, "get_device_by_tracking_no")
                else None
            )
            if not device:
                device = self.db.cursor.execute(
                    """
                    SELECT *
                    FROM devices
                    WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0
                    """,
                    (tracking_no,),
                ).fetchone()
            if not device:
                self.notify("Servis kaydi bulunamadi.", "warning")
                return
            success, path = PDFManagerQt(self.db).create_zpl_label(device)
            if success:
                self.notify(
                    f"Cihaz etiketi B olusturuldu: {path}",
                    "success",
                )
            else:
                self.notify(f"Etiket olusturulamadi: {path}", "error")
        except Exception as exc:
            self.notify(f"Yazdirma hatasi: {exc}", "error")

    def _service_print_payload(self, tracking_no):
        device = None
        if hasattr(self.db, "get_device_by_tracking_no"):
            device = self.db.get_device_by_tracking_no(tracking_no)
        if not device:
            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            ).fetchone()
            device = row
        if not device:
            return None, [], 0.0
        if hasattr(device, "keys"):
            device = {key: device[key] for key in device.keys()}
        parts = []
        try:
            if hasattr(self.db, "get_used_parts"):
                parts = self.db.get_used_parts(tracking_no) or []
            else:
                parts = self.db.cursor.execute(
                    "SELECT * FROM used_parts WHERE tracking_no=?",
                    (tracking_no,),
                ).fetchall() or []
        except Exception as exc:
            logger.warning("Service print parts lookup failed: %s", exc)
        labor = 0.0
        for key in ("labor_cost", "service_fee", "repair_cost"):
            try:
                value = float(device.get(key) or 0)
            except (TypeError, ValueError):
                value = 0.0
            if value > 0:
                labor = value
                break
        return device, parts, labor

    def _get_service_print_options(self, profile, title):
        from src.ui.dialogs.service_print_options_dialog import (
            ServicePrintOptionsDialog,
        )

        return ServicePrintOptionsDialog.get_options(
            self.db,
            parent=self,
            profile=profile,
            title=title,
        )

    def _complete_service_print(self, path, options, success_message):
        if options.direct_print:
            from src.utils.windows_printing import print_pdf_file

            printed, result = print_pdf_file(path, options.printer_name)
            if not printed:
                self.notify(f"Yazd\u0131rma hatas\u0131: {result}", "error")
                return
            printer = options.printer_name or "Windows varsay\u0131lan yaz\u0131c\u0131s\u0131"
            self.notify(f"{success_message}. Yaz\u0131c\u0131: {printer}", "success")
            return
        self.notify(f"{success_message}: {path}", "success")

    def _run_service_print(
        self,
        tracking_no,
        method_name,
        success_message,
        profile="document",
    ):
        try:
            from src.utils.pdf_manager import PDFManagerQt
            device, parts, labor = self._service_print_payload(tracking_no)
            if not device:
                self.notify("Servis kaydi bulunamadi.", "warning")
                return
            options = self._get_service_print_options(
                profile,
                "Servis Fi\u015fi Yazd\u0131rma Ayarlar\u0131",
            )
            if not options:
                return
            pdf = PDFManagerQt(self.db)
            pdf._suppress_service_open = options.direct_print
            kwargs = {}
            if profile == "document":
                kwargs = {
                    "page_size": options.page_size,
                    "orientation": options.orientation,
                }
            success, path = getattr(pdf, method_name)(
                device,
                parts,
                labor,
                **kwargs,
            )
            if success:
                self._complete_service_print(path, options, success_message)
            else:
                self.notify(f"Olusturma basarisiz: {path}", "error")
        except Exception as exc:
            logger.exception("Service print failed")
            self.notify(f"Yazdirma hatasi: {exc}", "error")

    def print_short_receipt(self, tracking_no):
        self._run_service_print(
            tracking_no,
            "create_short_service_receipt",
            "Kisa fis olusturuldu",
            profile="receipt",
        )

    def print_detailed_receipt(self, tracking_no):
        self._run_service_print(
            tracking_no,
            "create_detailed_service_receipt",
            "Detayli fis olusturuldu",
        )

    def print_service_form(self, tracking_no):
        self._run_service_print(tracking_no, "create_service_receipt", "Servis formu olusturuldu")

    def print_cargo_receipt(self, tracking_no):
        self._run_service_print(
            tracking_no,
            "create_cargo_receipt",
            "Kargo fisi olusturuldu",
            profile="receipt",
        )

    def delete_service(self, tracking_no):
        try:
            from src.ui.dialogs.simple_confirm import SimpleConfirmDialog

            dialog = SimpleConfirmDialog(parent=self, title="Onay", text=f"{tracking_no} nolu kaydı SİLMEK istediğinize emin misiniz\nBu işlem geri alınamaz.")
            from PyQt6.QtWidgets import QDialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if self.db.delete_device(tracking_no):
                    if hasattr(self, "audit_logger"): self.audit_logger.log_action("devices", "DELETE", f"Barkod/Takip No: {tracking_no} olan cihaz kaydı silindi.")
                    self.refresh_data()
                    self.notify("Kayıt başarıyla silindi.", "success")
                else: self.notify("Silme işlemi başarısız.", "error")
        except Exception as e: self.notify(f"Silme hatası: {e}", "error")

    def quick_close_service(self, tracking_no):
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        from PyQt6.QtWidgets import QDialog
        dlg = SimpleConfirmDialog(self, "İşlemi Kapat", f"#{tracking_no} numaralı servis işlemini kapatıp teslim edildi olarak işaretlemek istiyor musunuz")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.notify("Teslim edildi işlemini teknisyen panelinden tahsilat ile tamamlayın.", "info")
                self.open_technician_panel(tracking_no)
            except Exception as e: self.notify(f"Teknisyen paneli açılamadı: {e}", "error")

    def perform_web_search(self):
        query = self.search_inp.text().strip() if hasattr(self, "search_inp") else ""
        if not query: return
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
        except Exception:
            QWebEngineView = None
        if QWebEngineView:
            from src.ui.widgets.premium_dialog import PremiumDialog
            from PyQt6.QtCore import QUrl
            from src.utils.theme_colors import theme_qss
            dlg = PremiumDialog(f"Web Arama: {query}", self)
            dlg.resize(1200, 850)
            web = QWebEngineView()
            web.load(QUrl(url))
            web.setStyleSheet(theme_qss("border-radius: 10px;"))
            dlg.body_layout.addWidget(web)
            self.notify(f"'{query}' araması yapılıyor...", "info")
            dlg.exec()
        else: self.notify(f"'{query}' araması tarayıcıda açılıyor...", "info"); webbrowser.open(url)

    def open_context_menu_action(self, action_type, tracking_no):
        if action_type in {"sms", "photos", "payment"}:
            QTimer.singleShot(0, lambda: self._open_context_menu_action_deferred(action_type, tracking_no))
        else: self._open_context_menu_action_deferred(action_type, tracking_no)

    def _open_context_menu_action_deferred(self, action_type, tracking_no):
        if action_type == "info": self.notify(f"{'Araç iş emri' if self._is_automotive() else 'Cihaz'}: {tracking_no}", "info")
        elif action_type == "customer":
            try:
                row = self.db.cursor.execute("SELECT customer_id FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,)).fetchone()
                if row and row["customer_id"]: self.main_window.open_customer_360_by_id(row["customer_id"])
                else: self.main_window.on_menu_click(21)
            except Exception as e: self.notify(f"Müşteri açılırken hata: {str(e)}", "error")
        elif action_type == "invoice":
            try:
                row = self.db.cursor.execute(
                    """
                    SELECT customer_id
                    FROM devices
                    WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0
                    """,
                    (tracking_no,),
                ).fetchone()
                customer_id = row["customer_id"] if row else None
                if not customer_id:
                    self.notify(
                        "Fatura icin kayitli musteri bulunamadi.",
                        "warning",
                    )
                    return
                from src.ui.dialogs.service_invoice_dialog import (
                    ServiceInvoiceDialog,
                )

                ServiceInvoiceDialog(
                    self.db,
                    customer_id,
                    self,
                ).exec()
                self.refresh_data()
            except Exception as exc:
                self.notify(
                    f"Fatura ekrani acilamadi: {exc}",
                    "error",
                )
        elif action_type == "sms":
            try:
                row = self.db.cursor.execute("SELECT customer_name, customer_contact FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,)).fetchone()
                if row:
                    from src.ui.dialogs.send_sms_dialog import SendSMSDialog
                    dlg = SendSMSDialog(self.db, self, row["customer_name"], row["customer_contact"], tracking_no)
                    dlg.exec()
                else: self.notify("Müşteri bilgisi bulunamadı.", "warning")
            except Exception as e: self.notify(f"SMS ekranı açılamadı: {e}", "error")
        elif action_type == "photos":
            try:
                from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
                dlg = PhotoGalleryDialog(self.db, tracking_no, self); dlg.exec()
            except Exception as e: self.notify(f"Galeri hatası: {e}", "error")
        elif action_type == "whatsapp":
            res = self.db.cursor.execute("SELECT customer_name, customer_contact FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,)).fetchone()
            if res:
                cname = res["customer_name"] or "Müşteri"
                phone = "".join(ch for ch in str(res["customer_contact"] or "") if ch.isdigit())
                if phone.startswith("0"): phone = phone[1:]
                if len(phone) == 10: phone = f"90{phone}"
                if not phone: self.notify("Telefon numarası bulunamadı.", "warning"); return
                msg = quote(f"Merhaba {cname}, servis kaydınız hakkında sizinle iletişime geçiyoruz.")
                webbrowser.open(f"https://wa.me/{phone}?text={msg}")
            else: self.notify("Telefon numarası bulunamadı.", "warning")
        elif action_type == "payment":
            try:
                from src.ui.dialogs.tahsilat_dialog import TahsilatDialog

                row = self.db.cursor.execute("SELECT customer_id, customer_name, customer_contact FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0", (tracking_no,)).fetchone()
                if not row: self.notify("Müşteri bilgisi bulunamadı.", "warning"); return
                cid = row["customer_id"]
                customer = {"id": cid, "name": row["customer_name"] or "", "phone": row["customer_contact"] or "", "email": ""}
                if cid:
                    crow = self.db.cursor.execute("SELECT id, name, phone, email FROM customers WHERE id=?", (cid,)).fetchone()
                    if crow: customer = {"id": crow["id"], "name": crow["name"], "phone": crow["phone"], "email": crow["email"]}
                dlg = TahsilatDialog(self, self.db, customer)
                if dlg.exec():
                    if self._save_dashboard_payment(customer, dlg.get_data() or {}, tracking_no):
                        self._emit_financial_data_changed()
                        self._announce_payment_received(); self.refresh_data()
                        if self.main_window and hasattr(self.main_window, "refresh_loaded_page"):
                            for pid in (21, 101, 105, 106): 
                                try: self.main_window.refresh_loaded_page(pid)
                                except: pass
            except Exception as e: self.notify(f"Tahsilat ekranı açılamadı: {e}", "error")

    def _save_dashboard_payment(self, customer, data, tracking_no=None):
        customer_id = customer.get("id") if isinstance(customer, dict) else None
        if not customer_id: self.notify("Tahsilat için kayıtlı müşteri bulunamadı.", "warning"); return False
        try:
            currency = str(data.get("currency") or CurrencyHelper.get_code(self.db) or "TRY").upper()
            rate = float(data.get("exchange_rate", 1.0) or 1.0)
            amt = float(data.get("amount", 0) or 0)
            if amt <= 0: self.notify("Tahsilat tutarı geçersiz.", "warning"); return False
            if tracking_no:
                open_debts = self.db.get_unpaid_debts(customer_id, currency=None)
                matching = [row for row in open_debts if str(row[2] or "TRY").upper() == currency and str(row[4] or "") == str(tracking_no)]
                if not matching:
                    available = [str(row[2] or "TRY").upper() for row in open_debts if str(row[4] or "") == str(tracking_no)]
                    expected = available[0] if available else None
                    self.notify(
                        f"Bu servis icin tahsilat para birimi {expected or 'tanimsiz'} olmalidir.",
                        "warning",
                    )
                    return False
                remaining = round(sum(max(0.0, -float(row[6] or 0.0)) for row in matching), 2)
                if amt > remaining + 0.009:
                    self.notify(f"Acik servis borcu {remaining:,.2f} {currency}. Fazla tahsilat yapilamaz.", "warning")
                    return False
            acc_date, c_at = None, None
            if data.get("date"):
                parsed = QDate.fromString(str(data.get("date")), "dd.MM.yyyy")
                if parsed.isValid(): 
                    acc_date = parsed.toString("yyyy-MM-dd")
                    c_at = f"{acc_date} {datetime.now().strftime('%H:%M:%S')}"
            ref_tr = data.get("reference_tracking_no") or tracking_no or None
            notes = (data.get("notes") or "").strip()
            full_desc = f"Ref: {ref_tr} | {notes or 'Cari borç kapatma tahsilatı'}"
            try: self.db.create_payment_debt_links_table()
            except: pass
            saved = self.db.add_currency_transaction(customer_id=customer_id, amount=amt, currency=currency, transaction_type="CREDIT", exchange_rate=rate, description=full_desc, tracking_no=ref_tr, created_at=c_at, commit=False)
            if not saved: self.notify("Tahsilat kaydedilemedi.", "warning"); return False
            try:
                pid = self.db.get_last_currency_transaction_id()
                if pid: self.db.apply_payment_to_debts(customer_id=customer_id, payment_amount=amt, currency=currency, payment_transaction_id=pid, selected_debt_ids=data.get("selected_debt_ids"), commit=False)
            except Exception as e: logger.warning(f"Payment allocation error: {e}")
            tl_amt = amt * (rate if currency != "TRY" else 1.0)
            try:
                self.db.add_transaction(t_type="Gelir", category="Tahsilat", amount=tl_amt, description=full_desc, customer_name=customer.get("name"), customer_id=customer_id, date=acc_date, payment_method=data.get("method"), bank_account_id=data.get("bank_account_id"), tracking_no=ref_tr, ref_no=ref_tr, currency=currency, original_amount=amt)
            except Exception as e:
                self.db.conn.rollback()
                logger.error("Payment accounting mirror failed: %s", e)
                self.notify("Tahsilat ve muhasebe kaydi birlikte kaydedilemedi.", "error")
                return False
            self.db.conn.commit()
            return True
        except Exception as e: logger.exception("Payment save failed"); self.notify(f"Hata: {e}", "error"); return False
