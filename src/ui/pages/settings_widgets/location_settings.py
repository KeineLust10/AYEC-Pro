# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFrame, QHBoxLayout, QGridLayout)
from PyQt6.QtGui import QFont, QAction, QColor, QPainter, QPen
from PyQt6.QtCore import Qt, QPoint
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils import message_helper
from src.ui.dialogs.location_picker_dialog import LocationPickerDialog
import logging

logger = logging.getLogger("AYECProLogger")


class LocationMapPreview(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.latitude = ""
        self.longitude = ""
        self.setFixedHeight(160)
        self.setStyleSheet("background: #080f1a; border: 1px solid #28364c; border-radius: 5px;")

    def set_coordinates(self, latitude, longitude):
        self.latitude = str(latitude or "")
        self.longitude = str(longitude or "")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#080f1a"))
        grid_pen = QPen(QColor("#162234"), 1)
        painter.setPen(grid_pen)
        for x in range(0, rect.width(), 22):
            painter.drawLine(x, 0, x, rect.height())
        for y in range(0, rect.height(), 22):
            painter.drawLine(0, y, rect.width(), y)
        painter.setPen(QPen(QColor("#29445a"), 4))
        painter.drawLine(-20, rect.height() - 8, rect.width() + 16, 18)
        painter.setPen(QPen(QColor("#24463c"), 4))
        painter.drawLine(int(rect.width() * 0.35), -10, int(rect.width() * 0.62), rect.height() + 10)
        center_x = rect.width() // 2
        center_y = rect.height() // 2
        painter.setPen(QPen(QColor("#f87171"), 3))
        painter.setBrush(QColor("#991b1b"))
        painter.drawEllipse(center_x - 7, center_y - 7, 14, 14)
        coordinates = f"{self.latitude}, {self.longitude}".strip(", ")
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QColor("#080f1a"))
        badge = painter.fontMetrics().boundingRect(coordinates).adjusted(-5, -2, 5, 2)
        badge.moveCenter(QPoint(center_x, center_y + 17))
        painter.drawRoundedRect(badge, 3, 3)
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, coordinates)
        painter.setPen(QColor("#34d399"))
        painter.drawText(rect.adjusted(5, 4, -6, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, "GPS Kalibre Edildi")
        painter.setPen(QColor("#64748b"))
        painter.drawText(rect.adjusted(5, 4, -6, -4), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, "OpenStreetMap Dark Tiles")
        painter.end()


class LocationSettingsWidget(QWidget):
    """
    Konum ve Harita Ayarları Widget'ı
    Varsayılan harita başlangıç noktasını ve diğer harita ayarlarını yönetir.
    """
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.selected_address = ""
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Location Selection Area
        loc_group = QFrame()
        loc_group.setStyleSheet(theme_qss("background-color: @surface; border: 1px solid @border; border-radius: 8px;"))
        loc_layout = QVBoxLayout(loc_group)
        loc_layout.setContentsMargins(5, 4, 5, 4)
        loc_layout.setSpacing(3)

        lbl_current = QLabel("Varsayılan Merkez Konumu")
        lbl_current.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))
        loc_layout.addWidget(lbl_current)
        
        # Lat/Lng Display (Grid Layout for better alignment)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        
        self.inp_lat = QLineEdit()
        self.inp_lat.setPlaceholderText("Enlem")
        self.inp_lat.setFixedHeight(26)
        self.inp_lat.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 4px; padding: 4px 7px; background-color: @surface_alt;"))
        
        self.inp_lng = QLineEdit()
        self.inp_lng.setPlaceholderText("Boylam")
        self.inp_lng.setFixedHeight(26)
        self.inp_lng.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 4px; padding: 4px 7px; background-color: @surface_alt;"))

        lbl_lat = QLabel("Enlem (Latitude)")
        lbl_lat.setFont(QFont(DesignTokens.FONT_NAME, 10))
        grid_layout.addWidget(lbl_lat, 0, 0)
        grid_layout.addWidget(self.inp_lat, 1, 0)
        
        lbl_lng = QLabel("Boylam (Longitude)")
        lbl_lng.setFont(QFont(DesignTokens.FONT_NAME, 10))
        grid_layout.addWidget(lbl_lng, 0, 1)
        grid_layout.addWidget(self.inp_lng, 1, 1)
        
        loc_layout.addLayout(grid_layout)
        
        # Pick Button
        self.btn_pick = QPushButton("Haritadan Konum Seç")
        self.btn_pick.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick.setFixedHeight(30)
        self.btn_pick.setFont(QFont(DesignTokens.FONT_NAME, 9, QFont.Weight.Bold))
        self.btn_pick.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @accent; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                text-align: center;
                padding-left: 0px;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        self.btn_pick.clicked.connect(self.open_location_picker)
        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        action_row.addWidget(self.btn_pick, 1)
        # Save Button
        btn_save = QPushButton("💾 AYARLARI KAYDET")
        btn_save.setFixedHeight(30)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @success; 
                color: white; 
                border-radius: 6px; 
                font-weight: bold; 
                font-size: 11px;
            }
            QPushButton:hover { background-color: @success; }
        """))
        btn_save.clicked.connect(self.save_data)
        action_row.addWidget(btn_save, 1)
        self.map_preview = LocationMapPreview(self)
        self.inp_lat.textChanged.connect(self._update_map_preview)
        self.inp_lng.textChanged.connect(self._update_map_preview)
        location_columns = QHBoxLayout()
        location_columns.setSpacing(8)
        left_column = QVBoxLayout()
        left_column.setSpacing(4)
        left_column.addWidget(loc_group)
        left_column.addLayout(action_row)
        location_columns.addLayout(left_column, 3)
        location_columns.addWidget(self.map_preview, 2)
        layout.addLayout(location_columns)

    def _get_current_username(self):
        username = ""
        try:
            if self.main_window and hasattr(self.main_window, "user_data") and self.main_window.user_data:
                data = self.main_window.user_data
                if isinstance(data, dict):
                    username = data.get("username", "") or ""
                elif isinstance(data, (list, tuple)) and len(data) > 1:
                    username = data[1] or ""
        except Exception:
            username = ""
        if not username:
            try:
                username = self.db.get_setting("last_login_user", "") or ""
            except Exception:
                username = ""
        return username

    def _load_default_location_values(self):
        username = self._get_current_username()
        lat = self.db.get_setting("installation_lat", "")
        lng = self.db.get_setting("installation_lng", "")
        self.selected_address = self.db.get_setting("installation_address", "")
        if username and (not lat or not lng):
            try:
                lat = self.db.get_setting(f"map_default_lat_user_{username}", "")
                lng = self.db.get_setting(f"map_default_lng_user_{username}", "")
            except Exception:
                lat = ""
                lng = ""
        if not lat or not lng:
            lat = self.db.get_setting("map_default_lat", "40.1044116")
            lng = self.db.get_setting("map_default_lng", "27.6563981")
        return lat, lng

    def load_data(self):
        lat, lng = self._load_default_location_values()
        self.inp_lat.setText(lat)
        self.inp_lng.setText(lng)
        self.map_preview.set_coordinates(lat, lng)

    def _update_map_preview(self, _value=None):
        if hasattr(self, "map_preview"):
            self.map_preview.set_coordinates(self.inp_lat.text(), self.inp_lng.text())

    def open_location_picker(self):
        try:
            curr_lat = float(self.inp_lat.text()) if self.inp_lat.text() else None
            curr_lng = float(self.inp_lng.text()) if self.inp_lng.text() else None
            
            dlg = LocationPickerDialog(self, curr_lat, curr_lng)
            dlg.location_selected.connect(self.on_location_selected)
            dlg.exec()
        except Exception as e:
            logger.error("Location picker error: %s", e)
            from src.ui.widgets.modern_confirm_dialog import ModernAlertDialog
            ModernAlertDialog("Hata", f"Harita açılamadı: {str(e)}", parent=self, ok_text="Tamam", variant="error").exec()

    def _parse_city_district(self, address):
        city = ""
        district = ""
        parts = [p.strip() for p in str(address or "").split(",") if p.strip()]
        if len(parts) >= 3:
            city = parts[-3]
        if len(parts) >= 4:
            district = parts[-4]
        elif parts:
            district = parts[0]
        return city, district

    def on_location_selected(self, lat, lng, address):
        self.inp_lat.setText(str(lat))
        self.inp_lng.setText(str(lng))
        self.map_preview.set_coordinates(lat, lng)
        self.selected_address = str(address or "").strip()
        username = self._get_current_username()
        if username:
            try:
                self.db.set_setting(f"map_default_address_user_{username}", str(address or ""))
                city, district = self._parse_city_district(address)
                if city:
                    self.db.set_setting(f"map_default_city_user_{username}", city)
                if district:
                    self.db.set_setting(f"map_default_district_user_{username}", district)
            except Exception:
                pass
        if self.main_window:
            self.main_window.show_notification(f"Konum seçildi: {str(address)[:40]}...", "info")

    def save_data(self, silent=False):
        if not self.inp_lat.text() or not self.inp_lng.text():
            if not silent:
                message_helper.show_warning(self, "Uyar\u0131", "L\u00fctfen ge\u00e7erli bir konum se\u00e7in.")
            return

        lat_val = self.inp_lat.text().strip().replace(",", ".")
        lng_val = self.inp_lng.text().strip().replace(",", ".")
        try:
            latitude = float(lat_val)
            longitude = float(lng_val)
        except ValueError:
            if not silent:
                message_helper.show_warning(self, "Uyar\u0131", "Enlem ve boylam say\u0131sal olmal\u0131d\u0131r.")
            return
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            if not silent:
                message_helper.show_warning(self, "Uyar\u0131", "Enlem -90 ile 90, boylam -180 ile 180 aras\u0131nda olmal\u0131d\u0131r.")
            return
        self.inp_lat.setText(lat_val)
        self.inp_lng.setText(lng_val)

        username = self._get_current_username()
        if username:
            try:
                self.db.set_setting(f"map_default_lat_user_{username}", lat_val)
                self.db.set_setting(f"map_default_lng_user_{username}", lng_val)
            except Exception:
                pass

        self.db.set_setting("map_default_lat", lat_val)
        self.db.set_setting("map_default_lng", lng_val)
        self.db.set_setting("installation_lat", lat_val)
        self.db.set_setting("installation_lng", lng_val)
        if self.selected_address:
            self.db.set_setting("installation_address", self.selected_address)
            self.db.set_setting("company_address", self.selected_address)
        
        # Instant Update for Field Service Page (Index 61, matching ModernDesktopApp page_mapping)
        if self.main_window and hasattr(self.main_window, 'pages'):
            field_page = self.main_window.pages.get(61)
            # Check if page is loaded and valid
            if field_page and hasattr(field_page, 'update_default_location'):
                field_page.update_default_location(float(lat_val), float(lng_val))

        if self.main_window and not silent:
            self.main_window.show_notification(
                "Konum ayarlari kaydedildi ve kurulum haritasina gonderiliyor.",
                "success",
            )
            if hasattr(self.main_window, "start_web_sync"):
                self.main_window.start_web_sync(silent=True)
        elif not silent:
            message_helper.show_info(self, "Başarılı", "Konum ayarları kaydedildi.")

