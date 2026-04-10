import json
import uuid

from PyQt6.QtCore import QDate, QEvent, QSettings, QTimer, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs.bulk_stock_select_dialog import BulkStockSelectDialog
from src.ui.pages.transaction_multi_select_dialog import MultiSelectServiceDialog
from src.ui.pages.transaction_page_behaviors import TransactionPageBehaviorMixin
from src.ui.widgets.empty_state import EmptyState
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import tc, theme_qss
from src.utils.toast_notification import show_error, show_warning


class NewTransactionV2Page(TransactionPageBehaviorMixin, QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.cart_items = []
        self.current_exchange_rate = 1.0
        self.services_data = {}
        self.parts_data = {}
        self._last_item_type = None

        self._build_ui()
        self._bind_legacy_aliases()
        self._apply_global_currency_setting()
        QTimer.singleShot(0, self._deferred_load_customers)

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
            pass

    def load_services(self):
        try:
            self.cmb_service_types.blockSignals(True)
            self.cmb_parts.blockSignals(True)
            self.cmb_service_types.clear()
            self.cmb_parts.clear()
            self.services_data = {}
            self.parts_data = {}

            services = self.db.get_services_list() or []
            for s in services:
                name = s['name']
                try:
                    raw_price = str(s['price']).replace(" ₺", "").replace("₺", "").strip() if s['price'] else "0"
                    final_price = float(raw_price)
                except (TypeError, ValueError):
                    final_price = 0.0

                info = {
                    'id': s.get('id'),
                    'name': name,
                    'type': 'service',
                    'price': final_price,
                    'description': s.get('description', '')
                }
                self.services_data[name] = info
                display_price = CurrencyHelper.format_try_for_display(final_price, db=self.db, include_try_reference=False)
                display_str = f"{name} - {display_price}"
                self.cmb_service_types.addItem(display_str, info)

            self.db.cursor.execute("SELECT id, name, category, stock, price, currency FROM parts ORDER BY name")
            parts = self.db.cursor.fetchall() or []
            for p in parts:
                try:
                    part_id = p["id"]
                    name = p["name"]
                    category = p["category"]
                    stock = p["stock"]
                    price = p["price"]
                    currency = p["currency"]
                except Exception:
                    part_id = p[0]
                    name = p[1]
                    category = p[2] if len(p) > 2 else ""
                    stock = p[3] if len(p) > 3 else 0
                    price = p[4] if len(p) > 4 else 0
                    currency = p[5] if len(p) > 5 else "TRY"
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
                    'currency': currency,
                    'original_price': final_price,
                }
                self.parts_data[name] = info
                display_price = CurrencyHelper.format_amount(final_price, db=self.db, currency_code=currency)
                display_str = f"{name} (Stok: {stock}) - {display_price}"
                self.cmb_parts.addItem(display_str, info)

            # Placeholder olarak gölge metin göster (seçili öğe yok)
            self.cmb_service_types.setCurrentIndex(-1)
            self.cmb_parts.setCurrentIndex(-1)

        except Exception as e:
            show_warning(self, f"Veri y\u00fcklenemedi: {e}")
        finally:
            self.cmb_service_types.blockSignals(False)
            self.cmb_parts.blockSignals(False)

    def _setup_searchable_combo(self, combo, placeholder):
        combo.setEditable(True)
        combo.setCurrentIndex(-1)
        line_edit = combo.lineEdit()
        if line_edit:
            line_edit.setReadOnly(False)
            line_edit.setPlaceholderText(placeholder)
            line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            line_edit.installEventFilter(self)
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
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
        else:
            info = self.cmb_parts.currentData()
            if info:
                self._last_item_type = 'part'
                self.cmb_service_types.blockSignals(True)
                self.cmb_service_types.setCurrentIndex(-1)
                self.cmb_service_types.blockSignals(False)
                self.inp_price.setValue(float(info.get('price') or 0))
                self.inp_desc.setCurrentText(f"Stok \u00fcr\u00fcn: {info.get('name', '')}")

    def add_to_cart(self):
        service_info = self.cmb_service_types.currentData()
        part_info = self.cmb_parts.currentData()

        selected = None
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
            data = {
                "customer": self.cmb_customer.currentText(),
                "cart_items": self.cart_items,
            }
            QSettings().setValue(self._DRAFT_KEY, json.dumps(data, default=str))
        except Exception:
            pass

    def _clear_draft(self):
        QSettings().remove(self._DRAFT_KEY)

    def _restore_draft(self):
        """Sayfa açılışında kaydedilmiş taslak varsa kullanıcıya sor."""
        from src.utils.toast_notification import show_warning
        try:
            raw = QSettings().value(self._DRAFT_KEY)
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
                self.refresh_cart_ui()
                self.update_totals()
                cust = data.get("customer", "")
                if cust:
                    idx = self.cmb_customer.findText(cust)
                    if idx >= 0:
                        self.cmb_customer.setCurrentIndex(idx)
                    else:
                        self.cmb_customer.setCurrentText(cust)
            else:
                self._clear_draft()
        except Exception:
            pass
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
        root.setContentsMargins(20, 6, 20, 20)
        root.setSpacing(10)

        self.lbl_customer_state = QLabel('Müşteri seçilmedi')
        self.lbl_currency_state = QLabel('TRY')
        self.lbl_cart_state = QLabel('0 kalem')
        self.lbl_customer_state.hide()
        self.lbl_currency_state.hide()
        self.lbl_cart_state.hide()

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addLayout(self._build_context_column(), 4)
        body.addLayout(self._build_workbench_column(), 5)
        body.addLayout(self._build_summary_column(), 3)
        root.addLayout(body, 1)

    def _build_header(self):
        return QFrame()

    def _build_context_column(self):
        column = QVBoxLayout()
        column.setSpacing(12)

        customer_card, customer_layout = self._panel_card('M\u00fc\u015fteri ve \u0130\u015flem Bilgileri')
        customer_grid = QGridLayout()
        customer_grid.setHorizontalSpacing(12)
        customer_grid.setVerticalSpacing(12)

        self.cmb_customer = QComboBox()
        self.cmb_customer.setEditable(True)
        self.cmb_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_customer.setMinimumHeight(46)
        self.cmb_customer.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self.cmb_customer.currentTextChanged.connect(self._refresh_customer_preview)
        self.cmb_customer.lineEdit().setPlaceholderText('M\u00fc\u015fteri se\u00e7in veya ad yaz\u0131n...')
        self.customer_completer = QCompleter(self.cmb_customer.model(), self.cmb_customer)
        self.customer_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.customer_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.customer_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.cmb_customer.setCompleter(self.customer_completer)

        btn_search_customer = QPushButton('Ara')
        btn_search_customer.setFixedSize(88, 46)
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
        self.date_edit.setFixedHeight(44)
        self.date_edit.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_currency = QComboBox()
        self.cmb_currency.addItems(['TRY - T\u00fcrk Liras\u0131 (TL)', 'USD - Amerikan Dolar\u0131 ($)', 'EUR - Euro (EUR)'])
        self.cmb_currency.setFixedHeight(44)
        self.cmb_currency.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
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

        self.customer_preview = QLabel('M\u00fc\u015fteri se\u00e7ildi\u011finde burada \u00f6zet g\u00f6r\u00fcn\u00fcr. Genel m\u00fc\u015fteri ile devam etmek yerine listeden se\u00e7im yap\u0131n.')
        self.customer_preview.setWordWrap(True)
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
        customer_grid.addWidget(self.customer_preview, 5, 0, 1, 2)
        customer_layout.addLayout(customer_grid)

        column.addWidget(customer_card)
        column.addWidget(self._build_composer_card())
        column.addStretch()
        return column

    def _build_composer_card(self):
        composer_card, composer_layout = self._panel_card('Hizmet/Par\u00e7a Giri\u015f')

        composer_grid = QGridLayout()
        composer_grid.setHorizontalSpacing(12)
        composer_grid.setVerticalSpacing(12)

        self.cmb_service_types = QComboBox()
        self.cmb_service_types.setEditable(True)
        self.cmb_service_types.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_service_types.setMinimumHeight(46)
        self.cmb_service_types.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self._setup_searchable_combo(self.cmb_service_types, 'Hizmet se\u00e7in veya yaz\u0131n...')
        self.cmb_service_types.currentIndexChanged.connect(lambda: self._on_item_selection_change('service'))

        self.cmb_parts = QComboBox()
        self.cmb_parts.setEditable(True)
        self.cmb_parts.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_parts.setMinimumHeight(46)
        self.cmb_parts.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self._setup_searchable_combo(self.cmb_parts, 'Par\u00e7a se\u00e7in veya yaz\u0131n...')
        self.cmb_parts.currentIndexChanged.connect(lambda: self._on_item_selection_change('part'))

        self.inp_qty = QSpinBox()
        self.inp_qty.setRange(1, 9999)
        self.inp_qty.setValue(1)
        self.inp_qty.setFixedHeight(44)
        self.inp_qty.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_qty.valueChanged.connect(self.update_calc_total)

        self.inp_price = QDoubleSpinBox()
        self.inp_price.setRange(0, 999999999)
        self.inp_price.setDecimals(2)
        self.inp_price.setValue(0.0)
        self.inp_price.setFixedHeight(44)
        self.inp_price.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_price.valueChanged.connect(self.update_calc_total)

        self.inp_desc = QComboBox()
        self.inp_desc.setEditable(True)
        self.inp_desc.setFixedHeight(44)
        self.inp_desc.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_desc.lineEdit().setPlaceholderText('Servis notu, cihaz durumu veya stok a\u00e7\u0131klamas\u0131')

        self.lbl_line_total = QLabel(
            f"Sat\u0131r Toplam\u0131: {CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False)}"
        )
        self.lbl_line_total.setStyleSheet(theme_qss('font-size: 14px; font-weight: 900; color: @accent;'))

        self.btn_add_to_cart = QPushButton('Sepete Ekle')
        self.btn_add_to_cart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_to_cart.setFixedHeight(48)
        self.btn_add_to_cart.setStyleSheet(theme_qss(DesignTokens.get_button_qss('success', size='lg')))
        self.btn_add_to_cart.clicked.connect(self.add_to_cart)

        self.btn_bulk = QPushButton('Toplu Se\u00e7im')
        self.btn_bulk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk.setFixedHeight(48)
        self.btn_bulk.setStyleSheet(theme_qss('''
            QPushButton {
                background: @surface_alt;
                color: @text;
                border: 1px solid @accent;
                border-radius: 14px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: @selection_bg;
                color: @selection_text;
                border: 1px solid @selection_bg;
            }
            QPushButton:pressed {
                background: @accent;
                color: @selection_text;
            }
            QPushButton:disabled {
                background: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
            }
        '''))
        self.btn_bulk.clicked.connect(self.open_multi_select_v2)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addWidget(self.btn_add_to_cart)
        action_row.addWidget(self.btn_bulk)

        composer_grid.addWidget(self._field_label('Hizmetler'), 0, 0, 1, 2)
        composer_grid.addWidget(self.cmb_service_types, 1, 0, 1, 2)
        composer_grid.addWidget(self._field_label('Par\u00e7a (\u00dcr\u00fcnler)'), 2, 0, 1, 2)
        composer_grid.addWidget(self.cmb_parts, 3, 0, 1, 2)
        composer_grid.addWidget(self._field_label('Adet'), 4, 0)
        composer_grid.addWidget(self._field_label('Birim Fiyat'), 4, 1)
        composer_grid.addWidget(self.inp_qty, 5, 0)
        composer_grid.addWidget(self.inp_price, 5, 1)
        composer_grid.addWidget(self._field_label('A\u00e7\u0131klama'), 6, 0, 1, 2)
        composer_grid.addWidget(self.inp_desc, 7, 0, 1, 2)
        composer_grid.addWidget(self.lbl_line_total, 8, 0, 1, 2)

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

        self.inp_discount = QDoubleSpinBox()
        self.inp_discount.setRange(0, 999999999)
        self.inp_discount.setDecimals(2)
        self.inp_discount.setFixedHeight(44)
        self.inp_discount.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_discount.valueChanged.connect(self.update_totals)

        self.cmb_vat = QComboBox()
        self.cmb_vat.addItems(['%0', '%1', '%10', '%18', '%20'])
        self.cmb_vat.setCurrentText('%20')
        self.cmb_vat.setFixedHeight(44)
        self.cmb_vat.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self.cmb_vat.currentTextChanged.connect(self.update_totals)

        self.date_edit_transaction = QDateEdit(QDate.currentDate())
        self.date_edit_transaction.setCalendarPopup(True)
        self.date_edit_transaction.setDisplayFormat('dd.MM.yyyy')
        self.date_edit_transaction.setFixedHeight(44)
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
        frame.setStyleSheet(theme_qss('background: @surface; border: 1px solid @border; border-radius: 22px;'))
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

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
        box.setStyleSheet(theme_qss('background: @surface_alt; border: 1px solid @border; border-radius: 16px;'))
        box.setMinimumHeight(72)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss('font-size: 10px; color: @text_muted; font-weight: 800;'))

        value_label = QLabel(value)
        color_map = {
            'primary': '@accent',
            'warning': '@warning',
            'secondary': '@text',
            'success': '@success',
        }
        value_label.setStyleSheet(theme_qss(f"font-size: 15px; font-weight: 900; color: {color_map.get(variant, '@text')};"))

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        box.value_label = value_label
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
        self._clear_draft()
        self.refresh_cart_ui()
        self.update_totals()

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

        self.cart_content_stack.setCurrentWidget(self.cart_table if self.cart_items else self.cart_empty_state)
        self._refresh_header_state()

    def update_calc_total(self):
        total_try = self.inp_qty.value() * self.inp_price.value()
        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        display_total = self._convert_from_try(total_try, currency_code)
        self.lbl_line_total.setText(
            f"Sat\u0131r Toplam\u0131: {CurrencyHelper.format_amount(display_total, db=self.db, currency_code=currency_code)}"
        )

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

        self.inp_price.setSuffix(f" {CurrencyHelper.get_symbol(self.db, currency_code)}")
        self.inp_discount.setSuffix(f" {CurrencyHelper.get_symbol(self.db, currency_code)}")

        self.lbl_subtotal.setText(
            f"Ara Toplam: {CurrencyHelper.format_amount(subtotal, db=self.db, currency_code=currency_code)}"
        )
        if currency_code != 'TRY':
            self.lbl_subtotal.setText(
                "Ara Toplam: "
                f"{CurrencyHelper.format_amount(subtotal, db=self.db, currency_code=currency_code)}"
                f"  |  {CurrencyHelper.format_amount(subtotal_try, db=self.db, currency_code='TRY')}"
            )

        self.lbl_total.setText(CurrencyHelper.format_amount(total, db=self.db, currency_code=currency_code))
        if currency_code != 'TRY':
            self.lbl_total.setText(
                f"{CurrencyHelper.format_amount(total, db=self.db, currency_code=currency_code)}\n"
                f"{CurrencyHelper.format_amount(total_try, db=self.db, currency_code='TRY')}"
            )

        self.stat_subtotal.value_label.setText(
            CurrencyHelper.format_amount(subtotal, db=self.db, currency_code=currency_code)
        )
        self.stat_discount.value_label.setText(
            CurrencyHelper.format_amount(discount, db=self.db, currency_code=currency_code)
        )
        self.stat_vat.value_label.setText(
            CurrencyHelper.format_amount(vat_amount, db=self.db, currency_code=currency_code)
        )
        self.stat_total.value_label.setText(
            CurrencyHelper.format_amount(total, db=self.db, currency_code=currency_code)
        )

        self.refresh_cart_ui()
        self._refresh_header_state()
        return subtotal_try, discount_try, vat_try, total_try, net_try

    def _refresh_customer_preview(self):
        current_index = self.cmb_customer.currentIndex()
        if current_index <= 0:
            self.customer_preview.setText('M\u00fc\u015fteri se\u00e7ildi\u011finde burada \u00f6zet g\u00f6r\u00fcn\u00fcr. Genel m\u00fc\u015fteri ile devam etmek yerine listeden se\u00e7im yap\u0131n.')
            self.lbl_customer_state.setText('M\u00fc\u015fteri se\u00e7ilmedi')
            return

        customer_name = self.cmb_customer.currentText()
        customer_id = self.cmb_customer.currentData()
        preview_parts = [f'Se\u00e7ili m\u00fc\u015fteri: {customer_name}']
        if customer_id:
            preview_parts.append(f'Kay\u0131t ID: {customer_id}')
        preview_parts.append('Ayn\u0131 ekrandan servis, tahsilat ve proforma ak\u0131\u015flar\u0131n\u0131 s\u00fcrd\u00fcrebilirsiniz.')
        self.customer_preview.setText(' | '.join(preview_parts))
        self.lbl_customer_state.setText(customer_name[:28])

    def _handle_currency_change(self, currency_text):
        self.on_currency_changed(currency_text)
        self.update_calc_total()
        self.update_totals()
        self._refresh_header_state()

    def _refresh_header_state(self):
        currency_code = self._parse_currency_code(self.cmb_currency.currentText())
        self.lbl_currency_state.setText(currency_code)
        self.lbl_cart_state.setText(f'{len(self.cart_items)} kalem')
        if self.cmb_customer.currentIndex() <= 0:
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

    def _is_combo_auto_popup_enabled(self):
        """Ayarlardan combobox otomatik popup açma durumunu kontrol et."""
        try:
            return self.db.get_setting('combo_auto_popup', '0') == '1'
        except Exception:
            return False

    def eventFilter(self, source, event):
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
