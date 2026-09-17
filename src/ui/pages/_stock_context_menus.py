# -*- coding: utf-8 -*-
# _stock_context_menus.py
# Sağ tık menüleri işlemleri

import os
from PyQt6.QtWidgets import (
    QMenu,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import (
    show_success,
    show_error,
)
from src.utils.message_helper import show_question
from src.utils.context_menu_settings import is_context_menu_enabled
from src.ui.dialogs.modern_input_dialog import ModernInputDialog


class StockContextMenusMixin:
    """Sağ tık menüleri ve ilgili işlemler için mixin."""

    def show_history_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=50):
            return
        idx = self.table_hist.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        self.table_hist.selectRow(row)
        item = self.table_hist.item(row, 6)
        if item is None:
            return

        menu = QMenu()
        menu.addAction("📊 Excel'e Aktar").triggered.connect(
            self.export_history_to_excel
        )
        menu.addAction("📄 PDF Olarak Kaydet").triggered.connect(
            self.export_history_to_pdf
        )
        menu.addAction("🖨️ Yazdır").triggered.connect(self.print_history_table)
        menu.addSeparator()

        def _ask_delete_hist():
            from src.ui.dialogs.security_confirm_dialog import SecurityConfirmDialog
            dialog = SecurityConfirmDialog(
                self.db,
                "Geçmişten Kayıt Silme",
                "Bu geçmiş kaydını silmek için şifrenizi (Giriş Şifresi) girin.",
                self,
            )
            if dialog.exec():
                self.delete_history_context(row)

        menu.addAction("🗑️ Bu Hareket Kaydını Geçmişten Sil").triggered.connect(
            _ask_delete_hist
        )
        menu.exec(self.table_hist.viewport().mapToGlobal(pos))

    def delete_history_context(self, row):
        item_desc = self.table_hist.item(row, 6)
        item_date = self.table_hist.item(row, 7)
        if item_desc is None or item_date is None:
            return
        desc = item_desc.text()

        reply = show_question(
            self,
            "Hareketi Sil",
            "Bu işlem sadece log kaydını siler, finansı ve gerçek stoğu değiştirmez! Geçmiş kaydını silmek istediğinize emin misiniz?",
        )
        if reply:
            try:
                self.db.cursor.execute(
                    "UPDATE stock_movements SET is_deleted=1, deleted_at=datetime('now','localtime') WHERE description = ?",
                    (desc,),
                )
                self.db.conn.commit()
                show_success(self, "Hareket geçmişten silindi!")
                self.load_history()
                self.reload_data()
            except Exception as e:
                show_error(self, f"Silme hatası: {e}")

    def show_stock_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=50):
            return
        idx = self.table_stock.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        item_id = self._stock_part_id_from_row(row)
        item_name = self.table_stock.item(row, 2)
        if item_id is None or item_name is None:
            return
        i_id = item_id
        i_n = item_name.text()

        menu = QMenu()
        menu.addAction("📦 Stok Ekle/Çıkar").triggered.connect(
            lambda: self.update_stock_amount(i_id, i_n)
        )
        menu.addAction("✏️ Düzenle").triggered.connect(
            lambda: self.open_add_stock_dialog(int(i_id))
        )
        menu.addAction("📷 Fotoğrafı Görüntüle").triggered.connect(
            lambda: self._view_part_photo(i_id, i_n)
        )
        menu.addSeparator()
        menu.addAction("📄 PDF Olarak Kaydet").triggered.connect(
            self.export_stock_to_pdf
        )
        menu.addAction("🖨️ Yazdır").triggered.connect(self.print_stock_table)
        menu.addAction("📊 Excel'e Aktar").triggered.connect(self.export_to_excel)
        menu.addSeparator()

        def _ask_delete():
            from src.ui.dialogs.security_confirm_dialog import SecurityConfirmDialog
            dialog = SecurityConfirmDialog(
                self.db,
                "Stok Silme Onayı",
                f"'{i_n}' isimli stoku silmek için şifrenizi (Giriş Şifresi) girin.",
                self,
            )
            if dialog.exec():
                self.delete_part_context(i_id, i_n)

        menu.addAction("🗑️ Sil").triggered.connect(_ask_delete)
        menu.exec(self.table_stock.viewport().mapToGlobal(pos))

    def delete_part_context(self, i_id, i_n):
        try:
            self.db.cursor.execute(
                "SELECT stock, purchase_price, currency FROM parts WHERE id=?", (i_id,)
            )
            row = self.db.cursor.fetchone()
            stok = float(row[0] or 0) if row else 0.0
            buy = float(row[1] or 0) if row else 0.0
            cur = str(row[2] or "TRY") if row else "TRY"

            try:
                self.db.record_stock_movement(
                    i_id,
                    -stok,
                    current_stock=stok,
                    type_val="Çıkış (Silindi)",
                    desc=f"Kart Silindi: {i_n}",
                )
            except Exception as e:
                pass

            if stok > 0 and buy > 0:
                total_refund = stok * buy
                self.db.add_transaction(
                    t_type="Gelir",
                    category="Stok İptali / Silinme",
                    amount=total_refund,
                    description=f"Stok Kartı Silinme İadesi: {stok} x {i_n}",
                    payment_method="Nakit",
                    currency=cur,
                    original_amount=total_refund,
                )
        except Exception as e:
            import logging
            logging.getLogger().error(f"Stock delete reversal error: {e}")

        if self.db.delete_part(i_id):
            try:
                main_window = getattr(self, "main_window", None) or getattr(
                    self.window(), "main_window", None
                )
                if main_window and hasattr(main_window, "stock_updated"):
                    main_window.stock_updated.emit()
            except Exception:
                pass
            show_success(self, "Stok ve finans geçmişi güncellendi (Silindi)!")
            self.reload_data()
            self.load_history()

    def update_stock_amount(self, item_id, item_name):
        if not item_id or item_id == "False":
            show_error(self, "Hata: Geçersiz ürün ID! Lütfen sayfayı yenileyin.")
            return

        val, ok = ModernInputDialog.get_int(
            self, "Stok Güncelle", f"{item_name}\nMiktar:", 0
        )

        if ok and val != 0:
            if self.db.adjust_stock(item_id, val, f"Manuel Güncelleme - {item_name}"):
                if val > 0:
                    try:
                        self.db.cursor.execute(
                            "SELECT purchase_price, currency FROM parts WHERE id=?",
                            (item_id,),
                        )
                        row = self.db.cursor.fetchone()
                        purchase_price = float(row[0]) if row and row[0] else 0.0
                        currency = str(row[1] or "TRY").upper() if row else "TRY"
                        if purchase_price > 0:
                            self.db.add_transaction(
                                t_type="Gider",
                                category="Stok Alımı",
                                amount=purchase_price * val,
                                description=f"Stok Ekleme (Kısayol): {val} x {item_name}",
                                payment_method="Nakit",
                                currency=currency,
                                original_amount=purchase_price * val,
                                selected_services=[
                                    {
                                        "kind": "stock_purchase",
                                        "name": item_name,
                                        "quantity": val,
                                        "unit_price": purchase_price,
                                        "currency": currency,
                                        "line_total": purchase_price * val,
                                    }
                                ],
                            )
                    except Exception as e:
                        from src.utils.logger import logger
                        logger.error(f"StockPage stock update accounting error: {e}")
                elif val < 0:
                    try:
                        self.db.cursor.execute(
                            "SELECT purchase_price, currency FROM parts WHERE id=?",
                            (item_id,),
                        )
                        row = self.db.cursor.fetchone()
                        purchase_price = float(row[0]) if row and row[0] else 0.0
                        currency = str(row[1] or "TRY").upper() if row else "TRY"
                        removed_qty = abs(val)
                        if purchase_price > 0:
                            self.db.add_transaction(
                                t_type="Gider",
                                category="Stok Düşümü / Fire",
                                amount=purchase_price * removed_qty,
                                description=f"Stok Düşümü (Manuel): {removed_qty} x {item_name}",
                                currency=currency,
                                original_amount=purchase_price * removed_qty,
                            )
                    except Exception as e:
                        from src.utils.logger import logger
                        logger.error(f"StockPage stock decrease accounting error: {e}")

                try:
                    main_window = getattr(self, "main_window", None) or getattr(
                        self.window(), "main_window", None
                    )
                    if main_window and hasattr(main_window, "stock_updated"):
                        main_window.stock_updated.emit()
                except Exception:
                    pass

                show_success(self, "Stok güncellendi!")
                self.refresh_data()

    def _view_part_photo(self, item_id, item_name):
        try:
            self.db.cursor.execute(
                "SELECT photo_path FROM parts WHERE id=?", (item_id,)
            )
            row = self.db.cursor.fetchone()
            photo_path = row[0] if row else None
        except Exception:
            photo_path = None

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Fotoğraf — {item_name}")
        dlg.setMinimumSize(400, 420)
        dlg.setStyleSheet(
            theme_qss("QDialog { background: @surface; } QLabel { color: @text; }")
        )
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(12)

        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setMinimumSize(360, 340)
        lbl_img.setStyleSheet(
            theme_qss(
                "border: 1px solid @border; border-radius: 12px; background: @surface_alt;"
            )
        )

        if photo_path and os.path.exists(photo_path):
            pix = QPixmap(photo_path).scaled(
                360,
                340,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl_img.setPixmap(pix)
        else:
            lbl_img.setText(
                "📷\n\nFotoğraf bulunamadı! Düzenle menüsünden ekleyebilirsiniz."
            )
            lbl_img.setStyleSheet(
                lbl_img.styleSheet() + " font-size: 15px; color: @text_muted;"
            )

        vl.addWidget(lbl_img)

        btn_close = QPushButton("Kapat")
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet(
            theme_qss(
                "QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 8px; color: @text; padding: 0 20px; }"
            )
        )
        btn_close.clicked.connect(dlg.accept)
        vl.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()
