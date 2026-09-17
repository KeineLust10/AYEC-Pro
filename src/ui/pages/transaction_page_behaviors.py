# -*- coding: utf-8 -*-

from datetime import datetime
import uuid

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import QMenu, QTreeWidgetItem

from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import (
    show_error,
    show_info,
    show_success,
    show_warning,
)
from src.utils.logger import logger
from src.ui.pages.transaction_multi_select_dialog import MultiSelectServiceDialog


class TransactionPageBehaviorMixin:
    @staticmethod
    def _exchange_rate_style(variant="success"):
        colors = {
            "success": ("@success_bg", "@success"),
            "accent": ("@surface_alt", "@accent"),
            "danger": ("@danger_bg", "@danger"),
        }
        background, foreground = colors.get(variant, colors["success"])
        return theme_qss(
            f"""
            font-size: 12px;
            color: {foreground};
            font-weight: 600;
            padding: 8px;
            background: {background};
            border-radius: 6px;
            border-left: 3px solid {foreground};
            """
        )

    def _get_selected_currency_code(self):
        if hasattr(self, "cmb_currency"):
            return self._parse_currency_code(self.cmb_currency.currentText())
        return "TRY"

    def _convert_try_for_selected_currency(self, amount_try):
        currency_code = self._get_selected_currency_code()
        if currency_code == "TRY":
            return float(amount_try or 0)
        rate = (
            self.current_exchange_rate
            if getattr(self, "current_exchange_rate", 0) > 0
            else 1.0
        )
        return float(amount_try or 0) / rate

    def _convert_amount_between_currencies(
        self, amount, from_currency="TRY", to_currency=None
    ):
        return CurrencyHelper.convert_amount(
            self.db,
            float(amount or 0),
            from_currency=(from_currency or "TRY").upper(),
            to_currency=(to_currency or self._get_selected_currency_code()).upper(),
        )

    def _format_selected_amount_from_try(self, amount_try, include_try_reference=False):
        currency_code = self._get_selected_currency_code()
        converted = self._convert_try_for_selected_currency(amount_try)
        primary = CurrencyHelper.format_amount(
            converted, db=self.db, currency_code=currency_code
        )
        if currency_code == "TRY" or not include_try_reference:
            return primary
        return f"{primary} | {CurrencyHelper.format_amount(amount_try, db=self.db, currency_code='TRY')}"

    @staticmethod
    def _parse_currency_code(currency_text):
        """Parse currency code from combobox text. Supports '₺ TRY', '$ USD', '€ EUR' and legacy 'TRY - Türk Lirası (₺)'."""
        if " - " in currency_text:
            return currency_text.split(" - ")[0].strip()
        parts = currency_text.strip().split()
        return parts[1] if len(parts) >= 2 else "TRY"

    def load_customers(self):
        """Müşteri listesini yükle"""
        try:
            customers = self.db.get_customers()
            self.cmb_customer.clear()
            for c in customers:
                # c is tuple: (id, name, phone, ...)
                # Handle both dict (if row_factory set) and tuple
                if isinstance(c, dict):
                    name = c.get("name")
                    cid = c.get("id")
                else:
                    cid = c[0]
                    name = c[1]

                self.cmb_customer.addItem(str(name), cid)
            self.cmb_customer.setCurrentIndex(-1)
        except Exception as e:
            logger.error(f"TransactionPage load_customers error: {e}")

    def load_services(self):
        """Hizmet ve Stok listelerini birleştirip yükle"""
        try:
            self.cmb_service.clear()
            self.services_data = {}

            # 1. Hizmetleri yükle
            selected_currency = self._get_selected_currency_code()
            services = self.db.get_services_list() or []
            for s in services:
                name = s["name"]
                source_currency = str(s.get("currency", "TRY") or "TRY").upper()
                # Store full info in services_data for backward compatibility or easy lookup
                try:
                    raw_price = (
                        str(s["price"]).replace(" ₺", "").replace("₺", "").strip()
                        if s["price"]
                        else "0"
                    )
                    source_price = float(raw_price)
                except (TypeError, ValueError):
                    source_price = 0.0

                final_price = self._convert_amount_between_currencies(
                    source_price,
                    from_currency=source_currency,
                    to_currency=selected_currency,
                )

                info = {
                    "id": s["id"],
                    "name": name,
                    "type": "service",
                    "price": final_price,
                    "source_price": source_price,
                    "source_currency": source_currency,
                    "description": s.get("description", ""),
                }
                self.services_data[name] = info
                # Add to combo with ALL info as data
                display_str = (
                    f"{name} - "
                    f"{CurrencyHelper.format_amount(final_price, db=self.db, currency_code=selected_currency)}"
                )
                self.cmb_service.addItem(display_str, info)

            # 2. Stoktaki Ürünleri yükle - Robust Query
            self.db.cursor.execute(
                "SELECT id, name, stock, price FROM parts ORDER BY name"
            )
            parts = self.db.cursor.fetchall() or []

            for p in parts:
                # Try explicit access first (Works for dict and sqlite3.Row)
                try:
                    pid = p["id"]
                    pname = p["name"]
                    pstock = p["stock"]
                    pprice = p["price"]
                except (TypeError, KeyError, IndexError):
                    # Tuple fallback for SELECT id, name, stock, price
                    pid = p[0]
                    pname = p[1]
                    pstock = p[2]
                    pprice = p[3]

                try:
                    raw_price = (
                        str(pprice).replace(" ₺", "").replace("₺", "").strip()
                        if pprice
                        else "0"
                    )
                    final_price = float(raw_price)
                except (TypeError, ValueError):
                    final_price = 0.0

                display_name = (
                    f"{pname} (Stok: {pstock}) - "
                    f"{CurrencyHelper.format_amount(final_price, db=self.db, currency_code=selected_currency)}"
                )
                info = {
                    "id": pid,
                    "name": pname,
                    "type": "part",
                    "price": final_price,
                    "description": f"Stoktan ürün: {pname}",
                    "stock": pstock,
                }
                self.services_data[display_name] = info
                self.cmb_service.addItem(display_name, info)

        except Exception as e:
            logger.error(f"TransactionPage load_services error: {e}")

    def on_service_selection_change(self, *args):
        """Hizmet seçimi değiştiğinde"""
        checked_items = self.cmb_service.getCheckedItems()

        if len(checked_items) == 1:
            # Single item: Enable editing and show details
            _, data = checked_items[0]
            if data:
                self.inp_price.setValue(float(data["price"]))
                self.inp_desc.setText(data["description"])
                self.inp_price.setEnabled(True)
                self.inp_desc.setEnabled(True)
        elif len(checked_items) > 1:
            # Multi: Calculate Total
            total_price = 0
            for _, data in checked_items:
                if data:
                    total_price += float(data["price"])

            self.inp_price.setValue(total_price)
            self.inp_desc.setText(
                f"{len(checked_items)} kalem seçildi - Toplam: "
                f"{self._format_selected_amount_from_try(total_price, include_try_reference=False)}"
            )
            self.inp_price.setEnabled(False)
            self.inp_desc.setEnabled(False)
        else:
            # None
            self.inp_price.setValue(0)
            self.inp_desc.clear()
            self.inp_price.setEnabled(True)
            self.inp_desc.setEnabled(True)

    def add_to_cart(self):
        """Sepete hizmet(leri) ekle"""
        checked_items = self.cmb_service.getCheckedItems()

        if not checked_items:
            self.notify("Lütfen en az bir hizmet seçin!", "warning")
            return

        date = self.date_edit.date().toString("dd.MM.yyyy")
        count = 0

        # If single item, use the input fields
        if len(checked_items) == 1:
            name, data = checked_items[0]
            price = self.inp_price.value()
            desc = self.inp_desc.text()
            qty = self.inp_qty.value()

            # info = data or self.services_data.get(name, {})
            info = data if data else {}

            self.cart_items.append(
                {
                    "id": str(uuid.uuid4()),
                    "item_id": info.get("id"),
                    "type": info.get("type", "service"),
                    "service": info.get("name", name),
                    "brand": info.get("brand", ""),
                    "description": desc,
                    "price": price,
                    "qty": qty,
                    "date": date,
                }
            )
            count = 1

        else:
            # Multi items
            for name, data in checked_items:
                if data:
                    price = (
                        float(data["price"]) if data.get("price") is not None else 0.0
                    )
                    desc = data["description"]

                    self.cart_items.append(
                        {
                            "id": str(uuid.uuid4()),
                            "item_id": data.get("id"),
                            "type": data.get("type", "service"),
                            "service": data.get("name", name),
                            "brand": data.get("brand", ""),
                            "description": desc,
                            "price": price,
                            "qty": 1,
                            "date": date,
                        }
                    )
                    count += 1

        self.refresh_cart_ui()

        # Clear selection without reloading all services/stock every add.
        if hasattr(self.cmb_service, "clearChecks"):
            self.cmb_service.clearChecks()
        else:
            self.cmb_service.clear()
            self.load_services()

        self.inp_price.setValue(0)
        self.inp_qty.setValue(1)
        self.inp_desc.clear()
        self.inp_price.setEnabled(True)
        self.inp_qty.setEnabled(True)
        self.inp_desc.setEnabled(True)

        self.update_totals()

        if count > 0:
            show_success(self.window(), f"{count} kalem sepete eklendi ✅")

    def open_multi_select(self):
        """Toplu seçim dialogunu aç"""
        try:
            # Hizmet verilerini hazırla
            if not hasattr(self, "services_data") or not self.services_data:
                self.load_services()  # Veri yoksa yükle

            dialog = MultiSelectServiceDialog(self, self.services_data)
            if dialog.exec():
                selected_items = dialog.get_selected()
                if not selected_items:
                    return

                date = self.date_edit.date().toString("dd.MM.yyyy")
                count = 0

                # Get quantity from the input field
                try:
                    qty = int(self.qty_input.text() or 1)
                    if qty < 1:
                        qty = 1
                except (TypeError, ValueError, AttributeError):
                    qty = 1

                for name, price, desc in selected_items:
                    self.cart_items.append(
                        {
                            "id": str(uuid.uuid4()),
                            "item_id": None,  # ID bilgisi şu an yok, gerekirse services_data'dan alınabilir
                            "type": "service",
                            "service": name,
                            "description": desc,
                            "price": float(price),
                            "qty": qty,
                            "date": date,
                        }
                    )
                    count += 1

                self.refresh_cart_ui()
                self.update_totals()

                if count > 0:
                    show_success(self, f"{count} kalem ({qty} adet) eklendi.")

        except Exception as e:
            show_error(self, f"Hata: {e}")

    def refresh_cart_ui(self):
        """Sepet ağacını yeniden çiz"""
        self.cart_table.clear()

        # Group by date
        grouped = {}
        for item in self.cart_items:
            # date format dd.mm.yyyy usually
            d = item["date"]
            if d not in grouped:
                grouped[d] = []
            grouped[d].append(item)

        # Sort dates
        def date_sorter(d_str):
            try:
                return datetime.strptime(d_str, "%d.%m.%Y")
            except (TypeError, ValueError):
                return datetime.min

        sorted_dates = sorted(list(grouped.keys()), key=date_sorter, reverse=True)

        # Populate
        self.cart_table.blockSignals(True)

        for d in sorted_dates:
            items = grouped[d]
            total_grp = sum(float(x["price"]) * int(x.get("qty", 1)) for x in items)

            # Parent
            root = QTreeWidgetItem(self.cart_table)
            root.setText(0, f"📅 {d}")
            root.setText(1, f"{len(items)} Kalem")
            root.setText(
                4,
                self._format_selected_amount_from_try(
                    total_grp, include_try_reference=False
                ),
            )

            # Style Parent
            for c in range(5):
                root.setBackground(c, QColor("#f1f5f9"))
                f = root.font(c)
                f.setBold(True)
                root.setFont(c, f)

            # Children
            for item in items:
                child = QTreeWidgetItem(root)
                child.setData(0, Qt.ItemDataRole.UserRole, item["id"])  # Store ID

                child.setText(0, "")  # Date column empty for child
                child.setText(1, item["service"])
                child.setText(2, str(item.get("qty", 1)))
                child.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
                child.setText(3, item["description"])

                t = item["price"] * item.get("qty", 1)
                child.setText(
                    4,
                    self._format_selected_amount_from_try(
                        t, include_try_reference=False
                    ),
                )
                child.setTextAlignment(4, Qt.AlignmentFlag.AlignRight)

            root.setExpanded(True)

        self.cart_table.blockSignals(False)

        # Show/Hide
        if not self.cart_items:
            self.cart_content_stack.setCurrentWidget(self.cart_empty_state)
        else:
            self.cart_content_stack.setCurrentWidget(self.cart_table)







    def add_description_context(self):
        item = self.cart_table.currentItem()
        if not item:
            return
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        cart_item = next((x for x in self.cart_items if x.get("id") == item_id), None)
        if not cart_item:
            return

        current_desc = cart_item.get("description", "")
        from src.ui.dialogs.modern_input_dialog import ModernInputDialog

        desc, ok = ModernInputDialog.get_multiline(
            self, "A\u00e7\u0131klama Ekle", "Hizmet a\u00e7\u0131klamas\u0131:", current_desc
        )
        if ok:
            cart_item["description"] = desc
            self.refresh_cart_ui()

    def copy_service_context(self):
        item = self.cart_table.currentItem()
        if not item:
            return
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        original_item = next(
            (x for x in self.cart_items if x.get("id") == item_id), None
        )
        if not original_item:
            return

        new_item = original_item.copy()
        new_item["id"] = str(uuid.uuid4())
        self.cart_items.append(new_item)
        self.refresh_cart_ui()
        self.update_totals()
        show_info(self, "Hizmet kopyaland\u0131.")

    def remove_from_cart(self):
        """Sepetten hizmet çıkar"""
        item = self.cart_table.currentItem()
        if not item:
            return

        # User role holds ID
        item_id = item.data(0, Qt.ItemDataRole.UserRole)

        if not item_id:
            # Parent clicked
            self.notify(
                "Lütfen silmek için bir işlem seçin (Tarih başlığını silemezsiniz).",
                "warning",
            )
            return

        # Remove from list
        self.cart_items = [x for x in self.cart_items if x.get("id") != item_id]

        self.update_totals()
        self.refresh_cart_ui()

        # Show empty state if cart is now empty
        if not self.cart_items:
            self.cart_content_stack.setCurrentWidget(self.cart_empty_state)
        else:
            self.cart_content_stack.setCurrentWidget(self.cart_table)

    def clear_cart(self):
        """Sepeti temizle"""
        self.cart_items = []
        if hasattr(self, "cart_table"):
            self.cart_table.clear()
            self.cart_table.setRowCount(0)
        if hasattr(self, "inp_discount"):
            self.inp_discount.setValue(0)
        self.update_totals()
        if hasattr(self, "cart_content_stack") and hasattr(self, "cart_empty_state"):
            self.cart_content_stack.setCurrentWidget(self.cart_empty_state)
        if hasattr(self, "switch_tab"):
            try:
                self.switch_tab(0)
            except Exception:
                pass

    def update_totals(self):
        """Toplamları hesapla ve güncelle"""
        # Centralized Currency Symbol
        currency_code = self._get_selected_currency_code()
        symbol = CurrencyHelper.get_symbol(self.db, currency_code)

        if hasattr(self, "inp_price"):
            self.inp_price.setSuffix(f" {symbol}")
        if hasattr(self, "inp_discount"):
            self.inp_discount.setSuffix(f" {symbol}")

        if not self.cart_items:
            zero_amount = CurrencyHelper.format_amount(
                0, db=self.db, currency_code=currency_code
            )
            if hasattr(self, "lbl_subtotal"):
                self.lbl_subtotal.setText(f"Ara Toplam: {zero_amount}")
            if hasattr(self, "lbl_total"):
                self.lbl_total.setText(zero_amount)
            return 0, 0, 0, 0, 0

        subtotal = sum(item["price"] * item.get("qty", 1) for item in self.cart_items)
        discount = self.inp_discount.value()

        vat_text = self.cmb_vat.currentText().replace("%", "")
        try:
            vat_rate = int(vat_text) / 100
        except (TypeError, ValueError):
            vat_rate = 0

        net = subtotal - discount
        vat_amount = net * vat_rate
        total = net + vat_amount

        # Dual Currency Display Logic
        display_subtotal = self._format_selected_amount_from_try(
            subtotal, include_try_reference=currency_code != "TRY"
        )
        display_total = self._format_selected_amount_from_try(
            total, include_try_reference=currency_code != "TRY"
        )

        if hasattr(self, "lbl_subtotal"):
            self.lbl_subtotal.setText(f"Ara Toplam: {display_subtotal}")

        if hasattr(self, "lbl_total"):
            self.lbl_total.setText(display_total)

        return subtotal, discount, vat_amount, total, net

    def show_cart_context_menu(self, position):
        """Display context menu for cart table."""
        if not is_context_menu_enabled(self.db):
            return
        item = self.cart_table.itemAt(position)
        if not item:
            return

        # Select item
        item.setSelected(True)
        self.cart_table.setCurrentItem(item)

        menu = QMenu()

        # Group 1: Edit
        action_edit_qty = QAction("Miktari Degistir", self)
        action_edit_qty.triggered.connect(self.edit_quantity_context)
        menu.addAction(action_edit_qty)

        action_edit_price = QAction("Fiyati Guncelle", self)
        action_edit_price.triggered.connect(self.edit_price_context)
        menu.addAction(action_edit_price)

        action_add_desc = QAction("Aciklama Ekle", self)
        action_add_desc.triggered.connect(self.add_description_context)
        menu.addAction(action_add_desc)

        menu.addSeparator()

        # Group 2: Copy
        action_copy = QAction("Hizmeti Kopyala", self)
        action_copy.triggered.connect(self.copy_service_context)
        menu.addAction(action_copy)

        menu.addSeparator()

        # Group 3: Remove
        action_remove = QAction("Sepetten Cikar", self)
        action_remove.triggered.connect(self.remove_from_cart)
        menu.addAction(action_remove)
        menu.exec(self.cart_table.viewport().mapToGlobal(position))

    def edit_quantity_context(self):
        item = self.cart_table.currentItem()
        if not item:
            return
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        # Find in list
        cart_item = next((x for x in self.cart_items if x.get("id") == item_id), None)
        if not cart_item:
            return

        current_qty = cart_item.get("qty", 1)
        from src.ui.dialogs.modern_input_dialog import ModernInputDialog

        quantity_dialog = (
            ModernInputDialog.get_int
            if cart_item.get("type") == "part"
            else ModernInputDialog.get_double
        )
        qty, ok = quantity_dialog(
            self, "Miktar Değiştir", "Yeni miktar:", current_qty
        )
        if ok:
            cart_item["qty"] = qty
            self.refresh_cart_ui()
            self.update_totals()

    def edit_price_context(self):
        item = self.cart_table.currentItem()
        if not item:
            return
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        cart_item = next((x for x in self.cart_items if x.get("id") == item_id), None)
        if not cart_item:
            return

        current_price = cart_item["price"]
        from src.ui.dialogs.modern_input_dialog import ModernInputDialog

        price_label = CurrencyHelper.get_label(
            self._get_selected_currency_code(), db=self.db
        )
        price, ok = ModernInputDialog.get_double(
            self, "Fiyat Güncelle", f"Yeni birim fiyat ({price_label}):", current_price
        )
        if ok:
            cart_item["price"] = price
            self.refresh_cart_ui()
            self.update_totals()



    # Legacy _internal_save removed to prevent conflicts
    # All save logic is now handled by the multi-currency enabled save_transaction method below.


    def create_proforma(self):
        """Proforma PDF oluştur"""
        if not self.cart_items:
            self.notify("Sepet boş!", "warning")
            return

        customer_id = self.cmb_customer.currentData()
        customer_name = self.cmb_customer.currentText()
        customer_company = ""
        if self.cmb_customer.currentIndex() == -1:
            customer_name = "Peşin / Genel Müşteri"
            customer_id = None
        else:
            try:
                self.db.cursor.execute("SELECT name, company_name FROM customers WHERE id=?", (customer_id,))
                row = self.db.cursor.fetchone()
                if row:
                    if hasattr(row, "keys"):
                        customer_name = str(row["name"] or customer_name).strip()
                        customer_company = str(row["company_name"] or "").strip()
                    else:
                        customer_name = str(row[0] or customer_name).strip()
                        customer_company = str(row[1] or "").strip() if len(row) > 1 else ""
            except Exception as e:
                logger.debug(f"Proforma customer detail fallback used: {e}")

        # Determine current currency selection
        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        currency_mode = (
            "USD"
            if currency_code == "USD"
            else "EUR"
            if currency_code == "EUR"
            else "TL"
        )

        # Proforma dialog aç
        from src.ui.pages.transaction.dialogs.proforma_dialog import ProformaDialog

        dialog = ProformaDialog(
            self,
            self.db,
            self.cart_items,
            self.update_totals(),
            customer_name,
            currency_mode=currency_mode,
            customer_id=customer_id,
            customer_company=customer_company,
            initial_project=getattr(self, "_editing_offer_project", ""),
            preferred_template=getattr(self, "_editing_offer_template", ""),
            source="sales_hub",
            existing_offer_id=getattr(self, "_editing_offer_id", None),
            existing_offer_no=getattr(self, "_editing_offer_no", ""),
            include_approval=(
                self.toggle_offer_approval.isChecked()
                if hasattr(self, "toggle_offer_approval")
                else True
            ),
        )
        dialog.exec()
        self.load_services()

    def notify(self, message, level="info"):
        """Centralized notification proxy"""
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
        elif hasattr(self.window(), "show_notification"):
            self.window().show_notification(message, level)
        else:
            # Fallback to local helper if available
            if level == "error":
                show_error(self.window(), message)
            elif level == "success":
                show_success(self.window(), message)
            elif level == "warning":
                show_warning(self.window(), message)
            else:
                show_info(self.window(), message)

    def eventFilter(self, source, event):
        """Handle events for specific widgets."""
        return super().eventFilter(source, event)

    # ProformaDialog removed - Using the one from src.ui.pages.transaction.dialogs.proforma_dialog

    def update_exchange_rates(self):
        """TCMB'den güncel kurları çek ve veritabanına kaydet"""
        try:
            # Kurları güncelle
            ExchangeRateManager.update_rates_if_needed(self.db)

            # İlk kuru göster (TRY seçili)
            self.on_currency_changed(self.cmb_currency.currentText())

        except Exception as e:
            self.lbl_exchange_rate.setText(f"Kur güncellenemedi: {e}")
            self.lbl_exchange_rate.setStyleSheet(self._exchange_rate_style("danger"))

    def refresh_financial_defaults(self):
        from src.utils.tax_settings import TaxSettings

        if hasattr(self, "cmb_vat") and not getattr(
            self,
            "_editing_offer_id",
            None,
        ):
            vat_text = TaxSettings.combo_text(self.db)
            if self.cmb_vat.findText(vat_text) < 0:
                self.cmb_vat.addItem(vat_text)
            self.cmb_vat.setCurrentText(vat_text)
        self.update_exchange_rates()

    def on_currency_changed(self, currency_text):
        """Para birimi değiştiğinde kuru güncelle"""
        try:
            # Widget henüz oluşturulmamışsa çık
            if not hasattr(self, "lbl_exchange_rate"):
                return

            # Para birimi kodunu çıkar (TRY, USD, EUR)
            currency_code = self._parse_currency_code(currency_text)

            if currency_code == "TRY":
                self.current_exchange_rate = 1.0
                self.lbl_exchange_rate.setText("TRY - Kur: 1.00")
                self.lbl_exchange_rate.setStyleSheet(self._exchange_rate_style("success"))
            else:
                # TCMB'den kuru al
                rate = ExchangeRateManager.get_current_rate(
                    self.db, currency_code, "selling"
                )

                if rate:
                    self.current_exchange_rate = rate
                    symbol = "$" if currency_code == "USD" else "€"
                    self.lbl_exchange_rate.setText(
                        f"{symbol} {currency_code} Satış Kuru: {rate:.4f} {CurrencyHelper.get_symbol(self.db, 'TRY')}"
                    )
                    self.lbl_exchange_rate.setStyleSheet(self._exchange_rate_style("accent"))
                else:
                    self.lbl_exchange_rate.setText(f"{currency_code} kuru bulunamadı!")
                    self.lbl_exchange_rate.setStyleSheet(
                        self._exchange_rate_style("danger")
                    )
                    self.current_exchange_rate = 1.0

            # Toplamları güncelle (eğer metod varsa)
            if hasattr(self, "load_services"):
                self.load_services()
            if hasattr(self, "update_totals"):
                self.update_totals()

        except Exception as e:
            if hasattr(self, "lbl_exchange_rate"):
                self.lbl_exchange_rate.setText(f"Hata: {e}")
            self.current_exchange_rate = 1.0

    def save_and_pay(self):
        """Servis Kaydı + Ödeme Alma (Tahsilat) - Çoklu Para Birimi"""
        self.save_transaction(pay_now=True)

    def save_transaction(self, pay_now=False):
        """Servisi borç olarak kaydet (Çoklu para birimi destekli)"""
        try:
            # Müşteri seçimi kontrolü
            if (
                self.cmb_customer.currentIndex() == -1
                or not self.cmb_customer.currentText()
            ):
                show_error(self, "Lütfen bir müşteri seçin!")
                return

            # Sepet kontrolü
            if not self.cart_items:
                show_error(self, "Sepette hiç ürün/hizmet yok!")
                return

            # Müşteri bilgilerini al
            customer_text = self.cmb_customer.currentText()
            # customer_id = int(customer_text.split(' - ')[0]) if ' - ' in customer_text else None
            # FIX: Use item data directly
            customer_id = self.cmb_customer.currentData()

            if not customer_id:
                show_error(
                    self,
                    "Geçersiz müşteri seçimi!\\nLütfen müşteri listesinden seçim yapın.",
                )
                return

            # Para birimi bilgilerini al
            currency_text = self.cmb_currency.currentText()
            currency_code = self._parse_currency_code(currency_text)
            if currency_code == "TRY":
                self.current_exchange_rate = 1.0
            else:
                current_rate = ExchangeRateManager.get_current_rate(
                    self.db,
                    currency_code,
                    "selling",
                )
                if not current_rate:
                    show_error(
                        self,
                        "Guncel doviz kuru bulunamadi. Islem kaydedilmedi.",
                    )
                    return
                self.current_exchange_rate = float(current_rate)

            # Toplam tutarı hesapla
            total_try = self.calculate_cart_total()  # TL cinsinden toplam

            # Döviz cinsinden tutarı hesapla
            if currency_code == "TRY":
                amount_in_currency = total_try
            else:
                amount_in_currency = (
                    total_try / self.current_exchange_rate
                    if self.current_exchange_rate > 0
                    else 0
                )

            payment_amount = 0.0
            payment_method = None
            payment_note = ""
            if pay_now:
                from src.ui.dialogs.sale_payment_dialog import SalePaymentDialog

                payment_dialog = SalePaymentDialog(
                    total=amount_in_currency,
                    currency_code=currency_code,
                    customer_name=customer_text,
                    parent=self,
                )
                if not payment_dialog.exec():
                    return
                payment_amount = payment_dialog.payment_amount
                payment_method = payment_dialog.payment_method
                payment_note = payment_dialog.payment_note

            if pay_now and not self.db.create_payment_debt_links_table():
                show_error(
                    self,
                    "Odeme dagitim tablosu hazirlanamadi. Islem kaydedilmedi.",
                )
                return

            stock_plan = []
            for item in self.cart_items:
                if item.get("type") != "part" or not item.get("item_id"):
                    continue
                qty = int(
                    item.get("qty")
                    or item.get("quantity")
                    or item.get("adet")
                    or 1
                )
                if qty <= 0:
                    show_error(self, "Stok miktari pozitif olmalidir.")
                    return
                part_id = int(item.get("item_id"))
                part_row = self.db.cursor.execute(
                    """
                    SELECT name, COALESCE(stock, 0)
                    FROM parts
                    WHERE id=? AND COALESCE(is_deleted, 0)=0
                    """,
                    (part_id,),
                ).fetchone()
                if not part_row:
                    show_error(self, f"Stok karti bulunamadi: {part_id}")
                    return
                available = int(part_row[1] or 0)
                if available < qty:
                    show_error(
                        self,
                        (
                            f"Yetersiz stok: {part_row[0]} "
                            f"(mevcut {available}, istenen {qty})"
                        ),
                    )
                    return
                stock_plan.append((part_id, qty, str(part_row[0] or "")))

            # Tracking number olustur
            tracking_no = f"SRV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ref_label = f"Ref: {tracking_no}"

            # Detayli aciklama olustur (her urun ve adedi ile)
            item_details = []
            for item in self.cart_items:
                item_name = item.get("service") or item.get("part_name") or "Urun"
                qty = item.get("qty") or item.get("quantity") or item.get("adet") or 1
                price = item.get("price", 0)
                item_details.append(
                    f"{item_name} (x{qty}) - "
                    f"{CurrencyHelper.format_amount(price * qty, db=self.db, currency_code='TRY')}"
                )

            description = (
                f"{ref_label} | Servis Islemi - {len(self.cart_items)} kalem\n"
                + "\n".join(item_details)
            )

            # Tarih al (datepicker varsa)
            from datetime import datetime as dt

            txn_date = None
            if hasattr(self, "date_edit_transaction"):
                date_str = self.date_edit_transaction.date().toString("yyyy-MM-dd")
                time_str = dt.now().strftime("%H:%M:%S")
                txn_date = f"{date_str} {time_str}"

            # 1. Dovizli islem kaydet (BORC)
            success = self.db.add_currency_transaction(
                customer_id=customer_id,
                amount=amount_in_currency,
                currency=currency_code,
                transaction_type="DEBIT",
                exchange_rate=self.current_exchange_rate
                if currency_code != "TRY"
                else 1.0,
                description=description,
                tracking_no=tracking_no,
                created_at=txn_date,
                commit=False,
            )

            if not success:
                raise RuntimeError("Customer debt could not be recorded")
            debt_txn_id = None
            if pay_now:
                debt_txn_id = self.db.get_last_currency_transaction_id()
                if not debt_txn_id:
                    raise RuntimeError("Customer debt transaction id is missing")

            accounting_id = self.db.add_transaction(
                t_type="Gelir",
                category="Satis",
                amount=amount_in_currency,
                description=description,
                customer_name=customer_text,
                customer_id=customer_id,
                date=self.date_edit_transaction.date().toString("yyyy-MM-dd")
                if hasattr(self, "date_edit_transaction")
                else None,
                payment_method=payment_method,
                tracking_no=tracking_no,
                ref_no=tracking_no,
                selected_services=self.cart_items,
                currency=currency_code,
                original_amount=amount_in_currency,
                exchange_rate=self.current_exchange_rate,
                commit=False,
            )
            if not accounting_id:
                raise RuntimeError("Accounting transaction could not be recorded")

            # 2. Deduct stock after all stock cards have passed preflight.
            for part_id, qty, part_name in stock_plan:
                logger.debug(
                    "Deducting stock - Part ID: %s, Quantity: %s",
                    part_id,
                    qty,
                )
                if not self.db.use_part(
                    part_id,
                    qty,
                    tracking_no,
                    commit=False,
                ):
                    raise RuntimeError(
                        f"Stock deduction failed: {part_name}"
                    )

            # 2. Ödeme Alma (Varsa) - DÖVİZLİ
            if pay_now:
                # Tahsilat kaydı (ALACAK)
                payment_description = (
                    f"Tahsilat ({payment_method}) - {description}"
                )
                if payment_note:
                    payment_description += f"\nOdeme Notu: {payment_note}"
                credit_ok = self.db.add_currency_transaction(
                    customer_id=customer_id,
                    amount=payment_amount,
                    currency=currency_code,
                    transaction_type="CREDIT",  # Alacak (Ödeme)
                    exchange_rate=self.current_exchange_rate,
                    description=payment_description,
                    tracking_no=tracking_no,
                    commit=False,
                )

                if not credit_ok:
                    raise RuntimeError("Payment could not be recorded")
                payment_txn_id = self.db.get_last_currency_transaction_id()
                if not payment_txn_id:
                    raise RuntimeError("Payment transaction id is missing")
                allocation = self.db.apply_payment_to_debts(
                    customer_id=customer_id,
                    payment_amount=payment_amount,
                    currency=currency_code,
                    payment_transaction_id=payment_txn_id,
                    selected_debt_ids=[debt_txn_id],
                    commit=False,
                )
                if not allocation.get("ok", False):
                    raise RuntimeError(
                        allocation.get("error")
                        or "Payment could not be allocated to debt"
                    )

                self.db.conn.commit()
                try:
                    self.db.notify_jarvis(
                        (
                            f"{customer_text} tarafindan "
                            f"{payment_amount:.2f} {currency_code} "
                            "odeme alindi."
                        ),
                        "payment",
                        True,
                    )
                except Exception as voice_error:
                    logger.warning(
                        "Post-commit voice notification failed for %s: %s",
                        tracking_no,
                        voice_error,
                    )
                if credit_ok:
                    remaining_debt = max(
                        0.0,
                        amount_in_currency - payment_amount,
                    )
                    show_success(
                        self,
                        (
                            "Islem ve odeme kaydedildi!\n"
                            f"Alinan: {payment_amount:.2f} {currency_code}\n"
                            f"Kalan borc: {remaining_debt:.2f} {currency_code}"
                        ),
                    )
                if hasattr(self, "main_window") and self.main_window and hasattr(self.main_window, "financial_data_changed"):
                    self.main_window.financial_data_changed.emit()
                self.clear_cart()
                if hasattr(self, "main_window") and self.main_window and hasattr(self.main_window, "refresh_loaded_page"):
                    for pid in (21, 40, 101, 105, 106):
                        try:
                            self.main_window.refresh_loaded_page(pid)
                        except Exception as refresh_error:
                            logger.warning(
                                "Page refresh failed after %s (page %s): %s",
                                tracking_no,
                                pid,
                                refresh_error,
                            )

            elif success:
                self.db.conn.commit()
                try:
                    self.db.notify_jarvis(
                        f"{tracking_no} servis kaydi olusturuldu.",
                        "payment",
                        False,
                    )
                except Exception as voice_error:
                    logger.warning(
                        "Post-commit voice notification failed for %s: %s",
                        tracking_no,
                        voice_error,
                    )
                show_success(
                    self,
                    f"Servis Kaydedildi!\\n{amount_in_currency:.2f} {currency_code} borç eklendi.",
                )
                if hasattr(self, "main_window") and self.main_window and hasattr(self.main_window, "financial_data_changed"):
                    self.main_window.financial_data_changed.emit()
                self.clear_cart()
                if hasattr(self, "main_window") and self.main_window and hasattr(self.main_window, "refresh_loaded_page"):
                    for pid in (21, 40, 101, 105, 106):
                        try:
                            self.main_window.refresh_loaded_page(pid)
                        except Exception as refresh_error:
                            logger.warning(
                                "Page refresh failed after %s (page %s): %s",
                                tracking_no,
                                pid,
                                refresh_error,
                            )
            else:
                show_error(self, "İşlem kaydedilemedi!")

        except Exception as e:
            try:
                self.db.conn.rollback()
            except Exception as rollback_error:
                logger.error(
                    "Service save rollback failed: %s",
                    rollback_error,
                )
            logger.exception("Service transaction save failed")
            show_error(self, f"Hata: {e}")

    def calculate_cart_total(self):
        """Sepetteki toplam tutarı hesapla (TL cinsinden, indirim ve KDV dahil)"""
        _, _, _, total, _ = self.update_totals()
        return total
