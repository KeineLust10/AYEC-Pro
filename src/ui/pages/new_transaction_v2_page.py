# -*- coding: utf-8 -*-

import json
import logging
import uuid

from PyQt6.QtCore import QDate, QEvent, QSettings, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs.bulk_stock_select_dialog import BulkStockSelectDialog
from src.ui.pages.transaction_multi_select_dialog import MultiSelectServiceDialog
from src.ui.pages.transaction_page_behaviors import TransactionPageBehaviorMixin
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.empty_state import EmptyState
from src.ui.widgets.modern_inputs import InlineNumberStepper, ModernComboBox
from src.ui.widgets.transaction_reference_card import TransactionReferenceCard
from src.ui.widgets.financial_reference_controls import FinancialReferenceActionButton, FinancialReferenceIconButton, ReferenceMetricValueLabel, ReferenceTotalLabel
from src.ui.widgets.reference_date_edit import ReferenceDateEdit
from src.ui.widgets.reference_currency_stepper import ReferenceCurrencyStepper
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.tax_settings import TaxSettings
from src.utils.theme_colors import tc, theme_qss
from src.utils.toast_notification import show_error, show_warning



class NewTransactionV2Page(TransactionPageBehaviorMixin, QWidget):
    PRODUCT_DOMAIN_KEYWORDS = {
        "security": [
            "kamera", "cctv", "nvr", "dvr", "alarm", "guvenlik", "g\u00fcvenlik",
            "sensor", "sens\u00f6r", "dedektor", "dedekt\u00f6r", "yangin", "yang\u0131n",
            "siren", "manyetik", "kontak", "rfid", "parmak", "kilit", "poe",
            "cat6", "bnc", "skyhawk", "purple", "kablo",
        ],
        "computer": [
            "pc", "bilgisayar", "laptop", "notebook", "anakart", "islemci",
            "i\u015flemci", "ram", "ssd", "nvme", "ekran kart", "gpu", "psu",
            "kasa", "monitor", "monit\u00f6r", "klavye", "mouse", "termal",
            "fan", "sogutucu", "so\u011futucu", "adapt\u00f6r", "adapter", "windows",
            "ddr", "intel", "amd", "ryzen", "rtx",
        ],
        "smart_home": [
            "akilli", "ak\u0131ll\u0131", "smart", "hub", "priz", "role", "r\u00f6le",
            "termostat", "zigbee", "dimmer", "perde", "interkom",
            "otomasyon", "wiipro", "wiicom", "wiicap", "wiimmd", "gateway",
            "ayd\u0131nlatma", "aydinlatma", "kapi zili", "kap\u0131 zili",
        ],
    }

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        body = getattr(self, 'reference_body_layout', None)
        if body is not None:
            checkout_weight = 28 if event.size().height() < 980 else 35
            body.setStretch(0, 100 - checkout_weight)
            body.setStretch(1, checkout_weight)
        compact = event.size().height() < 980
        if compact != getattr(self, '_reference_dense_mode', False):
            self._reference_dense_mode = compact
            self._apply_reference_density(compact)
            if hasattr(self, 'cart_cards_layout') and self.cart_items:
                self._refresh_reference_cart_cards()
        column_count = 1 if self.width() < 720 else 2 if self.width() < 1180 else 3
        if column_count != getattr(self, '_catalog_columns', 3) and hasattr(self, 'catalog_cards_layout'):
            self._catalog_columns = column_count
            self._refresh_parts_combo()

    def _apply_reference_density(self, compact):
        if hasattr(self, 'customer_panel'):
            self.customer_panel.setFixedHeight(72 if compact else 198)
            self.customer_grid.setContentsMargins(
                10, 4, 10, 4
            ) if compact else self.customer_grid.setContentsMargins(14, 16, 14, 16)
            self.customer_avatar.setFixedSize(40 if compact else 58, 40 if compact else 58)
            self.customer_title.setStyleSheet(theme_qss(
                'color: @finance_text; font-size: 12px; font-weight: 800;'
                if compact else
                'color: @finance_text; font-size: 16px; font-weight: 800;'
            ))
            self.customer_preview.setStyleSheet(theme_qss(
                'color: @finance_text_muted; font-size: 9px; font-weight: 600;'
                if compact else
                'color: @finance_text_muted; font-size: 11px; font-weight: 600;'
            ))
            self.date_edit.setFixedSize(110, 32) if compact else self.date_edit.setFixedSize(150, 40)
            self.reference_due_badge.setFixedSize(110, 32) if compact else self.reference_due_badge.setFixedSize(150, 40)
            self.btn_change_customer.setFixedSize(92, 32) if compact else self.btn_change_customer.setFixedSize(116, 40)
            self.btn_new_customer.setFixedSize(92, 32) if compact else self.btn_new_customer.setFixedSize(116, 40)
        if hasattr(self, 'reference_total_card'):
            self.reference_total_card.setFixedHeight(54 if compact else 86)
            self.reference_total_primary.setStyleSheet(theme_qss(
                'color: @finance_text; font: 700 15px "JetBrains Mono";'
                if compact else
                'color: @finance_text; font: 700 22px "JetBrains Mono";'
            ))
        if hasattr(self, 'reference_summary_layout'):
            self.reference_summary_layout.setSpacing(2 if compact else 8)
        if hasattr(self, 'reference_summary_panel'):
            if compact:
                self.reference_summary_panel.setFixedHeight(360)
            else:
                self.reference_summary_panel.setMinimumHeight(430)
                self.reference_summary_panel.setMaximumHeight(16777215)
        if hasattr(self, 'reference_currency_buttons'):
            for button in self.reference_currency_buttons.values():
                button.setFixedHeight(20 if compact else 34)
        if hasattr(self, 'btn_offer'):
            for button in (self.btn_offer, self.btn_proforma, self.btn_account, self.btn_pay):
                button.setFixedHeight(26 if compact else 34)
        if hasattr(self, 'catalog_layout'):
            self.catalog_layout.setContentsMargins(8, 6, 8, 4) if compact else self.catalog_layout.setContentsMargins(8, 16, 8, 8)
            self.catalog_search.setFixedHeight(32 if compact else 50)
            self.btn_catalog_filter.setFixedSize(72 if compact else 104, 32 if compact else 50)
            self.btn_bulk.setFixedHeight(32 if compact else 50)
            self.btn_catalog_details.setFixedHeight(32 if compact else 50)
            self.catalog_filter_top_spacer.changeSize(
                0, 6 if compact else 12,
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed,
            )
            self.catalog_filter_bottom_spacer.changeSize(
                0, 0 if compact else 26,
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed,
            )
            for button in self.catalog_filter_buttons.values():
                button.setFixedHeight(22 if compact else 32)
            self.catalog_layout.invalidate()
        if hasattr(self, 'catalog_cards_layout'):
            height = 256 if compact else 354
            for index in range(self.catalog_cards_layout.count()):
                card = self.catalog_cards_layout.itemAt(index).widget()
                if card is not None and card.objectName() == 'TransactionProductCard':
                    card.setFixedHeight(height)

    def __init__(self, db, main_window=None, *, draft_settings=None):
        super().__init__(main_window if isinstance(main_window, QWidget) else None)
        self._draft_settings = draft_settings if draft_settings is not None else QSettings()
        self.db = db
        self.main_window = main_window
        self.cart_items = []
        self.current_exchange_rate = 1.0
        self.services_data = {}
        self.parts_data = {}
        self._all_parts_catalog = []
        self._catalog_columns = 3
        self._reference_terms_expanded = False
        self._catalog_stock_only = False
        self._defer_service_load = main_window is not None
        self._last_item_type = None
        self._editing_offer_id = None
        self._editing_offer_no = ""
        self._editing_offer_project = ""
        self._editing_offer_template = ""

        self._build_ui()
        self._bind_legacy_aliases()
        self._apply_global_currency_setting()
        QTimer.singleShot(0, self._deferred_load_customers)

    @staticmethod
    def _row_value(row, key, default=None):
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            return default

    def _apply_global_currency_setting(self):
        if not hasattr(self, "cmb_currency"):
            return
        code = CurrencyHelper.get_code(self.db)
        index_map = {"TRY": 0, "USD": 1, "EUR": 2}
        self.cmb_currency.setCurrentIndex(index_map.get(code, 0))

    def _deferred_load_customers(self):
        self.load_customers()
        self._refresh_customer_preview()
        QTimer.singleShot(0, self._deferred_load_services)

    def _deferred_load_services(self):
        self.load_services()
        QTimer.singleShot(0, self._deferred_load_exchange_rates)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.load_services()
        except Exception:
            logging.exception("Could not refresh transaction services on show")

    def load_services(self):
        selections = []
        for combo in (self.cmb_service_types, self.cmb_parts):
            data = combo.currentData()
            selections.append((data.get('id') if isinstance(data, dict) else None, combo.currentText(), combo.blockSignals(True)))
        try:
            self.cmb_service_types.clear()
            self.cmb_parts.clear()
            self.services_data = {}
            self.parts_data = {}
            self._all_parts_catalog = []

            services = self.db.get_services_list() or []
            for s in services:
                name = self._row_value(s, 'name', '')
                if not name:
                    continue
                try:
                    service_price = self._row_value(s, 'price', 0)
                    raw_price = str(service_price).replace(" \u20ba", "").replace("\u20ba", "").strip() if service_price else "0"
                    final_price = float(raw_price)
                except (TypeError, ValueError):
                    final_price = 0.0

                info = {
                    'id': self._row_value(s, 'id'),
                    'name': name,
                    'type': 'service',
                    'price': final_price,
                    'description': self._row_value(s, 'description', '')
                }
                self.services_data[name] = info
                display_price = CurrencyHelper.format_try_for_display(final_price, db=self.db, include_try_reference=False)
                display_str = f"{name} - {display_price}"
                self.cmb_service_types.addItem(display_str, info)

            self.db.cursor.execute("SELECT id, name, category, stock, price, currency, code, description FROM parts ORDER BY name")
            parts = self.db.cursor.fetchall() or []
            for p in parts:
                try:
                    part_id = p["id"]
                    name = p["name"]
                    category = p["category"]
                    stock = p["stock"]
                    price = p["price"]
                    currency = p["currency"]
                    description = p["description"]
                except Exception:
                    part_id = p[0]
                    name = p[1]
                    category = p[2] if len(p) > 2 else ""
                    stock = p[3] if len(p) > 3 else 0
                    price = p[4] if len(p) > 4 else 0
                    currency = p[5] if len(p) > 5 else "TRY"
                    part_code = p[6] if len(p) > 6 else ""
                    description = p[7] if len(p) > 7 else ""
                else:
                    part_code = p["code"]
                currency = str(currency or "TRY").upper()
                try:
                    final_price = float(str(price).replace(" ₺", "").replace("₺", "").strip())
                except (TypeError, ValueError):
                    final_price = 0.0
                price_try = CurrencyHelper.convert_amount(self.db, final_price, currency, "TRY")
                info = {
                    'id': part_id,
                    'name': name,
                    'type': 'part',
                    'price': price_try,
                    'stock': stock,
                    'category': category,
                    'description': description or '',
                    'currency': currency,
                    'code': part_code or '',
                    'original_price': final_price,
                }
                self._all_parts_catalog.append(info)

            self._refresh_parts_combo()

            for combo, (selected_id, search_text, _blocked) in zip((self.cmb_service_types, self.cmb_parts), selections):
                selected_index = next((index for index in range(combo.count()) if selected_id is not None and combo.itemData(index).get('id') == selected_id), -1)
                combo.setCurrentIndex(selected_index)
                if selected_id is None and search_text and combo.isEditable():
                    combo.setEditText(search_text)

        except Exception as e:
            show_warning(self, f"Veri y\u00fcklenemedi: {e}")
        finally:
            for combo, (_selected_id, _search_text, blocked) in zip((self.cmb_service_types, self.cmb_parts), selections):
                combo.blockSignals(blocked)

    def _selected_product_domain(self):
        if hasattr(self, "cmb_product_domain"):
            return self.cmb_product_domain.currentData() or "security"
        return "security"

    def _part_matches_domain(self, info, domain):
        if domain == "all":
            return True
        text = " ".join(
            str(info.get(key) or "")
            for key in ("name", "category", "description", "code")
        ).casefold()
        keywords = self.PRODUCT_DOMAIN_KEYWORDS.get(domain, [])
        return any(keyword.casefold() in text for keyword in keywords)

    def _visible_parts_catalog(self):
        domain = self._selected_product_domain()
        return [
            info
            for info in self._all_parts_catalog
            if self._part_matches_domain(info, domain)
            and (not self._catalog_stock_only or float(info.get('stock') or 0) > 0)
        ]

    def _refresh_parts_combo(self):
        if not hasattr(self, "cmb_parts"):
            return
        previous_text = self.cmb_parts.currentText()
        was_blocked = self.cmb_parts.blockSignals(True)
        self.cmb_parts.clear()
        self.parts_data = {}
        filtered = self._visible_parts_catalog()
        self._refresh_catalog_cards(filtered)
        for info in filtered:
            name = info.get("name") or ""
            self.parts_data[name] = info
            display_price = CurrencyHelper.format_amount(
                info.get("original_price", info.get("price", 0)),
                db=self.db,
                currency_code=info.get("currency", "TRY"),
            )
            display_str = f"{name} (Stok: {info.get('stock', 0)}) - {display_price}"
            self.cmb_parts.addItem(display_str, info)
        idx = self.cmb_parts.findText(previous_text)
        self.cmb_parts.setCurrentIndex(idx if idx >= 0 else -1)
        self.cmb_parts.blockSignals(was_blocked)

    def _on_product_domain_changed(self):
        self.cmb_parts.setCurrentIndex(-1)
        self._last_item_type = None
        self._refresh_parts_combo()

    def _setup_searchable_combo(self, combo, placeholder):
        combo.setEditable(True)
        combo.setCurrentIndex(-1)
        line_edit = combo.lineEdit()
        if line_edit:
            line_edit.setReadOnly(False)
            line_edit.setPlaceholderText(placeholder)
            line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            line_edit.installEventFilter(self)
        completer = combo.completer()
        if completer:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.installEventFilter(self)

    def _show_combo_popup(self, combo):
        if combo and not combo.view().isVisible():
            combo.showPopup()
            if combo.lineEdit():
                QTimer.singleShot(0, combo.lineEdit().setFocus)

    def _on_item_selection_change(self, item_type):
        if item_type == 'service':
            info = self.cmb_service_types.currentData()
            if info:
                self._last_item_type = 'service'
                self.cmb_parts.blockSignals(True)
                self.cmb_parts.setCurrentIndex(-1)
                self.cmb_parts.blockSignals(False)
                self.inp_price.setValue(float(info.get('price') or 0))
                self.inp_desc.setCurrentText(info.get('description', ''))
                self.catalog_tabs.setCurrentIndex(1)
        else:
            info = self.cmb_parts.currentData()
            if info:
                self._last_item_type = 'part'
                self.cmb_service_types.blockSignals(True)
                self.cmb_service_types.setCurrentIndex(-1)
                self.cmb_service_types.blockSignals(False)
                self.inp_price.setValue(float(info.get('price') or 0))
                self.inp_desc.setCurrentText(f"Stok \u00fcr\u00fcn: {info.get('name', '')}")
                self.catalog_tabs.setCurrentIndex(0)
                self._refresh_catalog_cards(self._visible_parts_catalog())

    def add_to_cart(self, selected_override=None):
        service_info = self.cmb_service_types.currentData()
        part_info = self.cmb_parts.currentData()

        selected = selected_override if isinstance(selected_override, dict) else None
        if selected is None:
            if self._last_item_type == 'service' and service_info:
                selected = service_info
            elif self._last_item_type == 'part' and part_info:
                selected = part_info
            elif service_info:
                selected = service_info
            elif part_info:
                selected = part_info

        if not selected:
            show_warning(self, "L\u00fctfen bir hizmet veya par\u00e7a se\u00e7in.")
            return

        date = self.date_edit.date().toString("dd.MM.yyyy")
        name = selected.get('name') or ''
        price = self.inp_price.value()
        desc = self.inp_desc.currentText() or ''
        qty = self.inp_qty.value()

        self.cart_items.append({
            'id': str(uuid.uuid4()),
            'item_id': selected.get('id'),
            'type': selected.get('type', 'service'),
            'service': name,
            'description': desc,
            'price': price,
            'qty': qty,
            'date': date
        })

        self._auto_save_draft()
        self.refresh_cart_ui()
        self.update_totals()

        self.cmb_service_types.blockSignals(True)
        self.cmb_parts.blockSignals(True)
        self.cmb_service_types.setCurrentIndex(-1)
        self.cmb_parts.setCurrentIndex(-1)
        self.cmb_service_types.blockSignals(False)
        self.cmb_parts.blockSignals(False)
        self._last_item_type = None

        self.inp_price.setValue(0)
        self.inp_qty.setValue(1)
        self.inp_desc.setCurrentText('')

    def _deferred_load_exchange_rates(self):
        self.update_exchange_rates()
        QTimer.singleShot(0, self._restore_draft)

    # ── Taslak Kayıt (Draft Save) ─────────────────────────────────────────

    _DRAFT_KEY = "NewTransactionV2/draft"

    def _auto_save_draft(self):
        """Sepet her değiştiğinde taslağı QSettings'e yaz."""
        try:
            self._save_reference_draft()
        except Exception:
            logging.exception("Could not save the transaction draft")

    def _clear_draft(self):
        self._draft_settings.remove(self._DRAFT_KEY)

    def _save_reference_draft(self):
        data = {
            'customer_id': self.cmb_customer.currentData(),
            'customer': self.cmb_customer.currentText(),
            'cart_items': self.cart_items,
            'currency': self._parse_currency_code(self.cmb_currency.currentText()),
            'exchange_rate': self.current_exchange_rate,
            'discount_try': self.inp_discount.value(),
            'vat': self.cmb_vat.currentText(),
            'date': self.date_edit.date().toString('yyyy-MM-dd'),
            'transaction_date': self.date_edit_transaction.date().toString('yyyy-MM-dd'),
            'include_approval': self.toggle_offer_approval.isChecked(),
        }
        self._draft_settings.setValue(self._DRAFT_KEY, json.dumps(data, default=str))
        if hasattr(self, 'command_context'):
            self._refresh_header_state()

    def _restore_reference_draft_fields(self, data):
        customer_id = data.get('customer_id')
        if customer_id is not None:
            index = self.cmb_customer.findData(customer_id)
            if index >= 0:
                self.cmb_customer.setCurrentIndex(index)
            else:
                self.cmb_customer.setCurrentIndex(-1)
        elif data.get('customer'):
            index = self.cmb_customer.findText(data['customer'])
            if index >= 0:
                self.cmb_customer.setCurrentIndex(index)
            else:
                self.cmb_customer.setCurrentIndex(-1)
        currency = str(data.get('currency') or 'TRY').upper()
        if 'currency' in data:
            for index in range(self.cmb_currency.count()):
                if self._parse_currency_code(self.cmb_currency.itemText(index)) == currency:
                    self.cmb_currency.setCurrentIndex(index)
                    break
        if 'exchange_rate' in data:
            try:
                rate = float(data.get('exchange_rate') or 1.0)
                self.current_exchange_rate = rate if rate > 0 else 1.0
            except (TypeError, ValueError):
                self.current_exchange_rate = 1.0
        self.inp_discount.setValue(float(data.get('discount_try') or 0))
        vat = str(data.get('vat') or '')
        if vat:
            if self.cmb_vat.findText(vat) < 0:
                self.cmb_vat.addItem(vat)
            self.cmb_vat.setCurrentText(vat)
        for key, control in (('date', self.date_edit), ('transaction_date', self.date_edit_transaction)):
            if data.get(key):
                value = QDate.fromString(str(data[key]), 'yyyy-MM-dd')
                if value.isValid():
                    control.setDate(value)
        if 'include_approval' in data:
            self.toggle_offer_approval.setChecked(bool(data['include_approval']))
        self._refresh_customer_preview()

    def _restore_draft(self):
        """Sayfa açılışında kaydedilmiş taslak varsa kullanıcıya sor."""
        from src.utils.toast_notification import show_warning
        try:
            raw = self._draft_settings.value(self._DRAFT_KEY)
            if not raw:
                return
            data = json.loads(raw)
            items = data.get("cart_items", [])
            if not items:
                return
            from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
            dlg = ModernConfirmDialog(
                "Kaydedilmemiş Taslak",
                f"Önceki oturumdan {len(items)} kalemlik tamamlanmamış bir form bulundu.\nGeri yüklensin mi?",
                self,
                confirm_text="Geri Yükle",
                cancel_text="Sil",
            )
            if dlg.exec():
                self.cart_items = items
                self._restore_reference_draft_fields(data)
                self.refresh_cart_ui()
                self.update_totals()
            else:
                self._clear_draft()
        except Exception:
            logging.exception("Could not restore the saved transaction draft")
        self.update_totals()

    def _bind_legacy_aliases(self):
        self.customer_combo = self.cmb_customer
        self.service_combo = self.cmb_service_types
        self.discount_input = self.inp_discount
        self.vat_combo = self.cmb_vat
        self.subtotal_label = self.lbl_subtotal
        self.total_label = self.lbl_total
        self.transaction_date = self.date_edit_transaction
        self.qty_input = self.inp_qty

    def switch_tab(self, index):
        return index

    def _build_ui(self):
        self.setObjectName('NewTransactionV2Page')
        self.setStyleSheet(
            theme_qss(
                """
                QWidget#NewTransactionV2Page {
                    background: transparent;
                }
                QLabel {
                    background: transparent;
                    border: none;
                    color: @text;
                }
                """
            )
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.lbl_customer_state = QLabel('Müşteri seçilmedi')
        self.lbl_currency_state = QLabel('TRY')
        self.lbl_cart_state = QLabel('0 kalem')
        self.lbl_customer_state.hide()
        self.lbl_currency_state.hide()
        self.lbl_cart_state.hide()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.reference_body_layout = body
        body.addLayout(self._build_reference_catalog_column(), 75)
        body.addLayout(self._build_reference_checkout_column(), 25)
        root.addLayout(body, 1)

    def _reference_panel(self, name, *, radius=6, background='@finance_surface'):
        panel = QFrame()
        panel.setObjectName('TransactionReferencePanel')
        panel.setStyleSheet(theme_qss(
            f'QFrame#TransactionReferencePanel {{ background: {background}; '
            f'border: 1px solid @finance_outline; border-radius: {radius}px; }}'
        ))
        panel.setProperty('referenceSection', name)
        return panel

    def _build_reference_catalog_column(self):
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        customer = self._reference_panel('customer')
        self.customer_panel = customer
        customer.setMinimumHeight(198)
        customer.setMaximumHeight(198)
        customer_grid = QGridLayout(customer)
        self.customer_grid = customer_grid
        customer_grid.setContentsMargins(14, 16, 14, 16)
        customer_grid.setHorizontalSpacing(8)
        customer_grid.setVerticalSpacing(1)

        self.customer_avatar = QLabel('A')
        self.customer_avatar.setFixedSize(58, 58)
        self.customer_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.customer_avatar.setStyleSheet(theme_qss(
            'background: @finance_active_bg; color: @finance_primary; border: 1px solid '
            '@finance_primary; border-radius: 14px; font-size: 22px; font-weight: 800;'
        ))
        customer_grid.addWidget(self.customer_avatar, 0, 0, 2, 1, Qt.AlignmentFlag.AlignVCenter)

        self.customer_title = QLabel('M\u00fc\u015fteri se\u00e7ilmedi')
        self.customer_title.setWordWrap(True)
        self.customer_title.setStyleSheet(theme_qss(
            'color: @finance_text; font-size: 16px; font-weight: 800;'
        ))
        customer_grid.addWidget(self.customer_title, 0, 1)
        self.customer_preview = QLabel('')
        self.customer_preview.setWordWrap(True)
        self.customer_preview.setTextFormat(Qt.TextFormat.PlainText)
        self.customer_preview.setStyleSheet(theme_qss(
            'color: @finance_text_muted; font-size: 11px; font-weight: 600;'
        ))
        customer_grid.addWidget(self.customer_preview, 1, 1)

        self.date_edit = ReferenceDateEdit(QDate.currentDate(), compact=True)
        self.date_edit.setFixedSize(150, 40)
        customer_grid.addWidget(self.date_edit, 0, 2, Qt.AlignmentFlag.AlignLeft)
        self.reference_due_badge = QLabel('Vade: Pesin / Cari')
        self.reference_due_badge.setFixedSize(150, 40)
        self.reference_due_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.reference_due_badge.setStyleSheet(theme_qss(
            'background: @finance_surface_alt; color: @finance_text; border: 1px solid '
            '@finance_outline; border-radius: 8px; padding: 0 6px; font-size: 9px;'
        ))
        customer_grid.addWidget(self.reference_due_badge, 1, 2)
        self.btn_change_customer = QPushButton('M\u00fc\u015fteri De\u011fi\u015ftir')
        self.btn_change_customer.setFixedSize(116, 40)
        self.btn_change_customer.clicked.connect(self.open_customer_search)
        self.btn_new_customer = QPushButton('+ Yeni M\u00fc\u015fteri')
        self.btn_new_customer.setFixedSize(116, 40)
        self.btn_new_customer.clicked.connect(self.open_new_reference_customer)
        for button in (self.btn_change_customer, self.btn_new_customer):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                'QPushButton { background: @finance_active_bg; color: @finance_primary; '
                'border: 1px solid @finance_outline; border-radius: 6px; font-size: 8px; } '
                'QPushButton:hover { border-color: @finance_primary; }'
            ))
        customer_grid.addWidget(self.btn_change_customer, 0, 3)
        customer_grid.addWidget(self.btn_new_customer, 1, 3)
        customer_grid.setColumnStretch(1, 1)

        self.cmb_customer = ModernComboBox(min_height=38)
        self.cmb_customer.setEditable(True)
        self.cmb_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_customer.currentTextChanged.connect(self._refresh_customer_preview)
        self.cmb_customer.hide()
        self.customer_completer = self.cmb_customer.completer()
        if self.customer_completer:
            self.customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.customer_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.customer_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        column.addWidget(customer)

        catalog = self._reference_panel('catalog', background='@finance_surface_lowest')
        catalog_layout = QVBoxLayout(catalog)
        catalog_layout.setContentsMargins(8, 16, 8, 8)
        catalog_layout.setSpacing(4)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText('Barkod okutun veya parca adi/kodu ile arayin... [Enter: Hizli Ekle]')
        self.catalog_search.setFixedHeight(50)
        self.catalog_search.setClearButtonEnabled(True)
        self.catalog_search.setStyleSheet(theme_qss(
            'QLineEdit { background: @finance_surface_lowest; color: @finance_text; '
            'border: 1px solid @finance_primary; border-radius: 9px; padding: 0 14px; '
            'font-size: 12px; }'
        ))
        self.catalog_search.textChanged.connect(self._on_catalog_search_changed)
        self.catalog_search.returnPressed.connect(self._add_catalog_search_result)
        toolbar.addWidget(self.catalog_search, 1)
        self.btn_catalog_filter = QPushButton('Filtreler \u2304')
        self.btn_catalog_filter.setFixedSize(104, 50)
        self.btn_catalog_filter.clicked.connect(self._toggle_catalog_stock_filter)
        toolbar.addWidget(self.btn_catalog_filter)
        self.btn_bulk = QPushButton('F2 Toplu Se\u00e7im')
        self.btn_bulk.setFixedHeight(50)
        self.btn_bulk.clicked.connect(self.open_multi_select_v2)
        toolbar.addWidget(self.btn_bulk)
        self.btn_catalog_details = QPushButton('Detayl\u0131 kalem ekleme')
        self.btn_catalog_details.setFixedHeight(50)
        self.btn_catalog_details.clicked.connect(self._toggle_catalog_details)
        toolbar.addWidget(self.btn_catalog_details)
        for button in (self.btn_catalog_filter, self.btn_bulk, self.btn_catalog_details):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                'QPushButton { background: @finance_surface_alt; color: @finance_text; '
                'border: 1px solid @finance_outline; border-radius: 8px; padding: 0 10px; '
                'font-size: 11px; font-weight: 600; } QPushButton:hover { border-color: @finance_primary; }'
            ))
        catalog_layout.addLayout(toolbar)

        self.catalog_tabs = QTabBar()
        self.catalog_tabs.addTab('Urunler')
        self.catalog_tabs.addTab('Hizmetler')
        self.catalog_tabs.hide()
        self.catalog_tabs.currentChanged.connect(self._set_catalog_mode)
        self.catalog_category_row = QHBoxLayout()
        self.catalog_category_row.setSpacing(6)
        self.catalog_filter_buttons = {}
        self.catalog_filter_base_labels = {}
        categories = (
            ('all', 'Tum\u00fc'), ('camera', 'G\u00fcvenlik & Kamera'),
            ('recorder', 'Kay\u0131t Cihaz\u0131 & NVR'), ('storage', 'Disk & Donan\u0131m'),
            ('network', 'A\u011f & Switch'), ('service', 'Montaj & \u0130\u015f\u00e7ilik'),
        )
        for key, label in categories:
            button = QPushButton(label)
            button.setFixedHeight(32)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=key: self._set_catalog_category(value))
            self.catalog_filter_buttons[key] = button
            self.catalog_filter_base_labels[key] = label
            self.catalog_category_row.addWidget(button)
        catalog_layout.addSpacing(12)
        self.catalog_filter_top_spacer = catalog_layout.itemAt(catalog_layout.count() - 1).spacerItem()
        catalog_layout.addLayout(self.catalog_category_row)
        catalog_layout.addSpacing(26)
        self.catalog_filter_bottom_spacer = catalog_layout.itemAt(catalog_layout.count() - 1).spacerItem()
        self.catalog_layout = catalog_layout

        self.catalog_cards_scroll = QScrollArea()
        self.catalog_cards_scroll.setWidgetResizable(True)
        self.catalog_cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.catalog_cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.catalog_cards_container = QWidget()
        self.catalog_cards_layout = QGridLayout(self.catalog_cards_container)
        self.catalog_cards_layout.setContentsMargins(0, 8, 0, 0)
        self.catalog_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.catalog_cards_layout.setHorizontalSpacing(8)
        self.catalog_cards_layout.setVerticalSpacing(5)
        self.catalog_cards_scroll.setWidget(self.catalog_cards_container)
        catalog_layout.addWidget(self.catalog_cards_scroll, 1)
        self.catalog_details = QWidget(catalog)
        self.catalog_details.setObjectName('TransactionCatalogDetails')
        details_layout = QVBoxLayout(self.catalog_details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        composer = self._build_composer_card()
        composer.setParent(self.catalog_details)
        details_layout.addWidget(composer)
        toolbar.addWidget(self.btn_bulk)
        self.catalog_details.hide()
        catalog_layout.addWidget(self.catalog_details)

        catalog_footer = QFrame()
        catalog_footer.setFixedHeight(24)
        catalog_footer.setStyleSheet(theme_qss(
            'QFrame { background: @finance_surface_lowest; border-top: 1px solid @finance_outline; }'
        ))
        footer_layout = QHBoxLayout(catalog_footer)
        footer_layout.setContentsMargins(8, 0, 8, 0)
        footer_layout.setSpacing(10)
        self.reference_scan_status = QLabel('Barkod Tarama Modu: A\u00e7\u0131k  |  Fiyat Listesi: Bayi \u00d6zel Toptan ($)')
        self.reference_scan_status.setStyleSheet(theme_qss('color: @finance_text_muted; font-size: 9px;'))
        self.reference_shortcut_status = QLabel('K\u0131sayollar: [F1: Arama] [F2: Barkod] [F5: Teklif] [F8: Bor\u00e7 \u0130\u015fle]')
        self.reference_shortcut_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.reference_shortcut_status.setStyleSheet(theme_qss('color: @finance_text_muted; font: 9px "JetBrains Mono";'))
        footer_layout.addWidget(self.reference_scan_status, 1)
        footer_layout.addWidget(self.reference_shortcut_status)
        catalog_layout.addWidget(catalog_footer)

        self.lbl_exchange_rate = QLabel('TRY - Kur: 1.00')
        self.lbl_exchange_rate.setObjectName('TransactionExchangeRate')
        self.lbl_exchange_rate.setStyleSheet(theme_qss(
            'color: @finance_secondary; background: @finance_surface_alt; border-left: 3px solid '
            '@finance_secondary; border-radius: 5px; padding: 8px 12px; font-size: 11px; font-weight: 700;'
        ))
        self.lbl_exchange_rate.hide()
        self._catalog_category = 'all'
        self._catalog_query = ''
        self._catalog_stock_only = False
        self._set_catalog_category('all')
        self._set_catalog_mode(0)
        column.addWidget(catalog, 1)
        return column

    def _build_reference_checkout_column(self):
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        basket = self._reference_panel('basket', background='@finance_surface')
        basket_layout = QVBoxLayout(basket)
        basket_layout.setContentsMargins(14, 12, 14, 0)
        basket_layout.setSpacing(35)
        heading = QHBoxLayout()
        cart_icon = FinancialReferenceIconButton('Sepet', 'cart')
        cart_icon.setObjectName('TransactionCartIcon')
        cart_icon.setFixedSize(28, 28)
        cart_icon.setStyleSheet(theme_qss(
            'QPushButton { background: @finance_active_bg; color: @finance_primary; '
            'border: 1px solid @finance_outline; border-radius: 8px; }'
        ))
        heading.addWidget(cart_icon)
        basket_title = QLabel('\u0130\u015eLEM SEPET\u0130 & KALEMLER')
        basket_title.setStyleSheet(theme_qss('font-size: 13px; font-weight: 800; color: @finance_text;'))
        heading.addWidget(basket_title)
        heading.addStretch()
        self.reference_cart_count = QLabel('0 Kalem | 0 Adet')
        self.reference_cart_count.hide()
        self.reference_cart_summary = QLabel('0 Kalem \u00dcr\u00fcn/Hizmet Se\u00e7ildi')
        self.reference_cart_summary.setStyleSheet(theme_qss('color: @finance_text_muted; font-size: 10px;'))
        heading.addWidget(self.reference_cart_summary)
        btn_clear = QPushButton('Temizle')
        btn_clear.clicked.connect(self.clear_cart)
        btn_clear.setStyleSheet(theme_qss('color: @finance_text_muted; border: none; font-size: 11px;'))
        heading.addWidget(btn_clear)
        basket_layout.addLayout(heading)
        self.cart_scroll = QScrollArea()
        self.cart_scroll.setWidgetResizable(True)
        self.cart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cart_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.cart_cards_container = QWidget()
        self.cart_cards_layout = QVBoxLayout(self.cart_cards_container)
        self.cart_cards_layout.setContentsMargins(0, 4, 0, 0)
        self.cart_cards_layout.setSpacing(8)
        self.cart_scroll.setWidget(self.cart_cards_container)
        self.cart_scroll.hide()
        basket_layout.addWidget(self.cart_scroll, 1)
        self.cart_table = QTreeWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHeaderLabels(['Tarih', 'Kalem', 'Adet', 'Aciklama', 'Tutar'])
        self.cart_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cart_table.customContextMenuRequested.connect(self.show_cart_context_menu)
        self.cart_table.hide()
        self.cart_empty_state = EmptyState('Sepet bos', 'Soldan urun veya hizmet secerek kalem ekleyin.')
        self.cart_empty_state.setMinimumHeight(120)
        basket_layout.addWidget(self.cart_empty_state)
        column.addWidget(basket, 50)

        summary = self._reference_panel('summary', background='@finance_surface_lowest')
        self.reference_summary_panel = summary
        summary_layout = QVBoxLayout(summary)
        self.reference_summary_layout = summary_layout
        summary_layout.setContentsMargins(6, 6, 6, 6)
        summary_layout.setSpacing(8)
        self.lbl_subtotal = QLabel('Ara Toplam (0 Kalem): 0.00')
        self.lbl_subtotal.setObjectName('TransactionCartSubtotal')
        self.lbl_subtotal.setFixedHeight(18)
        self.lbl_subtotal.setStyleSheet(theme_qss('color: @finance_text_muted; font-size: 12px;'))
        summary_layout.addWidget(self.lbl_subtotal)
        discount_heading = QHBoxLayout()
        discount_label = QLabel('\u0130skonto Uygula:')
        discount_label.setStyleSheet(theme_qss('font-size: 12px; font-weight: 700; color: @finance_primary;'))
        discount_heading.addWidget(discount_label)
        discount_heading.addStretch()
        self.reference_discount_value = QLabel('-% 0.00')
        self.reference_discount_value.setStyleSheet(theme_qss('color: @finance_secondary; font: 11px "JetBrains Mono";'))
        discount_heading.addWidget(self.reference_discount_value)
        self.reference_discount_presets = QHBoxLayout()
        self.reference_discount_buttons = {}
        for label, percent in (('%0', 0), ('%5', 5), ('%10', 10), ('%15', 15), ('Ozel %', -1)):
            button = QPushButton(label)
            button.setFixedHeight(30)
            button.clicked.connect(lambda _checked=False, value=percent: self._apply_discount_percent(value))
            self.reference_discount_buttons[label] = button
            self.reference_discount_presets.addWidget(button)
        discount_panel = QFrame()
        discount_panel.setObjectName('TransactionDiscountPanel')
        discount_panel.setFixedHeight(72)
        discount_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        discount_panel.setStyleSheet(theme_qss(
            'QFrame#TransactionDiscountPanel { background: @finance_active_bg; border: 1px solid @finance_outline; border-radius: 10px; }'
        ))
        discount_layout = QVBoxLayout(discount_panel)
        discount_layout.setContentsMargins(8, 6, 8, 6)
        discount_layout.setSpacing(6)
        discount_layout.addLayout(discount_heading)
        discount_layout.addLayout(self.reference_discount_presets)
        summary_layout.addWidget(discount_panel)
        self.inp_discount = ReferenceCurrencyStepper(value=0.0, decimals=2)
        self.inp_discount.setRange(0, 999999999)
        self.inp_discount.setFixedHeight(38)
        self.inp_discount.valueChanged.connect(self.update_totals)
        self.inp_discount.hide()
        self.cmb_vat = ModernComboBox(min_height=38)
        self.cmb_vat.addItems(['%0', '%1', '%10', '%18', '%20'])
        default_vat_text = TaxSettings.combo_text(self.db)
        if self.cmb_vat.findText(default_vat_text) < 0:
            self.cmb_vat.addItem(default_vat_text)
        self.cmb_vat.setCurrentText(default_vat_text)
        self.cmb_vat.setFixedHeight(38)
        self.cmb_vat.currentTextChanged.connect(self.update_totals)
        self.cmb_vat.hide()
        self.cmb_currency = ModernComboBox(min_height=38)
        self.cmb_currency.addItems(['TRY - Turk Lirasi (TL)', 'USD - Amerikan Dolari ($)', 'EUR - Euro (EUR)'])
        self.cmb_currency.currentTextChanged.connect(self._handle_currency_change)
        self.cmb_currency.hide()
        self.reference_currency_buttons = {}
        currency_row = QHBoxLayout()
        for code, label in (('USD', '$ USD ($)'), ('EUR', 'EUR (\u20ac)'), ('TRY', 'TRY (\u20ba)')):
            button = QPushButton(label)
            button.setFixedHeight(34)
            button.clicked.connect(lambda _checked=False, value=code: self._set_reference_currency(value))
            self.reference_currency_buttons[code] = button
            currency_row.addWidget(button)
        currency_heading = QHBoxLayout()
        currency_label = QLabel('Para Birimi Se\u00e7imi:')
        currency_label.setFixedHeight(16)
        currency_label.setStyleSheet(theme_qss('font-size: 11px; color: @finance_text_muted;'))
        currency_heading.addWidget(currency_label)
        currency_heading.addStretch()
        self.reference_cart_rate = QLabel('1 TRY = 1.0000 TRY')
        self.reference_cart_rate.setObjectName('TransactionCartExchangeRate')
        self.reference_cart_rate.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.reference_cart_rate.setFixedHeight(16)
        self.reference_cart_rate.setMinimumWidth(126)
        self.reference_cart_rate.setStyleSheet(theme_qss('color: @finance_secondary; font: 10px "JetBrains Mono";'))
        currency_heading.addWidget(self.reference_cart_rate)
        summary_layout.addLayout(currency_heading)
        summary_layout.addLayout(currency_row)
        self.reference_amount_breakdown = QLabel('')
        self.reference_amount_detail = QLabel('')
        for label in (self.reference_amount_breakdown, self.reference_amount_detail):
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            label.setFixedHeight(16)
            label.setStyleSheet(theme_qss('color: @finance_text_muted; font: 10px "JetBrains Mono";'))
            summary_layout.addWidget(label)
        self.stat_subtotal = self._summary_box('Ara Toplam', '0.00', 'primary')
        self.stat_discount = self._summary_box('Iskonto', '0.00', 'warning')
        self.stat_vat = self._summary_box('KDV', '0.00', 'secondary')
        self.stat_total = self._summary_box('Genel Toplam', '0.00', 'success')
        self.stat_subtotal.hide()
        self.stat_discount.hide()
        self.stat_vat.hide()
        self.stat_total.hide()
        self.lbl_total = ReferenceTotalLabel('0.00', primary_size=30, secondary_size=14, primary_token='finance_text')
        self.lbl_total.setObjectName('TransactionGrandTotal')
        self.lbl_total.setFixedHeight(56)
        self.lbl_total.setStyleSheet(theme_qss(
            'background: @finance_active_bg; border: 1px solid @finance_primary; '
            'border-radius: 8px; color: @finance_text;'
        ))
        self.lbl_total.hide()
        total_card = QFrame()
        self.reference_total_card = total_card
        total_card.setObjectName('TransactionGrandTotal')
        total_card.setFixedHeight(54)
        total_card.setStyleSheet(theme_qss(
            'QFrame#TransactionGrandTotal { background: @finance_active_bg; '
            'border: 1px solid @finance_primary; border-radius: 8px; }'
        ))
        total_row = QHBoxLayout(total_card)
        total_row.setContentsMargins(8, 5, 8, 5)
        total_copy = QVBoxLayout()
        total_copy.setSpacing(1)
        total_heading = QLabel('\u00d6DENECEK GENEL TOPLAM')
        total_heading.setStyleSheet(theme_qss('color: @finance_primary; font-size: 10px; font-weight: 800;'))
        total_caption = QLabel('T\u00fcm Vergiler ve \u0130skonto Dahil')
        total_caption.setStyleSheet(theme_qss('color: @finance_text_muted; font: 9px "JetBrains Mono";'))
        total_copy.addWidget(total_heading)
        total_copy.addWidget(total_caption)
        total_row.addLayout(total_copy, 1)
        total_values = QVBoxLayout()
        total_values.setSpacing(1)
        self.reference_total_primary = QLabel('0.00')
        self.reference_total_primary.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.reference_total_primary.setStyleSheet(theme_qss('color: @finance_text; font: 700 15px "JetBrains Mono";'))
        self.reference_total_secondary = QLabel('')
        self.reference_total_secondary.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.reference_total_secondary.setStyleSheet(theme_qss('color: @finance_secondary; font: 9px "JetBrains Mono";'))
        total_values.addWidget(self.reference_total_primary)
        total_values.addWidget(self.reference_total_secondary)
        total_row.addLayout(total_values)
        summary_layout.addSpacing(18)
        summary_layout.addWidget(total_card)
        self.date_edit_transaction = ReferenceDateEdit(QDate.currentDate())
        self.date_edit_transaction.setFixedHeight(38)
        self.date_edit_transaction.setParent(summary)
        self.date_edit_transaction.hide()
        approval_row = QWidget(summary)
        approval_row.setFixedHeight(40)
        self.toggle_offer_approval = AnimatedToggle(approval_row)
        self.toggle_offer_approval.setGeometry(0, 0, 1, 1)
        approval_row.hide()
        self.toggle_offer_approval.setChecked(True)
        self.toggle_offer_approval.hide()
        self.btn_save = QPushButton('Servis Kaydet')
        self.btn_save.clicked.connect(self.save_transaction)
        self.btn_pay = FinancialReferenceActionButton('Do\u011frudan Tahsilat Al & Servis Kaydet', 'collection', stacked=False, centered_inline=True, key_hint='F12')
        self.btn_pay.clicked.connect(self.save_and_pay)
        self.btn_proforma = FinancialReferenceActionButton('Proforma Olu\u015ftur', 'pdf', stacked=False, centered_inline=True, key_hint='F10')
        self.btn_proforma.clicked.connect(self.create_proforma)
        self.btn_account = FinancialReferenceActionButton('Bor\u00e7 / M\u00fc\u015fteriye \u0130\u015fle', 'customer', stacked=False, centered_inline=True, key_hint='F8')
        self.btn_account.clicked.connect(self.save_transaction)
        self.btn_offer = FinancialReferenceActionButton('Teklif Olu\u015ftur', 'pdf', stacked=False, centered_inline=True, key_hint='F5')
        self.btn_offer.clicked.connect(self.create_proforma)
        self.btn_save.hide()
        self.reference_command_buttons = [self.btn_save]
        for button in (self.btn_pay, self.btn_proforma, self.btn_account, self.btn_offer):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(34)
            button.setMinimumWidth(0)
            button.setStyleSheet(theme_qss(
                'QPushButton { background: @finance_primary; color: @finance_primary_text; '
                'border: 1px solid @finance_outline; border-radius: 8px; font-size: 9px; font-weight: 700; }'
            ))
        self.btn_pay.clicked.disconnect()
        self.btn_pay.clicked.connect(self.save_and_pay)
        self.btn_pay.setStyleSheet(theme_qss(
            'QPushButton { background: @finance_success_bg; color: @finance_secondary; border: 1px solid '
            '@finance_secondary; border-radius: 8px; font-size: 9px; font-weight: 700; }'
        ))
        self.btn_offer.setStyleSheet(theme_qss(
            'QPushButton { background: @finance_primary; color: @finance_primary_text; border: none; '
            'border-radius: 8px; font-size: 9px; font-weight: 700; }'
        ))
        self.btn_proforma.setStyleSheet(theme_qss(
            'QPushButton { background: #4f46e5; color: #ffffff; border: none; border-radius: 8px; font-size: 9px; font-weight: 700; }'
        ))
        self.btn_account.setStyleSheet(theme_qss(
            'QPushButton { background: #d97706; color: #ffffff; border: 1px solid #f59e0b; border-radius: 8px; font-size: 9px; font-weight: 700; }'
        ))
        action_pair = QHBoxLayout()
        action_pair.addWidget(self.btn_proforma)
        action_pair.addWidget(self.btn_account)
        summary_layout.addWidget(self.btn_offer)
        summary_layout.addLayout(action_pair)
        summary_layout.addWidget(self.btn_pay)
        self.reference_cart_shortcuts = []
        for key, callback, name in (
            ('F2', self.open_multi_select_v2, 'multi_select'),
            ('F5', self.create_proforma, 'offer'), ('F8', self.save_transaction, 'account'),
            ('F10', self.create_proforma, 'proforma'), ('F12', self.save_and_pay, 'payment'),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            setattr(self, f'reference_{name}_shortcut', shortcut)
            self.reference_cart_shortcuts.append(shortcut)
        self.reference_offer_shortcut = getattr(self, 'reference_offer_shortcut')
        self.reference_account_shortcut = getattr(self, 'reference_account_shortcut')
        self.reference_proforma_shortcut = getattr(self, 'reference_proforma_shortcut')
        self.reference_payment_shortcut = getattr(self, 'reference_payment_shortcut')
        self.command_context = QLabel('Genel Kayit')
        self.command_context.hide()
        column.addWidget(summary, 49)
        self._wire_ui_signals()
        return column

    def _wire_ui_signals(self):
        for stepper in (self.inp_qty, self.inp_price, self.inp_discount):
            stepper.valueChanged.connect(self._save_reference_draft)
            stepper.installEventFilter(self)
            if getattr(stepper, 'spn_counted', None) is not None:
                stepper.spn_counted.installEventFilter(self)
        self.catalog_search.installEventFilter(self)
        for control in (self.cmb_customer, self.cmb_currency, self.cmb_service_types, self.cmb_product_domain, self.cmb_parts, self.inp_desc, self.cmb_vat):
            control.setProperty('referenceChevron', True)
            control.setFixedHeight(38)
        self.cmb_customer.currentTextChanged.connect(self._save_reference_draft)
        self.date_edit.dateChanged.connect(self._save_reference_draft)
        self.date_edit_transaction.dateChanged.connect(self._save_reference_draft)
        self.cmb_vat.currentTextChanged.connect(self._save_reference_draft)
        self.toggle_offer_approval.toggled.connect(self._save_reference_draft)

    def _set_catalog_mode(self, index):
        if not hasattr(self, 'catalog_details'):
            return
        service_mode = index == 1
        if service_mode:
            self.catalog_cards_scroll.hide()
            self.catalog_details.show()
            self.cmb_service_types.show()
            self.cmb_parts.hide()
        else:
            self.catalog_details.hide()
            self.catalog_cards_scroll.show()
            self.cmb_service_types.hide()
            self.cmb_parts.hide()

    def _toggle_catalog_details(self):
        visible = self.catalog_details.isVisible()
        self.catalog_tabs.setCurrentIndex(0)
        self.catalog_details.setVisible(not visible)
        self.catalog_cards_scroll.setVisible(visible)

    def _toggle_catalog_stock_filter(self):
        self._catalog_stock_only = not self._catalog_stock_only
        self._refresh_parts_combo()

    def _set_catalog_category(self, category):
        self._catalog_category = category
        for key, button in self.catalog_filter_buttons.items():
            button.setStyleSheet(self._catalog_filter_style(key == category))
        self._refresh_catalog_cards(self._visible_parts_catalog())

    def _set_reference_currency(self, code):
        for index in range(self.cmb_currency.count()):
            if self._parse_currency_code(self.cmb_currency.itemText(index)) == code:
                self.cmb_currency.setCurrentIndex(index)
                return

    def _select_reference_currency(self, code):
        self._set_reference_currency(code)

    def _apply_discount_percent(self, percent):
        if percent < 0:
            self.inp_discount.setFocus()
            return
        subtotal = sum(float(item.get('price') or 0) * float(item.get('qty') or 1) for item in self.cart_items)
        self.inp_discount.setValue(subtotal * float(percent) / 100.0)
        for label, button in self.reference_discount_buttons.items():
            button.setStyleSheet(self._catalog_filter_style(label == f'%{percent}'))
        self.update_totals()

    def _on_catalog_query_changed(self, text):
        self._catalog_query = str(text or '').casefold().strip()
        self._refresh_catalog_cards(self._visible_parts_catalog())

    def _on_catalog_search_changed(self, text):
        self._on_catalog_query_changed(text)

    def _add_catalog_search_result(self):
        query = self._catalog_query.casefold().strip()
        info = next((item for item in self._visible_parts_catalog() if query and query in ' '.join(str(item.get(key) or '') for key in ('name', 'code', 'category')).casefold()), None)
        if info:
            self._add_catalog_card(info)

    def _catalog_filter_style(self, selected):
        if selected:
            return theme_qss('QPushButton { background: @finance_primary; color: @finance_primary_text; border: 1px solid @finance_primary; border-radius: 18px; padding: 0 12px; font-size: 10px; font-weight: 700; }')
        return theme_qss('QPushButton { background: @finance_surface_alt; color: @finance_text_muted; border: 1px solid @finance_outline; border-radius: 18px; padding: 0 12px; font-size: 10px; font-weight: 600; } QPushButton:hover { border-color: @finance_primary; color: @finance_text; }')

    def _refresh_catalog_cards(self, parts):
        if not hasattr(self, 'catalog_cards_layout'):
            return
        keywords = {
            'camera': ('kamera', 'camera', 'ipc', 'dahua'),
            'recorder': ('nvr', 'dvr', 'kayit', 'kay\u0131t'),
            'storage': ('disk', 'hdd', 'ssd', 'skyhawk'),
            'network': ('switch', 'ag', 'a\u011f', 'poe', 'cat6'),
            'service': ('montaj', 'iscilik', 'i\u015f\u00e7ilik', 'servis'),
        }
        labels = getattr(self, 'catalog_filter_base_labels', {})
        for key, button in getattr(self, 'catalog_filter_buttons', {}).items():
            if key == 'all':
                count = len(parts)
            else:
                terms = keywords.get(key, ())
                count = sum(any(term in ' '.join(str(info.get(field) or '') for field in ('name', 'code', 'category')).casefold() for term in terms) for info in parts)
            button.setText(f"{labels.get(key, button.text())} {count}".replace('&', '&&'))
        query = getattr(self, '_catalog_query', '').casefold().strip()
        category = getattr(self, '_catalog_category', 'all')
        filtered = [info for info in parts if (not query or query in ' '.join(str(info.get(key) or '') for key in ('name', 'code', 'category', 'description')).casefold()) and (category == 'all' or any(term in ' '.join(str(info.get(key) or '') for key in ('name', 'code', 'category')).casefold() for term in keywords.get(category, ())))]
        while self.catalog_cards_layout.count():
            item = self.catalog_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        columns = max(1, int(getattr(self, '_catalog_columns', 3)))
        if not filtered:
            empty = QLabel('\u00dcr\u00fcn bulunamad\u0131.')
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(120)
            self.catalog_cards_layout.addWidget(empty, 0, 0, 1, columns)
            return
        for index, info in enumerate(filtered[:18]):
            name = str(info.get('name') or '-')
            code = str(info.get('code') or f"PRD-{info.get('id', index + 1)}")
            currency = str(info.get('currency') or 'TRY').upper()
            price = CurrencyHelper.format_amount(info.get('original_price', info.get('price', 0)), db=self.db, currency_code=currency)
            price_try = CurrencyHelper.format_amount(info.get('price', 0), db=self.db, currency_code='TRY')
            card = QPushButton()
            card.setObjectName('TransactionProductCard')
            card.setFlat(True)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setFixedHeight(256 if self.height() < 980 else 354)
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            card.setToolTip(f"{name}\n{info.get('stock', 0)} adet | {price}\n{info.get('description') or info.get('category') or ''}")
            card.setAccessibleName(f"{name} | {code} | {price}")
            content = QVBoxLayout(card)
            content.setContentsMargins(14, 14, 14, 14)
            content.setSpacing(0)
            badges = QHBoxLayout()
            code_label = QLabel(code)
            code_label.setFixedSize(98, 44)
            code_label.setWordWrap(True)
            code_label.setStyleSheet(theme_qss('background: @finance_active_bg; color: @finance_primary; border: 1px solid @finance_outline; border-radius: 4px; padding: 5px; font: 10px "JetBrains Mono";'))
            stock = QLabel(f"Stok: {info.get('stock', 0)} Adet")
            stock.setFixedSize(92, 44)
            stock.setWordWrap(True)
            stock.setStyleSheet(theme_qss('background: @finance_success_bg; color: @finance_secondary; border: none; border-radius: 4px; padding: 5px; font-size: 10px;'))
            badges.addWidget(code_label)
            badges.addStretch()
            badges.addWidget(stock)
            content.addLayout(badges)
            content.addSpacing(12)
            title = QLabel(name)
            title.setWordWrap(True)
            title.setMaximumWidth(190)
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            title.setStyleSheet(theme_qss('background: transparent; border: none; color: @finance_text; font-size: 14px; font-weight: 700;'))
            content.addWidget(title)
            metadata = QLabel(str(info.get('description') or info.get('category') or ''))
            metadata.setWordWrap(True)
            metadata.setMaximumWidth(190)
            metadata.setStyleSheet(theme_qss('background: transparent; border: none; color: @finance_text_muted; font-size: 11px;'))
            content.addWidget(metadata)
            content.addSpacing(2)
            rule = QFrame()
            rule.setFixedHeight(1)
            rule.setStyleSheet(theme_qss('background: @finance_outline; border: none;'))
            content.addWidget(rule)
            unit = QLabel('Birim Sat\u0131\u015f (KDV Hari\u00e7)')
            unit.setStyleSheet(theme_qss('background: transparent; border: none; color: @finance_text_muted; font-size: 10px;'))
            content.addWidget(unit)
            content.addStretch(1)
            footer = QHBoxLayout()
            amount_stack = QHBoxLayout()
            amount_stack.setSpacing(4)
            amount = QLabel(price)
            amount.setObjectName('TransactionProductAmount')
            amount.setToolTip(price)
            amount.setStyleSheet(theme_qss('background: transparent; border: none; color: @finance_primary; font: 700 11px "JetBrains Mono";'))
            reference = QLabel(price_try)
            reference.setToolTip(price_try)
            reference.setStyleSheet(theme_qss('background: transparent; border: none; color: @finance_text_muted; font: 9px "JetBrains Mono";'))
            amount_stack.addWidget(amount)
            amount_separator = QLabel('/')
            amount_separator.setStyleSheet(theme_qss('background: transparent; border: none; color: @finance_text_muted; font-size: 9px;'))
            amount_stack.addWidget(amount_separator)
            amount_stack.addWidget(reference)
            footer.addLayout(amount_stack, 1)
            add = QPushButton('+  Ekle')
            add.setFixedHeight(42)
            add.setCursor(Qt.CursorShape.PointingHandCursor)
            add.setStyleSheet(theme_qss('QPushButton { background: @finance_primary; color: @finance_primary_text; border: none; border-radius: 8px; padding: 0 12px; font-size: 12px; font-weight: 700; } QPushButton:hover { background: @finance_primary_gradient; }'))
            add.clicked.connect(lambda _checked=False, item=info: self._add_catalog_card(item))
            footer.addWidget(add)
            content.addLayout(footer)
            card.setStyleSheet(theme_qss('QPushButton#TransactionProductCard { background: @finance_surface_container; border: 1px solid @finance_outline; border-radius: 12px; } QPushButton#TransactionProductCard:hover { border-color: @finance_primary; background: @finance_active_bg; }'))
            card.clicked.connect(lambda _checked=False, item=info: self._select_catalog_card(item))
            self.catalog_cards_layout.addWidget(card, index // columns, index % columns)
        for column in range(columns):
            self.catalog_cards_layout.setColumnStretch(column, 1)

    def _select_catalog_card(self, info):
        selected_id = info.get('id') if isinstance(info, dict) else None
        index = next((i for i in range(self.cmb_parts.count()) if self.cmb_parts.itemData(i).get('id') == selected_id), -1)
        self.cmb_parts.setCurrentIndex(index)
        self._last_item_type = 'part'
        self.inp_price.setValue(float(info.get('price') or 0))
        self.inp_desc.setCurrentText(str(info.get('description') or info.get('name') or ''))

    def _add_catalog_card(self, info):
        if not isinstance(info, dict):
            return
        self.inp_qty.setValue(1)
        self.inp_price.setValue(float(info.get('price') or 0))
        self.inp_desc.setCurrentText(str(info.get('description') or info.get('name') or ''))
        self.add_to_cart(info)

    def _build_header(self):
        return QFrame()

    def _build_context_column(self):
        column = QVBoxLayout()
        column.setSpacing(12)

        customer_card, customer_layout = self._panel_card('M\u00fc\u015fteri ve \u0130\u015flem Bilgileri')
        customer_grid = QGridLayout()
        customer_grid.setHorizontalSpacing(12)
        customer_grid.setVerticalSpacing(8)

        self.cmb_customer = QComboBox()
        self.cmb_customer.setEditable(True)
        self.cmb_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_customer.setFixedHeight(38)
        self.cmb_customer.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self.cmb_customer.currentTextChanged.connect(self._refresh_customer_preview)
        self.cmb_customer.lineEdit().setPlaceholderText('M\u00fc\u015fteri se\u00e7in veya ad yaz\u0131n...')
        self.customer_completer = self.cmb_customer.completer()
        if self.customer_completer:
            self.customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.customer_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.customer_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        btn_search_customer = QPushButton('Ara')
        btn_search_customer.setFixedSize(80, 38)
        btn_search_customer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search_customer.setStyleSheet(theme_qss(DesignTokens.get_button_qss('secondary', size='md')))
        btn_search_customer.clicked.connect(self.open_customer_search)

        customer_row = QHBoxLayout()
        customer_row.setSpacing(10)
        customer_row.addWidget(self.cmb_customer, 1)
        customer_row.addWidget(btn_search_customer)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('dd.MM.yyyy')
        self.date_edit.setFixedHeight(38)
        self.date_edit.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_currency = QComboBox()
        self.cmb_currency.addItems(['TRY - T\u00fcrk Liras\u0131 (TL)', 'USD - Amerikan Dolar\u0131 ($)', 'EUR - Euro (EUR)'])
        self.cmb_currency.setFixedHeight(38)
        self.cmb_currency.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self.cmb_currency.currentTextChanged.connect(self._handle_currency_change)

        self.lbl_exchange_rate = QLabel('Kur bilgisi y\u00fckleniyor...')
        self.lbl_exchange_rate.setStyleSheet(
            theme_qss(
                """
                background: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 700;
                """
            )
        )

        self.customer_preview = QLabel('')
        self.customer_preview.setWordWrap(True)
        self.customer_preview.hide()
        self.customer_preview.setStyleSheet(
            theme_qss(
                """
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 16px;
                padding: 12px 14px;
                font-size: 12px;
                font-weight: 600;
                """
            )
        )

        customer_grid.addWidget(self._field_label('M\u00fc\u015fteri'), 0, 0, 1, 2)
        customer_grid.addLayout(customer_row, 1, 0, 1, 2)
        customer_grid.addWidget(self._field_label('\u0130\u015flem Tarihi'), 2, 0)
        customer_grid.addWidget(self._field_label('Para Birimi'), 2, 1)
        customer_grid.addWidget(self.date_edit, 3, 0)
        customer_grid.addWidget(self.cmb_currency, 3, 1)
        customer_grid.addWidget(self.lbl_exchange_rate, 4, 0, 1, 2)
        customer_layout.addLayout(customer_grid)

        column.addWidget(customer_card)
        column.addWidget(self._build_composer_card())
        column.addStretch()
        return column

    def _build_composer_card(self):
        composer_card, composer_layout = self._panel_card('Hizmet&Par\u00e7a Se\u00e7im')

        composer_grid = QGridLayout()
        composer_grid.setHorizontalSpacing(12)
        composer_grid.setVerticalSpacing(6)

        self.cmb_service_types = ModernComboBox(min_height=38)
        self.cmb_service_types.setEditable(True)
        self.cmb_service_types.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_service_types.setFixedHeight(38)
        self.cmb_service_types.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self._setup_searchable_combo(self.cmb_service_types, 'Hizmet se\u00e7in veya yaz\u0131n...')
        self.cmb_service_types.currentIndexChanged.connect(lambda: self._on_item_selection_change('service'))

        self.cmb_product_domain = ModernComboBox(min_height=38)
        self.cmb_product_domain.addItem("G\u00fcvenlik Sistemleri", "security")
        self.cmb_product_domain.addItem("Bilgisayar", "computer")
        self.cmb_product_domain.addItem("Ak\u0131ll\u0131 Ev", "smart_home")
        self.cmb_product_domain.setFixedHeight(38)
        self.cmb_product_domain.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self.cmb_product_domain.currentIndexChanged.connect(self._on_product_domain_changed)

        self.cmb_parts = ModernComboBox(min_height=38)
        self.cmb_parts.setEditable(True)
        self.cmb_parts.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_parts.setFixedHeight(38)
        self.cmb_parts.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self._setup_searchable_combo(self.cmb_parts, 'Par\u00e7a se\u00e7in veya yaz\u0131n...')
        self.cmb_parts.currentIndexChanged.connect(lambda: self._on_item_selection_change('part'))

        self.inp_qty = InlineNumberStepper(value=1, decimals=0)
        self.inp_qty.setRange(1, 9999)
        self.inp_qty.setFixedHeight(38)
        self.inp_qty.valueChanged.connect(self.update_calc_total)

        self.inp_price = ReferenceCurrencyStepper(value=0.0, decimals=2)
        self.inp_price.setRange(0, 999999999)
        self.inp_price.setFixedHeight(38)
        self.inp_price.valueChanged.connect(self.update_calc_total)

        self.inp_desc = ModernComboBox(min_height=38)
        self.inp_desc.setEditable(True)
        self.inp_desc.setFixedHeight(38)
        self.inp_desc.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self.inp_desc.lineEdit().setPlaceholderText('Servis notu, cihaz durumu veya stok a\u00e7\u0131klamas\u0131')

        self.lbl_line_total = QLabel(
            f"Sat\u0131r Toplam\u0131: {CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)}"
        )
        self.lbl_line_total.setObjectName('TransactionLineAmount')
        self.lbl_line_total.setStyleSheet(theme_qss('font-size: 14px; font-weight: 900; color: @accent;'))

        self.btn_add_to_cart = QPushButton('Sepete Ekle')
        self.btn_add_to_cart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_to_cart.setMinimumWidth(180)
        self.btn_add_to_cart.setFixedHeight(52)
        self.btn_add_to_cart.setStyleSheet(theme_qss('''
            QPushButton {
                background: @success;
                color: white;
                border: 1px solid @success;
                border-radius: 14px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: @success_bg;
                border-color: @success;
            }
        '''))
        self.btn_add_to_cart.clicked.connect(self.add_to_cart)

        if not hasattr(self, 'btn_bulk'):
            self.btn_bulk = QPushButton('Toplu Se\u00e7im')
            self.btn_bulk.clicked.connect(self.open_multi_select_v2)
        self.btn_bulk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk.setFixedHeight(42)
        self.btn_bulk.setStyleSheet(theme_qss(
            'QPushButton { background: @finance_surface_alt; color: @finance_text; '
            'border: 1px solid @finance_outline; border-radius: 8px; padding: 0 10px; '
            'font-size: 11px; font-weight: 600; } QPushButton:hover { border-color: @finance_primary; }'
        ))

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addWidget(self.btn_add_to_cart)
        action_row.addWidget(self.btn_bulk)

        composer_grid.addWidget(self._field_label('Hizmetler'), 0, 0, 1, 2)
        composer_grid.addWidget(self.cmb_service_types, 1, 0, 1, 2)
        composer_grid.addWidget(self._field_label('\u00dcr\u00fcn Grubu'), 2, 0, 1, 2)
        composer_grid.addWidget(self.cmb_product_domain, 3, 0, 1, 2)
        composer_grid.addWidget(self._field_label('Par\u00e7a (\u00dcr\u00fcnler)'), 4, 0, 1, 2)
        composer_grid.addWidget(self.cmb_parts, 5, 0, 1, 2)
        composer_grid.addWidget(self._field_label('Adet'), 6, 0)
        composer_grid.addWidget(self._field_label('Birim Fiyat'), 6, 1)
        composer_grid.addWidget(self.inp_qty, 7, 0)
        composer_grid.addWidget(self.inp_price, 7, 1)
        composer_grid.addWidget(self._field_label('A\u00e7\u0131klama'), 8, 0, 1, 2)
        composer_grid.addWidget(self.inp_desc, 9, 0, 1, 2)
        composer_grid.addWidget(self.lbl_line_total, 10, 0, 1, 2)

        composer_layout.addLayout(composer_grid)
        composer_layout.addLayout(action_row)
        return composer_card

    def _build_workbench_column(self):
        column = QVBoxLayout()
        column.setSpacing(12)

        workbench_card, workbench_layout = self._panel_card('\u0130\u015flem Sepeti')

        basket_top = QHBoxLayout()
        basket_top.setSpacing(10)

        self.lbl_subtotal = QLabel(
            f"Ara Toplam: {CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)}"
        )
        self.lbl_subtotal.setStyleSheet(theme_qss('font-size: 14px; font-weight: 900; color: @text;'))

        btn_clear = QPushButton('Sepeti Bo\u015falt')
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(theme_qss(DesignTokens.get_button_qss('ghost', size='sm')))
        btn_clear.clicked.connect(self.clear_cart)

        basket_top.addWidget(self.lbl_subtotal)
        basket_top.addStretch()
        basket_top.addWidget(btn_clear)
        workbench_layout.addLayout(basket_top)

        self.cart_table = QTreeWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHeaderLabels(['Tarih', 'Kalem', 'Adet', 'A\u00e7\u0131klama', 'Tutar'])
        self.cart_table.setRootIsDecorated(False)
        self.cart_table.setAlternatingRowColors(False)
        self.cart_table.setUniformRowHeights(False)
        self.cart_table.setIndentation(16)
        self.cart_table.setMinimumHeight(540)
        self.cart_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.cart_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cart_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cart_table.customContextMenuRequested.connect(self.show_cart_context_menu)
        header = self.cart_table.header()
        header.setStretchLastSection(False)
        header.resizeSection(0, 110)
        header.resizeSection(1, 220)
        header.resizeSection(2, 60)
        header.resizeSection(3, 260)
        header.resizeSection(4, 120)

        self.cart_empty_state = EmptyState('Sepet bo\u015f', 'Soldan hizmet veya par\u00e7a se\u00e7erek kalem ekleyin.')
        self.cart_empty_state.setMinimumHeight(540)
        self.cart_content_stack = _SimpleStack(self.cart_table, self.cart_empty_state)
        self.cart_content_stack.setCurrentWidget(self.cart_empty_state)
        workbench_layout.addWidget(self.cart_content_stack, 1)

        column.addWidget(workbench_card, 1)
        return column

    def _build_summary_column(self):
        column = QVBoxLayout()
        column.setSpacing(12)

        summary_card, summary_layout = self._panel_card('Toplam ve Kay\u0131t')

        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(10)
        stats_grid.setVerticalSpacing(10)
        zero_amount = CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)
        self.stat_subtotal = self._summary_box('Ara Toplam', zero_amount, 'primary')
        self.stat_discount = self._summary_box('\u0130skonto', zero_amount, 'warning')
        self.stat_vat = self._summary_box('KDV', zero_amount, 'secondary')
        self.stat_total = self._summary_box('Genel Toplam', zero_amount, 'success')
        stats_grid.addWidget(self.stat_subtotal, 0, 0)
        stats_grid.addWidget(self.stat_discount, 0, 1)
        stats_grid.addWidget(self.stat_vat, 1, 0)
        stats_grid.addWidget(self.stat_total, 1, 1)
        summary_layout.addLayout(stats_grid)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.inp_discount = InlineNumberStepper(value=0.0, decimals=2)
        self.inp_discount.setRange(0, 999999999)
        self.inp_discount.setFixedHeight(38)
        self.inp_discount.valueChanged.connect(self.update_totals)

        self.cmb_vat = QComboBox()
        self.cmb_vat.addItems(['%0', '%1', '%10', '%18', '%20'])
        default_vat_text = TaxSettings.combo_text(self.db)
        if self.cmb_vat.findText(default_vat_text) < 0:
            self.cmb_vat.addItem(default_vat_text)
        self.cmb_vat.setCurrentText(default_vat_text)
        self.cmb_vat.setFixedHeight(38)
        self.cmb_vat.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss(min_height=32)))
        self.cmb_vat.currentTextChanged.connect(self.update_totals)

        self.date_edit_transaction = QDateEdit(QDate.currentDate())
        self.date_edit_transaction.setCalendarPopup(True)
        self.date_edit_transaction.setDisplayFormat('dd.MM.yyyy')
        self.date_edit_transaction.setFixedHeight(38)
        self.date_edit_transaction.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        form.addWidget(self._field_label('\u0130skonto'), 0, 0)
        form.addWidget(self._field_label('KDV'), 0, 1)
        form.addWidget(self.inp_discount, 1, 0)
        form.addWidget(self.cmb_vat, 1, 1)
        form.addWidget(self._field_label('Kay\u0131t Tarihi'), 2, 0, 1, 2)
        form.addWidget(self.date_edit_transaction, 3, 0, 1, 2)
        summary_layout.addLayout(form)

        self.lbl_total = QLabel(CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False))
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_total.setMinimumHeight(88)
        self.lbl_total.setStyleSheet(
            theme_qss(
                """
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 20px;
                color: @success;
                font-size: 22px;
                font-weight: 900;
                padding: 12px;
                """
            )
        )
        summary_layout.addWidget(self.lbl_total)

        approval_row = QFrame()
        approval_row.setObjectName('OfferApprovalRow')
        approval_row.setStyleSheet(
            theme_qss(
                """
                QFrame#OfferApprovalRow {
                    background: @surface_alt;
                    border: 1px solid @border;
                    border-radius: 12px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                    color: @text;
                    font-size: 12px;
                    font-weight: 800;
                }
                """
            )
        )
        approval_layout = QHBoxLayout(approval_row)
        approval_layout.setContentsMargins(12, 7, 12, 7)
        approval_layout.setSpacing(10)
        approval_label = QLabel('Teklif Onay\u0131')
        approval_label.setToolTip(
            'A\u00e7\u0131kken PDF belgesine teklif onay ve imza alan\u0131 eklenir.'
        )
        self.toggle_offer_approval = AnimatedToggle(active_color=tc('success'))
        self.toggle_offer_approval.setChecked(True)
        self.toggle_offer_approval.setToolTip(approval_label.toolTip())
        approval_layout.addWidget(approval_label)
        approval_layout.addStretch()
        approval_layout.addWidget(self.toggle_offer_approval)
        summary_layout.addWidget(approval_row)

        self.btn_save = QPushButton('Servis Kaydet')
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(46)
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss('warning', size='lg')))
        self.btn_save.clicked.connect(self.save_transaction)
        summary_layout.addWidget(self.btn_save)

        self.btn_pay = QPushButton('\u00d6deme Al ve Kaydet')
        self.btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pay.setFixedHeight(52)
        self.btn_pay.setStyleSheet(theme_qss(DesignTokens.get_button_qss('success', size='lg')))
        self.btn_pay.clicked.connect(self.save_and_pay)
        summary_layout.addWidget(self.btn_pay)

        self.btn_proforma = QPushButton('Proforma Olu\u015ftur')
        self.btn_proforma.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_proforma.setFixedHeight(42)
        self.btn_proforma.setStyleSheet(theme_qss(DesignTokens.get_button_qss('primary', size='lg')))
        self.btn_proforma.clicked.connect(self.create_proforma)
        summary_layout.addWidget(self.btn_proforma)

        summary_layout.addStretch()
        column.addWidget(summary_card)
        return column

    def _top_chip(self, text):
        chip = QLabel(text)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setMinimumHeight(36)
        chip.setStyleSheet(
            theme_qss(
                """
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 800;
                """
            )
        )
        return chip

    def _panel_card(self, title):
        frame = QFrame()
        frame.setStyleSheet(theme_qss('background: @surface; border: 1px solid @border; border-radius: 10px;'))
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss('font-size: 17px; font-weight: 900; color: @text;'))
        layout.addWidget(title_label)
        return frame, layout

    def _field_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(theme_qss('font-size: 11px; color: @text_muted; font-weight: 800;'))
        return label

    def _summary_box(self, title, value, variant):
        box = QFrame()
        box.setObjectName('TransactionSummaryMetric')
        box.setStyleSheet(theme_qss('QFrame#TransactionSummaryMetric { background: @finance_surface_lowest; border: 1px solid @finance_outline; border-radius: 6px; }'))
        box.setMinimumHeight(90)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss('font-size: 11px; color: @finance_text_muted; font-weight: 500; background: transparent; border: none;'))

        color_map = {
            'primary': '@accent',
            'warning': '@warning',
            'secondary': '@text',
            'success': '@success',
        }
        value_label = ReferenceMetricValueLabel(value, primary_token=color_map.get(variant, '@text').lstrip('@'), primary_size=15)
        value_label.setStyleSheet(theme_qss(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {color_map.get(variant, '@text')};"))

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        reference_label = QLabel('')
        reference_label.setFont(QFont(DesignTokens.MONO_FONT_NAME))
        reference_label.setStyleSheet(theme_qss(f'background: transparent; border: none; font-size: 10px; font-family: "{DesignTokens.MONO_FONT_NAME}"; color: @finance_text_muted;'))
        reference_label.hide()
        layout.addWidget(reference_label)
        box.value_label = value_label
        box.reference_label = reference_label
        return box

    @staticmethod
    def _currency_meta(currency_code):
        if currency_code == 'USD':
            return '$', 'USD'
        if currency_code == 'EUR':
            return '\u20ac', 'EUR'
        return '\u20ba', 'TRY'

    def _convert_from_try(self, amount_try, currency_code):
        if currency_code == 'TRY':
            return amount_try
        rate = self.current_exchange_rate if self.current_exchange_rate > 0 else 1.0
        return amount_try / rate

    def clear_cart(self):
        self.cart_items = []
        self._editing_offer_id = None
        self._editing_offer_no = ""
        self._editing_offer_project = ""
        self._editing_offer_template = ""
        if hasattr(self, "toggle_offer_approval"):
            self.toggle_offer_approval.setChecked(True)
        self._clear_draft()
        self.refresh_cart_ui()
        self.update_totals()

    def load_offer_for_edit(self, offer_id):
        offer = self.db.get_offer_record(int(offer_id))
        if not offer:
            raise RuntimeError("Offer record was not found.")
        status = str(offer["status"] or "").strip().lower()
        status = (
            status.replace("\u0131", "i")
            .replace("\u015f", "s")
            .replace("\u0130", "i")
            .replace("\u015e", "s")
            .replace("\u0307", "")
        )
        if status in {"accepted", "processed", "islenmis", "kabul edildi"}:
            raise RuntimeError("Accepted offers cannot be edited.")

        rows = self.db.get_offer_items_detailed(int(offer_id)) or []
        if not rows:
            raise RuntimeError("Offer has no line items.")

        self.load_customers()
        customer_index = self.cmb_customer.findData(offer["customer_id"])
        if customer_index >= 0:
            self.cmb_customer.setCurrentIndex(customer_index)

        currency_code = str(offer["currency_code"] or "TRY").upper()
        for index in range(self.cmb_currency.count()):
            if self._parse_currency_code(self.cmb_currency.itemText(index)) == currency_code:
                self.cmb_currency.setCurrentIndex(index)
                break

        exchange_rate = float(offer["exchange_rate"] or 1.0)
        if currency_code != "TRY":
            self.current_exchange_rate = exchange_rate
        offer_date = str(offer["created_at"] or "")[:10]
        self.cart_items = []
        for row in rows:
            unit_price = float(row["unit_price"] or 0)
            price_try = (
                unit_price
                if currency_code == "TRY"
                else unit_price * exchange_rate
            )
            self.cart_items.append(
                {
                    "id": str(uuid.uuid4()),
                    "item_id": row["item_id"],
                    "type": str(row["item_type"] or ""),
                    "service": str(row["service"] or ""),
                    "description": str(row["description"] or ""),
                    "brand": str(row["brand"] or ""),
                    "qty": int(float(row["qty"] or 1)),
                    "price": float(price_try),
                    "date": offer_date
                    or QDate.currentDate().toString("yyyy-MM-dd"),
                }
            )

        self.inp_discount.setValue(float(offer["discount_try"] or 0))
        stored_vat_rate = float(offer["vat_rate"] or 0)
        vat_ratio = (
            stored_vat_rate / 100
            if stored_vat_rate > 1
            else stored_vat_rate
        )
        vat_percent = round(vat_ratio * 100)
        vat_text = f"%{vat_percent}"
        if self.cmb_vat.findText(vat_text) < 0:
            self.cmb_vat.addItem(vat_text)
        self.cmb_vat.setCurrentText(vat_text)
        self._editing_offer_id = int(offer_id)
        self._editing_offer_no = str(offer["offer_no"] or "")
        self._editing_offer_project = str(offer["project_name"] or "")
        self._editing_offer_template = str(offer["template_type"] or "")
        approval_enabled = True
        try:
            payload = json.loads(str(offer["payload_json"] or "{}"))
            if isinstance(payload, dict):
                approval_enabled = bool(payload.get("include_approval", True))
        except (TypeError, ValueError, json.JSONDecodeError):
            approval_enabled = True
        if hasattr(self, "toggle_offer_approval"):
            self.toggle_offer_approval.setChecked(approval_enabled)
        self.refresh_cart_ui()
        self.update_totals()
        self._refresh_customer_preview()
        self.notify(
            "Teklif sat\u0131\u015f sepetine y\u00fcklendi. "
            "De\u011fi\u015fikliklerden sonra Proforma Olu\u015ftur ile kaydedin.",
            "success",
        )

    def refresh_cart_ui(self):
        self.cart_table.clear()
        self.cart_table.setHeaderLabels(['Tarih', 'Kalem', 'Adet', 'A\u00e7\u0131klama', 'Tutar'])
        grouped = {}
        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        _symbol, code_label = self._currency_meta(currency_code)

        for item in self.cart_items:
            grouped.setdefault(item['date'], []).append(item)

        for date_key in sorted(grouped.keys(), reverse=True):
            items = grouped[date_key]
            group_total_try = sum(float(x['price']) * int(x.get('qty', 1)) for x in items)
            group_total = self._convert_from_try(group_total_try, currency_code)

            root = QTreeWidgetItem(self.cart_table)
            root.setText(0, date_key)
            root.setText(1, f'{len(items)} kalem')
            root.setText(4, CurrencyHelper.format_amount(group_total, db=self.db, currency_code=currency_code))
            root.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            root.setTextAlignment(4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            for col in range(5):
                root.setBackground(col, QColor(tc('selection_bg')))
                root.setForeground(col, QColor(tc('text')))
                font = root.font(col)
                font.setBold(True)
                root.setFont(col, font)

            for idx, item in enumerate(items):
                child = QTreeWidgetItem(root)
                child.setData(0, Qt.ItemDataRole.UserRole, item['id'])
                child.setText(1, item['service'])
                child.setText(2, str(item.get('qty', 1)))
                description = item.get('description', '')
                if description.startswith('Stoktan \u00fcr\u00fcn: '):
                    description = description.replace('Stoktan \u00fcr\u00fcn: ', '', 1)
                child.setText(3, description)
                line_total_try = item['price'] * item.get('qty', 1)
                line_total = self._convert_from_try(line_total_try, currency_code)
                child.setText(4, CurrencyHelper.format_amount(line_total, db=self.db, currency_code=currency_code))
                child.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
                child.setTextAlignment(4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                for col in range(5):
                    child.setBackground(col, QColor(tc('surface') if idx % 2 == 0 else tc('surface_alt')))
                    child.setForeground(col, QColor(tc('text')))
                    if col == 4:
                        font = child.font(col)
                        font.setBold(True)
                        child.setFont(col, font)

            root.setExpanded(True)

        self._refresh_reference_cart_cards()
        self.cart_scroll.setVisible(bool(self.cart_items))
        self.cart_empty_state.setVisible(not self.cart_items)
        self._refresh_header_state()

    def _refresh_reference_cart_cards(self):
        while self.cart_cards_layout.count():
            entry = self.cart_cards_layout.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        currency = self._parse_currency_code(self.cmb_currency.currentText())
        for index, item in enumerate(self.cart_items, 1):
            unit_try = float(item.get('price') or 0)
            quantity = float(item.get('qty') or 1)
            unit = self._convert_from_try(unit_try, currency)
            amount = self._convert_from_try(unit_try * quantity, currency)
            item_code = next((str(info.get('code') or '') for info in self._all_parts_catalog if str(info.get('id')) == str(item.get('item_id'))), '')
            card = TransactionReferenceCard(
                item, index,
                CurrencyHelper.format_amount(amount, db=self.db, currency_code=currency),
                CurrencyHelper.format_amount(unit, db=self.db, currency_code=currency),
                vat_text=self.cmb_vat.currentText(),
                try_reference=CurrencyHelper.format_amount(unit_try * quantity, db=self.db, currency_code='TRY') if currency != 'TRY' else '',
                code=item_code,
                compact=getattr(self, '_reference_dense_mode', False),
            )
            card.quantity_requested.connect(self._change_reference_cart_quantity)
            card.action_requested.connect(self._reference_cart_action)
            self.cart_cards_layout.addWidget(card)
        self.cart_cards_layout.addStretch(1)

    def _select_reference_cart_item(self, item_id):
        for index in range(self.cart_table.topLevelItemCount()):
            group = self.cart_table.topLevelItem(index)
            for child_index in range(group.childCount()):
                child = group.child(child_index)
                if str(child.data(0, Qt.ItemDataRole.UserRole)) == str(item_id):
                    self.cart_table.setCurrentItem(child)
                    return True
        return False

    def _change_reference_cart_quantity(self, item_id, delta):
        item = next((row for row in self.cart_items if str(row.get('id')) == str(item_id)), None)
        if item is None:
            return
        minimum = 0.01 if item.get('type') == 'service' else 1
        item['qty'] = max(minimum, float(item.get('qty', 1)) + int(delta))
        self.refresh_cart_ui()
        self.update_totals()
        self._auto_save_draft()

    def _reference_cart_action(self, item_id, action):
        if not self._select_reference_cart_item(item_id):
            return
        if action == 'remove':
            self.remove_from_cart()
            self._auto_save_draft()
            return
        menu = QMenu(self)
        for title, callback in (
            ('Miktari Degistir', self.edit_quantity_context),
            ('Fiyati Guncelle', self.edit_price_context),
            ('Aciklama Ekle', self.add_description_context),
            ('Kalemi Kopyala', self.copy_service_context),
        ):
            menu.addAction(title, callback)
        self._reference_cart_menu = menu
        sender = self.sender()
        position = sender.mapToGlobal(sender.rect().bottomRight()) if sender else self.mapToGlobal(self.rect().center())
        menu.popup(position)

    def update_calc_total(self):
        total_try = self.inp_qty.value() * self.inp_price.value()
        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        display_total = self._convert_from_try(total_try, currency_code)
        text = CurrencyHelper.format_amount(display_total, db=self.db, currency_code=currency_code)
        if currency_code != 'TRY':
            text += '\n' + CurrencyHelper.format_amount(total_try, db=self.db, currency_code='TRY')
        self.lbl_line_total.setText(text)
        self.lbl_line_total.setToolTip(text)

    def update_totals(self):
        subtotal_try = sum(item['price'] * item.get('qty', 1) for item in self.cart_items)
        discount_try = self.inp_discount.value()
        vat_text = self.cmb_vat.currentText().replace('%', '')
        try:
            vat_rate = int(vat_text) / 100
        except (TypeError, ValueError):
            vat_rate = 0

        net_try = subtotal_try - discount_try
        vat_try = net_try * vat_rate
        total_try = net_try + vat_try

        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        _symbol, code_label = self._currency_meta(currency_code)

        subtotal = self._convert_from_try(subtotal_try, currency_code)
        discount = self._convert_from_try(discount_try, currency_code)
        vat_amount = self._convert_from_try(vat_try, currency_code)
        total = self._convert_from_try(total_try, currency_code)

        display_rate = 1.0 if currency_code == 'TRY' else self.current_exchange_rate
        for control in (self.inp_price, self.inp_discount):
            control.set_display_rate(display_rate)
            control.setToolTip(f'{currency_code} / TRY: {display_rate:g}; kayit degerleri TRY olarak saklanir.')
        self.inp_price.setSuffix(f" {CurrencyHelper.get_symbol(self.db, currency_code)}")
        self.inp_discount.setSuffix(f" {CurrencyHelper.get_symbol(self.db, currency_code)}")

        self.lbl_subtotal.setText(
            f"Ara Toplam ({len(self.cart_items)} Kalem): {CurrencyHelper.format_amount(subtotal, db=self.db, currency_code=currency_code)}"
        )
        self.lbl_subtotal.setToolTip(self.lbl_subtotal.text())
        total_text = CurrencyHelper.format_amount(total, db=self.db, currency_code=currency_code)
        if currency_code != 'TRY':
            total_text += '\n' + CurrencyHelper.format_amount(total_try, db=self.db, currency_code='TRY')
        self.lbl_total.setText(total_text)
        self.lbl_total.setToolTip(total_text)
        self.reference_total_primary.setText(total_text.splitlines()[0])
        self.reference_total_secondary.setText(total_text.splitlines()[1] if len(total_text.splitlines()) > 1 else '')
        for box, value_try in (
            (self.stat_subtotal, subtotal_try),
            (self.stat_discount, -discount_try),
            (self.stat_vat, vat_try),
            (self.stat_total, net_try),
        ):
            display_value = self._convert_from_try(value_try, currency_code)
            text = CurrencyHelper.format_amount(display_value, db=self.db, currency_code=currency_code)
            if box is self.stat_vat and value_try > 0:
                text = '+' + text
            box.value_label.setText(text)
            box.value_label.setToolTip(text)
            box.reference_label.setText(CurrencyHelper.format_amount(value_try, db=self.db, currency_code='TRY'))
            box.reference_label.setVisible(currency_code != 'TRY')
        self.reference_discount_value.setText(CurrencyHelper.format_amount(-discount, db=self.db, currency_code=currency_code))
        self.reference_amount_breakdown.setText(
            '\u0130skonto Sonras\u0131 Tutar: ' + CurrencyHelper.format_amount(net_try, db=self.db, currency_code=currency_code)
        )
        self.reference_amount_detail.setText(
            f'Hesaplanan KDV ({self.cmb_vat.currentText()}): '
            + CurrencyHelper.format_amount(vat_amount, db=self.db, currency_code=currency_code)
            + '  (' + CurrencyHelper.format_amount(vat_try, db=self.db, currency_code='TRY') + ')'
        )
        for code, button in self.reference_currency_buttons.items():
            button.setStyleSheet(self._catalog_filter_style(code == currency_code))

        self.refresh_cart_ui()
        self._refresh_header_state()
        return subtotal_try, discount_try, vat_try, total_try, net_try

    def _refresh_customer_preview(self):
        current_index = self.cmb_customer.currentIndex()
        customer_id = self.cmb_customer.currentData()
        if current_index < 0 or customer_id is None:
            self.customer_preview.hide()
            self.customer_title.setText('M\u00fc\u015fteri se\u00e7ilmedi')
            self.reference_due_badge.setText('Vade: Pesin / Cari')
            self.customer_avatar.setText('A')
            self.lbl_customer_state.setText('M\u00fc\u015fteri se\u00e7ilmedi')
            return

        customer_name = self.cmb_customer.currentText()
        self.customer_title.setText(customer_name)
        self.customer_avatar.setText(customer_name[:1].upper() or 'A')
        currency = self._parse_currency_code(self.cmb_currency.currentText())
        preview_parts = [f'Yetkili: {customer_name}']
        detail_parts = []
        try:
            balance = self.db.get_customer_currency_balance(customer_id, currency)
            preview_parts.append(f'Cari bakiye ({currency}): {CurrencyHelper.format_amount(balance, db=self.db, currency_code=currency)}')
        except Exception:
            preview_parts.append('Cari bakiye: --')
        try:
            row = self.db.cursor.execute('SELECT phone, term_days, limit_amount, tax_number, tax_office FROM customers WHERE id=?', (customer_id,)).fetchone()
            if row is not None:
                if row[0]:
                    preview_parts.append(f'Tel: {row[0]}')
                if int(row[1] or 0) > 0:
                    self.reference_due_badge.setText(f'Vade: {int(row[1])} Gun')
                else:
                    self.reference_due_badge.setText('Vade: Pesin / Cari')
                if float(row[2] or 0) > 0:
                    preview_parts.append(f'Kredi Limiti: {CurrencyHelper.format_amount(row[2], db=self.db, currency_code=currency)}')
                detail_parts.append(f'Vergi No / Daire: {row[3] or "--"} / {row[4] or "--"}')
        except Exception:
            pass
        preview_text = (
            ' | '.join(preview_parts)
            if getattr(self, '_reference_dense_mode', False)
            else '\n'.join(preview_parts)
        )
        self.customer_preview.setText(preview_text)
        self.customer_preview.setToolTip(' | '.join(preview_parts + detail_parts))
        self.customer_preview.show()
        self.lbl_customer_state.setText(customer_name[:28])

    def _handle_currency_change(self, currency_text):
        self.on_currency_changed(currency_text)
        self.update_calc_total()
        self.update_totals()
        self._refresh_customer_preview()
        self._refresh_header_state()

    def refresh_financial_defaults(self):
        if not self._editing_offer_id:
            default_vat_text = TaxSettings.combo_text(self.db)
            if self.cmb_vat.findText(default_vat_text) < 0:
                self.cmb_vat.addItem(default_vat_text)
            self.cmb_vat.setCurrentText(default_vat_text)
        self.update_exchange_rates()

    def _refresh_header_state(self):
        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        self.lbl_currency_state.setText(currency_code)
        self.lbl_cart_state.setText(f'{len(self.cart_items)} kalem')
        quantity = sum(float(item.get('qty', 1)) for item in self.cart_items)
        if hasattr(self, 'reference_cart_count'):
            quantity = sum(float(item.get('qty', 1)) for item in self.cart_items)
            self.reference_cart_count.setText(f'{len(self.cart_items)} Kalem | {quantity:g} Adet')
            self.reference_cart_summary.setText(f'{len(self.cart_items)} Kalem \u00dcr\u00fcn/Hizmet Se\u00e7ildi')
            self.reference_cart_rate.setText(f'1 {currency_code} = {1.0 if currency_code == "TRY" else self.current_exchange_rate:.4f} TRY')
        if hasattr(self, 'command_context'):
            context = self._editing_offer_project or self._editing_offer_no
            if not context:
                context = self.cmb_customer.currentText() if self.cmb_customer.currentData() else 'Genel Kayit'
            self.command_context.setText(f'Aktif teklif: {context} | {len(self.cart_items)} kalem')
        if self.cmb_customer.currentData() is None:
            self.lbl_customer_state.setText('Genel Kay\u0131t' if self.cart_items else 'M\u00fc\u015fteri se\u00e7ilmedi')

    def open_customer_search(self):
        try:
            from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
        except ImportError:
            show_error(self, 'Hata', 'M\u00fc\u015fteri arama penceresi bulunamad\u0131')
            return

        dialog = CustomerSelectDialog(self.db, self)
        if dialog.exec():
            selected_id = dialog.selected_customer_id
            index = self.cmb_customer.findData(selected_id)
            if index >= 0:
                self.cmb_customer.setCurrentIndex(index)
                self._refresh_customer_preview()

    def open_new_reference_customer(self):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        sector_id = "teknik_servis"
        try:
            from src.utils.system_config import SystemConfig

            sector_id = SystemConfig.get_current_sector(self.db) or sector_id
        except Exception:
            pass

        if str(sector_id).casefold() == "otomotiv":
            from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog as dialog_cls
        else:
            from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog as dialog_cls

        dialog = dialog_cls(self.db, self, sector_manager=sector_manager)
        if not dialog.exec():
            return

        customer_id = getattr(dialog, "saved_customer_id", None)
        self.load_customers()
        if customer_id is not None:
            index = self.cmb_customer.findData(customer_id)
            if index >= 0:
                self.cmb_customer.setCurrentIndex(index)
        self._refresh_customer_preview()
        self._save_reference_draft()
        if self.main_window and hasattr(self.main_window, 'refresh_loaded_page'):
            self.main_window.refresh_loaded_page(40)

    def _is_combo_auto_popup_enabled(self):
        """Ayarlardan combobox otomatik popup açma durumunu kontrol et."""
        try:
            return self.db.get_setting('combo_auto_popup', '0') == '1'
        except Exception:
            return False

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and source is getattr(self, 'catalog_search', None):
            if event.key() == Qt.Key.Key_F2:
                self.open_multi_select_v2()
                return True
        if event.type() == QEvent.Type.KeyPress and source is getattr(self.inp_qty, 'spn_counted', None):
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.add_to_cart()
                return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            if hasattr(self, 'cmb_customer') and source is self.cmb_customer.lineEdit():
                self._show_combo_popup(self.cmb_customer)
                return False
            # Combo auto-popup ayarı açıksa hizmet/parça combobox'larında da popup aç
            if self._is_combo_auto_popup_enabled():
                if hasattr(self, 'cmb_service_types') and source in (self.cmb_service_types, self.cmb_service_types.lineEdit()):
                    self._show_combo_popup(self.cmb_service_types)
                    return False
                if hasattr(self, 'cmb_parts') and source in (self.cmb_parts, self.cmb_parts.lineEdit()):
                    self._show_combo_popup(self.cmb_parts)
                    return False
        return super().eventFilter(source, event)

    def open_multi_select_v2(self):
        if not self.parts_data and not self.services_data:
            show_warning(self, 'Hizmet veya stok verisi hen\u00fcz y\u00fcklenmedi')
            return

        dialog = BulkStockSelectDialog(self, self.db, self.services_data, self.parts_data)
        if dialog.exec():
            selected_items = dialog.get_selected_items()
            if not selected_items:
                return

            date_text = self.date_edit.date().toString('dd.MM.yyyy')
            for item in selected_items:
                qty = int(item.get('qty') or 1)
                unit_price_try = float(item.get('price') or 0.0)
                item_type = item.get('type') or 'service'
                description = item.get('description') or ''
                if item_type == 'part' and not description:
                    description = f"Stok ürün: {item.get('name') or ''}"
                self.cart_items.append(
                    {
                        'id': uuid.uuid4().hex,
                        'item_id': item.get('id'),
                        'type': item_type,
                        'service': item.get('name') or '',
                        'brand': item.get('brand', ''),
                        'description': description,
                        'price': unit_price_try,
                        'qty': qty,
                        'date': date_text,
                    }
                )

            self._auto_save_draft()
            self.refresh_cart_ui()
            self.update_totals()


class _SimpleStack(QWidget):
    def __init__(self, primary, empty):
        super().__init__()
        self.primary = primary
        self.empty = empty

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(primary)
        layout.addWidget(empty)

    def setCurrentWidget(self, widget):
        self.primary.setVisible(widget is self.primary)
        self.empty.setVisible(widget is self.empty)

    def _wire_ui_signals(self):
        self.inp_desc.currentIndexChanged.connect(self._on_ui_widget_changed)
