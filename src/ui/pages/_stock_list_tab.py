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
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.design_system import DesignTokens, enable_row_hover
from src.ui.widgets.empty_state import EmptyState


class PurchasePriceHeader(QHeaderView):
    """Header that keeps the sensitive-price column out of table sorting."""

    def __init__(self, blocked_section_getter, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._blocked_section_getter = blocked_section_getter
        self._fit_weights = None
        self._fitting_sections = False

    def set_fit_weights(self, weights):
        self._fit_weights = tuple(max(1, int(weight)) for weight in weights)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._fit_weights or self._fitting_sections:
            return
        available = self.viewport().width()
        base_total = sum(self._fit_weights)
        if available <= 0:
            return
        if available < base_total:
            return
        self._fitting_sections = True
        try:
            widths = [max(40, round(available * weight / base_total)) for weight in self._fit_weights]
            widths[-1] = max(40, available - sum(widths[:-1]))
            for section, width in enumerate(widths):
                self.resizeSection(section, width)
        finally:
            self._fitting_sections = False

    def mousePressEvent(self, event):
        if self.logicalIndexAt(event.position().toPoint()) == self._blocked_section_getter():
            event.accept()
            return
        super().mousePressEvent(event)


class StockQuantityItem(QTableWidgetItem):
    def __lt__(self, other):
        return float(self.data(Qt.ItemDataRole.UserRole + 1) or 0) < float(
            other.data(Qt.ItemDataRole.UserRole + 1) or 0
        )


class StockReferenceCellDelegate(QStyledItemDelegate):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind

    def paint(self, painter, option, index):
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        value = item_option.text
        item_option.text = ""
        option.widget.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, item_option, painter, option.widget
        )
        if not value:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = option.rect.adjusted(5, 0, -5, 0)
        font = QFont(option.font)
        font.setPointSize(9)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text = metrics.elidedText(value, Qt.TextElideMode.ElideRight, max(20, bounds.width() - 16))
        if self.kind == "quantity":
            foreground = index.data(Qt.ItemDataRole.ForegroundRole)
            color = foreground.color() if foreground and foreground.style() != Qt.BrushStyle.NoBrush else QColor("#34d399")
            fill = QColor(color)
            fill.setAlpha(28)
            painter.setPen(QColor(color.red(), color.green(), color.blue(), 110))
            painter.setBrush(fill)
        elif self.kind == "code":
            color = QColor("#22d3ee")
            painter.setPen(QColor(8, 145, 178, 130))
            painter.setBrush(QColor(8, 145, 178, 28))
        else:
            color = QColor("#cbd5e1")
            painter.setPen(QColor("#334155"))
            painter.setBrush(QColor(30, 41, 59, 220))
        pill = bounds.adjusted(5, (bounds.height() - 30) // 2, -5, -((bounds.height() - 30) // 2))
        pill.setHeight(min(30, bounds.height() - 8))
        painter.drawRoundedRect(pill, 9, 9)
        painter.setPen(color)
        painter.drawText(pill.adjusted(7, 0, -7, 0), Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class StockProductDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        title = item_option.text
        subtitle = str(index.data(Qt.ItemDataRole.UserRole + 1) or "")
        if subtitle.strip() == title.strip():
            subtitle = ""
        item_option.text = ""
        option.widget.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, item_option, painter, option.widget
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        content = option.rect.adjusted(12, 12, -10, -10)
        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(option.palette.color(option.palette.ColorRole.Text))
        title_metrics = painter.fontMetrics()
        title_rect = content.adjusted(0, 0, 0, -max(18, content.height() // 3))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, title_rect.width()))
        if subtitle:
            sub_font = QFont(option.font)
            sub_font.setPointSize(8)
            painter.setFont(sub_font)
            painter.setPen(QColor("#8292aa"))
            sub_metrics = painter.fontMetrics()
            sub_rect = content.adjusted(0, content.height() // 3, 0, 0)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sub_metrics.elidedText(subtitle, Qt.TextElideMode.ElideRight, sub_rect.width()))
        painter.restore()


class StockListTabMixin:
    """Liste sekmesi için mixin sınıfı."""

    def setup_list_tab(self):
        layout = QVBoxLayout(self.tab_list)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(17)

        self.cat_container = QWidget()
        self.cat_layout = QHBoxLayout(self.cat_container)
        self.cat_layout.setContentsMargins(10, 4, 10, 4)
        self.cat_layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setFixedHeight(54)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(theme_qss("QScrollArea { background: @surface; border: 1px solid @border; border-radius: 8px; }"))
        scroll.setWidget(self.cat_container)
        layout.addWidget(scroll)

        filter_bar = QFrame()
        filter_bar.setFixedHeight(68)
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(12, 8, 12, 8)
        fb_layout.setSpacing(8)
        filter_bar.setStyleSheet(
            theme_qss(
                "background: @surface; border-radius: 12px; border: 1px solid @border;"
            )
        )

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("🔍 Ürün adı veya barkod ile ara...")
        self.search_inp.setMinimumWidth(220)
        self.search_inp.setFixedHeight(40)
        self.search_inp.textChanged.connect(self.on_stock_search_changed)
        fb_layout.addWidget(self.search_inp)

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
            self.table_stock.setColumnCount(14 if self.is_automotive else 12)
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
                    "S.No",
                    "Stok Kodu",
                    "Par\u00e7a / \u00dcr\u00fcn Tan\u0131m\u0131",
                    "Kategori",
                    "Miktar & Durum",
                    "Birim",
                    "Al\u0131\u015f Fiyat\u0131",
                    "Sat\u0131\u015f Fiyat\u0131",
                    "K\u00e2r (%)",
                    "Raf Yeri",
                    "Min. Stok",
                    "\u0130\u015flemler",
                ]
                self._stock_column_map = {
                    "id": 0,
                    "code": 1,
                    "name": 2,
                    "category": 3,
                    "stock": 4,
                    "unit": 5,
                    "currency": 5,
                    "purchase_price": 6,
                    "price": 7,
                    "profit": 8,
                    "shelf_number": 9,
                    "min_stock": 10,
                }
            if self.is_automotive:
                self._stock_column_map = None

        if headers:
            headers[0] = "S.No"
            purchase_price_column = self._purchase_price_column()
            if 0 <= purchase_price_column < len(headers):
                headers[purchase_price_column] = "Al\u0131\u015f Fiyat\u0131"
        self.table_stock.setHorizontalHeaderLabels(headers)
        if len(headers) == 12 and headers[2] == "Par\u00e7a / \u00dcr\u00fcn Tan\u0131m\u0131":
            self.table_stock.setItemDelegateForColumn(1, StockReferenceCellDelegate("code", self.table_stock))
            self.table_stock.setItemDelegateForColumn(2, StockProductDelegate(self.table_stock))
            self.table_stock.setItemDelegateForColumn(3, StockReferenceCellDelegate("category", self.table_stock))
            self.table_stock.setItemDelegateForColumn(4, StockReferenceCellDelegate("quantity", self.table_stock))
        self.table_stock.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table_stock.horizontalHeader().setStretchLastSection(True)
        self.table_stock.horizontalHeader().setMinimumSectionSize(40)
        self.table_stock.horizontalHeader().setFixedHeight(72)
        reference_widths = [44, 100, 210, 100, 128, 58, 100, 100, 86, 90, 80, 100]
        for column in range(len(headers)):
            width = reference_widths[column] if len(headers) in (10, 12) else 120
            self.table_stock.setColumnWidth(column, width)
        if len(headers) in (10, 12):
            self.table_stock.horizontalHeader().set_fit_weights(reference_widths[:len(headers)])
        self.table_stock.verticalHeader().setDefaultSectionSize(
            110 if len(headers) == 12 else 42
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

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM parts
                WHERE COALESCE(is_deleted, 0) = 0
                """
            )
            self._active_part_count = int(cursor.fetchone()[0] or 0)
        except Exception:
            self._active_part_count = 0

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
            if category == all_label:
                button = QPushButton(f"{category} ({self._active_part_count})")
            else:
                button = QPushButton(category)
            button.setProperty('stock_category_key', category)
            button.setCheckable(True)
            button.setChecked(category == self.selected_category)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                theme_qss(self._cat_style(category == self.selected_category))
            )
            button.clicked.connect(
                lambda _checked=False, value=category: self._select_stock_category(value)
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
                active = widget.property('stock_category_key') == category
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
            item_name.setData(Qt.ItemDataRole.UserRole + 1, str(_get("description", "") or ""))
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

            unit_text = str(_get("unit", "Adet") or "Adet")
            s_item = StockQuantityItem(f"{int(stock_val)} {unit_text}")
            s_item.setData(Qt.ItemDataRole.UserRole + 1, stock_val)
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
                "profit": QTableWidgetItem(
                    f"{((sel_p - pur_p) / pur_p * 100):+.1f}%" if pur_p > 0 else "--"
                ),
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
                    "category",
                    "stock",
                    "unit",
                    "purchase_price",
                    "price",
                    "profit",
                    "shelf_number",
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

            if self.table_stock.columnCount() == 12:
                action_cell = QWidget()
                action_layout = QHBoxLayout(action_cell)
                action_layout.setContentsMargins(4, 0, 4, 0)
                action_layout.setSpacing(8)
                edit_action = QPushButton("\u270e")
                edit_action.setToolTip("\u00dcr\u00fcn\u00fc d\u00fczenle")
                edit_action.setAccessibleName("\u00dcr\u00fcn\u00fc d\u00fczenle")
                edit_action.setFixedSize(28, 30)
                edit_action.setStyleSheet(theme_qss(
                    "QPushButton { color: @text_muted; background: transparent; border: 0; border-radius: 5px; font-size: 16px; }"
                    "QPushButton:hover { color: @accent; background: @surface_alt; }"
                ))
                edit_action.clicked.connect(
                    lambda checked=False, part_id=item_id: self.open_add_stock_dialog(part_id)
                )
                movement_action = QPushButton("\u21c4")
                movement_action.setToolTip("Stok Hareketi")
                movement_action.setAccessibleName("Stok Hareketi")
                movement_action.setFixedSize(28, 30)
                movement_action.setStyleSheet(theme_qss(
                    "QPushButton { color: @text_muted; background: transparent; border: 0; border-radius: 5px; font-size: 17px; }"
                    "QPushButton:hover { color: @accent; background: @surface_alt; }"
                ))
                movement_action.clicked.connect(
                    lambda checked=False, part_id=item_id, name=item_name.text(): self.update_stock_amount(part_id, name)
                )
                action_layout.addStretch(1)
                action_layout.addWidget(edit_action)
                action_layout.addWidget(movement_action)
                action_layout.addStretch(1)
                self.table_stock.setCellWidget(i, 11, action_cell)

            for col in range(self.table_stock.columnCount()):
                it = self.table_stock.item(i, col)
                if it:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if col != self._purchase_price_column():
                        it.setToolTip(it.text())

            if self.table_stock.columnCount() == 12:
                for price_column in (6, 7):
                    price_item = self.table_stock.item(i, price_column)
                    if price_item:
                        price_item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )

            name_column = (self._stock_column_map or {}).get('name', 2)
            name_item = self.table_stock.item(i, name_column)
            if name_item:
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

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
        if int(logical_index) == self._purchase_price_column():
            self.toggle_purchase_price_visibility()

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
        if int(col) != self._purchase_price_column():
            return
        part_id = self._stock_part_id_from_row(row)
        if part_id is None:
            return
        revealed = set(getattr(self, "_revealed_purchase_price_ids", set()))
        if part_id in revealed:
            revealed.remove(part_id)
        else:
            revealed.add(part_id)
        self._revealed_purchase_price_ids = revealed
        self._update_purchase_price_cell(row)

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
