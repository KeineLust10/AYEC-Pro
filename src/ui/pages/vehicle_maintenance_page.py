import html
import os
import re
import urllib.parse
import webbrowser
from datetime import datetime

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QTextDocument, QAction, QPageLayout
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QStyle,
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from src.ui.dialogs.vehicle_maintenance_dialog import VehicleMaintenanceDialog
from src.ui.dialogs.vehicle_maintenance_photo_gallery_dialog import VehicleMaintenancePhotoGalleryDialog
from src.ui.dialogs.vehicle_history_qr_dialog import VehicleHistoryQrDialog
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.system_config import SystemConfig
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_info, show_success, show_warning


class VehicleMaintenancePage(QWidget):
    def __init__(self, db, main_window=None, sector_manager=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.sector_manager = sector_manager or getattr(main_window, "sector_manager", None)
        self.is_automotive = self._is_automotive()
        self._row_payloads = []
        self._build_ui()
        QTimer.singleShot(120, self.load_cards)

    def _is_automotive(self):
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _build_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss("background-color: @window;"))
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header_frame = QFrame()
        self.header_frame = header_frame
        header_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(18, 16, 18, 16)
        header.setSpacing(14)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Arac Bakim Takibi")
        title.setStyleSheet(theme_qss("font-size: 26px; font-weight: 800; color: @text; border: none; background: transparent;"))
        subtitle = QLabel("Periyodik bakim kartlarini kaydedin, taslak randevu ve hatirlatma uretin.")
        subtitle.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted; border: none; background: transparent;"))
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        btn_new = QPushButton("Yeni Bakim Karti")
        btn_new.setFixedHeight(42)
        btn_new.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success")))
        btn_new.clicked.connect(self.open_new_card)
        self.btn_gallery = QPushButton("Foto Galeri")
        self.btn_gallery.setFixedHeight(42)
        self.btn_gallery.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_gallery.clicked.connect(self.open_photo_gallery)
        self.btn_history = QPushButton("QR / Gecmis")
        self.btn_history.setFixedHeight(42)
        self.btn_history.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_history.clicked.connect(self.open_history_qr)
        self.btn_excel = QPushButton()
        self.btn_excel.setToolTip("Excel'e Aktar")
        self.btn_excel.setAccessibleName("Excel'e Aktar")
        self.btn_excel.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_excel.setIconSize(QSize(20, 20))
        self.btn_excel.setFixedSize(42, 42)
        self.btn_excel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_excel.clicked.connect(self.export_to_excel)
        self.btn_pdf = QPushButton()
        self.btn_pdf.setToolTip("PDF'e Aktar")
        self.btn_pdf.setAccessibleName("PDF'e Aktar")
        self.btn_pdf.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_pdf.setIconSize(QSize(20, 20))
        self.btn_pdf.setFixedSize(42, 42)
        self.btn_pdf.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_pdf.clicked.connect(self.export_to_pdf)
        self.btn_print = QPushButton()
        self.btn_print.setToolTip("Yazd\u0131r")
        self.btn_print.setAccessibleName("Yazd\u0131r")
        self.btn_print.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_print.setIconSize(QSize(20, 20))
        self.btn_print.setFixedSize(42, 42)
        self.btn_print.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_print.clicked.connect(self.print_table)
        header.addWidget(self.btn_print)
        header.addWidget(self.btn_pdf)
        header.addWidget(self.btn_excel)
        header.addWidget(self.btn_history)
        header.addWidget(self.btn_gallery)
        header.addWidget(btn_new)
        root.addWidget(header_frame)

        tools = QFrame()
        self.tools_frame = tools
        tools.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        tools_layout = QHBoxLayout(tools)
        tools_layout.setContentsMargins(14, 12, 14, 12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Musteri, plaka, marka veya model ara...")
        self.search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.search.textChanged.connect(self.load_cards)
        tools_layout.addWidget(self.search)
        root.addWidget(tools)

        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        self.stats_grid = QGridLayout(self.stats_frame)
        self.stats_grid.setContentsMargins(14, 12, 14, 12)
        self.stats_grid.setHorizontalSpacing(10)
        self.stats_grid.setVerticalSpacing(10)
        self.stat_labels = {}
        self._stat_cards = []
        for index, title in enumerate(("Toplam Kart", "Yaklasan Bakim", "Muayene Yakini", "Acik Is Emri")):
            card = QFrame()
            card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 14px;"))
            self._stat_cards.append(card)
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(12, 10, 12, 10)
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet(theme_qss("font-size: 11px; font-weight: 700; color: @text; border: none; background: transparent;"))
            lbl_value = QLabel("0")
            lbl_value.setStyleSheet(theme_qss("font-size: 22px; font-weight: 800; color: @accent; border: none; background: transparent;"))
            card_lay.addWidget(lbl_title)
            card_lay.addWidget(lbl_value)
            self.stat_labels[title] = lbl_value
            self.stats_grid.addWidget(card, 0, index)
        root.addWidget(self.stats_frame)

        self.table_shell = QFrame()
        self.table_shell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.table_shell.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        table_layout = QVBoxLayout(self.table_shell)
        table_layout.setContentsMargins(14, 14, 14, 14)
        table_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "Musteri", "Plaka", "Arac", "Bakim Tarihi",
            "Sonraki Bakim", "Muayene", "Yaklasan KM", "Taslak Randevu", "Hatirlatma", "Foto"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setMinimumSectionSize(78)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.cellDoubleClicked.connect(self._open_selected_card)
        self.table.itemSelectionChanged.connect(self._refresh_detail_panel)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        table_layout.addWidget(self.table)
        root.addWidget(self.table_shell, 1)

        detail = QFrame()
        self.detail_frame = detail
        detail.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        detail_lay = QVBoxLayout(detail)
        detail_lay.setContentsMargins(16, 14, 16, 14)
        detail_lay.setSpacing(10)
        detail_title = QLabel("Bakim ve Is Emri Ozet Paneli")
        detail_title.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text; border: none; background: transparent;"))
        self.lbl_detail_summary = QLabel("Bir bakim karti secin.")
        self.lbl_detail_summary.setWordWrap(True)
        self.lbl_detail_summary.setStyleSheet(theme_qss("color: @text; font-size: 12px; border: none; background: transparent;"))
        self.lbl_detail_history = QLabel("")
        self.lbl_detail_history.setWordWrap(True)
        self.lbl_detail_history.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none; background: transparent;"))
        actions = QHBoxLayout()
        self.btn_open_linked_service = QPushButton("Bagli Servis Formu")
        self.btn_open_linked_service.setFixedHeight(38)
        self.btn_open_linked_service.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_open_linked_service.clicked.connect(self.open_linked_service_form)
        self.btn_open_linked_service.setEnabled(False)
        actions.addWidget(self.btn_open_linked_service)
        actions.addStretch()
        detail_lay.addWidget(detail_title)
        detail_lay.addWidget(self.lbl_detail_summary)
        detail_lay.addWidget(self.lbl_detail_history)
        detail_lay.addLayout(actions)
        root.addWidget(detail)

    def apply_theme_styles(self):
        self.setStyleSheet(theme_qss("background-color: @window;"))
        if hasattr(self, "tools_frame"):
            self.tools_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        if hasattr(self, "header_frame"):
            self.header_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        if hasattr(self, "stats_frame"):
            self.stats_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        for card in getattr(self, "_stat_cards", []):
            card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 14px;"))
        if hasattr(self, "table_shell"):
            self.table_shell.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        if hasattr(self, "detail_frame"):
            self.detail_frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        if hasattr(self, "search"):
            self.search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        if hasattr(self, "table"):
            self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))

    def load_cards(self):
        rows = self.db.get_vehicle_maintenance_cards(self.search.text().strip())
        self._row_payloads = [dict(row) for row in rows]
        self.table.setRowCount(0)
        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)
            vehicle_name = " ".join(part for part in [row["vehicle_brand"], row["vehicle_model"]] if part)
            next_due_odometer = int(row["next_due_odometer_min"] or 0)
            current_odometer = int(row["odometer"] or 0)
            km_text = ""
            if next_due_odometer > 0:
                km_text = f"{max(0, next_due_odometer - current_odometer)} KM"
            values = [
                str(row["id"]),
                row["customer_name"] or "",
                row["vehicle_plate"] or "",
                vehicle_name,
                row["service_date"] or "",
                row["next_maintenance_date"] or "",
                row["inspection_due_date"] or "",
                km_text,
                row["appointment_date"] or "",
                row["reminder_date"] or "",
                str(row["photo_count"] or 0),
            ]
            for col_idx, value in enumerate(values):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(value))
        self._refresh_stats(rows)
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
        else:
            self._refresh_detail_panel()

    def _refresh_stats(self, rows):
        today = datetime.now().strftime("%Y-%m-%d")
        total_cards = len(rows or [])
        due_maintenance = 0
        due_inspection = 0
        open_jobs = 0
        for row in rows or []:
            next_maintenance = str(row["next_maintenance_date"] or "")
            inspection_due = str(row["inspection_due_date"] or "")
            linked_device_id = row["linked_device_id"] if "linked_device_id" in row.keys() else None
            if next_maintenance and next_maintenance <= today:
                due_maintenance += 1
            if inspection_due and inspection_due <= today:
                due_inspection += 1
            if linked_device_id:
                open_jobs += 1
        self.stat_labels["Toplam Kart"].setText(str(total_cards))
        self.stat_labels["Yaklasan Bakim"].setText(str(due_maintenance))
        self.stat_labels["Muayene Yakini"].setText(str(due_inspection))
        self.stat_labels["Acik Is Emri"].setText(str(open_jobs))

    def _selected_payload(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._row_payloads):
            return None
        return self._row_payloads[row]

    def _refresh_detail_panel(self):
        payload = self._selected_payload()
        if not payload:
            self.lbl_detail_summary.setText("Bir bakim karti secin.")
            self.lbl_detail_history.setText("")
            self.btn_open_linked_service.setEnabled(False)
            return
        summary_row = self.db.get_vehicle_maintenance_card_summary(payload["id"])
        maintenance_rows, service_rows = self.db.get_vehicle_history_snapshot(payload.get("vehicle_plate", ""))
        selected_count = 0
        nearest_due = "-"
        nearest_km = "-"
        if summary_row:
            try:
                selected_count = int(summary_row["selected_count"] or 0)
                nearest_due = summary_row["nearest_due_date"] or "-"
                nearest_km_value = int(summary_row["nearest_due_odometer"] or 0)
                nearest_km = str(nearest_km_value) if nearest_km_value else "-"
            except Exception:
                pass
        linked_tracking = str(payload.get("linked_device_tracking_no", "") or "")
        self.lbl_detail_summary.setText(
            f"Musteri: {payload.get('customer_name') or '-'} | Plaka: {payload.get('vehicle_plate') or '-'}\n"
            f"Bakim kalemi: {selected_count} | En yakin tarih: {nearest_due} | En yakin KM: {nearest_km}\n"
            f"Bagli servis: {linked_tracking or 'Yok'} | Taslak randevu: {payload.get('appointment_date') or '-'} {payload.get('appointment_time') or ''}".strip()
        )
        open_service_count = len([row for row in service_rows if str(row["status"] or "") not in {"Teslim Edildi", "Tamamlandi"}])
        self.lbl_detail_history.setText(
            f"Bakim gecmisi: {len(maintenance_rows)} kayit | Servis gecmisi: {len(service_rows)} kayit | Acik servis: {open_service_count}"
        )
        self.btn_open_linked_service.setEnabled(bool(linked_tracking))

    def open_linked_service_form(self):
        payload = self._selected_payload()
        tracking_no = str((payload or {}).get("linked_device_tracking_no", "") or "")
        if not tracking_no:
            show_warning(self, "Secili bakim kartina bagli servis kaydi yok.")
            return
        try:
            from src.ui.dialogs.automotive_technician_panel import AutomotiveTechnicianPanel

            dialog = AutomotiveTechnicianPanel(
                self.db,
                tracking_no,
                self.window(),
                sector_manager=self.sector_manager,
            )
            dialog.exec()
            self.load_cards()
        except Exception as exc:
            show_warning(self, f"Ba\u011fl\u0131 servis formu a\u00e7\u0131lamad\u0131: {exc}")

    @staticmethod
    def _normalize_phone(phone):
        digits = re.sub(r"\D", "", str(phone or ""))
        if digits.startswith("0") and len(digits) == 11:
            return "90" + digits[1:]
        if len(digits) == 10:
            return "90" + digits
        return digits

    def _offer_appointment_whatsapp(self, card_id):
        card, items = self.db.get_vehicle_maintenance_card(card_id)
        if not card:
            return
        important_labels = [
            str(item["item_label"] or "").strip()
            for item in items
            if str(item["item_type"] or "").strip().lower() != "glass_water"
            and str(item["item_label"] or "").replace(" ", "").strip().lower() != "camsuyu"
            and int(item["performed"] if item["performed"] is not None else 1) == 1
        ]
        important_labels = [label for label in important_labels if label]
        if not important_labels:
            return

        phone = self._normalize_phone(card["customer_phone"])
        if not phone:
            show_warning(
                self,
                "M\u00fc\u015fterinin telefon numaras\u0131 olmad\u0131\u011f\u0131 i\u00e7in WhatsApp mesaj\u0131 a\u00e7\u0131lamad\u0131.",
            )
            return

        from src.ui.components.message_box import ModernConfirm

        if not ModernConfirm.ask(
            self,
            "Randevu kaydedildi. WhatsApp randevu mesaj\u0131n\u0131 \u015fimdi a\u00e7mak istiyor musunuz?",
            "Randevu Mesaj\u0131",
        ):
            return

        appointment_date = str(card["appointment_date"] or "-")
        try:
            appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            pass
        appointment_time = str(card["appointment_time"] or "").strip()
        item_text = ", ".join(important_labels[:5])
        if len(important_labels) > 5:
            item_text += f" ve {len(important_labels) - 5} kalem daha"
        message = (
            f"Say\u0131n {card['customer_name']}, {card['vehicle_plate'] or card['vehicle_brand'] or 'arac\u0131n\u0131z'} "
            f"i\u00e7in {appointment_date} {appointment_time} tarihli randevunuz olu\u015fturulmu\u015ftur. "
            f"Planlanan bak\u0131m: {item_text}. AYEC Pro Otomotiv"
        )
        webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")

    def open_new_card(self):
        dlg = VehicleMaintenanceDialog(self.db, self.window(), sector_manager=self.sector_manager)
        if dlg.exec():
            self.load_cards()
            if self.main_window:
                self.main_window.refresh_notification_bell()
            show_success(self, "Bakim karti kaydedildi ve taslak randevu olusturuldu.")
            self._offer_appointment_whatsapp(dlg.saved_card_id)

    def _open_selected_card(self, row=None, column=None):
        if row is None or row < 0:
            row = self.table.currentRow()
        if row < 0:
            return
        card_id = int(self.table.item(row, 0).text())
        dlg = VehicleMaintenanceDialog(self.db, self.window(), card_id=card_id, sector_manager=self.sector_manager)
        if dlg.exec():
            self.load_cards()
            if self.main_window:
                self.main_window.refresh_notification_bell()
            show_success(self, "Bakim karti guncellendi.")

    def open_photo_gallery(self):
        row = self.table.currentRow()
        if row < 0:
            show_warning(self.window() or self, "Once bir bakim karti secin.")
            return
        card_id = int(self.table.item(row, 0).text())
        plate = self.table.item(row, 2).text()
        dlg = VehicleMaintenancePhotoGalleryDialog(self.db, card_id, plate, self.window())
        dlg.exec()

    def open_history_qr(self):
        row = self.table.currentRow()
        if row < 0:
            show_warning(self.window() or self, "Once bir bakim karti secin.")
            return
        plate = self.table.item(row, 2).text()
        dlg = VehicleHistoryQrDialog(self.db, plate, self.window())
        dlg.exec()

    def open_context_menu(self, pos):
        if not is_context_menu_enabled(self.db):
            return
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        self.table.selectRow(row)
        menu = QMenu(self)
        menu.addAction("Bakim Kartini Ac").triggered.connect(lambda: self._open_selected_card(row, 0))
        menu.addAction("Foto Galeri").triggered.connect(self.open_photo_gallery)
        menu.addAction("QR / Gecmis").triggered.connect(self.open_history_qr)
        menu.addSeparator()
        menu.addAction("Excel'e Aktar").triggered.connect(self.export_to_excel)
        menu.addAction("PDF Olustur").triggered.connect(self.export_to_pdf)
        menu.addAction("Yazdir").triggered.connect(self.print_table)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _collect_table_rows(self):
        rows = []
        for row_idx in range(self.table.rowCount()):
            rows.append(
                {
                    "ID": self.table.item(row_idx, 0).text() if self.table.item(row_idx, 0) else "",
                    "Musteri": self.table.item(row_idx, 1).text() if self.table.item(row_idx, 1) else "",
                    "Plaka": self.table.item(row_idx, 2).text() if self.table.item(row_idx, 2) else "",
                    "Arac": self.table.item(row_idx, 3).text() if self.table.item(row_idx, 3) else "",
                    "Bakim Tarihi": self.table.item(row_idx, 4).text() if self.table.item(row_idx, 4) else "",
                    "Sonraki Bakim": self.table.item(row_idx, 5).text() if self.table.item(row_idx, 5) else "",
                    "Muayene": self.table.item(row_idx, 6).text() if self.table.item(row_idx, 6) else "",
                    "Yaklasan KM": self.table.item(row_idx, 7).text() if self.table.item(row_idx, 7) else "",
                    "Taslak Randevu": self.table.item(row_idx, 8).text() if self.table.item(row_idx, 8) else "",
                    "Hatirlatma": self.table.item(row_idx, 9).text() if self.table.item(row_idx, 9) else "",
                    "Foto": self.table.item(row_idx, 10).text() if self.table.item(row_idx, 10) else "",
                }
            )
        return rows

    def export_to_excel(self):
        try:
            rows = self._collect_table_rows()
            if not rows:
                show_warning(self, "Aktarilacak bakim karti bulunamadi.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Olarak Kaydet",
                f"arac_bakim_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel Dosyasi (*.xlsx)",
            )
            if not path:
                return
            df = pd.DataFrame(rows)
            df.to_excel(path, index=False)
            show_success(self, "Bakim listesi disa aktarildi.")
        except Exception as e:
            show_warning(self, f"Excel aktarim hatasi: {e}")

    def _build_html_report(self):
        rows = self._collect_table_rows()
        company_name = str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro").strip() or "AYEC Pro"
        logo_path = str(self.db.get_setting("logo_path", "") or "").strip()
        logo_html = ""
        if logo_path and os.path.exists(logo_path):
            logo_url = logo_path.replace("\\", "/")
            logo_html = f"<img src='file:///{logo_url}' style='height:56px; max-width:180px; object-fit:contain;' />"

        columns = [
            ("ID", "6%"),
            ("Musteri", "15%"),
            ("Plaka", "9%"),
            ("Arac", "12%"),
            ("Bakim Tarihi", "10%"),
            ("Sonraki Bakim", "10%"),
            ("Muayene", "8%"),
            ("Yaklasan KM", "8%"),
            ("Taslak Randevu", "10%"),
            ("Hatirlatma", "8%"),
            ("Foto", "4%"),
        ]
        body_rows = []
        for row in rows:
            cells = []
            for key, _ in columns:
                cells.append(f"<td>{html.escape(str(row.get(key, '') or '—'))}</td>")
            body_rows.append("<tr>" + "".join(cells) + "</tr>")
        headers = "".join(f"<th style='width:{width};'>{html.escape(label)}</th>" for label, width in columns)
        return f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    color: #0f172a;
                    margin: 20px 24px;
                }}
                .topbar {{
                    border-bottom: 2px solid #0ea5a4;
                    padding-bottom: 12px;
                    margin-bottom: 14px;
                }}
                .brand {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .brand td {{
                    vertical-align: middle;
                }}
                .title {{
                    font-size: 20pt;
                    font-weight: 800;
                    margin: 0;
                }}
                .subtitle {{
                    margin-top: 4px;
                    font-size: 9pt;
                    color: #475569;
                }}
                .meta {{
                    text-align: right;
                    font-size: 9pt;
                    color: #0f172a;
                }}
                .stats {{
                    margin: 12px 0 14px 0;
                }}
                .stat {{
                    display: inline-block;
                    min-width: 120px;
                    margin-right: 10px;
                    background: #f8fafc;
                    border: 1px solid #cbd5e1;
                    border-radius: 10px;
                    padding: 9px 11px;
                }}
                .stat-label {{
                    font-size: 8pt;
                    color: #64748b;
                    text-transform: uppercase;
                }}
                .stat-value {{
                    margin-top: 2px;
                    font-size: 15pt;
                    font-weight: 800;
                    color: #0f172a;
                }}
                table.report {{
                    width: 100%;
                    border-collapse: collapse;
                    table-layout: fixed;
                    font-size: 8.6pt;
                }}
                table.report thead th {{
                    background: #e2e8f0;
                    color: #0f172a;
                    border: 1px solid #cbd5e1;
                    padding: 8px 6px;
                    text-align: left;
                    font-weight: 800;
                    white-space: normal;
                }}
                table.report tbody td {{
                    border: 1px solid #dbe4ee;
                    padding: 8px 6px;
                    vertical-align: top;
                    word-break: break-word;
                    white-space: normal;
                }}
                table.report tbody tr:nth-child(even) {{
                    background: #f8fafc;
                }}
                .footer {{
                    margin-top: 12px;
                    text-align: right;
                    font-size: 8.5pt;
                    color: #64748b;
                }}
            </style>
        </head>
        <body>
            <div class='topbar'>
                <table class='brand'>
                    <tr>
                        <td>
                            {logo_html}
                            <div class='title'>{html.escape(company_name)} - Arac Bakim Listesi</div>
                            <div class='subtitle'>Arac bakim, muayene ve hatirlatma kartlarinin toplu ozeti</div>
                        </td>
                        <td class='meta'><b>Olusturma Tarihi</b><br>{datetime.now().strftime('%d.%m.%Y %H:%M')}</td>
                    </tr>
                </table>
            </div>
            <div class='stats'>
                <div class='stat'><div class='stat-label'>Toplam Kart</div><div class='stat-value'>{len(rows)}</div></div>
                <div class='stat'><div class='stat-label'>Yaklasan Bakim</div><div class='stat-value'>{self.stat_labels['Yaklasan Bakim'].text()}</div></div>
                <div class='stat'><div class='stat-label'>Muayene Yakini</div><div class='stat-value'>{self.stat_labels['Muayene Yakini'].text()}</div></div>
                <div class='stat'><div class='stat-label'>Acik Is Emri</div><div class='stat-value'>{self.stat_labels['Acik Is Emri'].text()}</div></div>
            </div>
            <table class='report' cellspacing='0' cellpadding='0'>
                <thead><tr>{headers}</tr></thead>
                <tbody>{''.join(body_rows)}</tbody>
            </table>
            <div class='footer'>{html.escape(company_name)} | AYEC Pro Arac Bakim Raporu</div>
        </body>
        </html>
        """

    def export_to_pdf(self):
        try:
            if self.table.rowCount() == 0:
                show_warning(self, "PDF icin veri bulunamadi.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "PDF Olarak Kaydet",
                f"arac_bakim_{datetime.now().strftime('%Y%m%d')}.pdf",
                "PDF Dosyasi (*.pdf)",
            )
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            doc = QTextDocument()
            doc.setHtml(self._build_html_report())
            doc.print(printer)
            show_success(self, "PDF olusturuldu.")
        except Exception as e:
            show_warning(self, f"PDF olusturma hatasi: {e}")

    def print_table(self):
        try:
            if self.table.rowCount() == 0:
                show_warning(self, "Yazdirilacak veri bulunamadi.")
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_html_report())
            doc.print(printer)
            show_info(self, "Bakim listesi yazdirmaya gonderildi.")
        except Exception as e:
            show_warning(self, f"Yazdirma hatasi: {e}")
