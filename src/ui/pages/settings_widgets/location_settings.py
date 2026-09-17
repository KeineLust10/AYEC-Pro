# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QHBoxLayout, QGridLayout)
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss, tc
from src.utils import message_helper
from src.ui.dialogs.location_picker_dialog import LocationPickerDialog
import logging

logger = logging.getLogger("AYECProLogger")

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
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("📍 Konum ve Harita Ayarları")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; margin-bottom: 10px;"))
        layout.addWidget(title)
        
        # Info Card
        info_card = QFrame()
        info_card.setStyleSheet(theme_qss("background-color: @surface_alt; border: 1px solid @surface_alt; border-radius: 8px; padding: 15px;"))
        ic_layout = QVBoxLayout(info_card)
        lbl_info = QLabel("Buradan uygulamanın harita başlangıç konumunu ayarlayabilirsiniz.\n"
                          "Bu konum, uygulama açıldığında ve 'Eve Dön' butonuna tıklandığında kullanılır.")
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
        lbl_info.setWordWrap(True)
        ic_layout.addWidget(lbl_info)
        layout.addWidget(info_card)
        
        # Location Selection Area
        loc_group = QFrame()
        loc_group.setStyleSheet(theme_qss("background-color: @surface; border: 1px solid @border; border-radius: 8px; padding: 20px;"))
        loc_layout = QVBoxLayout(loc_group)

        lbl_current = QLabel("Varsayılan Merkez Konumu")
        lbl_current.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        loc_layout.addWidget(lbl_current)
        
        # Lat/Lng Display (Grid Layout for better alignment)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        self.inp_lat = QLineEdit()
        self.inp_lat.setPlaceholderText("Enlem")
        self.inp_lat.setReadOnly(True)
        self.inp_lat.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 6px; padding: 10px; background-color: @surface_alt;"))
        
        self.inp_lng = QLineEdit()
        self.inp_lng.setPlaceholderText("Boylam")
        self.inp_lng.setReadOnly(True)
        self.inp_lng.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 6px; padding: 10px; background-color: @surface_alt;"))

        lbl_lat = QLabel("Enlem:")
        lbl_lat.setFont(QFont("Segoe UI", 10))
        grid_layout.addWidget(lbl_lat, 0, 0)
        grid_layout.addWidget(self.inp_lat, 0, 1)
        
        lbl_lng = QLabel("Boylam:")
        lbl_lng.setFont(QFont("Segoe UI", 10))
        grid_layout.addWidget(lbl_lng, 0, 2)
        grid_layout.addWidget(self.inp_lng, 0, 3)
        
        loc_layout.addLayout(grid_layout)
        
        # Pick Button
        self.btn_pick = QPushButton("Haritadan Konum Seç")
        self.btn_pick.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick.setFixedHeight(50)
        self.btn_pick.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
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
        loc_layout.addWidget(self.btn_pick)
        
        layout.addWidget(loc_group)
        layout.addStretch()
        
        # Save Button
        btn_save = QPushButton("💾 AYARLARI KAYDET")
        btn_save.setFixedHeight(50)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @success; 
                color: white; 
                border-radius: 6px; 
                font-weight: bold; 
                font-size: 14px;
            }
            QPushButton:hover { background-color: @success; }
        """))
        btn_save.clicked.connect(self.save_data)
        layout.addWidget(btn_save)

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
            lat = self.db.get_setting("map_default_lat", "39.6484")
            lng = self.db.get_setting("map_default_lng", "27.8826")
        return lat, lng

    def load_data(self):
        lat, lng = self._load_default_location_values()
        self.inp_lat.setText(lat)
        self.inp_lng.setText(lng)

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

    def save_data(self):
        if not self.inp_lat.text() or not self.inp_lng.text():
            message_helper.show_warning(self, "Uyarı", "Lütfen geçerli bir konum seçin.")
            return

        lat_val = self.inp_lat.text()
        lng_val = self.inp_lng.text()

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

        if self.main_window:
            self.main_window.show_notification(
                "Konum ayarlari kaydedildi ve kurulum haritasina gonderiliyor.",
                "success",
            )
            if hasattr(self.main_window, "start_web_sync"):
                self.main_window.start_web_sync(silent=True)
        else:
            message_helper.show_info(self, "Başarılı", "Konum ayarları kaydedildi.")

