# -*- coding: utf-8 -*-
# _stock_list_tab.py
# Liste sekmesi işlemleri

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QStackedWidget,
    QLabel,
)
from PyQt6.QtCore import Qt, QTimer
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.design_system import DesignTokens, enable_row_hover
from src.ui.widgets.empty_state import EmptyState


class PurchasePriceHeader(QHeaderView):
    """Header that keeps the sensitive-price column out of table sorting."""

    def __init__(self, blocked_section_getter, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._blocked_section_getter = blocked_section_getter

    def mousePressEvent(self, event):
        if self.logicalIndexAt(event.position().toPoint()) == self._blocked_section_getter():
            event.accept()
            return
        super().mousePressEvent(event)


class StockListTabMixin:
    """Liste sekmesi için mixin sınıfı."""

    def setup_list_tab(self):
        layout = QVBoxLayout(self.tab_list)

        self.cat_container = QWidget()
        self.cat_layout = QHBoxLayout(self.cat_container)
        scroll = QScrollArea()
        scroll.setFixedHeight(60)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cat_container)
        layout.addWidget(scroll)

        filter_bar = QFrame()
        fb_layout = QHBoxLayout(filter_bar)
        filter_bar.setStyleSheet(
            theme_qss(
                "background: @surface; border-radius: 12px; border: 1px solid @border;"
            )
        )

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("🔍 Ürün adı veya barkod ile ara...")
        self.search_inp.setMinimumWidth(350)
        self.search_inp.setFixedHeight(42)
        self.search_inp.textChanged.connect(self.on_stock_search_changed)
        fb_layout.addWidget(self.search_inp)


        fb_layout.addStretch()

        self.btn_critical = QPushButton("⚠️ Kritik Stoklar")
        self.btn_critical.setCheckable(True)
        self.btn_critical.setMinimumWidth(120)
        self.btn_critical.setFixedHeight(40)
        self.btn_critical.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_critical.setStyleSheet(
            theme_qss(DesignTokens.get_button_qss("warning", size="sm"))
        )
        self.btn_critical.clicked.connect(self.toggle_critical_filter)
        fb_layout.addWidget(self.btn_critical)

        def make_tool_button(icon, tooltip):
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.setAccessibleName(tooltip)
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                theme_qss("""
                    QPushButton {
                        background: @surface_alt;
                        border: 1px solid @border;
                        border-radius: 8px;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background: @hover_bg;
                        border-color: @accent;
                    }
                """)
            )
            return btn

        self._purchase_prices_all_visible = True
        self._revealed_purchase_price_ids = set()
        self.btn_purchase_price_visibility = make_tool_button(
            "\U0001F441", "Al\u0131\u015f fiyatlarini goster"
        )
        self.btn_purchase_price_visibility.clicked.connect(
            self.toggle_purchase_price_visibility
        )
        fb_layout.addWidget(self.btn_purchase_price_visibility)

        # İçe/Dışa Aktar Butonları
        self.btn_import = make_tool_button("📥", "Akıllı İçe Aktar")
        self.btn_import.clicked.connect(self.open_smart_stock_import)
        fb_layout.addWidget(self.btn_import)

        self.btn_export = make_tool_button("📤", "Dışa Aktar")
        self.btn_export.clicked.connect(self.export_to_excel)
        fb_layout.addWidget(self.btn_export)

        self.btn_pdf = make_tool_button("📄", "PDF Olarak Kaydet")
        self.btn_pdf.clicked.connect(self.export_active_tab_to_pdf)
        fb_layout.addWidget(self.btn_pdf)

        self.btn_print = make_tool_button("🖨️", "Yazdır")
        self.btn_print.clicked.connect(self.print_active_tab)
        fb_layout.addWidget(self.btn_print)

        # Yeni ürün ekleme butonu
        btn_add = QPushButton("➕ Yeni Ürün Ekle")
        btn_add.setFixedSize(160, 40)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(
            theme_qss(DesignTokens.get_button_qss("primary", size="sm"))
        )
        btn_add.clicked.connect(lambda: self.open_add_stock_dialog(None))
        fb_layout.addWidget(btn_add)
        layout.addWidget(filter_bar)

        self.table_stock = QTableWidget()
        self.table_stock.setHorizontalHeader(
            PurchasePriceHeader(self._purchase_price_column, self.table_stock)
        )

        # Plugin'den stok kolonlarını al
        if self.is_automotive:
            self.table_stock.setColumnCount(18)
            headers = [
                "ID",
                "Stok Kodu",
                "Parça Adı",
                "Marka",
                "Kategori",
                "OEM",
                "Muadil",
                "Araç Marka",
                "Araç Model",
                "Uyumlu Araç / Motor",
                "Konum",
                "Tedarikçi",
                "Raf",
                "Stok",
                "Alış 👁️",
                "Satış",
                "PB",
                "Limit",
            ]
            self._stock_column_map = None
        elif self.sector_manager:
            stock_columns = self.sector_manager.get_stock_columns()
            self.table_stock.setColumnCount(len(stock_columns))
            headers = [col["title"] if col["title"] != "Alış" else "Alış 👁️" for col in stock_columns]
            self._stock_column_map = {
                col["name"]: idx for idx, col in enumerate(stock_columns)
            }
        else:
            # Fallback: eski hardcoded yapı
            self.table_stock.setColumnCount(14 if self.is_automotive else 10)
            if self.is_automotive:
                headers = [
                    "ID",
                    "Barkod",
                    "Ürün Adı",
                    "Marka",
                    "Kategori",
                    "OEM",
                    "Muadil",
                    "Uyumlu Modeller",
                    "Raf",
                    "Stok",
                    "Alış 👁️",
                    "Satış",
                    "PB",
                    "Limit",
                ]
            else:
                headers = [
                    "ID",
                    "Barkod",
                    "Ürün Adı",
                    "Marka",
                    "Kategori",
                    "Stok",
                    "Alış 👁️",
                    "Satış",
                    "PB",
                    "Limit",
                ]
            self._stock_column_map = None

        if headers:
            headers[0] = "S.No"
            purchase_price_column = self._purchase_price_column()
            if 0 <= purchase_price_column < len(headers):
                headers[purchase_price_column] = "Al\u0131\u015f Fiyat\u0131"
        self.table_stock.setHorizontalHeaderLabels(headers)
        self.table_stock.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table_stock.horizontalHeader().sectionClicked.connect(
            self._on_stock_header_section_clicked
        )
        self.table_stock.verticalHeader().setVisible(False)
        self.table_stock.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_stock.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_stock.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_stock.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )
        self.table_stock.setMouseTracking(True)
        self.table_stock.cellEntered.connect(self._on_stock_cell_entered)
        self.table_stock.setStyleSheet(
            theme_qss(
                DesignTokens.get_table_qss()
                + """
            QTableWidget::item:hover {
                background-color: transparent;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
                font-weight: 600;
            }
        """
            )
        )
        enable_row_hover(self.table_stock, tc("selection_bg"), tc("selection_text"))
        self.table_stock.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_stock.customContextMenuRequested.connect(
            self.show_stock_context_menu
        )
        self.table_stock.itemDoubleClicked.connect(self.on_stock_double_click)
        self.table_stock.setSortingEnabled(True)


        self.stock_content_stack = QStackedWidget()
        self.stock_content_stack.addWidget(self.table_stock)
        self.stock_empty_state = EmptyState(
            icon="📦",
            title="Ürün Yok",
            message="Envanter boş veya kriterlere uyan ürün bulunamadı.",
        )
        self.stock_content_stack.addWidget(self.stock_empty_state)

        # Loading State
        self.loading_label = QLabel("Yükleniyor...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(
            theme_qss("font-size: 18px; color: @text_muted;")
        )
        self.stock_content_stack.addWidget(self.loading_label)

        layout.addWidget(self.stock_content_stack)

        # Pagination Controls
        self._setup_pagination_ui(layout)

    def _load_categories_fresh(self):
        all_label = "T\u00fcm\u00fc"
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT category
                FROM parts
                WHERE COALESCE(is_deleted, 0) = 0
                  AND TRIM(COALESCE(category, '')) <> ''
                ORDER BY category COLLATE NOCASE
                """
            )
            self._raw_categories = [
                str(row[0]).strip() for row in (cursor.fetchall() or []) if row[0]
            ]
        except Exception:
            self._raw_categories = []

        while self.cat_layout.count():
            item = self.cat_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if bool(getattr(self, "is_automotive", False)):
            categories = [all_label] + list(self._raw_categories)
        else:
            categories = [all_label] + list(self.CATEGORY_GROUPS.keys())
            grouped_values = {
                self._normalize_category(value)
                for values in self.CATEGORY_GROUPS.values()
                for value in values
            }
            categories.extend(
                raw
                for raw in self._raw_categories
                if self._normalize_category(raw) not in grouped_values
            )

        seen = set()
        for category in categories:
            key = self._normalize_category(category)
            if key in seen:
                continue
            seen.add(key)
            button = QPushButton(category)
            button.setCheckable(True)
            button.setChecked(category == self.selected_category)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                theme_qss(self._cat_style(category == self.selected_category))
            )
            button.clicked.connect(
                lambda _checked=False, value=category: self._select_stock_category(
                    value
                )
            )
            self.cat_layout.addWidget(button)
        self.cat_layout.addStretch()

    def _select_stock_category(self, category):
        if category == self.selected_category:
            return
        self.selected_category = category
        self.current_page = 0
        for index in range(self.cat_layout.count()):
            widget = self.cat_layout.itemAt(index).widget()
            if isinstance(widget, QPushButton):
                active = widget.text() == category
                widget.setChecked(active)
                widget.setStyleSheet(theme_qss(self._cat_style(active)))
        self.reload_data()

    def _setup_pagination_ui(self, parent_layout):
        pag_container = QWidget()
        pag_layout = QHBoxLayout(pag_container)
        pag_layout.setContentsMargins(0, 0, 0, 0)
        pag_layout.setSpacing(10)

        page_button_qss = theme_qss("""
            QPushButton {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 9px;
                font-weight: 700;
            }
            QPushButton:hover:enabled {
                background: @surface_alt;
                border-color: @accent;
                color: @text;
            }
            QPushButton:disabled {
                background: @disabled_bg;
                color: @disabled_text;
                border: 1px solid @border;
            }
        """)

        self.btn_prev = QPushButton("◀ Önceki")
        self.btn_prev.setFixedSize(100, 36)
        self.btn_prev.setStyleSheet(page_button_qss)
        self.btn_prev.clicked.connect(self.prev_page)

        self.lbl_page_info = QLabel("Sayfa 1 / 1")
        self.lbl_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page_info.setMinimumWidth(90)
        self.lbl_page_info.setStyleSheet(
            theme_qss(
                "QLabel { font-weight: 800; color: @text; background: @surface; "
                "border: 1px solid @border; border-radius: 9px; padding: 8px 12px; }"
            )
        )

        self.btn_next = QPushButton("Sonraki ▶")
        self.btn_next.setFixedSize(100, 36)
        self.btn_next.setStyleSheet(page_button_qss)
        self.btn_next.clicked.connect(self.next_page)

        pag_layout.addStretch()
        pag_layout.addWidget(self.btn_prev)
        pag_layout.addWidget(self.lbl_page_info)
        pag_layout.addWidget(self.btn_next)
        pag_layout.addStretch()

        parent_layout.addWidget(pag_container)

    def _update_pagination_controls(self):
        total = max(0, int(getattr(self, "total_count", 0) or 0))
        limit = max(1, int(getattr(self, "page_limit", 50) or 50))
        page_count = max(1, (total + limit - 1) // limit)
        current = max(0, min(int(getattr(self, "current_page", 0) or 0), page_count - 1))
        self.current_page = current
        self.lbl_page_info.setText(f"Sayfa {current + 1} / {page_count}")
        self.btn_prev.setEnabled(current > 0)
        self.btn_next.setEnabled(current + 1 < page_count)

    def prev_page(self):
        if int(getattr(self, "current_page", 0) or 0) <= 0:
            return
        self.current_page -= 1
        self.reload_data()

    def next_page(self):
        total = max(0, int(getattr(self, "total_count", 0) or 0))
        limit = max(1, int(getattr(self, "page_limit", 50) or 50))
        page_count = max(1, (total + limit - 1) // limit)
        if int(getattr(self, "current_page", 0) or 0) + 1 >= page_count:
            return
        self.current_page += 1
        self.reload_data()

    def _fill_table(self, parts):
        self.table_stock.setSortingEnabled(False)
        self.table_stock.clearSelection()
        self.table_stock.setRowCount(0)
        self.table_stock.setUpdatesEnabled(False)

        for i, p in enumerate(parts):
            self.table_stock.insertRow(i)

            def _get(key, default="-"):
                try:
                    return p[key] if p[key] is not None else default
                except Exception:
                    return default

            part_id = _get("id", 0)
            display_no = (self.current_page * self.page_limit) + i + 1
            item_id = QTableWidgetItem()
            item_id.setData(Qt.ItemDataRole.DisplayRole, display_no)
            item_id.setData(Qt.ItemDataRole.EditRole, display_no)
            item_id.setData(Qt.ItemDataRole.UserRole, part_id)
            item_code = QTableWidgetItem(str(_get("code", "-")))
            item_name = QTableWidgetItem(str(_get("name", "Adsız")))
            item_cat = QTableWidgetItem(str(_get("category", "Genel")))

            try:
                item_id.setData(Qt.ItemDataRole.UserRole, int(part_id))
            except Exception:
                item_id.setData(Qt.ItemDataRole.UserRole, part_id)

            try:
                stock_val = float(_get("stock", 0) or 0)
            except Exception:
                stock_val = 0.0
            try:
                limit = float(_get("min_stock", 5) or 5)
            except Exception:
                limit = 5.0

            s_item = QTableWidgetItem(str(int(stock_val)))
            s_item.setData(Qt.ItemDataRole.EditRole, int(stock_val))
            if stock_val <= 0:
                s_item.setForeground(qc("danger"))
            elif stock_val <= limit:
                s_item.setForeground(qc("warning"))
            else:
                s_item.setForeground(qc("success"))

            item_curr = str(_get("currency", "TRY") or "TRY").upper()
            try:
                pur_p = float(_get("purchase_price", 0) or 0)
            except Exception:
                pur_p = 0.0
            try:
                sel_p = float(_get("price", 0) or 0)
            except Exception:
                sel_p = 0.0

            p_in = QTableWidgetItem()
            p_in.setData(Qt.ItemDataRole.UserRole, pur_p)
            p_in.setData(Qt.ItemDataRole.EditRole, pur_p)
            p_out = QTableWidgetItem(f"{sel_p:,.2f}")
            p_out.setData(Qt.ItemDataRole.EditRole, sel_p)
            p_curr = QTableWidgetItem(item_curr)
            p_lim = QTableWidgetItem(str(int(limit)))
            p_lim.setData(Qt.ItemDataRole.EditRole, int(limit))

            item_brand = QTableWidgetItem(str(_get("brand", "") or ""))
            compatible_models_text = str(_get("compatible_models", "") or "")
            automotive_meta = self._extract_automotive_meta(
                _get("description", "") or ""
            )
            vehicle_brand_text = automotive_meta.get("vehicle_brand", "")
            vehicle_model_text = automotive_meta.get("vehicle_model", "")
            position_text = automotive_meta.get("position", "")
            supplier_text = automotive_meta.get("supplier", "")
            row_items = {
                "id": item_id,
                "code": item_code,
                "name": item_name,
                "part_name": item_name,
                "brand": item_brand,
                "category": item_cat,
                "oem_code": QTableWidgetItem(str(_get("oem_code", "") or "")),
                "oem_no": QTableWidgetItem(str(_get("oem_code", "") or "")),
                "equivalent_code": QTableWidgetItem(
                    str(_get("equivalent_code", "") or "")
                ),
                "cross_ref": QTableWidgetItem(str(_get("equivalent_code", "") or "")),
                "compatible_models": QTableWidgetItem(compatible_models_text),
                "vehicle_brand": QTableWidgetItem(vehicle_brand_text),
                "vehicle_model": QTableWidgetItem(vehicle_model_text),
                "position": QTableWidgetItem(position_text),
                "supplier": QTableWidgetItem(supplier_text),
                "shelf_number": QTableWidgetItem(str(_get("shelf_number", "") or "")),
                "location": QTableWidgetItem(str(_get("shelf_number", "") or "")),
                "stock": s_item,
                "quantity": s_item.clone(),
                "purchase_price": p_in,
                "price": p_out,
                "sale_price": p_out.clone(),
                "currency": p_curr,
                "unit": p_curr.clone(),
                "min_stock": p_lim,
            }
            if self._stock_column_map:
                for col_name, col_idx in self._stock_column_map.items():
                    item = row_items.get(col_name)
                    if item is not None:
                        self.table_stock.setItem(i, col_idx, item)
            else:
                default_columns = [
                    "id",
                    "code",
                    "name",
                    "brand",
                    "category",
                    "stock",
                    "purchase_price",
                    "price",
                    "currency",
                    "min_stock",
                ]
                if self.is_automotive:
                    default_columns = [
                        "id",
                        "code",
                        "name",
                        "brand",
                        "category",
                        "oem_code",
                        "equivalent_code",
                        "vehicle_brand",
                        "vehicle_model",
                        "compatible_models",
                        "position",
                        "supplier",
                        "shelf_number",
                        "stock",
                        "purchase_price",
                        "price",
                        "currency",
                        "min_stock",
                    ]
                for col_idx, col_name in enumerate(default_columns):
                    self.table_stock.setItem(i, col_idx, row_items[col_name])

            for col in range(self.table_stock.columnCount()):
                it = self.table_stock.item(i, col)
                if it:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self._update_purchase_price_cell(i)

        self._renumber_stock_rows()
        self.table_stock.setSortingEnabled(True)
        self.table_stock.setUpdatesEnabled(True)
        self.table_stock.viewport().update()


    def _renumber_stock_rows(self):
        for i in range(self.table_stock.rowCount()):
            item = self.table_stock.item(i, 0)
            if item:
                display_no = (self.current_page * self.page_limit) + i + 1
                item.setText(str(display_no))

    def _on_stock_header_section_clicked(self, logical_index):
        # The purchase-price section is consumed by PurchasePriceHeader.
        # Other headers continue to use the table's built-in sorting.
        return

    def toggle_purchase_price_visibility(self):
        all_visible = bool(getattr(self, "_purchase_prices_all_visible", False))
        self._purchase_prices_all_visible = not all_visible
        self._revealed_purchase_price_ids = set()
        self._refresh_all_purchase_price_cells()

        button = getattr(self, "btn_purchase_price_visibility", None)
        if button:
            visible = self._purchase_prices_all_visible
            button.setToolTip(
                "Al\u0131\u015f fiyatlarini gizle"
                if visible
                else "Al\u0131\u015f fiyatlarini goster"
            )
            button.setAccessibleName(button.toolTip())

    def _on_stock_cell_entered(self, row, col):
        pass

    def _on_stock_cell_clicked_toggle_purchase_price(self, row, col):
        # Individual cells no longer toggle price visibility.
        # The toolbar eye button controls every purchase price consistently.
        return

    def _update_purchase_price_cell(self, row):
        target_col = self._purchase_price_column()
        item = self.table_stock.item(row, target_col)
        if item:
            part_id = self._stock_part_id_from_row(row)
            visible = (
                bool(getattr(self, "_purchase_prices_all_visible", False))
                or part_id in set(getattr(self, "_revealed_purchase_price_ids", set()))
            )
            purchase_price = float(item.data(Qt.ItemDataRole.UserRole) or 0.0)
            item.setData(Qt.ItemDataRole.UserRole + 99, not visible)
            item.setText(f"{purchase_price:,.2f}" if visible else "***")

    def _purchase_price_column(self):
        classic_col = 14 if bool(getattr(self, "is_automotive", False)) else 6
        column_map = getattr(self, "_stock_column_map", None)
        if column_map:
            return int(column_map.get("purchase_price", classic_col))
        return classic_col

    def _stock_part_id_from_row(self, row):
        item = self.table_stock.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _refresh_all_purchase_price_cells(self):
        for row in range(self.table_stock.rowCount()):
            self._update_purchase_price_cell(row)
