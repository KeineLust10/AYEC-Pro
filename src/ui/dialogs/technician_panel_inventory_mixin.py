# -*- coding: utf-8 -*-

import threading

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem

from src.ui.dialogs.device_history_dialog import DeviceHistoryDialog
from src.ui.dialogs.modern_manual_product_dialog import ModernManualProductDialog
from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.utils.voice_worker import VoiceWorker
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success, show_warning, show_toast
from src.utils.logger import logger
from src.ui.widgets.animated_toggle import AnimatedToggle


class TechnicianPanelInventoryMixin:
    def _has_any_photo(self):
        """Check if device has at least one photo (photo_paths or legacy photo_path)"""
        try:
            row = self.db.cursor.execute(
                "SELECT photo_path, photo_paths FROM devices WHERE tracking_no=?",
                (self.tracking_no,),
            ).fetchone()
            if not row:
                return bool(self.photo_path_str)
            photo_path = row[0] if len(row) > 0 else None
            photo_paths_str = row[1] if len(row) > 1 else None
            has_single = bool(photo_path)
            has_multiple = False
            if photo_paths_str:
                paths = [p.strip() for p in str(photo_paths_str).split(',') if p.strip()]
                has_multiple = len(paths) > 0
            return has_single or has_multiple
        except Exception:
            return bool(self.photo_path_str)
    
    def _open_photo_gallery(self, stage="Giriş"):
        """Open the photo gallery/uploader for this device"""
        try:
            from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
            dlg = PhotoGalleryDialog(self.db, self.tracking_no, self, read_only=False, stage=stage)
            dlg.exec()
        except Exception as e:
            self.notify(f"Galeri açılamadı: {e}", "error")
    
    def load_used_parts(self):
        # Fetch currency too (with fallback for old DBs)
        try:
            self.db.cursor.execute("PRAGMA table_info(used_parts)")
            _cols = [r[1] for r in self.db.cursor.fetchall()]
        except Exception:
            _cols = []
        has_currency = "currency" in _cols
        has_quantity = "quantity" in _cols
        has_rate = "exchange_rate" in _cols
        has_price_try = "price_try" in _cols
        deleted_col = "is_deleted" if "is_deleted" in _cols else ("is_archived" if "is_archived" in _cols else None)

        query = (
            "SELECT id, part_name, price, created_at, {currency}, {quantity}, "
            "{rate}, {price_try} FROM used_parts WHERE tracking_no=?"
        ).format(
            currency="COALESCE(currency,'TRY')" if has_currency else "'TRY'",
            quantity="COALESCE(quantity,1)" if has_quantity else "1",
            rate="COALESCE(exchange_rate,1)" if has_rate else "1",
            price_try="COALESCE(price_try,0)" if has_price_try else "0",
        )
        if deleted_col:
            query = query.replace("WHERE tracking_no=?", f"WHERE tracking_no=? AND ({deleted_col}=0 OR {deleted_col} IS NULL)")

        self.db.cursor.execute(query, (self.tracking_no,))
        parts = self.db.cursor.fetchall()
        self.table_used_parts.setRowCount(0)
        self.table_used_parts.setUpdatesEnabled(False)
        self.table_used_parts.setRowCount(len(parts))
        total_parts_cost_try = 0.0
        _sym = {"USD": "$", "EUR": "€", "TRY": "₺"}

        for i, p in enumerate(parts):
            real_id = p[0]
            part_name = str(p[1] or "")
            try:
                price_val = float(p[2] or 0)
            except Exception:
                price_val = 0.0
            part_currency = str(p[4] or 'TRY').upper()
            quantity = float(p[5] or 1)
            stored_rate = float(p[6] or 0)
            stored_price_try = float(p[7] or 0)
            sym = _sym.get(part_currency, part_currency)

            # Convert to TRY for the running total
            price_try = stored_price_try
            if price_try <= 0:
                if part_currency == "TRY":
                    price_try = price_val
                elif stored_rate > 1:
                    price_try = price_val * stored_rate
                else:
                    price_try = CurrencyHelper.convert_amount(
                        self.db, price_val, part_currency, "TRY"
                    )
            total_parts_cost_try += price_try * quantity

            self.table_used_parts.setItem(i, 0, QTableWidgetItem(part_name))
            quantity_text = f" x{quantity:g}" if quantity != 1 else ""
            self.table_used_parts.setItem(
                i, 1, QTableWidgetItem(f"{price_val:,.2f} {sym}{quantity_text}")
            )
            self.table_used_parts.setItem(i, 2, QTableWidgetItem(str(p[3])))
            
            btn_del = QPushButton("SİL")
            btn_del.setFixedSize(65, 30)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(theme_qss("background-color: @danger; color: white; border-radius: 4px; font-weight: bold;"))
            
            if real_id:
                btn_del.clicked.connect(lambda ch, pid=real_id: self.delete_used_part(pid))
            
            self.table_used_parts.setCellWidget(i, 3, btn_del)

        self.table_used_parts.setUpdatesEnabled(True)
        self.table_used_parts.viewport().update()
        self.inp_part_cost.setText(f"{total_parts_cost_try:.2f}")

    def delete_used_part(self, part_id):
        reply = ModernConfirmDialog("Onay", "Seçili parçayı silmek istediğinize emin misiniz", self)
        if reply.exec() == QDialog.DialogCode.Accepted:
            try:
                remove_ok = self.db.remove_used_part(part_id) if hasattr(self.db, "remove_used_part") else self.db.soft_delete_record("used_parts", "id", part_id)
                if not remove_ok:
                    raise RuntimeError("Parca kaydi silinemedi")
                self.notify("Parça kaydı silindi.", "success")
                self.audit_logger.log_action('devices', 'DELETE_PART', f"Cihaz parça kaydı silindi ID: {part_id}")
                self.load_used_parts()
                self.refresh_logs()
            except Exception as e:
                self.notify(f"Silme hatası: {e}", "error")

    def load_parts(self):
        self.combo_parts.clear()
        try:
            self.db.cursor.execute("""
                SELECT id, name, stock, price, COALESCE(currency, 'TRY') AS currency
                FROM parts
                WHERE (is_deleted = 0 OR is_deleted IS NULL) AND COALESCE(stock, 0) > 0
                ORDER BY name
            """)
            parts = self.db.cursor.fetchall() or []
            for p in parts:
                cur = str(p[4] or 'TRY').upper()
                self.combo_parts.addItem(
                    f"{p[1]} (Stok: {p[2]}) - {CurrencyHelper.format_amount(p[3], currency_code=cur)}",
                    p[0],
                )
        except Exception as e:
            logger.error(f"TechnicianPanelInventoryMixin.load_parts error: {e}")

    def refresh_logs(self):
        if not hasattr(self, "table_logs"):
            return
        try:
            logs = self.db.get_logs(self.tracking_no)
            history_rows = []

            for log in logs:
                history_rows.append({
                    "created_at": str(log[4] or ""),
                    "entry_type": str(log[2] or "Sistem"),
                    "message": str(log[3] or ""),
                    "color": QColor("honeydew") if str(log[2] or "") == "Customer" else QColor("white"),
                })

            try:
                self.db.cursor.execute("PRAGMA table_info(used_parts)")
                used_part_cols = [row[1] for row in self.db.cursor.fetchall()]
            except Exception:
                used_part_cols = []

            deleted_col = "is_deleted" if "is_deleted" in used_part_cols else ("is_archived" if "is_archived" in used_part_cols else None)
            has_currency = "currency" in used_part_cols
            has_quantity = "quantity" in used_part_cols

            if has_currency:
                part_query = "SELECT part_name, price, created_at, COALESCE(currency, 'TRY') FROM used_parts WHERE tracking_no=?"
            else:
                part_query = "SELECT part_name, price, created_at, 'TRY' FROM used_parts WHERE tracking_no=?"
            if deleted_col:
                part_query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            if has_quantity:
                part_query = part_query.replace(" FROM used_parts ", ", COALESCE(quantity, 1) FROM used_parts ")
            else:
                part_query = part_query.replace(" FROM used_parts ", ", 1 FROM used_parts ")
            part_query += " ORDER BY created_at DESC"

            try:
                self.db.cursor.execute(part_query, (self.tracking_no,))
                used_parts = self.db.cursor.fetchall()
            except Exception:
                used_parts = []

            for part in used_parts:
                part_name = str(part[0] or "").strip()
                if not part_name:
                    continue
                try:
                    price_value = float(part[1] or 0)
                except Exception:
                    price_value = 0.0
                created_at = str(part[2] or "")
                currency = str(part[3] or "TRY").upper()
                try:
                    quantity = int(part[4] or 1)
                except Exception:
                    quantity = 1
                currency_symbol = CurrencyHelper.get_label(currency)
                quantity_text = f" x{quantity}" if quantity > 1 else ""
                message = (
                    f"Malzeme/Parca eklendi: {part_name}{quantity_text} - "
                    f"{CurrencyHelper.format_amount(price_value, currency_code=currency)}"
                )
                history_rows.append({
                    "created_at": created_at,
                    "entry_type": "Malzeme",
                    "message": message,
                    "color": QColor("#F5F9FF"),
                })

            history_rows.sort(key=lambda row: row["created_at"], reverse=True)
            self.table_logs.setRowCount(0)
            self.table_logs.setUpdatesEnabled(False)
            self.table_logs.setRowCount(len(history_rows))
            for row_idx, entry in enumerate(history_rows):
                for col, key in enumerate(("created_at", "entry_type", "message")):
                    val = str(entry[key])
                    item = QTableWidgetItem(val)
                    item.setBackground(entry["color"])
                    self.table_logs.setItem(row_idx, col, item)
            self.table_logs.setUpdatesEnabled(True)
            self.table_logs.viewport().update()
        except Exception as e:
            if hasattr(self, "table_logs"):
                self.table_logs.setUpdatesEnabled(True)
            logger.error(f"TechnicianPanelInventoryMixin.refresh_logs error: {e}")

    def notify(self, message, n_type="info"):
        t_type = n_type
        if n_type == "critical": t_type = "error"
        # Always use local toast to ensure positioning relative to this dialog (bottom-right)
        show_toast(self, message, t_type)

    def use_part(self):
        part_id = self.combo_parts.currentData()
        if not part_id: return
        
        part_text = self.combo_parts.currentText()
        try:
            stock = int(part_text.split("Stok: ")[1].split(")")[0])
        except (ValueError, IndexError):
            stock = 0
        
        if stock <= 0:
            self.notify("Bu parça stokta yok!", "warning")
            return
            
        if self.db.use_part(part_id, 1, self.tracking_no, post_debt=True):
            self.db.add_log(self.tracking_no, "System", f"Parça Kullanıldı: {part_text.split(' (')[0]}")
            self.load_parts()
            self.load_used_parts()
            self.refresh_logs()
            self.notify("Parça düşüldü ve işlem kaydedildi.", "success")
        else:
            self.notify("İşlem başarısız veya stok yetersiz.", "critical")

    def add_manual_product(self):
        dialog = ModernManualProductDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data:
            name, price = dialog.result_data
            # use add_used_part from database
            self.db.add_used_part(self.tracking_no, name, price, post_debt=True)
            self.db.add_log(
                self.tracking_no,
                "System",
                f"Manuel Ürün/Hizmet Eklendi: "
                f"{name} ({CurrencyHelper.format_try_for_display(price, db=self.db, include_try_reference=False)})",
            )
            self.load_used_parts()
            self.refresh_logs()
            self.notify(f"{name} başarıyla eklendi.", "success")
    
    def create_input_with_macros(self, text_widget, macros):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        
        # Add Mic Button next to input
        h_input = QHBoxLayout()
        h_input.setContentsMargins(0, 0, 0, 0)
        h_input.setSpacing(5)
        h_input.addWidget(text_widget)
        
        btn_mic = QPushButton("🎙️")
        btn_mic.setFixedSize(36, 36)
        btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        ad = str(self.db.get_setting("asistan_ozel_adi", "AYEC") or "AYEC")
        btn_mic.setToolTip(f"{ad}'e Anlat")
        btn_mic.setStyleSheet(theme_qss("""
            QPushButton { background: @selection_text; color: @warning; border: 1px solid @warning; border-radius: 18px; font-size: 14px; }
            QPushButton:hover { background: @warning; color: white; }
        """))
        btn_mic.clicked.connect(lambda: self.start_voice_note(text_widget, btn_mic))
        h_input.addWidget(btn_mic)
        
        lay.addLayout(h_input)
        
        # Macros
        if macros:
            btn_lay = QHBoxLayout()
            btn_lay.setContentsMargins(0, 0, 0, 0)
            btn_lay.setSpacing(5)
            lbl = QLabel("Hızlı:")
            lbl.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px; font-weight: bold; border:none; background:transparent;"))
            btn_lay.addWidget(lbl)
            
            for m in macros:
                toggle_vbox = QVBoxLayout()
                toggle_vbox.setSpacing(1)
                
                t = AnimatedToggle()
                t.setFixedSize(44, 22) # Slightly smaller
                
                # Robust Check: Split by common delimiters to check for exact word match
                # This prevents "Ekran" matching "Ekran Kırık" if we only wanted "Ekran"
                import re
                current_text = text_widget.text().upper()
                # Tokens in current text
                tokens = [t.strip() for t in re.split(r'[,•]', current_text) if t.strip()]
                
                # Check if this macro is fundamentally in the tokens
                # We check if the macro string is contained or if it's one of the tokens
                if m.upper() in tokens or m.upper() in current_text: 
                    t.setChecked(True)
                
                t.stateChanged.connect(lambda state, text_macro=m, widget=text_widget, toggle_btn=t: self.toggle_macro(widget, text_macro, toggle_btn))
                
                lbl_macro = QLabel(m)
                lbl_macro.setStyleSheet(theme_qss("font-size: 10px; color: @text_muted; font-weight: 600;"))
                lbl_macro.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                toggle_vbox.addWidget(t, 0, Qt.AlignmentFlag.AlignCenter)
                toggle_vbox.addWidget(lbl_macro)
                
                btn_lay.addLayout(toggle_vbox)
            
            btn_lay.addStretch()
            lay.addLayout(btn_lay)
            
        return container

    def start_voice_note(self, target_widget, mic_button):
        if self.voice_thread and self.voice_thread.isRunning():
            return
            
        mic_button.setStyleSheet(theme_qss("background: @danger; color: white; border: 1px solid @danger; border-radius: 18px; font-size: 14px;"))
        ad = str(self.db.get_setting("asistan_ozel_adi", "AYEC") or "AYEC")
        target_widget.setPlaceholderText(f"{ad} dinliyor...")
        
        # Audio feedback if parent has it
        if self.parent() and hasattr(self.parent(), 'assistant_sidebar'):
            self.parent().assistant_sidebar.speak("Sizi dinliyorum Admin.")
            
        try:
            # PyAudio Check
            try:
                import speech_recognition as sr
                import pyaudio
            except ImportError:
                 show_error(self, "Ses sistemi (PyAudio) yüklü değil. Lütfen 'pip install pyaudio' yapın.")
                 mic_button.setStyleSheet(theme_qss("""
                    QPushButton { background: @selection_text; color: @warning; border: 1px solid @warning; border-radius: 18px; font-size: 14px; }
                    QPushButton:hover { background: @warning; color: white; }
                 """))
                 target_widget.setPlaceholderText("Mikrofon hatası.")
                 return
 
            self.voice_thread = VoiceWorker(self.ai_service)
            self.voice_thread.text_received.connect(lambda text: self.on_voice_finished(text, target_widget, mic_button))
            self.voice_thread.error_occurred.connect(lambda err: self.on_voice_error(err, target_widget, mic_button))
            self.voice_thread.start()
            
        except TypeError as e:
            # Handle the specific 'missing argument' error if it ever happens again
            logger.error(f"TechnicianPanelInventoryMixin.start_voice_note init error: {e}")
            show_error(self, "Ses servisi başlatılamadı. (Init Error)")
            
        except Exception as e:
            logger.error(f"TechnicianPanelInventoryMixin.start_voice_note error: {e}")
            show_error(self, f"Mikrofon başlatılamadı: {e}")
            mic_button.setStyleSheet(theme_qss("""
                QPushButton { background: @selection_text; color: @warning; border: 1px solid @warning; border-radius: 18px; font-size: 14px; }
                QPushButton:hover { background: @warning; color: white; }
            """))

    def on_voice_finished(self, text, target_widget, mic_button):
        mic_button.setStyleSheet(theme_qss("background: @selection_text; color: @warning; border: 1px solid @warning; border-radius: 18px; font-size: 14px;"))
        target_widget.setPlaceholderText("Düşünülüyor...")
        
        refine_enabled = self.db.get_setting("jarvis_voice_refine_enabled", "1") == "1"
        
        if refine_enabled:
            def refine():
                refined = self.ai_service.refine_technical_note(text)
                target_widget.setText(refined)
                if self.parent() and hasattr(self.parent(), 'assistant_sidebar'):
                    self.parent().assistant_sidebar.speak("Notu düzenledim.")
            
            threading.Thread(target=refine, daemon=True).start()
        else:
            target_widget.setText(text)

    def on_voice_error(self, err, target_widget, mic_button):
        mic_button.setStyleSheet(theme_qss("background: @selection_text; color: @warning; border: 1px solid @warning; border-radius: 18px; font-size: 14px;"))
        target_widget.setPlaceholderText("Ses hatası: " + err)
        self.notify(f"Ses hatası: {err}", "warning")

    def toggle_macro(self, input_widget, text, button):
        # Use button state to decide action
        is_checked = button.isChecked()
        
        current_text = input_widget.text()
        import re
        # Split by comma or bullet, allow alphanumeric parts
        tags = [t.strip() for t in re.split(r'[,•]', current_text) if t.strip()]
        
        text_upper = text.upper()
        # Map existing tags to upper for comparison
        tags_map = {t.upper(): i for i, t in enumerate(tags)}
        
        if is_checked:
            if text_upper not in tags_map:
                tags.append(text)
        else:
            if text_upper in tags_map:
                # Remove carefully preserving others
                # Filter out the tag
                tags = [t for t in tags if t.upper() != text_upper]
                
        # Update text
        new_text = ", ".join(tags)
        input_widget.setText(new_text)

    def open_history(self):
        # Get serial_no from device_dict instead of non-existent self.device
        serial_no = self.device_dict.get('serial_no', '')
        # Eğer seri no yoksa (None veya boş string)
        if not serial_no or len(str(serial_no)) < 2:
            show_warning(self, "Bu cihazın kayıtlı bir seri numarası yok.")
            return
            
        dlg = DeviceHistoryDialog(self.db, serial_no, self.tracking_no, self)
        dlg.exec()
        
    def scan_part_barcode(self):
        code = self.inp_barcode_part.text().strip()
        if not code: return
        
        try:
            part = self.db.get_part_by_barcode(code)
            if part:
                # part: id(0), name(1), cat(2), stock(3), price(4), desc(5), min(6), code(7) (schema varies)
                # get_part_by_barcode returns row or None
                # DB schema check: 
                # id, name, category, stock, price, desc, min_stock, code
                
                # We need to simulate 'use_part' but directly
                part_id = part[0]
                name = part[1]
                # Fallback if no specific price column in tuple, try dict access if Row
                try:
                    price = part['price'] if 'price' in part.keys() else part[4] # Schema says price is at index 4
                except Exception:
                    price = part[4] # Fallback to index if keys fails
                
                stock = part[3] # Schema says stock is at index 3
                
                if stock <= 0:
                    show_error(self, f"'{name}' stokta yok!")
                    self.inp_barcode_part.clear()
                    return

                # Use unified use_part method
                if self.db.use_part(part_id, 1, self.tracking_no, post_debt=True):
                    self.db.add_log(self.tracking_no, "System", f"Parça (Barkod) Kullanıldı: {name}")
                    self.load_used_parts()
                    self.load_parts() # Refresh combo stocks
                    self.inp_barcode_part.clear()
                    self.inp_barcode_part.setFocus()
                    show_success(self, f"{name} eklendi.")
                else:
                    show_error(self, f"'{name}' stok düşülemedi!")
            else:
                show_warning(self, "Barkod bulunamadı.")
                self.inp_barcode_part.selectAll()
        except Exception as e:
            show_error(self, f"Barkod hatası: {e}")
