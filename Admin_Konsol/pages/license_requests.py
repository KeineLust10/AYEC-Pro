"""Admin approval page for manually verified license payments."""
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QFrame, QGridLayout, QMessageBox,
)

import api_client
from product_catalog import product_code


class _OrdersWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, status, product_code=''):
        super().__init__()
        self.status = status
        self.product_code = product_code

    def run(self):
        try:
            self.done.emit(api_client.license_orders(self.status, self.product_code))
        except Exception as error:
            self.failed.emit(str(error))


class _DecisionWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, order_id, approved, note, plan_code=""):
        super().__init__()
        self.order_id = order_id
        self.approved = approved
        self.note = note
        self.plan_code = plan_code

    def run(self):
        try:
            if self.approved:
                self.done.emit(api_client.approve_license_order(self.order_id, self.note, self.plan_code))
            else:
                self.done.emit(api_client.reject_license_order(self.order_id, self.note))
        except Exception as error:
            self.failed.emit(str(error))


class _CancelWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, order_id, note):
        super().__init__()
        self.order_id = int(order_id)
        self.note = str(note or "")

    def run(self):
        try:
            self.done.emit(api_client.cancel_license_order(self.order_id, self.note))
        except Exception as error:
            self.failed.emit(str(error))


class LicenseRequestsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.orders = []
        self.worker = None
        self._build()
        self.reload()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Lisans Talepleri")
        title.setObjectName("pageTitle")
        title_box.addWidget(title)
        subtitle = QLabel(
            "Musteri odemelerini inceleyin, lisansi kontrollu bicimde etkinlestirin."
        )
        subtitle.setObjectName("sectionTitle")
        title_box.addWidget(subtitle)
        top.addLayout(title_box)
        top.addStretch()
        self.status_filter = QComboBox()
        self.status_filter.setObjectName("combo")
        self.status_filter.addItem("Tum talepler", "")
        self.status_filter.addItem("Odeme bildirildi", "payment_reported")
        self.status_filter.addItem("Odeme bekleniyor", "payment_pending")
        self.status_filter.addItem("Onaylandi", "approved")
        self.status_filter.addItem("Reddedildi", "rejected")
        self.status_filter.addItem("Iptal edildi", "cancelled")
        self.status_filter.currentIndexChanged.connect(self.reload)
        top.addWidget(self.status_filter)
        refresh = QPushButton("Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self.reload)
        top.addWidget(refresh)
        root.addLayout(top)

        info = QFrame()
        info.setObjectName("detailCard")
        info_lay = QHBoxLayout(info)
        info_lay.setContentsMargins(16, 12, 16, 12)
        info_lay.addWidget(QLabel("1"), 0)
        info_text = QLabel(
            "Bir satiri secin. Hucreler bilerek salt okunurdur; duzenleme ve onay "
            "islemleri asagidaki guvenli islem alanindan yapilir."
        )
        info_text.setObjectName("cardDetail")
        info_text.setWordWrap(True)
        info_lay.addWidget(info_text, 1)
        root.addWidget(info)

        summary = QHBoxLayout()
        summary.setSpacing(12)
        self._summary_labels = {}
        for key, title_text in (
            ("total", "Toplam talep"),
            ("paid", "Odeme bildirildi"),
            ("pending", "Inceleme bekliyor"),
        ):
            card = QFrame()
            card.setObjectName("metricCard")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(16, 12, 16, 12)
            label = QLabel(title_text)
            label.setObjectName("metricTitle")
            value = QLabel("0")
            value.setObjectName("detailTitle")
            card_lay.addWidget(label)
            card_lay.addWidget(value)
            summary.addWidget(card, 1)
            self._summary_labels[key] = value
        root.addLayout(summary)

        self.table = QTableWidget(0, 12)
        self.table.setObjectName("dataTable")
        self.table.setHorizontalHeaderLabels([
            "Talep No", "Firma", "Yetkili", "Paket", "Tutar", "Referans",
            "Lisans Kodu", "Durum", "Konum", "Tarih", "Islem", "ID",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in ((0, 132), (1, 160), (2, 112), (3, 150),
                              (4, 108), (5, 142), (6, 170), (7, 100), (8, 150)):
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 170)
        header.setStretchLastSection(False)
        self.table.setColumnHidden(11, True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._show_selected)
        root.addWidget(self.table, 1)

        action_card = QFrame()
        action_card.setObjectName("formCard")
        action_root = QVBoxLayout(action_card)
        action_root.setContentsMargins(18, 14, 18, 14)
        self.selection_label = QLabel("Bir lisans talebi secin.")
        self.selection_label.setObjectName("panelTitle")
        action_root.addWidget(self.selection_label)
        actions = QHBoxLayout()
        actions.addWidget(QLabel("Onay paketi:"))
        self.plan = QComboBox()
        self.plan.setObjectName("combo")
        self.plan.addItem("Talepteki paket", "")
        self.plan.addItem("Aylik", "monthly")
        self.plan.addItem("6 Aylik", "six_months")
        self.plan.addItem("1 Yillik", "one_year")
        self.plan.addItem("2 Yillik", "two_years")
        self.plan.addItem("3 Yillik", "three_years")
        actions.addWidget(self.plan)
        actions.addWidget(QLabel("Yonetici notu:"))
        self.note = QLineEdit()
        self.note.setPlaceholderText("Odeme kontrol notu")
        actions.addWidget(self.note, 1)
        self.approve = QPushButton("Lisans Uret ve Etkinlestir")
        self.approve.setObjectName("primaryBtn")
        self.approve.clicked.connect(lambda: self.decide(True))
        actions.addWidget(self.approve)
        self.reject = QPushButton("Talebi Reddet")
        self.reject.setObjectName("dangerBtn")
        self.reject.clicked.connect(lambda: self.decide(False))
        actions.addWidget(self.reject)
        action_root.addLayout(actions)
        root.addWidget(action_card)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

    def reload(self):
        worker = _OrdersWorker(self.status_filter.currentData(), getattr(self, 'product_code', ''))
        worker.done.connect(self.populate)
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.worker = worker

    def set_product_filter(self, product_name: str):
        self.product_code = product_code(product_name)
        self.reload()

    def populate(self, orders):
        self.orders = orders
        self.table.setRowCount(0)
        paid_count = 0
        pending_count = 0
        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            amount = float(order.get("amount_try") or 0)
            values = [
                order.get("request_no", "-"),
                order.get("company_name", "-"),
                order.get("requester_name", "-"),
                order.get("plan_label", "-"),
                f"{amount:,.2f} TRY",
                order.get("payment_reference", "-"),
                order.get("license_code", "-") or "-",
                order.get("status", "-"),
                order.get("location_json", "-") if order.get("location_json") not in (None, "", "{}") else "-",
                order.get("created_at", "-"),
                "",
                str(order.get("id", "")),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
            self.table.item(row, 8).setToolTip(str(order.get("location_json") or "Konum bilgisi yok"))
            status = str(order.get("status") or "")
            cancel_button = QPushButton(
                "Iptal Edildi" if status == "cancelled" else "Lisansi Iptal Et"
            )
            cancel_button.setObjectName("tableDangerBtn")
            cancel_button.setEnabled(status == "active")
            cancel_button.clicked.connect(
                lambda _, current=dict(order): self.cancel_license(current)
            )
            self.table.setCellWidget(row, 10, cancel_button)
            if status in {"payment_reported", "active", "approved"}:
                paid_count += 1
            if status in {"payment_pending", "payment_reported"}:
                pending_count += 1
        self._summary_labels["total"].setText(str(len(orders)))
        self._summary_labels["paid"].setText(str(paid_count))
        self._summary_labels["pending"].setText(str(pending_count))
        self.status_label.setText(f"{len(orders)} lisans talebi listelendi.")
        if orders:
            self.table.selectRow(0)
        else:
            self.selection_label.setText("Bir lisans talebi secin.")

    def _show_selected(self):
        row = self.table.currentRow()
        if row < 0:
            self.selection_label.setText("Bir lisans talebi secin.")
            return
        company = self.table.item(row, 1).text() if self.table.item(row, 1) else "-"
        plan = self.table.item(row, 3).text() if self.table.item(row, 3) else "-"
        status = self.table.item(row, 7).text() if self.table.item(row, 7) else "-"
        self.selection_label.setText(
            f"Secili talep: {company}  |  {plan}  |  Durum: {status}"
        )

    def selected_order_id(self):
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 11):
            return 0
        return int(self.table.item(row, 11).text() or 0)

    def cancel_license(self, order):
        if str(order.get("status") or "") != "active":
            self.status_label.setText("Yalnizca aktif bir lisans iptal edilebilir.")
            return
        company = str(order.get("company_name") or "-")
        answer = QMessageBox.question(
            self,
            "Lisans Iptali",
            f"{company} firmasinin lisansi iptal edilsin mi?\n\n"
            "Firma programda islem yapamayacak ve masaustune iptal bildirimi gonderilecek.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        note = self.note.text().strip() or "Yonetim panelinden iptal edildi."
        worker = _CancelWorker(int(order.get("id") or 0), note)
        worker.done.connect(self._cancel_done)
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.worker = worker

    def _cancel_done(self, _result):
        self.note.clear()
        self.status_label.setText("Lisans iptal edildi ve masaustune bildirim gonderildi.")
        self.reload()

    def decide(self, approved):
        order_id = self.selected_order_id()
        if not order_id:
            self.status_label.setText("Lutfen bir lisans talebi secin.")
            return
        worker = _DecisionWorker(
            order_id,
            approved,
            self.note.text().strip(),
            self.plan.currentData() if approved else "",
        )
        worker.done.connect(lambda result: self._decision_done(approved, result))
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.worker = worker

    def _decision_done(self, approved, result=None):
        self.note.clear()
        self.status_label.setText("Lisans onaylandi." if approved else "Lisans talebi reddedildi.")
        self.reload()
        if approved and isinstance(result, dict):
            if result.get("mail_sent"):
                QMessageBox.information(self, "Lisans onayi", "Lisans onaylandi. Musteriye info@ayecpro.com adresinden e-posta gonderildi.")
            else:
                QMessageBox.warning(self, "E-posta gonderilemedi", "Lisans onaylandi ancak e-posta gonderilemedi. " + str(result.get("mail_message") or "SMTP ayarlarini kontrol edin."))
