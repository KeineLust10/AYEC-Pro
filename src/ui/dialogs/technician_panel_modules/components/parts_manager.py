"""
Parca yonetimi modulu.
Teknisyen paneli icin parca kullanma ve kayit islemleri.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QPushButton, QTableWidgetItem

from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.toast_notification import show_toast


class PartsManager:
    """Teknisyen paneli icindeki kullanilan parca islevleri."""

    def __init__(
        self,
        db,
        tracking_no,
        table_used_parts,
        inp_part_cost,
        combo_parts,
        audit_logger,
        refresh_logs_callback,
    ):
        self.db = db
        self.tracking_no = tracking_no
        self.table_used_parts = table_used_parts
        self.inp_part_cost = inp_part_cost
        self.combo_parts = combo_parts
        self.audit_logger = audit_logger
        self.refresh_logs = refresh_logs_callback

    def _used_parts_query(self):
        query = "SELECT id, part_name, price, created_at FROM used_parts WHERE tracking_no=?"
        try:
            self.db.cursor.execute("PRAGMA table_info(used_parts)")
            cols = [row[1] for row in self.db.cursor.fetchall() or []]
            deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
        except Exception:
            pass
        return query

    @staticmethod
    def _extract_amount_from_label(text):
        if " - " not in text:
            return 0.0
        value_text = text.rsplit(" - ", 1)[1].strip()
        for code in ("USD", "EUR", "TRY"):
            symbol = CurrencyHelper.get_symbol(currency_code=code)
            if value_text.endswith(symbol):
                raw = value_text[: -len(symbol)].strip().replace(",", "")
                return float(raw or 0)
        return 0.0

    def load_used_parts(self):
        """Kullanilan parcalari tabloya yukle."""
        parts = self.db.cursor.execute(self._used_parts_query(), (self.tracking_no,)).fetchall()

        self.table_used_parts.setRowCount(0)
        total_parts_cost = 0.0

        for row_index, part in enumerate(parts):
            self.table_used_parts.insertRow(row_index)
            total_parts_cost += float(part[2] or 0)

            self.table_used_parts.setItem(row_index, 0, QTableWidgetItem(str(part[1])))
            self.table_used_parts.setItem(
                row_index,
                1,
                QTableWidgetItem(
                    CurrencyHelper.format_try_for_display(
                        float(part[2] or 0),
                        db=self.db,
                        include_try_reference=False,
                    )
                ),
            )
            self.table_used_parts.setItem(row_index, 2, QTableWidgetItem(str(part[3])))

            btn_del = QPushButton("SIL")
            btn_del.setFixedSize(65, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(
                "background-color: #ff7675; color: white; border-radius: 4px; font-weight: bold;"
            )
            btn_del.clicked.connect(lambda _checked=False, pid=part[0]: self.delete_used_part(pid))
            self.table_used_parts.setCellWidget(row_index, 3, btn_del)

        self.inp_part_cost.setText(
            CurrencyHelper.format_try_for_display(
                total_parts_cost,
                db=self.db,
                include_try_reference=False,
            )
        )

    def delete_used_part(self, part_id):
        """Kullanilan parca kaydini soft delete ile kaldir."""
        reply = ModernConfirmDialog(
            "Onay",
            "Secili parcayi silmek istediginize emin misiniz",
            self.table_used_parts,
        )

        if reply.exec() == QDialog.DialogCode.Accepted:
            try:
                remove_part = getattr(self.db, "remove_used_part", None)
                removed = (
                    remove_part(part_id)
                    if callable(remove_part)
                    else self.db.soft_delete_record("used_parts", "id", part_id)
                )
                if not removed:
                    raise RuntimeError("Parca kaydi silinemedi")

                show_toast(self.table_used_parts, "Parca kaydi silindi.", "success")

                if self.audit_logger:
                    self.audit_logger.log_action(
                        "devices",
                        "DELETE_PART",
                        f"Cihaz parca kaydi silindi ID: {part_id}",
                    )

                self.load_used_parts()
                if self.refresh_logs:
                    self.refresh_logs()
            except Exception as exc:
                show_toast(self.table_used_parts, f"Silme hatasi: {exc}", "error")

    def load_parts(self):
        """Parca listesini combobox'a yukle."""
        self.combo_parts.clear()
        try:
            parts = self.db.get_all_parts()
            for part in parts:
                self.combo_parts.addItem(
                    f"{part[1]} (Stok: {part[2]}) - "
                    f"{CurrencyHelper.format_try_for_display(part[3], db=self.db, include_try_reference=False)}",
                    part[0],
                )
        except Exception:
            pass

    def use_part(self):
        """Parca kullan ve stoktan dus."""
        part_id = self.combo_parts.currentData()
        if not part_id:
            return

        part_text = self.combo_parts.currentText()
        try:
            stock = int(part_text.split("Stok: ")[1].split(")")[0])
        except Exception:
            stock = 0

        if stock <= 0:
            show_toast(self.combo_parts, "Bu parca stokta yok!", "warning")
            return

        if self.db.use_part(part_id, 1, self.tracking_no):
            part_name = part_text.split(" (")[0]
            try:
                price = self._extract_amount_from_label(part_text)
            except Exception:
                price = 0.0

            self.db.add_log(self.tracking_no, "System", f"Parca kullanildi: {part_name}")
            self.db.add_used_part(self.tracking_no, part_name, price)
            self.load_parts()
            self.load_used_parts()
            if self.refresh_logs:
                self.refresh_logs()
            show_toast(self.combo_parts, f"{part_name} kullanildi.", "success")
        else:
            show_toast(self.combo_parts, "Parca kullanilamadi!", "error")
