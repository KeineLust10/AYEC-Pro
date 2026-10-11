# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QBoxLayout, QHBoxLayout, QPushButton, QLabel, QStyle, QLineEdit, QSizePolicy
from PyQt6.QtCore import Qt, QEvent, QSize
from PyQt6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPixmap, QPen
from src.utils.theme_colors import tc, theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.navigation_glyph import navigation_icon

class Breadcrumb(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 0, 4, 0)
        self.layout.setSpacing(6)
        
        # Left side: Path items
        self.path_container = QWidget()
        self.path_layout = QHBoxLayout(self.path_container)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(5)
        self.path_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.path_container)

        self.finance_branch_gap = QWidget(self)
        self.finance_branch_gap.setFixedWidth(85)
        self.finance_branch_gap.hide()
        self.layout.addWidget(self.finance_branch_gap)

        self.finance_branch = QLabel()
        self.finance_branch.setObjectName("FinanceHeaderBranch")
        branch_name = "Eren Depo (Merkez)"
        try:
            branch_name = str(main_window.db.get_setting("active_branch_name", branch_name) or branch_name)
        except Exception:
            pass
        self.finance_branch.setText(f"\u25cf  \u015eube:  {branch_name}")
        self.finance_branch.setFixedSize(238, 40)
        self.finance_branch.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.finance_branch.setStyleSheet(theme_qss(
            "QLabel#FinanceHeaderBranch { color: @text; background: @surface; "
            "border: 1px solid @finance_outline; border-radius: 20px; padding: 0 14px; font-size: 12px; }"
        ))
        self.finance_branch.hide()
        self.layout.addWidget(self.finance_branch)

        self.invoice_status_gap = QWidget(self)
        self.invoice_status_gap.setFixedWidth(14)
        self.invoice_status_gap.hide()
        self.layout.addWidget(self.invoice_status_gap)
        self.invoice_status_chip = QLabel("\u2714  GIB & Uyumsoft Ba\u011fl\u0131\n(Aktif Portal)")
        self.invoice_status_chip.setObjectName("InvoicePortalStatus")
        self.invoice_status_chip.setFixedSize(250, 54)
        self.invoice_status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.invoice_status_chip.setStyleSheet(theme_qss(
            "QLabel#InvoicePortalStatus { color: #6ee7b7; background: #071d1c; "
            "border: 1px solid #047857; border-radius: 9px; padding: 0 10px; "
            "font-size: 12px; font-weight: 700; }"
        ))
        self.invoice_status_chip.hide()
        self.layout.addWidget(self.invoice_status_chip)
        self.invoice_rate_gap = QWidget(self)
        self.invoice_rate_gap.setFixedWidth(14)
        self.invoice_rate_gap.hide()
        self.layout.addWidget(self.invoice_rate_gap)
        self.invoice_rate_chip = QLabel()
        self.invoice_rate_chip.setObjectName("InvoiceRateStatus")
        rate_text = "49.0013"
        try:
            rate_row = main_window.db.conn.execute(
                "SELECT selling_rate FROM exchange_rates WHERE currency=? ORDER BY created_at DESC LIMIT 1",
                ("USD",),
            ).fetchone()
            if rate_row and rate_row[0] is not None:
                rate_text = f"{float(rate_row[0]):.4f}"
        except Exception:
            pass
        self.invoice_rate_chip.setText(f"1\n{rate_text} USD: TL  TCMB")
        self.invoice_rate_chip.setFixedSize(175, 54)
        self.invoice_rate_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.invoice_rate_chip.setStyleSheet(theme_qss(
            "QLabel#InvoiceRateStatus { color: @text; background: @surface; "
            "border: 1px solid @finance_outline; border-radius: 8px; padding: 0 8px; "
            "font: 10px 'JetBrains Mono'; }"
        ))
        self.invoice_rate_chip.hide()
        self.layout.addWidget(self.invoice_rate_chip)

        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("HeaderGlobalSearch")
        self.search_input.setPlaceholderText("Sistem genelinde ara (Marka, Seri No, ...)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedSize(264, 40)
        search_icon = QPixmap(16, 16)
        search_icon.fill(Qt.GlobalColor.transparent)
        search_painter = QPainter(search_icon)
        search_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        search_painter.setPen(QPen(QColor("#94a3b8"), 1.6))
        search_painter.drawEllipse(2, 2, 9, 9)
        search_painter.drawLine(10, 10, 14, 14)
        search_painter.end()
        self.search_input.addAction(QIcon(search_icon), QLineEdit.ActionPosition.LeadingPosition)
        self.search_input.setStyleSheet(theme_qss("""
            QLineEdit#HeaderGlobalSearch {
                background: @bg;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }
            QLineEdit#HeaderGlobalSearch:focus { border-color: @accent; }
            QLineEdit#HeaderGlobalSearch::placeholder { color: @text_muted; }
        """))
        self.search_input.returnPressed.connect(self._search_current_page)
        self.layout.addWidget(self.search_input)
        
        self.layout.addStretch()

        self.assistant_btn = QPushButton("\U0001f916 AYEC PRO CORE")
        self.assistant_btn.setToolTip('AYEC PRO CORE')
        self.assistant_btn.setAccessibleName('AYEC PRO CORE')
        self.assistant_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.assistant_btn.setFixedWidth(140)
        self.assistant_btn.setFixedHeight(32)
        self.assistant_btn.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: @finance_primary;
                color: @finance_primary_text;
                border: 1px solid @finance_primary;
                border-radius: 4px;
                font-family: {DesignTokens.FONT_FAMILY};
                font-weight: bold;
                font-size: 11px;
                padding: 0 6px;
            }}
            QPushButton:hover {{
                background-color: @finance_active_bg;
                border-color: @finance_primary;
                color: @finance_text;
            }}
        """))
        self.assistant_btn.clicked.connect(self.main_window.toggle_assistant)

        self.finance_core_gap = QWidget(self)
        self.finance_core_gap.setFixedWidth(0)
        self.finance_core_gap.hide()
        self.layout.addWidget(self.finance_core_gap)

        self.mute_btn = QPushButton()
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setFixedSize(32, 32)
        self.mute_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @finance_surface_lowest;
                color: @finance_text;
                border: 1px solid @finance_outline;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: @finance_surface_high;
                border-color: @finance_primary;
            }
            QPushButton:pressed {
                background-color: @finance_active_bg;
                border-color: @finance_primary;
            }
        """))
        self.mute_btn.clicked.connect(self.toggle_assistant_silent_mode)
        
        # User Welcome Label (Moved here per user request)
        user_name = "Admin Kullan\u0131c\u0131s\u0131"
        if hasattr(self.main_window, 'current_user') and self.main_window.current_user:
            user = self.main_window.current_user
            user_name = user.get('name') or user.get('full_name') or user.get('username') or user_name
             
        self._user_label_full = str(user_name)
        self.user_lbl = QLabel(self._user_label_full)
        self.user_lbl.setObjectName("HeaderUserLabel")
        self.user_lbl.setFixedWidth(104)
        self.user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.user_lbl.setToolTip(self._user_label_full)
        self.user_lbl.setStyleSheet(theme_qss(
            "QLabel#HeaderUserLabel { color: @finance_text; background: @surface; "
            "border: 1px solid @border; border-radius: 8px; padding: 0 8px; "
            "font-weight: 600; font-size: 12px; }"
        ))
        
        # Add widgets in correct order
        self.layout.addWidget(self.user_lbl)
        self.layout.addWidget(self.mute_btn)
        self.layout.addWidget(self.assistant_btn)
        self.layout.setAlignment(self.user_lbl, Qt.AlignmentFlag.AlignVCenter)
        self.layout.setAlignment(self.mute_btn, Qt.AlignmentFlag.AlignVCenter)
        self.layout.setAlignment(self.assistant_btn, Qt.AlignmentFlag.AlignVCenter)
        
        # Initial State
        self.refresh_assistant_silent_mode()
        self._refresh_user_label_text()
        self.update_path([("Ana Sayfa", 40)])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        window_width = self.main_window.width() if self.main_window is not None else self.width()
        page_id = getattr(self.main_window, "_current_page_index", None)
        compact = self.width() < 400 or window_width < (1000 if page_id == 146 else 1400)
        self._apply_page_header_mode(compact, window_width)

    def _apply_page_header_mode(self, compact=None, window_width=None):
        window_width = int(window_width or (
            self.main_window.width() if self.main_window is not None else self.width()
        ))
        compact = bool(compact) if compact is not None else window_width < 1400

        # Keep the breadcrumb area identical across routes. Finance and catalog
        # pages used to inject branch, rates, and product-specific chips here.
        for widget in (
            self.finance_branch, self.finance_branch_gap,
            self.invoice_status_gap, self.invoice_status_chip,
            self.invoice_rate_gap, self.invoice_rate_chip,
            self.finance_core_gap,
        ):
            self.layout.removeWidget(widget)
            self.path_layout.removeWidget(widget)
            widget.hide()
            widget.setParent(self)
            widget.setGeometry(0, 0, 0, 0)
            if isinstance(widget, QLabel):
                widget.clear()
        for index in range(self.layout.count() - 1, -1, -1):
            item = self.layout.itemAt(index)
            if item is not None and item.spacerItem() is not None:
                self.layout.takeAt(index)
        for widget in (
            self.path_container, self.search_input, self.user_lbl,
            self.mute_btn, self.assistant_btn,
        ):
            self.layout.removeWidget(widget)
        for index in range(self.path_layout.count() - 1, -1, -1):
            item = self.path_layout.itemAt(index)
            widget = item.widget() if item is not None else None
            if widget is not None and not isinstance(widget, QPushButton):
                self.path_layout.takeAt(index)
                widget.deleteLater()
        path_buttons = [
            self.path_layout.itemAt(index).widget()
            for index in range(self.path_layout.count())
            if isinstance(self.path_layout.itemAt(index).widget(), QPushButton)
        ]
        current = path_buttons[-1] if path_buttons else None
        for button in path_buttons[:-1]:
            self.path_layout.removeWidget(button)
            button.deleteLater()
        if current is not None:
            title_width = 180 if not compact else 116
            title = current.accessibleName() or current.text()
            current.setText(QFontMetrics(current.font()).elidedText(
                title, Qt.TextElideMode.ElideRight, title_width - 8
            ))
            current.setFixedSize(title_width, 36)
            current.setStyleSheet(theme_qss(
                "QPushButton { color: @text; background: transparent; border: none; "
                "font-size: 12px; font-weight: 600; text-align: left; padding: 0 4px; }"
            ))
        self.path_container.setFixedWidth(190 if not compact else 124)
        self.path_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        self.search_input.setFixedWidth(max(150, min(260, window_width - 1200)))
        self.assistant_btn.setFixedSize(32 if compact else 144, 32)
        self.assistant_btn.setText("\U0001f916" if compact else "\U0001f916 AYEC PRO CORE")
        self.assistant_btn.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; color: @text; "
            "border: 1px solid @border; border-radius: 4px; "
            "font-size: 11px; font-weight: 700; padding: 0 8px; }"
        ))
        self.user_lbl.setFixedSize(1, 1)
        self.mute_btn.setFixedSize(24, 24)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self.layout.addWidget(self.path_container)
        self.layout.addWidget(self.search_input)
        self.layout.addStretch(1)
        for widget in (self.user_lbl, self.mute_btn, self.assistant_btn):
            self.layout.addWidget(widget)
            widget.setVisible(widget is not self.user_lbl and (not compact or widget is self.assistant_btn))
        self.path_container.show()
        self.search_input.show()
        self._finance_header_signature = None
        return

    def _search_current_page(self):
        page_id = getattr(self.main_window, "_current_page_index", None)
        pages = getattr(self.main_window, "pages", {})
        page = pages.get(page_id) if isinstance(pages, dict) else None
        if page is None and hasattr(self.main_window, "content_area"):
            page = self.main_window.content_area.currentWidget()
        for attribute in ("inp_search", "search_input", "search_edit", "search_box"):
            field = getattr(page, attribute, None) if page is not None else None
            if isinstance(field, QLineEdit):
                field.setText(self.search_input.text())
                field.setFocus()
                return
            self.assistant_btn.setText('\U0001f916' if compact else '\U0001f916 AYEC PRO CORE')
        self._refresh_user_label_text()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange) and hasattr(self, 'mute_btn'):
            self.refresh_assistant_silent_mode()

    def _refresh_user_label_text(self):
        full = getattr(self, "_user_label_full", "")
        if not full:
            return
        page_id = getattr(self.main_window, "_current_page_index", None)
        if page_id in {140, 145, 146, 147}:
            try:
                key = "company_name" if page_id == 140 else "site_title"
                full = self.main_window.db.get_setting(key, full) or full
            except Exception:
                pass
        metrics = QFontMetrics(self.user_lbl.font())
        is_reference_header = page_id in {140, 145, 146, 147}
        available = (252 if page_id == 140 else 132) if is_reference_header else max(
            80, self.width() - self.assistant_btn.width() - self.mute_btn.width() - 110
        )
        available = min(available if is_reference_header else 240, available)
        self.user_lbl.setText(metrics.elidedText(full, Qt.TextElideMode.ElideRight, available))

    def refresh_assistant_silent_mode(self):
        silent = False
        try:
            silent = bool(self.main_window.is_assistant_silent_mode())
        except Exception:
            silent = False
        self._set_mute_state(silent)

    def _set_mute_state(self, silent):
        if getattr(self.main_window, "_current_page_index", None) == 140:
            self.mute_btn.setIcon(QIcon())
            self.mute_btn.setText("\u25cf")
            self.mute_btn.setStyleSheet(theme_qss(
                "QPushButton { color: @accent; background: transparent; border: none; "
                "font-size: 13px; padding: 0; }"
            ))
            self.mute_btn.setToolTip("Asistan sesi kapal\u0131" if silent else "Asistan sesi a\u00e7\u0131k")
            return
        icon = QStyle.StandardPixmap.SP_MediaVolumeMuted if silent else QStyle.StandardPixmap.SP_MediaVolume
        pixmap = self.style().standardIcon(icon).pixmap(16, 16)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(tc('finance_text')))
        painter.end()
        self.mute_btn.setIcon(QIcon(pixmap))
        self.mute_btn.setToolTip('Asistan sesi kapal\u0131' if silent else 'Asistan sesi a\u00e7\u0131k')
        self.mute_btn.setAccessibleName(self.mute_btn.toolTip())

    def toggle_assistant_silent_mode(self):
        silent = False
        try:
            silent = bool(self.main_window.is_assistant_silent_mode())
        except Exception:
            silent = False
        new_val = not silent
        applied = True
        try:
            applied = bool(self.main_window.set_assistant_silent_mode(new_val))
        except Exception:
            applied = False
        if not applied:
            self.refresh_assistant_silent_mode()
            return
        self._set_mute_state(new_val)

    def update_path(self, path_items):
        """
        path_items: List of tuples ("Title", page_id)
        e.g. [("Ana Sayfa", 40), ("Müşteriler", 21), ("Detay", None)]
        """
        # Clear existing path layout
        while self.path_layout.count():
            item = self.path_layout.takeAt(0)
            if item.widget():
                if item.widget() not in {
                    self.finance_branch, self.finance_branch_gap, self.invoice_status_gap,
                    self.invoice_status_chip, self.invoice_rate_gap, self.invoice_rate_chip,
                }:
                    item.widget().deleteLater()
        
        for i, (text, page_id) in enumerate(path_items):
            if i > 0:
                arrow = QLabel("›")
                arrow.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-size: 14px; font-weight: bold;"))
                self.path_layout.addWidget(arrow)
            
            btn = QPushButton(text.replace("&", "&&"))
            btn.setToolTip(text)
            btn.setAccessibleName(text)
            if page_id is not None and i < len(path_items) - 1:
                # Clickable ancestor
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(theme_qss(f"""
                    QPushButton {{
                        border: none; 
                        color: {DesignTokens.MUTED_FOREGROUND}; 
                        font-weight: normal;
                        background: transparent;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        color: {DesignTokens.ACCENT};
                        text-decoration: underline;
                    }}
                """))
                btn.clicked.connect(lambda checked, pid=page_id: self.main_window.switch_page(pid))
            else:
                # Current page (Active)
                btn.setStyleSheet(theme_qss(f"""
                    QPushButton {{
                        border: none;
                        color: @finance_breadcrumb_active;
                        font-weight: bold;
                        background: transparent;
                        text-align: left;
                    }}
                """))
                
            self.path_layout.addWidget(btn)
        self._apply_page_header_mode()
        self.refresh_assistant_silent_mode()
        self._refresh_user_label_text()

