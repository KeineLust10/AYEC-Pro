# -*- coding: utf-8 -*-
# _tp_operations.py

from datetime import datetime
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton
)

from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.ui.dialogs.base_modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens


class _TpOperations:

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def print_label(self):
        try:
            from src.utils.barcode_manager import BarcodeManager
            
            # Musteri adini ve cihaz bilgisini kisalt
            customer = str(self.device_dict.get("customer_name") or "Bilinmiyor")
            if len(customer) > 20:
                customer = customer[:18] + ".."
                
            device = str(self.device_dict.get("device_brand") or "") + " " + str(self.device_dict.get("device_model") or "")
            if len(device.strip()) < 3:
                device = str(self.device_dict.get("device_type") or "Cihaz")
                
            label_data = {
                "tracking_no": self.tracking_no,
                "customer_name": customer,
                "device_info": device,
                "entry_date": self.device_dict.get("entry_date", datetime.now().strftime("%Y-%m-%d")),
            }
            
            bm = BarcodeManager()
            success, msg = bm.print_service_label(label_data)
            if success:
                show_success(self, "Etiket yazdırıldı.")
            else:
                show_error(self, f"Yazdırma hatası: {msg}")
        except Exception as e:
            logger.error(f"Print label error: {e}")
            show_error(self, f"Etiket yazdırma işlemi başlatılamadı: {e}")

    def _create_service_receipt_pdf(self):
        try:
            query = "SELECT part_name, price FROM used_parts WHERE tracking_no=?"
            try:
                self.db.cursor.execute("PRAGMA table_info(used_parts)")
                cols = [row[1] for row in self.db.cursor.fetchall()]
                deleted_col = (
                    "is_deleted"
                    if "is_deleted" in cols
                    else ("is_archived" if "is_archived" in cols else None)
                )
                if deleted_col:
                    query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            except Exception:
                pass
            used_parts = (
                self.db.cursor.execute(query, (self.tracking_no,)).fetchall() or []
            )
            labor_cost = float(self.device_dict.get("labor_cost") or 0)
            from src.utils.pdf_manager import PDFManagerQt
            from src.ui.utils.background_task import run_cancellable_task

            device_dict = dict(self.device_dict)
            automotive_form = dict(
                getattr(self, "automotive_service_form", {}) or {}
            )
            automotive_mode = self._is_automotive()

            def produce_pdf(is_cancelled):
                if is_cancelled():
                    return None
                pdf = PDFManagerQt(self.db)
                if automotive_mode:
                    return pdf.create_automotive_service_form_pdf(
                        device_dict,
                        automotive_form,
                        used_parts,
                        labor_cost,
                    )
                return pdf.create_service_receipt(
                    device_dict,
                    used_parts,
                    labor_cost,
                )

            def pdf_ready(result):
                if not result:
                    return
                success, file_path = result
                if success and file_path:
                    show_success(self, f"Servis formu hazirlandi: {file_path}")
                else:
                    show_warning(
                        self,
                        "Servis formu olu\u015fturulamad\u0131.",
                    )

            run_cancellable_task(
                owner=self,
                title="Servis formu olusturuluyor",
                target=produce_pdf,
                on_success=pdf_ready,
                on_error=lambda message: show_error(
                    self,
                    f"Servis formu olu\u015fturma hatas\u0131: {message}",
                ),
            )
        except Exception as e:
            show_error(
                self,
                f"Servis formu olu\u015fturma hatas\u0131: {e}",
            )

    def _calculate_service_total(self):
        labor_cost = float(self.device_dict.get("labor_cost") or 0)
        total_parts = 0.0
        try:
            total_parts = float(
                self.db._get_used_parts_total_try(self.tracking_no) or 0.0
            )
        except Exception:
            total_parts = 0.0
        return labor_cost + total_parts, labor_cost, total_parts

    def _open_payment_and_invoice_flow(self):
        try:
            customer = {
                "id": self.device_dict.get("customer_id"),
                "name": self.device_dict.get("customer_name", ""),
                "phone": self.device_dict.get("phone_number", "")
                or self.device_dict.get("customer_contact", ""),
            }
            total_amount, labor_cost, parts_cost = self._calculate_service_total()
            if total_amount <= 0:
                show_warning(
                    self, "Tahsilat akışı için önce işçilik veya parça tutarı girin."
                )
                return

            from src.ui.dialogs.payment_dialog import ModernPaymentDialog

            payment_dialog = ModernPaymentDialog(self, self.db, customer)
            payment_dialog.reference_tracking_no = self.tracking_no
            payment_dialog.reference_desc = f"Servis Tahsilati - {self.tracking_no}"
            payment_dialog.inp_amount.setText(
                f"{total_amount:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            payment_dialog.inp_notes.setPlainText(
                f"Servis tahsilati\nTakip No: {self.tracking_no}\nIscilik: {labor_cost:.2f}\nParca: {parts_cost:.2f}"
            )
            if payment_dialog.exec():
                result = getattr(payment_dialog, "result_data", None) or {}
                amount = float(result.get("amount") or total_amount)
                self.db.add_transaction(
                    t_type="Gelir",
                    category="Servis Tahsilati",
                    amount=amount,
                    description=result.get("reference_desc")
                    or f"Servis Tahsilati: {self.tracking_no}",
                    customer_name=customer.get("name"),
                    customer_id=customer.get("id"),
                    date=datetime.now().strftime("%Y-%m-%d"),
                    payment_method=result.get("method"),
                    bank_account_id=result.get("bank_account_id"),
                    tracking_no=self.tracking_no,
                    selected_services=[
                        {
                            "kind": "service_collection",
                            "tracking_no": self.tracking_no,
                            "labor_cost": labor_cost,
                            "parts_cost": parts_cost,
                            "line_total": amount,
                        }
                    ],
                    currency=result.get("currency", "TRY"),
                    original_amount=amount,
                )
                self.db.cursor.execute(
                    "UPDATE devices SET payment_status=?, updated_at=? WHERE tracking_no=?",
                    (
                        "Odendi",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self.tracking_no,
                    ),
                )
                self.db.conn.commit()
                show_success(self, "\u00d6deme al\u0131nd\u0131.")
                try:
                    from src.utils.asistan_motoru import sesli_cevap_ver_async
                    sesli_cevap_ver_async("\u00d6deme al\u0131nd\u0131.")
                except Exception:
                    pass
                main_window = self.window()
                if main_window and hasattr(main_window, "refresh_loaded_page"):
                    for page_id in (101, 105, 106):
                        try:
                            main_window.refresh_loaded_page(page_id)
                        except Exception as refresh_error:
                            logger.warning(
                                "Technician page refresh failed for %s "
                                "(page %s): %s",
                                self.tracking_no,
                                page_id,
                                refresh_error,
                            )
                if main_window and hasattr(main_window, "financial_data_changed"):
                    try:
                        main_window.financial_data_changed.emit()
                    except Exception as signal_error:
                        logger.warning(
                            "Financial refresh signal failed for %s: %s",
                            self.tracking_no,
                            signal_error,
                        )

                if customer.get("id"):
                    from src.ui.dialogs.service_invoice_dialog import ServiceInvoiceDialog

                    invoice_dialog = ServiceInvoiceDialog(
                        self.db, customer.get("id"), self
                    )
                    invoice_dialog.exec()
        except Exception as e:
            show_error(self, f"Tahsilat / fatura akışı açılamadı: {e}")

    def save_update(self):
        """Save wizard data to database"""
        try:
            # Collect data from all wizard pages (if they exist)
            if (
                hasattr(self, "wizard_page1")
                and hasattr(self, "wizard_page2")
                and hasattr(self, "wizard_page3")
            ):
                data_page1 = self.wizard_page1.get_data()
                data_page2 = self.wizard_page2.get_data()
                data_page3 = self.wizard_page3.get_data()

                # Collect Test Data
                test_items = []
                if hasattr(self, "test_toggles"):
                    for name, toggle in self.test_toggles:
                        if toggle.isChecked():
                            test_items.append(name)

                # Merge all data
                merged_data = {**data_page1, **data_page2, **data_page3}
                if not self._is_automotive():
                    merged_data["device_type"] = self.get_technical_service_profile()
                if self._is_automotive():
                    if hasattr(self, "cmb_approval_status"):
                        merged_data["approval_status"] = self._approval_label_to_db(
                            self.cmb_approval_status.currentText().strip()
                        )
                    if hasattr(self, "txt_fault_codes"):
                        merged_data["fault_codes"] = self.txt_fault_codes.text().strip()
                    if hasattr(self, "txt_obd_notes"):
                        merged_data["obd_notes"] = self.txt_obd_notes.toPlainText().strip()
                    if hasattr(self, "txt_inspection_summary"):
                        merged_data["inspection_summary"] = (
                            self.txt_inspection_summary.toPlainText().strip()
                        )

                # Append test items to checklist_status
                base_checklist = merged_data.get("checklist_status", "")
                if base_checklist:
                    final_checklist = base_checklist + "," + ",".join(test_items)
                else:
                    final_checklist = ",".join(test_items)

                final_checklist = ",".join(
                    self._normalize_checklist_items(
                        [x for x in final_checklist.split(",")]
                    )
                )

                merged_data["checklist_status"] = final_checklist
                self._save_cached_checklist_status(final_checklist)
                old_status = self.device_dict.get("status", "")

                exit_date = self.device_dict.get("exit_date")
                delivered_at = self.device_dict.get("delivered_at")
                if merged_data.get("status") == "Teslim Edildi" and not exit_date:
                    now = datetime.now()
                    exit_date = now.strftime("%Y-%m-%d")
                    delivered_at = now.strftime("%Y-%m-%d %H:%M:%S")
                elif merged_data.get("status") != "Teslim Edildi":
                    exit_date = None
                    delivered_at = None

                # Update database
                self.db.cursor.execute(
                    """
                    UPDATE devices 
                    SET status=?, labor_cost=?, fault_description=?, repair_details=?,
                        internal_notes=?, warranty_end_date=?, warranty_status=?, accessories=?,
                        cargo_fee=?, delivery_type=?, payment_status=?, checklist_status=?, exit_date=?, delivered_at=?,
                        approval_status=?, fault_codes=?, obd_notes=?, inspection_summary=?
                    WHERE tracking_no=?
                """,
                    (
                        merged_data.get("status"),
                        merged_data.get("labor_cost"),
                        merged_data.get("fault_description"),
                        merged_data.get("repair_details"),
                        merged_data.get("internal_notes"),
                        merged_data.get("warranty_end_date"),
                        merged_data.get("warranty_status"),
                        merged_data.get("accessories"),
                        merged_data.get("cargo_fee"),
                        merged_data.get("delivery_type"),
                        merged_data.get("payment_status"),
                        merged_data.get("checklist_status"),
                        exit_date,
                        delivered_at,
                        merged_data.get(
                            "approval_status", self.device_dict.get("approval_status")
                        ),
                        merged_data.get(
                            "fault_codes", self.device_dict.get("fault_codes")
                        ),
                        merged_data.get("obd_notes", self.device_dict.get("obd_notes")),
                        merged_data.get(
                            "inspection_summary",
                            self.device_dict.get("inspection_summary"),
                        ),
                        self.tracking_no,
                    ),
                )
                self.db.conn.commit()
                # Use the canonical status writer as the final write so
                # technician-panel changes update delivery timestamps,
                # notifications, and legacy status integrations together.
                saved_status = self.db.update_status(self.tracking_no, merged_data.get("status"))
                if not saved_status:
                    raise RuntimeError("Servis durumu kaydedilemedi")
                if not self._is_automotive():
                    try:
                        self.db.cursor.execute(
                            "UPDATE devices SET device_type=? WHERE tracking_no=?",
                            (merged_data.get("device_type"), self.tracking_no),
                        )
                        self.db.conn.commit()
                    except Exception as profile_err:
                        logger.warning(
                            "Technician profile save skipped for %s: %s",
                            self.tracking_no,
                            profile_err,
                        )
                self._upsert_automotive_service_form_from_panel()
                self._update_automotive_panel_summary()

                try:
                    self.db._sync_service_debt_from_tracking(
                        self.tracking_no,
                        create_if_missing=True,
                        reason="technician_panel_save",
                    )
                except Exception as debt_sync_err:
                    logger.warning(
                        "Technician panel debt sync skipped for %s: %s",
                        self.tracking_no,
                        debt_sync_err,
                    )

                # Log action
                self.audit_logger.log_action(
                    "devices",
                    "UPDATE",
                    f"Teknisyen güncellemesi: {self.tracking_no} - Durum: {merged_data.get('status')}, "
                    + f"Tutar: {merged_data.get('labor_cost', 0) + merged_data.get('cargo_fee', 0)}",
                )

                # --- VOICE CONFIRMATION FOR ARCHIVING (Teslim Edildi) ---
                new_status = merged_data.get("status", "")

                if new_status == "Teslim Edildi" and old_status != "Teslim Edildi":
                    try:
                        # Calculate total amount
                        labor = float(merged_data.get("labor_cost", 0) or 0)
                        cargo = float(merged_data.get("cargo_fee", 0) or 0)

                        parts_cost = float(
                            self.db._get_used_parts_total_try(self.tracking_no)
                            or 0.0
                        )

                        total_amount = labor + cargo + parts_cost
                        customer_name = self.device_dict.get("customer_name", "")

                        # Gelir kaydı: Tutar > 0 ise ödeme/kasa diyaloğu göster
                        if total_amount > 0:
                            from src.utils.asistan_motoru import sesli_cevap_ver_async

                            sesli_cevap_ver_async(
                                f"Cihaz teslim ediliyor. Toplam {self._fmt_try(total_amount)}. Ödemeyi kasaya işleyelim mi?"
                            )

                            confirm_voice = False

                            def on_voice_response(text):
                                nonlocal confirm_voice
                                t = text.lower()
                                if "evet" in t or "onay" in t or "işle" in t:
                                    confirm_voice = True
                                    if (
                                        hasattr(self, "_confirm_dlg")
                                        and self._confirm_dlg
                                    ):
                                        self._confirm_dlg.accept()

                            if self.ai_service is None:
                                from src.utils.ai_service import AIService
                                self.ai_service = AIService(self.db)
                            
                            from src.utils.voice_worker import VoiceWorker
                            listener = VoiceWorker(self.ai_service)
                            listener.text_received.connect(on_voice_response)
                            listener.start()

                            class PaymentConfirmDialog(ModernDialog):
                                def __init__(self, parent=None, labor=0, parts_cost=0, cargo=0, total_amount=0, customer_name=""):
                                    super().__init__(
                                        title="Odeme Onayi ve Kasa Secimi",
                                        parent=parent,
                                        width=450,
                                        height=280,
                                    )
                                    self._parent_ptr = parent
                                    self.set_footer_visible(False)
                                    self.setStyleSheet(
                                        theme_qss(
                                            "background-color: @surface; border-radius: 8px;"
                                        )
                                    )
                                    self.selected_bank_id = None
                                    self.payment_method = "Nakit"

                                    layout = self.content_layout
                                    layout.setSpacing(12)
                                    layout.setContentsMargins(20, 20, 20, 20)

                                    # Tutar özeti
                                    summary = f"Cihaz: {parent.tracking_no if parent else ''}\n"
                                    summary += f"Müşteri: {customer_name}\n\n"
                                    if labor > 0:
                                        summary += f"İşçilik: {parent._fmt_try(labor)}\n"
                                    if parts_cost > 0:
                                        summary += f"Parça/Malzeme: {parent._fmt_try(parts_cost)}\n"
                                    if cargo > 0:
                                        summary += f"Kargo: {parent._fmt_try(cargo)}\n"
                                    summary += (
                                        f"\nTOPLAM: {parent._fmt_try(total_amount)}"
                                    )

                                    lbl_info = QLabel(summary)
                                    lbl_info.setStyleSheet(
                                        theme_qss("color: @text; font-size: 12px;")
                                    )
                                    layout.addWidget(lbl_info)

                                    layout.addWidget(QLabel("Ödeme Yöntemi:"))
                                    self.cmb_method = QComboBox()
                                    self.cmb_method.addItems(
                                        ["Nakit", "Kredi Kartı", "Havale/EFT"]
                                    )
                                    self.cmb_method.setStyleSheet(
                                        theme_qss(
                                            "padding: 8px; border: 1px solid @border; border-radius: 4px; color: @text; background: @surface;"
                                        )
                                    )
                                    layout.addWidget(self.cmb_method)

                                    layout.addWidget(QLabel("Kasa/Banka Seçimi:"))
                                    self.cmb_bank = QComboBox()
                                    self.cmb_bank.addItem("Ana Kasa (Varsayılan)", -1)
                                    self.cmb_bank.setStyleSheet(
                                        theme_qss(
                                            "padding: 8px; border: 1px solid @border; border-radius: 4px; color: @text; background: @surface;"
                                        )
                                    )
                                    try:
                                        db_obj = parent.db if parent else None
                                        if db_obj and hasattr(
                                            db_obj, "get_bank_accounts"
                                        ):
                                            for b in db_obj.get_bank_accounts():
                                                b_name = (
                                                    b.get("bank_name")
                                                    if isinstance(b, dict)
                                                    else b[1]
                                                )
                                                b_id = (
                                                    b.get("id")
                                                    if isinstance(b, dict)
                                                    else b[0]
                                                )
                                                self.cmb_bank.addItem(b_name, b_id)
                                    except Exception:
                                        pass
                                    layout.addWidget(self.cmb_bank)

                                    btn_lay = QHBoxLayout()
                                    btn_lay.setSpacing(10)
                                    btn_no = QPushButton("Ödeme Almadan Teslim Et")
                                    btn_no.setStyleSheet(
                                        theme_qss(
                                            DesignTokens.get_button_qss("secondary")
                                        )
                                    )
                                    btn_no.setFixedHeight(42)
                                    btn_no.clicked.connect(self.reject)

                                    btn_yes = QPushButton("Ödeme Al ve Kasaya İşle")
                                    btn_yes.setStyleSheet(
                                        theme_qss(
                                            DesignTokens.get_button_qss("primary")
                                        )
                                    )
                                    btn_yes.setFixedHeight(42)
                                    btn_yes.clicked.connect(self.accept_data)

                                    btn_lay.addWidget(btn_no)
                                    btn_lay.addWidget(btn_yes)
                                    layout.addLayout(btn_lay)

                                def accept_data(self):
                                    val = self.cmb_bank.currentData()
                                    self.selected_bank_id = val if val != -1 else None
                                    self.payment_method = self.cmb_method.currentText()
                                    self.accept()

                            self._confirm_dlg = PaymentConfirmDialog(
                                self, labor=labor, parts_cost=parts_cost, 
                                cargo=cargo, total_amount=total_amount, 
                                customer_name=customer_name
                            )
                            result = self._confirm_dlg.exec()
                            listener.stop()

                            # Detaylı açıklama
                            desc_parts = [f"Servis Geliri: {self.tracking_no}"]
                            if customer_name:
                                desc_parts.append(f"({customer_name})")
                            detail_parts = []
                            if labor > 0:
                                detail_parts.append(f"İşçilik: {self._fmt_try(labor)}")
                            if parts_cost > 0:
                                detail_parts.append(
                                    f"Parça: {self._fmt_try(parts_cost)}"
                                )
                            if cargo > 0:
                                detail_parts.append(f"Kargo: {self._fmt_try(cargo)}")
                            if detail_parts:
                                desc_parts.append(f"[{' + '.join(detail_parts)}]")
                            desc = " ".join(desc_parts)

                            if result or confirm_voice:
                                pm = getattr(
                                    self._confirm_dlg, "payment_method", "Nakit"
                                )
                                b_id = getattr(
                                    self._confirm_dlg, "selected_bank_id", None
                                )
                                merged_data["payment_status"] = pm

                                try:
                                    self.db.add_transaction_extended(
                                        type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc,
                                        date=datetime.now().strftime("%Y-%m-%d"),
                                        payment_method=pm,
                                        bank_account_id=b_id,
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                except Exception:
                                    self.db.add_transaction(
                                        t_type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc,
                                        payment_method=pm,
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                show_success(
                                    self,
                                    f"\u00d6deme al\u0131nd\u0131: {self._fmt_try(total_amount)}",
                                )
                                sesli_cevap_ver_async("\u00d6deme al\u0131nd\u0131.")
                            else:
                                merged_data["payment_status"] = "Ödenmedi"
                                # Kullanıcı ödeme almadan teslim ediyor; geliri yine de kaydet (ödeme bekliyor)
                                try:
                                    self.db.add_transaction_extended(
                                        type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc + " [Ödeme Bekliyor]",
                                        date=datetime.now().strftime("%Y-%m-%d"),
                                        payment_method="Ödenmedi",
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                except Exception:
                                    self.db.add_transaction(
                                        t_type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc + " [Ödeme Bekliyor]",
                                        payment_method="Ödenmedi",
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                show_info(
                                    self,
                                    f"Gelir kaydı oluşturuldu (Ödeme Bekliyor): {self._fmt_try(total_amount)}",
                                )
                                sesli_cevap_ver_async(
                                    "Gelir kaydı oluşturuldu. Ödeme henüz alınmadı."
                                )

                            # --- GİDER KAYDI: Malzeme Maliyeti ---
                            try:
                                # used_parts tablosundaki is_deleted kolonunu kontrol et
                                try:
                                    self.db.cursor.execute(
                                        "PRAGMA table_info(used_parts)"
                                    )
                                    up_cols = [r[1] for r in self.db.cursor.fetchall()]
                                    del_col = (
                                        "is_deleted"
                                        if "is_deleted" in up_cols
                                        else (
                                            "is_archived"
                                            if "is_archived" in up_cols
                                            else None
                                        )
                                    )
                                    has_pps = "purchase_price_snapshot" in up_cols
                                except Exception:
                                    del_col = None
                                    has_pps = False

                                if has_pps:
                                    cost_query = "SELECT part_name, purchase_price_snapshot, quantity FROM used_parts WHERE tracking_no=?"
                                    if del_col:
                                        cost_query += (
                                            f" AND ({del_col}=0 OR {del_col} IS NULL)"
                                        )
                                    cost_rows = self.db.cursor.execute(
                                        cost_query, (self.tracking_no,)
                                    ).fetchall()
                                    total_material_cost = sum(
                                        float(r[1] or 0) * int(r[2] or 1)
                                        for r in cost_rows
                                    )

                                    if total_material_cost > 0:
                                        part_names = [
                                            f"{r[0]}x{r[2]}" for r in cost_rows if r[0]
                                        ]
                                        cost_desc = f"Servis Malzeme Maliyeti: {self.tracking_no}"
                                        if customer_name:
                                            cost_desc += f" ({customer_name})"
                                        cost_desc += f" [{', '.join(part_names)}]"

                                        try:
                                            self.db.add_transaction_extended(
                                                type="Gider",
                                                category="Malzeme Maliyeti",
                                                amount=total_material_cost,
                                                description=cost_desc,
                                                date=datetime.now().strftime(
                                                    "%Y-%m-%d"
                                                ),
                                                tracking_no=self.tracking_no,
                                                ref_no=self.tracking_no,
                                            )
                                        except Exception:
                                            self.db.add_transaction(
                                                t_type="Gider",
                                                category="Malzeme Maliyeti",
                                                amount=total_material_cost,
                                                description=cost_desc,
                                                tracking_no=self.tracking_no,
                                                ref_no=self.tracking_no,
                                            )
                            except Exception as e:
                                logger.error(
                                    f"Technician panel material cost recording error: {e}"
                                )
                        else:
                            # total_amount == 0; sadece sesli bilgi
                            from src.utils.asistan_motoru import sesli_cevap_ver_async
                            sesli_cevap_ver_async("Cihaz teslim edildi.")

                    except Exception as e:
                        logger.error(
                            f"Technician panel archive confirmation error: {e}",
                            exc_info=True,
                        )

                self.device_dict.update(merged_data)
                self.device_dict["exit_date"] = exit_date
                self.device_dict["delivered_at"] = delivered_at
                self.device_dict["payment_status"] = merged_data.get("payment_status")
                self.db.cursor.execute(
                    "UPDATE devices SET payment_status=?, exit_date=?, delivered_at=? WHERE tracking_no=?",
                    (
                        merged_data.get("payment_status"),
                        exit_date,
                        delivered_at,
                        self.tracking_no,
                    ),
                )
                self.db.conn.commit()
                if hasattr(self.wizard_page3, "combo_payment") and merged_data.get(
                    "payment_status"
                ):
                    self.wizard_page3.combo_payment.setCurrentText(
                        str(merged_data.get("payment_status"))
                    )

                show_success(self, "Kayıt başarıyla güncellendi!")
                main_window = self.window()
                if main_window and hasattr(main_window, "refresh_loaded_page"):
                    for page_id in (101, 105, 106):
                        try:
                            main_window.refresh_loaded_page(page_id)
                        except Exception:
                            pass
                if main_window and hasattr(main_window, "financial_data_changed"):
                    try:
                        main_window.financial_data_changed.emit()
                    except Exception:
                        pass
                self.accept()
            else:
                show_error(self, "Wizard sayfalari yuklenemedi!")

        except Exception as e:
            logger.error(f"Technician panel save_update error: {e}", exc_info=True)
            show_error(self, f"Güncelleme hatası: {e}")

    def _perform_silent_save(self):
        """Used for auto-save when closing or certain events"""
        try:
            if not hasattr(self, "wizard_page1"):
                return
            data_page1 = self.wizard_page1.get_data()
            self.db.cursor.execute(
                "UPDATE devices SET internal_notes=?, accessories=? WHERE tracking_no=?",
                (data_page1.get("internal_notes"), data_page1.get("accessories"), self.tracking_no)
            )
            self.db.conn.commit()
        except Exception:
            pass

    def _handle_toggle_changed(self, name, is_checked):
        """Handle individual test toggle changes"""
        current_status = self._load_cached_checklist_status()
        items = [x.strip() for x in current_status.split(",") if x.strip()]
        
        if is_checked:
            if name not in items:
                items.append(name)
        else:
            if name in items:
                items.remove(name)
        
        new_status = ",".join(items)
        self._persist_toggle_state(new_status)
        
        # UI'daki checklist_status alanını (varsa) güncelle
        if hasattr(self, "wizard_page3") and hasattr(self.wizard_page3, "checklist_status"):
            self.wizard_page3.checklist_status.setText(new_status)

    def _wire_ui_signals(self):
        self.cmb_method.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_bank.currentIndexChanged.connect(self._on_ui_widget_changed)
