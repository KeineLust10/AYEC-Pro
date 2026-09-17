# -*- coding: utf-8 -*-

"""
Hizmet Tanımları Sayfası
- Inline form kaldırıldı
- Modern Add/Edit dialog akışı
- Tekli/çoklu silme
- Excel içe/dışa aktarma (TR sayı parse esnek)
"""

import re
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
)



from src.ui.dialogs.add_service_definition_dialog import AddServiceDefinitionDialog
from src.ui.dialogs.service_import_preview_dialog import ServiceImportPreviewDialog
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.audit_logger import get_audit_logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.design_system import DesignTokens
from src.utils.system_config import SystemConfig
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_info, show_success, show_warning
from src.ui.widgets.loading_overlay import LoadingOverlay
# ServiceParseProcessWorker (spawn-process) kaldırıldı; ServiceParseWorker (QThread) kullanılıyor


class ServiceParseWorker(QThread):
    """parse_file() işlemini arka planda çalıştırır."""
    finished = pyqtSignal(dict, bool)  # (parse_result, is_auto)
    error = pyqtSignal(str)

    def __init__(self, path, is_auto):
        super().__init__()
        self.path = path
        self.is_auto = is_auto

    def run(self):
        try:
            from src.utils.stock_import_parser import StockImportParser
            result = StockImportParser.parse_file(self.path)
            self.finished.emit(result, self.is_auto)
        except Exception as e:
            self.error.emit(str(e))


class ServicesPage(QWidget):
    PAGE_SIZE = 14

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.audit_logger = get_audit_logger(db)
        self._multi_select = False
        self._selected_id: Optional[int] = None
        self.current_page = 1
        self.total_count = 0
        self._build_ui()
        QTimer.singleShot(100, self.load_services)
        # Modern loading overlay
        self._svc_loading_overlay = LoadingOverlay(self, text="Dosya analiz ediliyor...")

    def _is_automotive(self) -> bool:
        """Aktif sektörün otomotiv olup olmadığını döner."""
        try:
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _build_ui(self):
        is_auto = self._is_automotive()
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(16)
        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        if is_auto:
            title_text = "🚗 Servis ve Fiyat Yönetimi"
            sub_text   = "Otomotiv servis hizmetleri — Tablodan seçip işlem uygulayın."
        else:
            title_text = "⚙️ Hizmet ve Ücret Yönetimi"
            sub_text   = "Hizmet ekleme/düzenleme dialog ile yapılır. Tablodan seçip işlem uygulayın."

        title = QLabel(title_text)
        title.setStyleSheet(theme_qss("font-size: 25px; font-weight: 800; color: @text;"))
        sub = QLabel(sub_text)
        sub.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()
        action_bar = QFrame()
        action_bar.setStyleSheet(theme_qss("background: transparent; border: none;"))
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        def _mkbtn(icon, tooltip):
            b = QPushButton(icon)
            b.setFixedSize(40, 40)
            b.setToolTip(tooltip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                theme_qss(DesignTokens.get_icon_btn_qss())
            )
            return b

        self.btn_multi = _mkbtn("\U0001f532", "\u00c7oklu Se\u00e7im")
        self.btn_multi.setCheckable(True)
        self.btn_multi.setStyleSheet(
            theme_qss(
                DesignTokens.get_icon_btn_qss()
                + "QPushButton:checked { background: @accent; color: @selection_text; }"
            )
        )
        self.btn_multi.clicked.connect(self.toggle_multiselect)

        new_icon = "\U0001f697" if is_auto else "\u2728"
        new_tip  = "Yeni Servis Ekle" if is_auto else "Yeni Hizmet Ekle"
        btn_new = _mkbtn(new_icon, new_tip)
        btn_new.clicked.connect(self.open_add_dialog)

        self.btn_edit = _mkbtn("\U0001f4dd", "Se\u00e7ileni D\u00fczenle")
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        self.btn_edit.setEnabled(False)

        self.btn_delete = _mkbtn("\U0001f5d1\ufe0f", "Se\u00e7ileni Sil")
        self.btn_delete.clicked.connect(self.delete_selected_action)
        self.btn_delete.setEnabled(False)

        btn_import_smart = _mkbtn("\U0001f9e0", "Ak\u0131ll\u0131 \u0130\u00e7e Aktar")
        btn_import_smart.clicked.connect(self.smart_import)

        btn_import = _mkbtn("\U0001f4e5", "Excel \u0130\u00e7e Aktar")
        btn_import.clicked.connect(self.import_from_csv)

        btn_export = _mkbtn("\U0001f4e4", "Excel D\u0131\u015fa Aktar")
        btn_export.clicked.connect(self.export_to_csv)

        for b in (self.btn_multi, btn_new, self.btn_edit, self.btn_delete,
                  btn_import_smart, btn_import, btn_export):
            action_layout.addWidget(b)

        header.addWidget(action_bar, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        tools_card = QFrame()
        tools_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        tools_l = QHBoxLayout(tools_card)
        tools_l.setContentsMargins(14, 12, 14, 12)
        tools_l.setSpacing(10)
        self.search = QLineEdit()
        if is_auto:
            self.search.setPlaceholderText("Servis adı / araç tipi / plaka / açıklama ara...")
        else:
            self.search.setPlaceholderText("Hizmet adı / barkod / açıklama ara...")
        self.search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.search.textChanged.connect(self._on_search_changed)
        tools_l.addWidget(self.search, 1)
        root.addWidget(tools_card)

        # Sektöre göre tablo sütunları
        self._is_auto_mode = is_auto
        if is_auto:
            col_headers = ["ID", "Barkod/Kod", "Servis Adı", "Birim Fiyat", "Açıklama",
                           "Araç Tipi", "Marka", "Model", "Yıl"]
        else:
            col_headers = ["ID", "Barkod", "Hizmet Adı", "Birim Fiyat", "Açıklama"]

        if not is_auto:
            col_headers = [
                "ID",
                "\u0130\u015f\u00e7ilik Ad\u0131",
                "TL",
                "Dolar (Anl\u0131k Kur)",
                "Euro (Anl\u0131k Kur)",
                "Durum",
                "D\u00fczenle",
                "Sil",
            ]

        self.table = QTableWidget()
        self.table.setObjectName("ServicesTable")
        self.table.setColumnCount(len(col_headers))
        self.table.setHorizontalHeaderLabels(col_headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(False)
        self.table.viewport().setMouseTracking(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setStyleSheet(
            theme_qss(
                DesignTokens.get_table_qss()
                + "QTableWidget#ServicesTable::item:hover { background-color: transparent; color: @text; }"
                + "QTableWidget#ServicesTable::item:selected:hover { background-color: @selection_bg; color: @selection_text; }"
            )
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 70)
        if not is_auto:
            self.table.setColumnHidden(0, True)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for column, width in ((2, 150), (3, 150), (4, 150), (5, 120), (6, 128), (7, 116)):
                self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(column, width)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemSelectionChanged.connect(self._sync_selected_id)
        root.addWidget(self.table, 1)
        self.empty_state = EmptyState(
            "Henüz hizmet yok",
            "Kaydedilmiş bir hizmet tanımı bulunamadı.",
            parent=self,
        )
        self.empty_state.hide()
        root.addWidget(self.empty_state, 1)

        footer = QHBoxLayout()
        self.lbl_page_info = QLabel("")
        footer.addWidget(self.lbl_page_info)
        footer.addStretch()
        self.btn_previous = QPushButton("\u00d6nceki")
        self.btn_next = QPushButton("Sonraki")
        self.lbl_page = QLabel("1")
        self.btn_previous.clicked.connect(self.previous_page)
        self.btn_next.clicked.connect(self.next_page)
        page_button_qss = theme_qss(
            """
            QPushButton {
                min-width: 86px;
                min-height: 32px;
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                border-color: @accent;
                background: @surface;
            }
            QPushButton:disabled {
                background: @surface;
                color: @text_muted;
                border-color: @border;
            }
            """
        )
        self.btn_previous.setStyleSheet(page_button_qss)
        self.btn_next.setStyleSheet(page_button_qss)
        footer.addWidget(self.btn_previous)
        footer.addWidget(self.lbl_page)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)
        for widget in (
            self.lbl_page_info,
            self.btn_previous,
            self.lbl_page,
            self.btn_next,
        ):
            widget.setVisible(not is_auto)

    def toggle_multiselect(self, checked: bool):
        self._multi_select = checked
        self.table.clearSelection()
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im Ac\u0131k")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im")
        self._sync_selected_id()

    def _sync_selected_id(self):
        rows = self._selected_rows()
        if len(rows) == 1:
            item = self.table.item(rows[0], 0)
            self._selected_id = int(item.text()) if item and item.text().isdigit() else None
        else:
            self._selected_id = None
        # Sil butonu: en az 1 satır seçiliyse aktif
        has_sel = len(rows) > 0
        self.btn_delete.setEnabled(has_sel)
        # Düzenle butonu: yalnızca tek seçimde aktif
        self.btn_edit.setEnabled(len(rows) == 1)

    def _selected_rows(self) -> List[int]:
        return sorted(set(i.row() for i in self.table.selectionModel().selectedRows()))

    def _service_dict_from_row(self, row: int) -> Dict:
        if not getattr(self, "_is_auto_mode", False):
            item = self.table.item(row, 0)
            data = item.data(Qt.ItemDataRole.UserRole) if item else None
            if isinstance(data, dict):
                return dict(data)
        return {
            "id": int(self.table.item(row, 0).text()),
            "barcode": self.table.item(row, 1).text(),
            "name": self.table.item(row, 2).text(),
            "price": float(self.table.item(row, 3).data(Qt.ItemDataRole.UserRole) or 0.0),
            "description": self.table.item(row, 4).text(),
        }

    def load_services(self, filtered: Optional[List[Dict]] = None):
        data = filtered if filtered is not None else list(self.db.get_services_list() or [])
        if not getattr(self, "_is_auto_mode", False):
            self._load_labor_services(data)
            return
        self.table.setRowCount(0)
        for r, s in enumerate(data):
            self.table.insertRow(r)
            sid     = s["id"]          if isinstance(s, dict) else s[0]
            name    = s["name"]        if isinstance(s, dict) else (s[1] if len(s) > 1 else "")
            price   = s["price"]       if isinstance(s, dict) else (s[2] if len(s) > 2 else 0)
            desc    = s.get("description", "") if isinstance(s, dict) else (s[3] if len(s) > 3 else "")
            barcode = s.get("barcode", "")     if isinstance(s, dict) else (s[4] if len(s) > 4 else "")

            self.table.setItem(r, 0, QTableWidgetItem(str(sid)))
            self.table.setItem(r, 1, QTableWidgetItem(str(barcode or "")))
            self.table.setItem(r, 2, QTableWidgetItem(str(name or "")))
            p_item = QTableWidgetItem(CurrencyHelper.format_amount(float(price or 0.0)))
            p_item.setData(Qt.ItemDataRole.UserRole, float(price or 0.0))
            self.table.setItem(r, 3, p_item)
            self.table.setItem(r, 4, QTableWidgetItem(str(desc or "")))

            # Otomotiv ek sütunlar (5-8)
            if getattr(self, "_is_auto_mode", False):
                vtype = s.get("vehicle_type", "") if isinstance(s, dict) else ""
                vbrand = s.get("vehicle_brand", "") if isinstance(s, dict) else ""
                vmodel = s.get("vehicle_model", "") if isinstance(s, dict) else ""
                vyear  = s.get("vehicle_year", "") if isinstance(s, dict) else ""
                self.table.setItem(r, 5, QTableWidgetItem(str(vtype  or "")))
                self.table.setItem(r, 6, QTableWidgetItem(str(vbrand or "")))
                self.table.setItem(r, 7, QTableWidgetItem(str(vmodel or "")))
                self.table.setItem(r, 8, QTableWidgetItem(str(vyear  or "")))

        self._sync_selected_id()
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)

    def _load_labor_services(self, data):
        self.total_count = len(data)
        total_pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(max(1, self.current_page), total_pages)
        start = (self.current_page - 1) * self.PAGE_SIZE
        page_rows = data[start:start + self.PAGE_SIZE]
        usd_rate = CurrencyHelper.require_rate(self.db, "USD")
        eur_rate = CurrencyHelper.require_rate(self.db, "EUR")
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row_index, service in enumerate(page_rows):
            self.table.insertRow(row_index)
            self.table.setRowHeight(row_index, 46)
            item_id = QTableWidgetItem(str(service.get("id", "")))
            item_id.setData(Qt.ItemDataRole.UserRole, dict(service))
            self.table.setItem(row_index, 0, item_id)
            self.table.setItem(
                row_index,
                1,
                QTableWidgetItem(str(service.get("name", "") or "")),
            )
            try_value = float(service.get("price_try", 0) or 0)
            prices = (
                (try_value, "TRY", False),
                (
                    try_value / usd_rate,
                    "USD",
                    True,
                ),
                (
                    try_value / eur_rate,
                    "EUR",
                    True,
                ),
            )
            for offset, (value, code, is_live_rate) in enumerate(prices, start=2):
                price_item = QTableWidgetItem(f"{value:,.2f} {code}")
                price_item.setData(Qt.ItemDataRole.UserRole, value)
                if is_live_rate:
                    rate = usd_rate if code == "USD" else eur_rate
                    price_item.setToolTip(
                        f"Anl\u0131k kur: 1 {code} = {rate:,.4f} TRY"
                    )
                self.table.setItem(row_index, offset, price_item)
            is_active = bool(service.get("is_active", 1))
            status_item = QTableWidgetItem("Aktif" if is_active else "Pasif")
            status_item.setData(Qt.ItemDataRole.UserRole, int(is_active))
            self.table.setItem(row_index, 5, status_item)

            edit_button = self._make_row_action_button("\u270e  D\u00fczenle", "edit")
            edit_button.clicked.connect(
                lambda _checked=False, sid=service.get("id"): self._edit_labor_row(sid)
            )
            self.table.setCellWidget(row_index, 6, edit_button)
            delete_button = self._make_row_action_button("\U0001f5d1  Sil", "delete")
            delete_button.clicked.connect(
                lambda _checked=False, sid=service.get("id"): self._delete_labor_row(sid)
            )
            self.table.setCellWidget(row_index, 7, delete_button)
        self.table.setSortingEnabled(True)
        has_rows = bool(page_rows)
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)
        first = start + 1 if self.total_count else 0
        last = min(start + len(page_rows), self.total_count)
        self.lbl_page_info.setText(
            f"{self.total_count} kay\u0131ttan {first} - {last} aras\u0131 g\u00f6steriliyor."
        )
        self.lbl_page.setText(f"{self.current_page} / {total_pages}")
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        self._sync_selected_id()

    @staticmethod
    def _make_row_action_button(text: str, action: str) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)
        button.setStyleSheet(
            theme_qss(
                "QPushButton { border: none; border-radius: 6px; font-weight: 700; padding: 0 10px; }"
                + (
                    "QPushButton { background: @accent; color: @selection_text; }"
                    "QPushButton:hover { background: @accent_hover; }"
                    if action == "edit"
                    else "QPushButton { background: @danger; color: @selection_text; }"
                    "QPushButton:hover { background: @danger_bg; color: @danger; }"
                )
            )
        )
        return button

    def _edit_labor_row(self, service_id):
        self._select_row_by_service_id(service_id)
        self.open_edit_dialog()

    def _delete_labor_row(self, service_id):
        self._select_row_by_service_id(service_id)
        self.delete_selected_action()

    def _select_row_by_service_id(self, service_id):
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and str(item.text()) == str(service_id):
                self.table.selectRow(row)
                break

    def _on_search_changed(self):
        self.current_page = 1
        self._apply_filter()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._apply_filter()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        if self.current_page < total_pages:
            self.current_page += 1
            self._apply_filter()

    def _apply_filter(self):
        q = self.search.text().strip().lower()
        if not q:
            self.load_services()
            return
        raw = list(self.db.get_services_list() or [])
        out = []
        for s in raw:
            name = str(s["name"] if isinstance(s, dict) else s[1] or "").lower()
            desc = str((s.get("description", "") if isinstance(s, dict) else (s[3] if len(s) > 3 else "")) or "").lower()
            barcode = str((s.get("barcode", "") if isinstance(s, dict) else (s[4] if len(s) > 4 else "")) or "").lower()
            if q in name or q in desc or q in barcode:
                out.append(s)
        self.load_services(out)

    def open_documents_center(self):
        UnifiedDocumentsCenterDialog(self.db, None, self).exec()

    def open_add_dialog(self):
        dlg = AddServiceDefinitionDialog(self)
        if dlg.exec():
            d = dlg.get_data()
            if not d["name"]:
                show_warning(self, "Hizmet adı boş olamaz.")
                return
            sid = self.db.add_service(
                d["name"],
                d["price"],
                d["description"],
                d["barcode"],
                d["currency"],
                price_try=d.get("price_try"),
                price_usd=d.get("price_usd"),
                price_eur=d.get("price_eur"),
                is_active=d.get("is_active", 1),
            )
            if sid:
                self.audit_logger.log_action("services", "INSERT", f"Hizmet eklendi: {d['name']}")
                show_success(self, "Hizmet eklendi.")
                self.load_services()
            else:
                show_error(self, "Hizmet eklenemedi. Aynı isim/barkod kontrol edin.")

    def open_edit_dialog(self):
        rows = self._selected_rows()
        if len(rows) != 1:
            show_warning(self, "Düzenlemek için tek bir satır seçin.")
            return
        item = self._service_dict_from_row(rows[0])
        dlg = AddServiceDefinitionDialog(self, service_data=item)
        if dlg.exec():
            d = dlg.get_data()
            ok = self.db.update_service(
                item["id"],
                d["name"],
                d["price"],
                d["description"],
                d["barcode"],
                d["currency"],
                price_try=d.get("price_try"),
                price_usd=d.get("price_usd"),
                price_eur=d.get("price_eur"),
                is_active=d.get("is_active", 1),
            )
            if ok:
                self.audit_logger.log_action("services", "UPDATE", f"Hizmet güncellendi: {item['id']}")
                show_info(self, "Hizmet güncellendi.")
                self.load_services()
            else:
                show_error(self, "Hizmet güncellenemedi.")

    def delete_selected_action(self):
        rows = self._selected_rows()
        if not rows:
            show_warning(self, "Silmek için satır seçin.")
            return
        if len(rows) == 1:
            item = self._service_dict_from_row(rows[0])
            txt = f"'{item['name']}' hizmeti silinsin mi"
        else:
            txt = f"{len(rows)} adet hizmet silinsin mi Bu işlem geri alınamaz."
        if SimpleConfirmDialog(parent=self, title="Onay", text=txt).exec() != 1:
            return
        ok_count = 0
        for r in rows:
            sid = self.table.item(r, 0).text()
            if self.db.delete_service(sid):
                ok_count += 1
        self.audit_logger.log_action("services", "DELETE", f"Toplu silme: {ok_count} kayıt")
        show_success(self, f"{ok_count} kayıt silindi.")
        self.load_services()

    def show_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=140):
            return
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        if not self.table.item(idx.row(), 0).isSelected():
            self.table.selectRow(idx.row())
        menu = QMenu(self)
        a_new = QAction("➕ Yeni Hizmet", self)
        a_edit = QAction("📝 Düzenle", self)
        a_del = QAction("🗑️ Sil", self)
        a_export = QAction("📤 Excel Aktar", self)
        a_pdf = QAction("📄 PDF Olarak Kaydet", self)
        a_print = QAction("🖨️ Yazdır", self)
        a_new.triggered.connect(self.open_add_dialog)
        a_edit.triggered.connect(self.open_edit_dialog)
        a_del.triggered.connect(self.delete_selected_action)
        a_export.triggered.connect(self.export_to_excel)
        a_pdf.triggered.connect(self.export_to_pdf)
        a_print.triggered.connect(self.print_list)
        menu.addAction(a_new)
        menu.addAction(a_edit)
        menu.addAction(a_del)
        menu.addSeparator()
        menu.addAction(a_export)
        menu.addAction(a_pdf)
        menu.addAction(a_print)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    @staticmethod
    def _parse_tl_number(raw) -> Optional[float]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        s = str(raw).strip()
        if not s:
            return None
        s = s.replace("₺", "").replace("TL", "").replace("tl", "").replace(" ", "")
        s = re.sub(r"[^\d,.\-]", "", s)
        if not s:
            return None
        # both separators exist -> rightmost one is decimal sep
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            # single comma: decimal separator
            if s.count(",") == 1:
                s = s.replace(",", ".")
            else:
                # thousands commas
                last = s.rfind(",")
                s = s[:last].replace(",", "") + "." + s[last + 1 :]
        elif "." in s and s.count(".") > 1:
            last = s.rfind(".")
            s = s[:last].replace(".", "") + "." + s[last + 1 :]
        try:
            return float(s)
        except Exception:
            return None

    def _collect_service_rows(self) -> List[Dict[str, str]]:
        if not getattr(self, "_is_auto_mode", False):
            query = self.search.text().strip().lower()
            source_rows = list(self.db.get_services_list() or [])
            if query:
                source_rows = [
                    service
                    for service in source_rows
                    if query in str(service.get("name", "")).lower()
                    or query in str(service.get("description", "")).lower()
                    or query in str(service.get("barcode", "")).lower()
                ]
            return [
                {
                    "\u0130\u015f\u00e7ilik Ad\u0131": str(service.get("name", "") or ""),
                    "TL": f"{float(service.get('price_try', 0) or 0):,.2f}",
                    "USD": f"{float(service.get('price_usd', 0) or 0):,.2f}",
                    "EURO": f"{float(service.get('price_eur', 0) or 0):,.2f}",
                    "Durum": (
                        "Aktif" if bool(service.get("is_active", 1)) else "Pasif"
                    ),
                }
                for service in source_rows
            ]
        rows: List[Dict[str, str]] = []
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        for row in range(self.table.rowCount()):
            rows.append(
                {
                    headers[col]: self.table.item(row, col).text() if self.table.item(row, col) else ""
                    for col in range(self.table.columnCount())
                }
            )
        return rows

    def _build_service_html(self) -> str:
        rows = self._collect_service_rows()
        header_keys = list(rows[0].keys()) if rows else ["ID", "Barkod", "Hizmet Adı", "Birim Fiyat", "Açıklama"]
        header_html = "".join(
            f"<th style='padding:8px;border:1px solid #d9d9d9;background:#f3f4f6;'>{key}</th>"
            for key in header_keys
        )
        body_rows = []
        for row in rows:
            body_rows.append(
                "<tr>" + "".join(f"<td style='padding:6px;border:1px solid #d9d9d9;'>{value}</td>" for value in row.values()) + "</tr>"
            )
        return f"""
        <html><head><meta charset='UTF-8'></head><body>
        <h2>AYEC Pro - Hizmet Tanimlari</h2>
        <p>Tarih: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        <table cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;font-size:10pt;'>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
        </table></body></html>
        """

    def export_to_csv(self):
        try:
            is_auto = self._is_automotive()
            default_name = "Servis_Listesi.xlsx" if is_auto else "Hizmet_Listesi.xlsx"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Servis Listesi Dışa Aktar" if is_auto else "Hizmet Listesi Dışa Aktar",
                default_name,
                "Excel Dosyası (*.xlsx)",
            )
            if not path:
                return

            rows = list(self.db.get_services_list() or [])
            if not rows:
                show_warning(self, "Dışa aktarılacak kayıt bulunamadı.")
                return

            import pandas as pd

            dict_rows = []
            for s in rows:
                if isinstance(s, dict) or hasattr(s, "keys"):
                    dict_rows.append(dict(s))
                else:
                    dict_rows.append({
                        "id": s[0],
                        "name": s[1] if len(s) > 1 else "",
                        "price": s[2] if len(s) > 2 else 0,
                        "description": s[3] if len(s) > 3 else "",
                        "barcode": s[4] if len(s) > 4 else "",
                    })

            df = pd.DataFrame(dict_rows)
            label = getattr(self.db, "get_setting", lambda k, d: d)("currency", "TRY")

            if is_auto:
                rename_map = {
                    "id": "ID",
                    "barcode": "Barkod/Kod",
                    "name": "Servis Adı",
                    "price": f"Birim Fiyat ({label})",
                    "description": "Açıklama",
                    "vehicle_type": "Araç Tipi",
                    "vehicle_brand": "Marka",
                    "vehicle_model": "Model",
                    "vehicle_year": "Yıl",
                    "vehicle_plate": "Plaka",
                    "currency": "Para Birimi",
                }
            else:
                rename_map = {
                    "id": "ID",
                    "barcode": "Barkod",
                    "name": "Hizmet Adı",
                    "price": f"Birim Fiyat ({label})",
                    "description": "Açıklama",
                    "currency": "Para Birimi",
                }

            if not is_auto:
                if "is_active" in df.columns:
                    df["is_active"] = df["is_active"].map(
                        lambda value: "Aktif" if bool(value) else "Pasif"
                    )
                rename_map = {
                    "name": "\u0130\u015f\u00e7ilik Ad\u0131",
                    "price_try": "TL",
                    "price_usd": "USD",
                    "price_eur": "EURO",
                    "is_active": "Durum",
                    "barcode": "Barkod",
                    "description": "A\u00e7\u0131klama",
                }

            df = df.rename(columns=rename_map)
            keep_cols = [v for k, v in rename_map.items() if v in df.columns]
            df = df[keep_cols]
            df.to_excel(path, index=False)
            show_success(self, f"Dışa aktarma tamamlandı:\n{path}")
        except Exception as e:
            show_error(self, f"Hata: {e}")

    def export_to_excel(self):
        self.export_to_csv()

    def export_to_pdf(self):
        try:
            if self.table.rowCount() == 0:
                show_warning(self, "PDF icin hizmet verisi bulunamadi.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Hizmet Listesi PDF Kaydet",
                "hizmet_listesi.pdf",
                "PDF Dosyasi (*.pdf)",
            )
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_service_html())
            doc.print(printer)
            show_success(self, f"PDF olusturuldu:\n{path}")
        except Exception as e:
            show_error(self, f"PDF olusturma hatasi: {e}")

    def print_list(self):
        try:
            if self.table.rowCount() == 0:
                show_warning(self, "Yazdirilacak hizmet verisi bulunamadi.")
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_service_html())
            doc.print(printer)
            show_info(self, "Hizmet listesi yazdirmaya gonderildi.")
        except Exception as e:
            show_error(self, f"Yazdirma hatasi: {e}")

    def import_from_csv(self):
        try:
            is_auto = self._is_automotive()
            dialog_title = "Servis Listesi İçe Aktar" if is_auto else "Hizmet Listesi İçe Aktar"
            path, _ = QFileDialog.getOpenFileName(
                self, dialog_title, "", "Excel Dosyası (*.xlsx *.xls *.csv)",
            )
            if not path: return

            import pandas as pd

            df = None
            if path.endswith(".csv"):
                for enc in ["utf-8-sig", "utf-8", "cp1254", "latin-1"]:
                    for sep in [",", ";", "\t"]:
                        try:
                            temp_df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, keep_default_na=False)
                            if len(temp_df.columns) > 1 or (len(temp_df.columns) == 1 and sep == ","):
                                df = temp_df
                                break
                        except Exception:
                            pass
                    if df is not None: break
                if df is None:
                    try: df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", dtype=str)
                    except Exception:
                        show_error(self, "CSV dosyası okunamadı.")
                        return
            else:
                try: df = pd.read_excel(path, dtype=str, keep_default_na=False)
                except Exception as e:
                    show_error(self, f"Excel okunamadı: {e}")
                    return

            if df is None or df.empty:
                show_error(self, "Dosya boş veya okunamadı.")
                return

            def _norm_col(c):
                c = str(c).lower().strip()
                for src_char, dst_char in [("ı","i"),("ğ","g"),("ü","u"),("ş","s"),("ö","o"),("ç","c")]:
                    c = c.replace(src_char, dst_char)
                return c.replace("_", " ").replace("-", " ")

            # Ortak alanlar
            col_map = {
                "hizmet adi": "name", "hizmet": "name", "servis adi": "name", "servis": "name",
                "ad": "name", "isim": "name", "service name": "name", "service": "name",
                "name": "name", "baslik": "name", "title": "name",
                "fiyat": "price", "tutar": "price", "birim fiyat": "price", "birim fiyat (tl)": "price",
                "ucret": "price", "price": "price", "unit price": "price", "amount": "price", "cost": "price",
                "aciklama": "description", "not": "description", "notlar": "description",
                "aciklama notlar": "description", "description": "description", "notes": "description", "desc": "description",
                "barkod": "barcode", "kod": "barcode", "referans": "barcode", "referans kodu": "barcode",
                "urun kodu": "barcode", "barcode": "barcode", "code": "barcode", "sku": "barcode",
                "para birimi": "currency", "currency": "currency", "doviz": "currency",
            }

            # Otomotiv ek alanları
            if is_auto:
                col_map.update({
                    "plaka": "vehicle_plate", "arac plaka": "vehicle_plate",
                    "vehicle plate": "vehicle_plate", "plate": "vehicle_plate",
                    "marka": "vehicle_brand", "arac marka": "vehicle_brand",
                    "vehicle brand": "vehicle_brand", "brand": "vehicle_brand",
                    "model": "vehicle_model", "arac model": "vehicle_model",
                    "vehicle model": "vehicle_model",
                    "yil": "vehicle_year", "model yili": "vehicle_year",
                    "year": "vehicle_year", "vehicle year": "vehicle_year",
                    "km": "vehicle_km", "kilometre": "vehicle_km", "odometer": "vehicle_km",
                    "arac tipi": "vehicle_type", "tip": "vehicle_type", "vehicle type": "vehicle_type",
                })

            header_found = False
            matched_cols = {}
            for col in df.columns:
                n = _norm_col(col)
                if n in col_map:
                    matched_cols[col_map[n]] = str(col)

            if "name" in matched_cols:
                header_found = True
            else:
                for idx, row in df.head(10).iterrows():
                    test_matched = {}
                    for col in df.columns:
                        n = _norm_col(str(row[col]))
                        if n in col_map:
                            test_matched[col_map[n]] = str(col)
                    if "name" in test_matched:
                        matched_cols = test_matched
                        header_found = True
                        df = df.iloc[idx+1:].reset_index(drop=True)
                        break

            if not header_found or "name" not in matched_cols:
                expected = "'Servis Adı, Fiyat, Plaka, Marka, Model'" if is_auto else "'Hizmet Adı, Fiyat, Açıklama, Barkod'"
                show_error(self, f"Dosyada 'Hizmet/Servis Adı' sütunu bulunamadı!\nBeklenen başlıklar: {expected}")
                return

            def parse_val(val, to_type=float):
                if val is None: return 0 if to_type in (int, float) else ""
                try:
                    is_missing = bool(pd.isna(val))
                except Exception:
                    is_missing = False
                if is_missing:
                    return 0 if to_type in (int, float) else ""
                val_str = str(val).strip()
                if not val_str or val_str.lower() in ["nan", "nat", "null", "none"]:
                    return 0 if to_type in (int, float) else ""
                if to_type in (int, float):
                    val_str = val_str.replace(".", "").replace(",", ".") if "," in val_str and "." in val_str else val_str.replace(",", ".")
                    try: return to_type(float(val_str))
                    except Exception: return 0 if to_type is int else 0.0
                return val_str

            def _str(row, key):
                if key not in matched_cols: return ""
                val = str(row[matched_cols[key]]).strip() if pd.notnull(row[matched_cols[key]]) else ""
                return "" if val.lower() in ("nan", "none", "null", "") else val

            success, fails = 0, 0
            for _, row in df.iterrows():
                try:
                    n_val = _str(row, "name")
                    if not n_val: continue
                    p_val   = parse_val(row[matched_cols["price"]], float) if "price" in matched_cols else 0.0
                    d_val   = _str(row, "description")
                    c_val   = _str(row, "barcode")
                    cur_val = _str(row, "currency") or "TRY"

                    # Otomotiv ek alanlar - description'a ekle
                    if is_auto:
                        plate  = _str(row, "vehicle_plate")
                        brand  = _str(row, "vehicle_brand")
                        model  = _str(row, "vehicle_model")
                        year   = _str(row, "vehicle_year")
                        km     = _str(row, "vehicle_km")
                        vtype  = _str(row, "vehicle_type")
                        # description'ı araç bilgisiyle zenginleştir
                        auto_extra = " | ".join(
                            f"{k}: {v}" for k, v in [
                                ("Plaka", plate), ("Marka", brand), ("Model", model),
                                ("Yıl", year), ("KM", km), ("Tip", vtype)
                            ] if v
                        )
                        if auto_extra and not d_val:
                            d_val = auto_extra
                        elif auto_extra:
                            d_val = f"{d_val} | {auto_extra}"

                    self.db.add_service(name=n_val, price=p_val, description=d_val, barcode=c_val, currency=cur_val)
                    success += 1
                except Exception:
                    fails += 1

            show_success(self, f"İçe aktarma tamamlandı.\nBaşarılı: {success}\nHatalı: {fails}")
            self.load_services()
        except Exception as e:
            show_error(self, f"İçe Aktarma Hatası: {e}")

    def smart_import(self):
        """Akıllı içe aktarma: Excel/CSV/PDF/Görsel/OCR destekli, önizlemeli."""
        try:
            is_auto = self._is_automotive()
            title = "Akıllı Servis İçe Aktar" if is_auto else "Akıllı Hizmet İçe Aktar"
            path, _ = QFileDialog.getOpenFileName(
                self,
                title,
                "",
                "Desteklenen Dosyalar (*.xlsx *.xls *.csv *.pdf *.docx *.jpg *.jpeg *.png *.bmp *.webp *.xml *.tif *.tiff *.ppm);;Tüm Dosyalar (*.*)",
            )
            if not path:
                return

            self._svc_loading_overlay.show_overlay("Dosya analiz ediliyor...")

            self._svc_parse_worker = ServiceParseWorker(path, is_auto)
            self._svc_parse_worker.finished.connect(self._on_svc_parse_done)
            self._svc_parse_worker.error.connect(self._on_svc_parse_error)
            self._svc_parse_worker.start()
        except Exception as e:
            show_error(self, f"Akıllı içe aktarma hatası: {e}")

    def _on_svc_parse_done(self, parse_result, is_auto):
        try:
            self._svc_loading_overlay.hide_overlay()
            dlg = ServiceImportPreviewDialog(self.db, parse_result, self, is_automotive=is_auto)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.load_services()
        except Exception as e:
            show_error(self, f"Akıllı içe aktarma hatası: {e}")

    def _on_svc_parse_error(self, err_msg):
        self._svc_loading_overlay.hide_overlay()
        show_error(self, f"Dosya analiz hatası: {err_msg}")
