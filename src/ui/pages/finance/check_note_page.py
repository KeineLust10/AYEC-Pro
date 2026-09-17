# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QDialog,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QDateEdit,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss, qc
from src.utils.toast_notification import show_success, show_error
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper



class CheckNotePage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.init_ui()

    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, amount_try):
        return CurrencyHelper.format_from_try(amount_try, db=self.db, currency_code=self._display_currency())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        header_layout = QHBoxLayout()
        title = QLabel("Çek & Senet Takibi")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("""
            QLabel {
                color: @text;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 @surface_alt, stop:1 @selection_bg);
                border-radius: 8px;
            }
        """))
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_add = QPushButton("Yeni Ekle")
        btn_add.clicked.connect(self.open_add_dialog)
        btn_add.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @success;
                color: @selection_text;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: @success; }
        """))
        header_layout.addWidget(btn_add)
        layout.addLayout(header_layout)

        filter_layout = QHBoxLayout()
        self.filter_status = QComboBox()
        self.filter_status.addItems(["Tümü", "Portföyde", "Tahsil Edildi", "Ciro Edildi", "Ödendi", "Karşılıksız", "İade"])
        self.filter_status.currentTextChanged.connect(self.load_data)
        filter_layout.addWidget(QLabel("Durum Filtresi:"))
        filter_layout.addWidget(self.filter_status)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Tür", "Yön", "Banka/Şube", "Tutar", "Vade Tarihi", "Keşideci/Borçlu", "Alıcı", "Durum", "İşlemler"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.cellDoubleClicked.connect(self.on_row_double_click)
        layout.addWidget(self.table)

        self.load_data()

    def _normalize_status_filter(self, current: str):
        mapping = {
            "Tümü": None,
            "Portföyde": "Portföyde",
            "Tahsil Edildi": "Tahsil Edildi",
            "Ciro Edildi": "Ciro Edildi",
            "Ödendi": "Ödendi",
            "Karşılıksız": "Karşılıksız",
            "İade": "İade",
        }
        return mapping.get(current)

    def open_add_dialog(self):
        dlg = AddCheckDialog(self.db, self)
        if dlg.exec():
            self.load_data()

    def load_data(self):
        status = self._normalize_status_filter(self.filter_status.currentText())
        try:
            rows = self.db.get_checks_notes(status_filter=status) or []
        except Exception as e:
            show_error(self, f"Veri yüklenirken hata: {e}")
            rows = []

        self.table.setRowCount(0)
        for idx_row, row in enumerate(rows):
            # Ensure row supports .get by converting to a dictionary type, handling sqlite3.Row specifically
            try:
                row_dict = dict(row)
            except Exception:
                row_dict = row if isinstance(row, dict) else {}
                
            rid = row["id"] if "id" not in row_dict else row_dict["id"]
            rtype = str(row_dict.get("type", ""))
            rdir = str(row_dict.get("direction", ""))
            bank = str(row_dict.get("bank_name", "") or "")
            branch = str(row_dict.get("branch_name", "") or "")
            bank_info = f"{bank} / {branch}".strip(" /")
            amount = float(row_dict.get("amount", 0) or 0)
            amount_str = self._format_display_money(amount)
            due = str(row_dict.get("due_date", "") or "")
            issuer = str(row_dict.get("issuer", "") or "")
            recipient = str(row_dict.get("recipient", "") or "")
            status_text = str(row_dict.get("status", "") or "")

            r = self.table.rowCount()
            self.table.insertRow(r)
            it0 = QTableWidgetItem(rtype)
            it0.setData(Qt.ItemDataRole.UserRole, rid)
            self.table.setItem(r, 0, it0)
            self.table.setItem(r, 1, QTableWidgetItem(rdir))
            self.table.setItem(r, 2, QTableWidgetItem(bank_info))
            self.table.setItem(r, 3, QTableWidgetItem(amount_str))
            self.table.setItem(r, 4, QTableWidgetItem(due))
            self.table.setItem(r, 5, QTableWidgetItem(issuer))
            self.table.setItem(r, 6, QTableWidgetItem(recipient))

            status_item = QTableWidgetItem(status_text)
            if status_text in ("Tahsil Edildi", "Ödendi"):
                status_item.setForeground(qc("success"))
            elif status_text == "Karşılıksız":
                status_item.setForeground(qc("selection_text"))
                status_item.setBackground(qc("danger"))
            elif status_text == "Ciro Edildi":
                status_item.setForeground(qc("accent"))
            elif status_text == "Portföyde":
                status_item.setForeground(qc("warning"))
            elif status_text == "İade":
                status_item.setForeground(qc("text_muted"))
            status_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

            self.table.setItem(r, 7, status_item)
            self.table.setItem(r, 8, QTableWidgetItem(""))

    def open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=101):
            return
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        check_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        current_status = self.table.item(row, 7).text()

        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        menu = QMenu()
        detail_action = QAction("Detay Görüntüle", self)
        detail_action.triggered.connect(lambda: self.show_details(check_id))
        menu.addAction(detail_action)
        menu.addSeparator()

        status_menu = menu.addMenu("Durum Değiştir")
        statuses = ["Portföyde", "Tahsil Edildi", "Ciro Edildi", "Ödendi", "Karşılıksız", "İade"]
        for st in statuses:
            if st == current_status:
                continue
            action = QAction(st, self)
            action.triggered.connect(lambda checked, new_status=st: self.change_status(check_id, new_status))
            status_menu.addAction(action)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def change_status(self, check_id, new_status):
        if not self.db.update_check_status(check_id, new_status):
            show_error(self.main_window, "Durum güncellenemedi.")
            return

        if new_status in ["Tahsil Edildi", "Ödendi", "Ciro Edildi"]:
            try:
                self.db.cursor.execute(
                    "SELECT type, direction, amount, bank_name, issuer, recipient FROM checks_notes WHERE id=?",
                    (check_id,),
                )
                row = self.db.cursor.fetchone()
                if row:
                    c_type = str(row[0] or "")
                    direction = str(row[1] or "")
                    amount = float(row[2] or 0.0)
                    bank = str(row[3] or "")
                    issuer = str(row[4] or "")
                    recipient = str(row[5] or "")
                    
                    # 'Alınan' çek tahsil edilince Kasa ARTAR (Gelir), Çek/Senet AZALIR (Gider)
                    # 'Verilen' çek ödenince Kasa AZALIR (Gider), Çek/Senet ARTAR (Gelir - Borç kapanır)
                    if direction == "Giriş (Alınan)" and new_status == "Tahsil Edildi":
                        bank_txn_type = "Gelir"
                        rev_txn_type = "Gider"
                    elif direction == "Çıkış (Verilen)" and new_status == "Ödendi":
                        bank_txn_type = "Gider"
                        rev_txn_type = "Gelir"
                    elif new_status == "Ciro Edildi":
                        # Ciro: Alınan çek başkasına verilir. Çek/Senet AZALIR (Gider). Kasa etkilenmez (genelde).
                        bank_txn_type = None
                        rev_txn_type = "Gider"
                    else:
                        bank_txn_type = None
                        rev_txn_type = None
                    
                    bank_id = None
                    if bank_txn_type: # Only ask for bank selection if there's a bank transaction
                        try:
                            if hasattr(self.db, 'get_bank_accounts'):
                                banks = self.db.get_bank_accounts()
                                if banks:
                                    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel
                                    dlg = QDialog(self.main_window)
                                    dlg.setWindowTitle("Banka/Kasa Seçimi")
                                    dlg.setStyleSheet("background-color: white; border-radius: 8px;")
                                    layout = QVBoxLayout(dlg)
                                    amount_text = self._format_display_money(amount)
                                    layout.addWidget(QLabel(f"Bu işlem banka/kasa bakiyenizi etkileyecektir ({amount_text} {bank_txn_type}).\nLütfen işlem yapılacak hesabı seçiniz:"))
                                    cmb = QComboBox(dlg)
                                    cmb.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
                                    cmb.addItem("Banka/Kasa Seçmeyin (Sadece Statü Değiştir)", -1)
                                    for b in banks:
                                        bid = b.get('id') if isinstance(b, dict) else b[0]
                                        bname = b.get('bank_name') if isinstance(b, dict) else b[1]
                                        cmb.addItem(bname, bid)
                                    layout.addWidget(cmb)
                                    b_ok = QPushButton("Onayla", dlg)
                                    b_ok.setStyleSheet("background-color: #3b82f6; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
                                    b_ok.clicked.connect(dlg.accept)
                                    layout.addWidget(b_ok)
                                    if dlg.exec():
                                        selected = cmb.currentData()
                                        if selected != -1:
                                            bank_id = selected
                        except Exception as e:
                            logger.error(f"Banka seçim dialogu hatası: {e}")

                    customer_name = issuer if direction == "Giriş (Alınan)" else recipient
                    desc_base = f"{c_type} {new_status} - {bank} - {issuer}/{recipient} (ID: {check_id})"

                    if rev_txn_type:
                        # 1. Ters Kayıt (Çek/Senet portföyden çıkışı)
                        self.db.add_transaction(
                            t_type=rev_txn_type,
                            category=f"{c_type} Portföy Çıkışı",
                            amount=amount,
                            description=f"{desc_base} - Portföy Çıkışı",
                            customer_name=customer_name,
                            payment_method="Çek/Senet"
                        )
                    
                    if bank_txn_type and bank_id is not None:
                        # 2. Banka/Kasa Kaydı (Gerçek para hareketi)
                        self.db.add_transaction(
                            t_type=bank_txn_type,
                            category=f"Banka/Kasa Hareketi ({c_type})",
                            amount=amount,
                            description=f"{desc_base} - Kasa İşlemi",
                            bank_account_id=bank_id,
                            customer_name=customer_name,
                            payment_method="Çek/Senet"
                        )
                        
                    if rev_txn_type or (bank_txn_type and bank_id is not None):
                        show_success(self.main_window, "Finans/Kasa kayıtları oluşturuldu.")
            except Exception as e:
                logger.error(f"Finans kaydı oluşturulurken hata: {e}")

        show_success(self.main_window, f"Durum güncellendi: {new_status}")
        self.load_data()

    def on_row_double_click(self, row, col):
        check_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.show_details(check_id)

    def show_details(self, check_id):
        dlg = QDialog(self)
        dlg.setWindowTitle("Çek / Senet Detay")
        dlg.setFixedSize(420, 320)
        dlg.setStyleSheet(theme_qss("background: @surface;"))

        layout = QVBoxLayout(dlg)
        found_data = {}
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == check_id:
                found_data = {
                    'Tür': self.table.item(r, 0).text(),
                    'Yön': self.table.item(r, 1).text(),
                    'Banka': self.table.item(r, 2).text(),
                    'Tutar': self.table.item(r, 3).text(),
                    'Vade': self.table.item(r, 4).text(),
                    'Keşideci/Borçlu': self.table.item(r, 5).text(),
                    'Alıcı': self.table.item(r, 6).text(),
                    'Durum': self.table.item(r, 7).text(),
                }
                break

        if not found_data:
            return

        form = QFormLayout()
        for k, v in found_data.items():
            form.addRow(f"<b>{k}:</b>", QLabel(v))
        layout.addLayout(form)

        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(dlg.accept)
        btn_close.setStyleSheet(theme_qss("background-color: @surface_alt; color: @text; padding: 8px; border-radius: 4px;"))
        layout.addWidget(btn_close)
        dlg.exec()


class AddCheckDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)

    def __init__(self, db, parent=None):
        super().__init__(parent, title="Çek / Senet Girişi", width=450, height=580)
        self.db = db
        self.set_footer_visible(True, 68)
        self.setup_ui()

        self._wire_ui_signals()

    def setup_ui(self):
        form = QFormLayout()

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Çek", "Senet"])
        form.addRow("Evrak Tipi:", self.cmb_type)

        self.cmb_dir = QComboBox()
        self.cmb_dir.addItems(["Giriş (Alınan)", "Çıkış (Verilen)"])
        form.addRow("Yön:", self.cmb_dir)

        self.txt_amount = QDoubleSpinBox()
        self.txt_amount.setRange(0, 100000000)
        self.txt_amount.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        form.addRow("Tutar:", self.txt_amount)

        self.txt_bank = QLineEdit()
        form.addRow("Banka:", self.txt_bank)

        self.txt_branch = QLineEdit()
        form.addRow("Şube:", self.txt_branch)

        self.txt_issuer = QLineEdit()
        form.addRow("Keşideci/Borçlu:", self.txt_issuer)

        self.txt_recipient = QLineEdit()
        form.addRow("Alıcı:", self.txt_recipient)

        self.date_due = QDateEdit()
        self.date_due.setCalendarPopup(True)
        self.date_due.setDate(QDate.currentDate())
        form.addRow("Vade Tarihi:", self.date_due)

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Portföyde", "Tahsil Edildi", "Ciro Edildi", "Ödendi", "Karşılıksız", "İade"])
        form.addRow("Durum:", self.cmb_status)

        self.content_layout.addLayout(form)
        self.clear_footer()
        self.add_cancel_button("Iptal")
        self.add_button("Kaydet", "success", self.save)

    def _wire_ui_signals(self):
        self.cmb_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_dir.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_status.currentIndexChanged.connect(self._on_ui_widget_changed)

    def save(self):
        data = {
            "type": self.cmb_type.currentText(),
            "direction": self.cmb_dir.currentText(),
            "amount": float(self.txt_amount.value()),
            "bank_name": self.txt_bank.text().strip(),
            "branch_name": self.txt_branch.text().strip(),
            "issuer": self.txt_issuer.text().strip(),
            "recipient": self.txt_recipient.text().strip(),
            "due_date": self.date_due.date().toString("yyyy-MM-dd"),
            "status": self.cmb_status.currentText(),
        }

        if data["amount"] <= 0:
            show_error(self, "Tutar 0'dan buyuk olmalidir.")
            return
        if not data["issuer"] and not data["recipient"]:
            show_error(self, "Kesideci/Borclu veya Alici alanlarindan en az biri doldurulmalidir.")
            return

        try:
            if self.db.add_check_note(data):
                # Türkiye Finans/Muhasebe Standartlarına Göre İlk Kayıt:
                # Çek/Senet alındığında "Alınan Çekler/Senetler" hesabına (Gelir yansıması/Varlık artışı)
                # Çek/Senet verildiğinde "Verilen Çekler/Senetler" hesabına (Gider yansıması/Yükümlülük artışı) kaydedilir.
                try:
                    c_type = data["type"]
                    direction = data["direction"]
                    amount = data["amount"]
                    issuer = data["issuer"]
                    recipient = data["recipient"]
                    
                    if direction == "Giriş (Alınan)":
                        txn_type = "Gelir"
                        category = f"Alınan {c_type}"
                        desc = f"{c_type} Alındı - Düzenleyen: {issuer} (Vade: {data['due_date']})"
                        customer_name = issuer if issuer else None
                    else:
                        txn_type = "Gider"
                        category = f"Verilen {c_type}"
                        desc = f"{c_type} Verildi - Alıcı: {recipient} (Vade: {data['due_date']})"
                        customer_name = recipient if recipient else None
                        
                    self.db.add_transaction(
                        t_type=txn_type,
                        category=category,
                        amount=amount,
                        description=desc,
                        customer_name=customer_name,
                        payment_method="Çek/Senet"
                    )
                except Exception as fin_err:
                    logger.error(f"Çek/Senet finans ilk kayıt hatası: {fin_err}")
                    
                show_success(self, "Kayıt eklendi ve finans modülüne işlendi.")
                self.accept()
            else:
                show_error(self, "Kayıt eklenemedi.")
        except Exception as e:
            show_error(self, f"Kaydetme hatası: {e}")
