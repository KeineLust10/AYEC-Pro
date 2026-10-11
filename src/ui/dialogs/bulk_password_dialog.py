"""Explicit bulk password editing using the existing account and password backend."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QLineEdit, QCheckBox, QHeaderView, QPushButton

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.reference_checkbox import ReferenceCheckBox
from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.ui.widgets.toast_notification import show_toast
from src.utils.role_utils import is_admin_role
from src.utils.theme_colors import theme_qss
from src.utils.user_account_actions import current_account_administrator, change_account_passwords


class BulkPasswordDialog(ModernDialog):
    def __init__(self, db, actor_id, parent=None):
        super().__init__(title="Toplu Parola Degistirme", parent=parent, width=1020, height=680)
        self.db = db
        self.actor_id = actor_id
        self.account_controls = {}
        note = QLabel("Her secili hesap icin farkli ve guclu bir parola girin. Eski parolalar ve hatirlanan giris belirtecleri gecersiz olur; acik oturumlar kapanmaz. Yonetici ve Master hesaplari bu toplu islemin disindadir.")
        note.setWordWrap(True)
        note.setTextFormat(Qt.TextFormat.PlainText)
        self.content_layout.addWidget(note)
        select_all = QPushButton("Uygun Hesaplari Sec")
        select_all.clicked.connect(self._select_eligible_accounts)
        self.content_layout.addWidget(select_all)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Sec", "Kullanici", "Personel", "Rol", "Hesap", "Yeni Parola"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 44)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { background: @finance_surface; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; }"
            "QHeaderView::section { background: @finance_surface_alt; color: @finance_text_muted; padding: 6px; border: none; }"
            "QLineEdit { background: @finance_surface_alt; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; padding: 5px; }"
        ))
        rows = db.conn.execute("SELECT u.id, u.username, p.name, u.role, COALESCE(u.active, 1) FROM users u LEFT JOIN personnel p ON p.id=u.personnel_id ORDER BY u.id").fetchall()
        self.table.setRowCount(len(rows))
        for index, (user_id, username, name, role, active) in enumerate(rows):
            eligible = str(user_id) != str(actor_id) and not is_admin_role(role)
            checkbox = ReferenceCheckBox()
            checkbox.setAccessibleName(f"Hesabi sec: {username}")
            checkbox.setEnabled(eligible)
            checkbox.toggled.connect(self._update_selection)
            self.table.setCellWidget(index, 0, checkbox)
            for column, text in enumerate((username, name or "-", role, "Aktif" if active else "Pasif"), 1):
                self.table.setItem(index, column, QTableWidgetItem(str(text)))
            password = QLineEdit()
            password.setEchoMode(QLineEdit.EchoMode.Password)
            password.setAccessibleName(f"Yeni parola: {username}")
            password.setEnabled(eligible)
            password.setPlaceholderText("En az 10 karakter")
            self.table.setCellWidget(index, 5, password)
            self.account_controls[user_id] = (checkbox, password)
        self.content_layout.addWidget(self.table, 1)
        self.selection_label = QLabel("0 hesap secildi")
        self.content_layout.addWidget(self.selection_label)
        self.add_button("Iptal", "secondary", self.reject)
        self.apply_button = self.add_button("Secili Parolalari Degistir", "primary", self._apply_passwords)
        self.apply_button.setEnabled(False)

    def _select_eligible_accounts(self):
        for checkbox, _password in self.account_controls.values():
            checkbox.setChecked(checkbox.isEnabled())

    def _update_selection(self, *_args):
        if not hasattr(self, "apply_button"):
            return
        count = sum(checkbox.isChecked() for checkbox, _password in self.account_controls.values())
        self.selection_label.setText(f"{count} hesap secildi")
        self.apply_button.setEnabled(count > 0)

    def _apply_passwords(self):
        context = current_account_administrator(self, self.db)
        if not context or str(context["id"]) != str(self.actor_id):
            show_toast(self, "Yonetici oturumu dogrulanamadi.", "error")
            return
        changes = [(user_id, password.text()) for user_id, (checkbox, password) in self.account_controls.items() if checkbox.isChecked() and checkbox.isEnabled()]
        if not changes:
            return
        confirm = ModernConfirmDialog("Parola Degisikliklerini Onayla", f"{len(changes)} hesabin parolasi degisecek. Kayitli giris belirtecleri iptal edilecek. Devam edilsin mi?", self, confirm_text="Parolalari Degistir", cancel_text="Geri Don", destructive=True)
        if not confirm.exec():
            return
        context = current_account_administrator(self, self.db)
        if not context or str(context["id"]) != str(self.actor_id):
            return
        try:
            count = change_account_passwords(self.db, self.actor_id, changes)
            for _checkbox, password in self.account_controls.values():
                password.clear()
            show_toast(self.parentWidget(), f"{count} yerel hesap parolasi guncellendi.", "success")
            self.accept()
        except Exception as exc:
            show_toast(self, f"Parolalar degistirilmedi: {exc}", "error")
