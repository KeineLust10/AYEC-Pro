import os
import unicodedata

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QDialog, QFormLayout, QLineEdit, QDateTimeEdit, QComboBox, QSplitter, QListWidget,
                             QGraphicsDropShadowEffect, QApplication, QSizePolicy, QStackedWidget)
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from src.utils.theme_colors import tc, theme_qss
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QDateTime
from PyQt6.QtGui import QFont, QFontDatabase, QColor, QIcon, QAction
# Keep WebEngine lazy until the in-app traffic map is requested.
QWebEngineView = None

import urllib.request
import urllib.parse
import threading
import time
from datetime import datetime

from src.ui.pages.field_service_components import (
    FieldMapOverview,
    FieldOperationsPanel,
    ManualLocationDialog,
    PersonnelCard,
    ModernConfirmDialog,
)
from src.ui.widgets.field_radar_canvas import FieldRadarCanvas
from src.ui.widgets.tomtom_vector_map.tomtom_vector_map_view import TomTomVectorMapView
from src.utils.design_system import DesignTokens

_NOMINATIM_REQUEST_LOCK = threading.Lock()
_NOMINATIM_NEXT_REQUEST_AT = 0.0
_FIELD_UI_FONT_ID = -1


def _ensure_field_ui_font():
    global _FIELD_UI_FONT_ID
    if _FIELD_UI_FONT_ID == -1:
        font_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "fonts", "Inter-Variable.ttf")
        _FIELD_UI_FONT_ID = QFontDatabase.addApplicationFont(os.path.abspath(font_path))
    return _FIELD_UI_FONT_ID


def _wait_for_nominatim_slot():
    global _NOMINATIM_NEXT_REQUEST_AT
    with _NOMINATIM_REQUEST_LOCK:
        delay = max(0.0, _NOMINATIM_NEXT_REQUEST_AT - time.monotonic())
        if delay:
            time.sleep(delay)
        _NOMINATIM_NEXT_REQUEST_AT = time.monotonic() + 1.05

class FieldServicePage(QWidget):
    search_finished = pyqtSignal(list, bool) # results, is_manual
    """
    PREMIUM FIELD SERVICE DASHBOARD v3
    - Balıkesir Centered
    - Manual Location & Search
    - Location Sharing
    - Modern Sidebar
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        font_id = _ensure_field_ui_font()
        ui_font = QFont("Inter" if font_id >= 0 else "Segoe UI")
        ui_font.setFamilies(["Inter", "Segoe UI", "Arial"] if font_id >= 0 else ["Segoe UI", "Arial"])
        self.setFont(ui_font)
        self.db = db
        self.main_window = main_window
        # Default Coordinates (From Settings or Balıkesir fallback)
        try:
            self.default_lat = float(self.db.get_setting("map_default_lat", "39.6484"))
            self.default_lng = float(self.db.get_setting("map_default_lng", "27.8826"))
        except (ValueError, TypeError):
             self.default_lat = 39.6484
             self.default_lng = 27.8826
        self.search_finished.connect(self.on_search_finished)

        self.search_results_data = []
        self._map_search_cache = {}
        self._action_buttons = []
        self.radar_category = "all"
        self.live_traffic_active = False
        self.vector_map_view = None

        self.setup_ui()

    def refresh_theme(self):
        from src.utils.theme_manager import ThemeManager

        ThemeManager.refresh_widget_tree(self)
        self.update()

    def update_default_location(self, lat, lng):
        """Called externally to update default location instantly"""
        self.default_lat = float(lat)
        self.default_lng = float(lng)
        
        # Move map and update center marker
        if isinstance(self.map_view, FieldRadarCanvas):
            self.map_view.focus_coordinates(lat, lng)
        elif QWebEngineView:
            # Remove old center marker if any (clearing all for simplicity or we can track it)
            # For a cleaner update, we just fly to new location and add the marker
            script = f"""
                map.setView([{lat}, {lng}], 13);
                // Optional: Remove old center marker logic if needed, 
                // but adding a new one is safe as 'addMarker' pushes to array
                addMarker({lat}, {lng}, "Merkez Ofis", "Güncellenen Konum", true);
            """
            self.map_view.page().runJavaScript(script)
            
        self.notify("Harita konumu güncellendi.", "info")

    def on_search_text_changed(self, text):
        if hasattr(self, 'list_results'):
            self.list_results.clear()
            self.list_results.setVisible(False)
        self.search_results_data = []

    def search_address(self):
        # Keep address lookup off the UI thread so the map stays responsive.
        query = self.address_input.text().strip()
        if not query: return
        
        self.notify("Arama yapılıyor (Lütfen bekleyin)...", "info")

        # Check for shared location links
        import re
        coords = re.findall(r'([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)', query)
        if coords:
            lat, lng = coords[0]
            if isinstance(self.map_view, FieldRadarCanvas):
                if self.map_view.focus_coordinates(lat, lng):
                    self.notify("Konum bulundu!", "success")
                else:
                    self.notify("Gecersiz koordinatlar.", "warning")
                return
            if QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}, 16); addMarker({lat}, {lng}, 'Paylaşılan Konum', 'Link üzerinden aktarıldı');")
            self.notify("Konum bulundu!", "success")
            return

        worker = threading.Thread(target=self._search_thread, args=(query, 5, True), daemon=True)
        worker.start()

    def _search_thread(self, query, limit=1, is_manual=False):
        """
        Background Thread for Autocomplete (typing)
        """
        try:
            results = self._get_search_results(query, limit)
        except Exception:
            results = []
        # Emit signal to update UI safely from thread
        self.search_finished.emit(results, is_manual)

    def _get_search_results(self, query, limit=1):
        """
        Explicit address lookup (Nominatim + Photon), never called while typing.
        Returns list of dicts. safe to call from any thread.
        """
        cache_key = (str(query or "").strip().casefold(), int(limit))
        cached = self._map_search_cache.get(cache_key)
        if cached is not None:
            return [dict(item) for item in cached]
        results = []
        import ssl
        import json
        
        # SSL Context for all requests
        ctx = ssl.create_default_context()
        
        headers = {
            'User-Agent': 'AYEC-Pro/2.0'
        }

        # --- ATTEMPT 1: NOMINATIM ---
        try:
            _wait_for_nominatim_slot()
            logger.debug(f"Trying Nominatim for: {query}")
            params = urllib.parse.urlencode({'q': query, 'format': 'json', 'addressdetails': 1, 'limit': limit})
            url = f"https://nominatim.openstreetmap.org/search?{params}"
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                if response.getcode() == 200:
                    results = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Nominatim error: {e}")

        # --- ATTEMPT 2: PHOTON (Fallback) ---
        if not results:
            try:
                logger.debug(f"Nominatim empty/failed. Trying Photon for: {query}")
                p_params = urllib.parse.urlencode({'q': query, 'limit': limit})
                p_url = f"https://photon.komoot.io/api/?{p_params}"
                
                req = urllib.request.Request(p_url, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                    if response.getcode() == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        # Normalize Photon GeoJSON
                        for feature in data.get('features', []):
                            props = feature.get('properties', {})
                            coords = feature.get('geometry', {}).get('coordinates', [0,0])
                            
                            # Construct display name
                            parts = [props.get(k) for k in ['name', 'city', 'state', 'country'] if props.get(k)]
                            display_name = ", ".join(parts) if parts else query
                            
                            results.append({
                                'display_name': display_name,
                                'lat': str(coords[1]),
                                'lon': str(coords[0]),
                                'addresstype': 'photon_result'
                            })
            except Exception as e:
                 logger.error(f"Photon error: {e}")
        self._map_search_cache[cache_key] = [dict(item) for item in results]
        if len(self._map_search_cache) > 100:
            self._map_search_cache.pop(next(iter(self._map_search_cache)))
        return results

    def on_search_finished(self, results, is_manual):
        logger.debug(f"Field service search finished. manual={is_manual} results={len(results)}")
        self.search_results_data = results

        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            if results:
                self.vector_map_view.focus_coordinates(float(results[0]["lat"]), float(results[0]["lon"]))
                self.vector_map_view.search_input.setText(results[0].get("display_name", ""))
            else:
                self.notify("Arama icin sonuc bulunamadi.", "warning")
            return
        
        if hasattr(self, 'list_results'):
            self.list_results.clear()
            
            if not results:
                self.list_results.setVisible(False)
                if is_manual is True:
                     # Critical Error Dialog
                     from PyQt6.QtWidgets import QMessageBox
                     QMessageBox.warning(self, "Arama Başarısız", 
                        f"'{self.address_input.text()}' adresi için sonuç bulunamadı.\n\n"
                        "Lütfen 'İlçe, İl' formatında yazarak tekrar deneyin.\n"
                        "(Örn: Gönen, Balıkesir)")
                return

            if is_manual and len(results) == 1:
                 # Direct fly to result if single result and manual trigger
                 self.on_result_clicked(None, pre_data=results[0])
                 self.list_results.setVisible(False)
            else:
                for item in results:
                    self.list_results.addItem(item.get('display_name', 'Bilinmeyen Adres'))
                self.list_results.setVisible(True)

    def on_result_clicked(self, item, pre_data=None):
        data = pre_data
        if not data and item:
            row = self.list_results.row(item)
            if row >= 0 and row < len(self.search_results_data):
                data = self.search_results_data[row]
        
        if data:
            lat = float(data['lat'])
            lng = float(data['lon'])
            name = data.get('display_name', 'Konum').replace("'", "")
            if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
                self.vector_map_view.focus_coordinates(lat, lng)
            elif isinstance(self.map_view, FieldRadarCanvas):
                self.map_view.focus_coordinates(lat, lng)
            
            elif QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}, 15); addMarker({lat}, {lng}, 'Seçilen', '{name}');")
            
            if hasattr(self, 'list_results'):
                self.list_results.setVisible(False)
            self.address_input.setText(data.get('display_name', ''))

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 0, 20, 12)
        self.main_layout.setSpacing(12)

        self.overview = FieldMapOverview({
            "create_task": self.create_field_task,
            "optimize_route": self.open_optimized_route,
            "toggle_traffic": self.toggle_traffic,
            "filter_personnel": self.focus_personnel_filter,
            "toggle_map_mode": self.toggle_map_mode,
        }, self)
        self.metric_cards = self.overview.metric_cards
        self.field_kpi_values = self.overview.metric_values
        self.field_kpi_notes = self.overview.metric_notes
        self.overview_subtitle = self.overview.subtitle
        self.live_traffic_button = self.overview.live_traffic_button
        self.main_layout.addWidget(self.overview)

        # Main Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(14)
        self.splitter.setStyleSheet(theme_qss("QSplitter::handle{background:@finance_canvas;}"))

        self.operation_panel = FieldOperationsPanel({
            "manual": self.manual_input,
            "home": self.reset_to_default,
            "whatsapp": self.paste_whatsapp_link,
            "share": self.share_location,
            "assign": self.assign_location_to_personnel,
            "filter_category": self._set_radar_category,
        }, self.refresh_data, self)
        self.sidebar = self.operation_panel
        self.personnel_search = self.operation_panel.personnel_search
        self.radar_filter_buttons = self.operation_panel.radar_filter_buttons
        self.location_toggle = self.operation_panel.location_toggle
        self.location_scroll = self.operation_panel.location_scroll
        self.location_controls = self.operation_panel.location_controls
        self.scroll_area = self.operation_panel.scroll_area
        self.scroll_layout = self.operation_panel.scroll_layout

        # --- RIGHT MAP AREA ---
        self.map_view = FieldRadarCanvas(self.default_lat, self.default_lng)
        self.address_input = self.map_view.map_search_input
        self.address_input.textChanged.connect(self.on_search_text_changed)
        self.list_results = QListWidget(self.map_view)
        self.list_results.setObjectName("field_map_search_results")
        self.list_results.setVisible(False)
        self.list_results.setMaximumHeight(200)
        self.list_results.setStyleSheet(theme_qss("""
            QListWidget{background:@finance_surface;color:@finance_text;border:1px solid @finance_outline;border-radius:6px;}
            QListWidget::item{padding:8px;border-bottom:1px solid @finance_outline;}
            QListWidget::item:hover{background:@finance_surface_alt;}
        """))
        self.list_results.itemClicked.connect(self.on_result_clicked)
        self.map_view.personnelClicked.connect(self.focus_personnel)
        self.map_view.homeClicked.connect(self.reset_to_default)
        self.map_view.searchRequested.connect(self.search_map_location)
        self.map_view.trafficReady.connect(self._traffic_ready)
        self.map_view.trafficFailed.connect(self._traffic_failed)
        self.map_view.routeCalculationRequested.connect(self._request_road_route)
        self.map_view.routeShareRequested.connect(self.share_route)
        self.map_view.routeCalculated.connect(self._route_calculated)
        self.map_stack = QStackedWidget()
        self.map_stack.addWidget(self.map_view)
        self.traffic_map_view = None
        
        # Add to Splitter
        self.splitter.addWidget(self.map_stack)
        self.splitter.addWidget(self.sidebar)
        self.splitter.setStretchFactor(0, 1) # Map takes more space

        self.main_layout.addWidget(self.splitter)
        self._update_responsive_layout()
        self._position_search_results()

        # Initial Load (harita yükle; veri ilk gösterimde showEvent/ModernDesktopApp tarafından yüklenir)
        self.load_map()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()
        self._position_search_results()

    def _position_search_results(self):
        if not hasattr(self, "list_results") or not hasattr(self, "map_view"):
            return
        width = max(220, min(420, self.map_view.width() - 28))
        top = 190 if self.map_view.width() < 520 else 138
        self.list_results.setGeometry(14, top, width, 200)

    def _update_responsive_layout(self):
        compact = self.width() <= 900
        dense = self.width() <= 1100 or self.height() <= 820
        self.overview.set_dense(dense)
        self.operation_panel.set_dense(dense, self.height() <= 700)
        self.overview.setFixedHeight(max(210, self.overview.layout().sizeHint().height()))
        self.map_view.setMinimumSize(360 if compact else 420, 280 if dense else 480)
        orientation = Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        if self.splitter.orientation() != orientation:
            self.splitter.setOrientation(orientation)
        if compact:
            self.sidebar.setMinimumWidth(0)
            self.sidebar.setMaximumWidth(16777215)
        else:
            self.sidebar.setFixedWidth(320 if dense else 368)

    def create_field_task(self):
        from src.ui.pages.appointments_page import AddAppointmentDialog

        dialog = AddAppointmentDialog(self.db, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()

    def focus_personnel_filter(self):
        self.personnel_search.setFocus()
        self.personnel_search.selectAll()

    def _map_coordinates(self):
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            return self.vector_map_view.selected_coordinates
        if isinstance(self.map_view, FieldRadarCanvas):
            return self.map_view.selected_coordinates
        return self.default_lat, self.default_lng

    def search_map_location(self, query):
        query = str(query or "").strip()
        if not query:
            self.notify("Aramak icin adres veya koordinat girin.", "warning")
            return
        target_input = (
            self.vector_map_view.search_input
            if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view
            else self.address_input
        )
        target_input.setText(query)
        self.search_address()

    def toggle_map_mode(self):
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            self.map_stack.setCurrentWidget(self.map_view)
            self.overview.map_mode_button.setFixedWidth(104)
            self.overview.map_mode_button.setText("3D Vektor")
            return

        from src.utils.local_secret_store import load_secret
        try:
            api_key = load_secret("tomtom_traffic_api_key")
        except Exception as error:
            self.notify("TomTom anahtari okunamadi: {}".format(error), "error")
            return
        if not api_key:
            api_key = self._prompt_tomtom_api_key()
            if not api_key:
                self.notify("3D harita icin TomTom Maps SDK erisimi olan bir API anahtari gerekli.", "warning")
                return
            from src.utils.local_secret_store import save_secret
            try:
                save_secret("tomtom_traffic_api_key", api_key)
            except (OSError, RuntimeError) as error:
                self.notify("TomTom anahtari guvenli kaydedilemedi: {}".format(error), "error")
                return

        if self.vector_map_view is None:
            try:
                self.vector_map_view = TomTomVectorMapView(
                    api_key, self.default_lat, self.default_lng, self.map_stack
                )
            except Exception as error:
                self.notify("WebGL haritasi baslatilamadi: {}".format(error), "error")
                self.vector_map_view = None
                return
            self.vector_map_view.searchRequested.connect(self.search_map_location)
            self.vector_map_view.routeCalculationRequested.connect(self._request_road_route)
            self.vector_map_view.routeShareRequested.connect(self.share_route)
            self.vector_map_view.trafficRequested.connect(self._set_vector_traffic)
            self.vector_map_view.twoDimensionalRequested.connect(self.toggle_map_mode)
            self.map_stack.addWidget(self.vector_map_view)
            self.vector_map_view.set_personnel(self.map_view.personnel)
            if self.map_view.route_points:
                self.vector_map_view.set_route(self.map_view.route_geometry or self.map_view.route_points)

        self.map_stack.setCurrentWidget(self.vector_map_view)
        self.vector_map_view.set_traffic_active(self.live_traffic_active)
        self.overview.map_mode_button.setFixedWidth(154)
        self.overview.map_mode_button.setText("2D Haritaya Don")

    def _set_vector_traffic(self, active):
        self.live_traffic_active = bool(active)
        if self.vector_map_view:
            self.vector_map_view.set_traffic_active(active)

    def toggle_traffic(self):
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            self._set_vector_traffic(not self.vector_map_view._traffic_active)
            return
        self.open_live_traffic()

    def _prompt_tomtom_api_key(self):
        from src.ui.widgets.modern_dialog import ModernDialog
        from PyQt6.QtGui import QDesktopServices

        dialog = ModernDialog(title="TomTom Harita ve Trafik Baglantisi", parent=self.window(), width=540, height=310)
        description = QLabel(
            "TomTom Maps Orbis/OpenStreetMap tabanli 2D gorunum korunur; 3D Vektor ve trafik katmani ayni anahtari kullanir. "
            "Traffic Flow ile Maps SDK erisimleri acik olmalidir. Vektor haritada 3D gorunum WebGL gerektirir; "
            "anahtar izinleri TomTom Developer Portal'dan acilir. "
            "Masaustu uygulamasinda anahtarin domain whitelist (Referer) kisiti kapali olmalidir. "
            "Kullanim limitleri ve olasi ucretleri TomTom gelistirici portalinda kontrol edin."
        )
        description.setWordWrap(True)
        dialog.add_widget(description)

        portal = QLabel('<a href="https://my.tomtom.com/">TomTom gelistirici portalini ac</a>')
        portal.setOpenExternalLinks(True)
        dialog.add_widget(portal)

        key_input = QLineEdit()
        key_input.setObjectName("tomtom_traffic_api_key")
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setClearButtonEnabled(True)
        key_input.setPlaceholderText("TomTom Traffic Flow API anahtari")
        key_input.setFixedHeight(40)
        dialog.add_widget(key_input)
        dialog.add_button("Vazgec", variant="secondary", callback=dialog.reject)
        save_button = dialog.add_button("Guvenli Kaydet", callback=dialog.accept)
        save_button.setEnabled(False)
        key_input.textChanged.connect(lambda value: save_button.setEnabled(bool(value.strip())))
        key_input.returnPressed.connect(dialog.accept)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return key_input.text().strip()
        return ""

    def open_live_traffic(self):
        if self.live_traffic_active:
            self.map_view.disable_tomtom_traffic()
            self.live_traffic_active = False
            self.live_traffic_button.setText("Canli Trafik")
            return
        from src.utils.local_secret_store import load_secret, save_secret
        try:
            api_key = load_secret("tomtom_traffic_api_key")
        except Exception as exc:
            self.notify("Kayitli harita API anahtari okunamadi: {}".format(exc), "error")
            return
        if not api_key:
            api_key = self._prompt_tomtom_api_key()
            if not api_key:
                return
            try:
                save_secret("tomtom_traffic_api_key", api_key.strip())
            except (OSError, RuntimeError) as exc:
                self.notify("API anahtari guvenli kaydedilemedi: {}".format(exc), "error")
                return
        self.live_traffic_button.setEnabled(False)
        self.live_traffic_button.setText("Baglaniyor...")
        self.map_view.enable_tomtom_traffic(api_key)

    def _traffic_ready(self):
        self.live_traffic_active = True
        self.live_traffic_button.setEnabled(True)
        self.live_traffic_button.setText("Trafik Katmanini Kapat")

    def _traffic_failed(self, message):
        self.live_traffic_active = False
        if self.map_view.traffic_active:
            self.map_view.disable_tomtom_traffic()
        self.live_traffic_button.setEnabled(True)
        self.live_traffic_button.setText("Canli Trafik")
        if self.map_view._traffic_auth_failed:
            from src.utils.local_secret_store import delete_secret
            delete_secret("tomtom_traffic_api_key")
        self.notify(message, "error")

    @staticmethod
    def _distance_km(first, second):
        import math

        lat1, lng1 = map(math.radians, first)
        lat2, lng2 = map(math.radians, second)
        delta_lat = lat2 - lat1
        delta_lng = lng2 - lng1
        value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
        return 6371.0 * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1.0 - value)))

    def _request_road_route(self, points):
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            self.vector_map_view.set_route(points)
        try:
            from src.utils.local_secret_store import load_secret
            api_key = load_secret("tomtom_traffic_api_key")
        except Exception:
            api_key = ""
        self.map_view.calculate_tomtom_route(api_key, points)

    def _route_calculated(self, geometry, distance_meters, duration_seconds):
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            self.vector_map_view.set_route(geometry)
            self.vector_map_view.status_label.setText(
                "TomTom yol rotasi: {:.1f} km, {} dk".format(
                    distance_meters / 1000.0, max(1, round(duration_seconds / 60))
                )
            )

    def open_optimized_route(self):
        records = []
        for row in self._read_radar_personnel():
            if not FieldRadarCanvas.valid_coordinates(row.get("lat"), row.get("lng")):
                continue
            records.append({
                "name": str(row.get("name") or "Personel"),
                "coordinates": (float(row["lat"]), float(row["lng"])),
            })
        if not records:
            self.notify("Rota icin en az bir saha personeline GPS konumu atayin.", "warning")
            return

        route = []
        current = (self.default_lat, self.default_lng)
        pending = list(records)
        while pending:
            nearest = min(pending, key=lambda item: self._distance_km(current, item["coordinates"]))
            route.append(nearest)
            pending.remove(nearest)
            current = nearest["coordinates"]

        points = [(self.default_lat, self.default_lng)] + [item["coordinates"] for item in route]
        self.map_view.set_route(points)
        self.map_view.fit_route()
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            self.vector_map_view.set_route(points)
        self._request_road_route(points)
        route_names = " -> ".join(item["name"] for item in route)
        self.notify(
            "Durak sirasi haritada cizildi: {}. TomTom yol geometrisi icin Routing API yetkisi gereklidir.".format(route_names),
            "success",
        )

    def load_map(self):
        if isinstance(self.map_view, FieldRadarCanvas):
            return
        if not QWebEngineView: return
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                #map {{ height: 100vh; width: 100vw; position: absolute; top:0; left:0; }}
                body {{ margin: 0; padding: 0; }}
                .ping {{
                    width: 20px;
                    height: 20px;
                    background-color: #3b82f6;
                    border-radius: 50%;
                    position: relative;
                    border: 3px solid white;
                    box-shadow: 0 0 10px rgba(0,0,0,0.3);
                }}
                .ping::after {{
                    content: '';
                    width: 100%;
                    height: 100%;
                    background-color: #3b82f6;
                    border-radius: 50%;
                    position: absolute;
                    animation: pulse 2s infinite;
                    opacity: 0.5;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 0.8; }}
                    100% {{ opacity: 0; }}
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map', {{ zoomControl: false }}).setView([{self.default_lat}, {self.default_lng}], 13);
                L.control.zoom({{ position: 'bottomright' }}).addTo(map);

                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors'
                }}).addTo(map);

                var personnelMarkers = [];
                var userMarker = null;
                var centerMarker = null;
                var selectedLat = {self.default_lat};
                var selectedLng = {self.default_lng};

                function addMarker(lat, lng, title, details, type='user') {{
                    // Types: 'center', 'user', 'personnel'
                    
                    var color = '#ef4444'; // Red default (user)
                    var html = '';
                    var zIndex = 1000;
                    
                    if (type === 'center') {{
                        html = '<div class="ping"></div>';
                        zIndex = 500;
                    }} else if (type === 'personnel') {{
                        color = '#10b981'; // Green
                        html = '<div style="background-color: ' + color + '; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>';
                        zIndex = 800;
                    }} else {{
                        // User
                        html = '<div style="background-color: ' + color + '; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>';
                        zIndex = 2000; // Top
                    }}

                    var icon = L.divIcon({{
                        className: 'custom-div-icon',
                        html: html,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    }});
                    
                    var m = L.marker([lat, lng], {{ icon: icon, zIndexOffset: zIndex }}).addTo(map);
                    m.bindPopup("<b>" + title + "</b><br>" + details);
                    if (type !== 'personnel') m.openPopup();
                    
                    if (type === 'user') {{
                         if (userMarker) map.removeLayer(userMarker);
                         userMarker = m;
                         selectedLat = lat;
                         selectedLng = lng;
                    }} else if (type === 'center') {{
                        if (centerMarker) map.removeLayer(centerMarker);
                        centerMarker = m;
                    }} else if (type === 'personnel') {{
                        personnelMarkers.push(m);
                    }}
                    
                    return m;
                }}

                function clearPersonnelMarkers() {{
                    personnelMarkers.forEach(m => map.removeLayer(m));
                    personnelMarkers = [];
                }}

                function flyTo(lat, lng, zoom=14) {{
                    map.flyTo([lat, lng], zoom);
                }}
                
                function getSelectedCoords(callback) {{
                    // This function is intended to be called by Python via runJavaScript
                    return [selectedLat, selectedLng];
                }}

                // Add default center
                addMarker({self.default_lat}, {self.default_lng}, "Merkez Ofis", "Balıkesir Operasyon Merkezi", 'center');
                
                // Map Click Event
                map.on('click', function(e) {{
                    addMarker(e.latlng.lat, e.latlng.lng, "Seçilen Konum", e.latlng.lat.toFixed(5) + ", " + e.latlng.lng.toFixed(5), 'user');
                }});
            </script>
        </body>
        </html>
        """
        self.map_view.setHtml(html)





    def manual_input(self):
        if not QWebEngineView and not isinstance(self.map_view, FieldRadarCanvas): return
        
        dialog = ManualLocationDialog(self.window()) # Attach to main window for better centering
        if dialog.exec() == QDialog.DialogCode.Accepted:
            coords = dialog.get_coordinates()
            if coords:
                lat, lng = coords
                if isinstance(self.map_view, FieldRadarCanvas):
                    if self.map_view.focus_coordinates(lat, lng):
                        self.notify("Konum secildi: {}, {}".format(lat, lng), "success")
                    else:
                        self.notify("Gecersiz koordinatlar.", "warning")
                    return
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}); addMarker({lat}, {lng}, 'Manuel Konum', '{lat}, {lng}', 'user');")
                self.notify(f"Konuma gidiliyor: {lat}, {lng}", "success")
            else:
                 self.notify("Geçersiz koordinat formatı.", "error")

    def reset_to_default(self):
        if self.vector_map_view and self.map_stack.currentWidget() is self.vector_map_view:
            self.vector_map_view.focus_coordinates(self.default_lat, self.default_lng)
            return
        if isinstance(self.map_view, FieldRadarCanvas):
            self.map_view.focus_coordinates(self.default_lat, self.default_lng)
            return
        if not QWebEngineView: return
        self.map_view.page().runJavaScript(f"flyTo({self.default_lat}, {self.default_lng}, 13);")

    def paste_whatsapp_link(self):
        from PyQt6.QtWidgets import QApplication
        import re
        
        text = QApplication.clipboard().text()
        if not text:
            self.notify("Pano boş!", "warning")
            return

        # Attempt to find coordinates in various formats
        # 1. Google Maps Link (q=lat,lng)
        # 2. Raw coordinates (lat, lng)
        
        lat, lng = None, None
        
        # Regex for "q=lat,lng" or just "lat,lng"
        # Handles: https://maps.google.com/q=39.6484,27.8826
        # Handles: 39.6484, 27.8826
        match = re.search(r'(?:[?&]q=|@|:|^|\s)([-+]?\d+\.\d+)[,\s]+([-+]?\d+\.\d+)', text)
        
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
            except ValueError:
                pass

        if lat is not None and lng is not None:
             if isinstance(self.map_view, FieldRadarCanvas):
                if self.map_view.focus_coordinates(lat, lng):
                    self.notify("Konum secildi: {}, {}".format(lat, lng), "success")
                else:
                    self.notify("Gecersiz koordinatlar.", "warning")
                return
             if QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}); addMarker({lat}, {lng}, 'WhatsApp Konumu', 'Panodan yapıştırıldı', 'user');")
                self.notify(f"Konum bulundu: {lat}, {lng}", "success")
        else:
            # Fallback to search query
            self.address_input.setText(text)
            self.search_address()
            self.notify("Metin arama kutusuna yapıştırıldı.", "info")

    def share_location(self):
        if isinstance(self.map_view, FieldRadarCanvas):
            self._open_whatsapp_share(*self.map_view.selected_coordinates)
            return
        # Async fetch of selected coordinates from JS
        if not QWebEngineView:
            self.notify("Harita modülü aktif değil.", "warning")
            return

        def on_coords_received(result):
            if result and isinstance(result, list) and len(result) == 2:
                lat, lng = result
                self._open_whatsapp_share(lat, lng)
            else:
                # Fallback to default if JS fails
                self._open_whatsapp_share(self.default_lat, self.default_lng)

        try:
            # Call JS function we defined in HTML
            self.map_view.page().runJavaScript("getSelectedCoords()", on_coords_received)
        except Exception as e:
            logger.error(f"Field service share error: {e}")
            self._open_whatsapp_share(self.default_lat, self.default_lng)

    def share_route(self, points):
        valid_points = [
            (float(latitude), float(longitude))
            for latitude, longitude in points
            if FieldRadarCanvas.valid_coordinates(latitude, longitude)
        ]
        if len(valid_points) < 2:
            self.notify("Paylasmak icin rotada en az iki durak olmali.", "warning")
            return
        import urllib.parse
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        origin = "{:.6f},{:.6f}".format(*valid_points[0])
        destination = "{:.6f},{:.6f}".format(*valid_points[-1])
        waypoints = "|".join(
            "{:.6f},{:.6f}".format(*point) for point in valid_points[1:-1]
        )
        query = urllib.parse.urlencode({
            "api": "1",
            "origin": origin,
            "destination": destination,
            "waypoints": waypoints,
            "travelmode": "driving",
        })
        maps_url = "https://www.google.com/maps/dir/?{}".format(query)
        share_url = "https://wa.me/?{}".format(
            urllib.parse.urlencode({"text": "Saha rotasi: " + maps_url})
        )
        if QDesktopServices.openUrl(QUrl(share_url)):
            self.notify("Rota WhatsApp'ta paylasim icin acildi.", "success")
        else:
            self.notify("WhatsApp paylasim baglantisi acilamadi.", "warning")

    def _open_whatsapp_share(self, lat, lng):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        import urllib.parse
        
        # Link construction
        maps_link = f"https://www.google.com/maps?q={lat},{lng}"
        text = f"📍 Konumum: {maps_link}"
        encoded_text = urllib.parse.quote(text)
        
        # WhatsApp Web URL
        whatsapp_url = f"https://wa.me/?text={encoded_text}"
        
        QDesktopServices.openUrl(QUrl(whatsapp_url))
        self.notify(f"WhatsApp yönlendirmesi açılıyor ({lat:.4f}, {lng:.4f})...", "success")

    def assign_location_to_personnel(self):
        """Seçili konumu bir personele atar"""
        if isinstance(self.map_view, FieldRadarCanvas):
            self._show_assignment_dialog(*self.map_view.selected_coordinates)
            return
        if not QWebEngineView:
            self.notify("Harita modülü aktif değil.", "warning")
            return

        # 1. Get Coordinates from JS
        def on_coords(result):
            if not result or not isinstance(result, list) or len(result) != 2:
                self.notify("Lütfen önce haritadan bir konum seçin (Kırmızı nokta).", "warning")
                return
            
            lat, lng = result
            # Check if it's default (approx check)
            if abs(lat - self.default_lat) < 0.0001 and abs(lng - self.default_lng) < 0.0001:
                 # It might be default, warn user but allow
                 pass
            
            self._show_assignment_dialog(lat, lng)

        self.map_view.page().runJavaScript("getSelectedCoords()", on_coords)


    def _show_assignment_dialog(self, lat, lng):
        from PyQt6.QtWidgets import QListWidgetItem
        from src.ui.widgets.modern_dialog import ModernDialog
        from PyQt6.QtCore import Qt
        from datetime import datetime
        if not FieldRadarCanvas.valid_coordinates(lat, lng):
            self.notify("Gecersiz koordinatlar.", "warning")
            return
        techs = self._read_radar_personnel()
        if not techs:
            self.notify("Sistemde saha personeli bulunamadi.", "warning")
            return
        dialog = ModernDialog(title="Konumu Personele Ata", parent=self.window(), width=400, height=500)
        layout = dialog.content_layout
        lbl_info = QLabel(f"Secilen Konum: {lat:.5f}, {lng:.5f}\n\nBu konumu hangi personele atamak istiyorsunuz?")
        lbl_info.setFont(QFont(self.font().family(), 10))
        lbl_info.setStyleSheet(theme_qss("color:@finance_text;background:transparent;border:none;"))
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        list_widget = QListWidget()
        list_widget.setFont(QFont(self.font().family(), 10))
        list_widget.setStyleSheet(theme_qss("QListWidget{background:@finance_surface;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;}QListWidget::item{padding:10px;border-bottom:1px solid @finance_outline;}QListWidget::item:selected{background:@selection_bg;color:@selection_text;}"))
        for t in techs:
            item = QListWidgetItem(f"{t['name']} ({t.get('job', 'Personel')})")
            item.setData(Qt.ItemDataRole.UserRole, t['id'])
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        dialog.add_button("Vazgec", variant="secondary", callback=dialog.reject)
        assign_button = dialog.add_button("Konumu Ata", callback=dialog.accept)
        assign_button.setEnabled(False)
        list_widget.itemSelectionChanged.connect(lambda: assign_button.setEnabled(bool(list_widget.selectedItems())))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = list_widget.selectedItems()
            if not selected_items: return
            p_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
            p_name = selected_items[0].text().split('(')[0].strip()
            try:
                ensure_schema = getattr(self.db, "update_personnel_location_schema", None)
                if callable(ensure_schema):
                    ensure_schema()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.cursor.execute("""
                    UPDATE personnel 
                    SET lat=?, lng=?, status=?, last_seen=?
                    WHERE id=?
                """, (lat, lng, "G\u00f6revde", now, p_id))
                self.db.conn.commit()
                self.notify(f"{p_name} konumu guncellendi.", "success")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self.refresh_data)
            except Exception as e:
                logger.error(f"Field service update error: {e}")
                self.notify("Veritabani guncelleme hatasi!", "error")

    def refresh_data(self):
        try:
            logger.info("Field service refresh started")

            # Clear existing widgets but KEEP the stretch at the end
            # More standard way:
            while self.scroll_layout.count() > 1:
                item = self.scroll_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            techs = self._read_radar_personnel()
            all_techs = techs
            counts = {
                "all": len(all_techs),
                "idle": sum(self._radar_search_key(row.get("status")) == "bosta" for row in all_techs),
                "warnings": sum(not FieldRadarCanvas.valid_coordinates(row.get("lat"), row.get("lng")) for row in all_techs),
            }
            for category, caption in (("all", "Ekipler"), ("idle", "Bekleyen"), ("warnings", "Uyarilar")):
                self.radar_filter_buttons[category].setText("{} ({})".format(caption, counts[category]))
            techs = [row for row in all_techs if self._radar_matches(row)]
            
            logger.info(f"Field service technicians fetched: {len(techs)}")
            if isinstance(self.map_view, FieldRadarCanvas):
                self.map_view.set_personnel(techs)
                if self.vector_map_view:
                    self.vector_map_view.set_personnel(techs)
                gps_count = sum(FieldRadarCanvas.valid_coordinates(row.get("lat"), row.get("lng")) for row in all_techs)
                self.field_kpi_values[0].setText("{} Personel".format(len(all_techs)))
                self.field_kpi_notes[0].setText("{} GPS kaydi / {} personel".format(gps_count, len(all_techs)))

            if QWebEngineView and not isinstance(self.map_view, FieldRadarCanvas):
                try:
                    self.map_view.page().runJavaScript(
                        "if (typeof clearPersonnelMarkers === 'function') { clearPersonnelMarkers(); }"
                    )
                except Exception:
                    pass

            if not techs:
                empty_lbl = QLabel("Aktif personel veya görev bulunmuyor.")
                empty_lbl.setStyleSheet("color: #94a3b8; font-style: italic;")
                empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.scroll_layout.insertWidget(0, empty_lbl)
            else:
                no_coord_names = []
                for t in techs:
                    name = t.get('name', 'Bilinmeyen')
                    job = t.get('job', t.get('role', 'Personel'))
                    status = t.get('status', 'Boşta')
                    card = PersonnelCard(t, self.focus_personnel, self.finish_personnel_duty)
                    self.scroll_layout.insertWidget(self.scroll_layout.count()-1, card)

                    try:
                        raw_lat = t.get('lat')
                        raw_lng = t.get('lng')
                        if raw_lat is None or raw_lng is None:
                            logger.debug("Field service skipping %s: no coordinates", name)
                            no_coord_names.append(name)
                            continue
                        lat = float(raw_lat)
                        lng = float(raw_lng)
                        if not FieldRadarCanvas.valid_coordinates(lat, lng):
                            no_coord_names.append(name)
                            continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Field service skipping {name}: coord error {e}")
                        no_coord_names.append(name)
                        continue
                    logger.debug("Field service adding marker for %s at %s, %s", name, lat, lng)

                    
                    if QWebEngineView and not isinstance(self.map_view, FieldRadarCanvas):
                        try:
                            # Use repr() to escape special chars in name/job
                            js_code = f"addMarker({lat}, {lng}, {repr(name)}, {repr(job)}, 'personnel');"
                            self.map_view.page().runJavaScript(js_code)
                        except Exception as e:
                            logger.error(f"Field service map JS error: {e}")

                # Koordinatsız personel için uyarı banneri
                if no_coord_names:
                    warn_lbl = QLabel(
                        "{} personelin GPS koordinati tanimli degil: {}. "
                        "Personel kaydindan konum ekleyebilirsiniz.".format(len(no_coord_names), ", ".join(no_coord_names))
                    )
                    warn_lbl.setWordWrap(True)
                    warn_lbl.setStyleSheet(theme_qss("background:@finance_warning_bg;color:@finance_tertiary;border:1px solid @finance_outline;border-radius:4px;padding:8px 12px;font-size:11px;"))
                    self.scroll_layout.insertWidget(0, warn_lbl)

        except Exception as e:
            logger.error(f"Field service refresh error: {e}")
            self.notify(f"Veri yenileme hatası: {e}", "error")

    @staticmethod
    def _radar_search_key(value):
        text = unicodedata.normalize("NFKD", str(value or "").casefold().replace("\u0131", "i"))
        return "".join(character for character in text if not unicodedata.combining(character))

    def _radar_matches(self, record):
        category = self.radar_category
        if category == "idle" and self._radar_search_key(record.get("status")) != "bosta":
            return False
        if category == "warnings" and FieldRadarCanvas.valid_coordinates(record.get("lat"), record.get("lng")):
            return False
        query = self._radar_search_key(self.personnel_search.text()).strip()
        return not query or any(query in self._radar_search_key(record.get(key)) for key in ("name", "job", "role", "workplace"))

    def _set_radar_category(self, category):
        self.radar_category = category if category in self.radar_filter_buttons else "all"
        for key, button in self.radar_filter_buttons.items():
            button.setChecked(key == self.radar_category)
        self.refresh_data()

    def _read_radar_personnel(self):
        cursor = getattr(self.db, "cursor", None)
        if cursor is None:
            getter = getattr(self.db, "get_field_technicians", None)
            return getter() if callable(getter) else []
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(personnel)").fetchall()}
        if not {"id", "name", "role"}.issubset(columns):
            return []
        conditions = []
        if "is_deleted" in columns:
            conditions.append("COALESCE(is_deleted,0)=0")
        if "is_active" in columns:
            conditions.append("COALESCE(is_active,1)=1")
        sql = "SELECT * FROM personnel" + (" WHERE " + " AND ".join(conditions) if conditions else "")
        rows = cursor.execute(sql).fetchall()
        names = [column[0] for column in cursor.description]
        result = []
        for row in rows:
            record = dict(zip(names, row))
            role = str(record.get("role") or "").casefold().replace("\u0307", "").replace("\u0131", "i")
            if any(word in role for word in ("saha", "teknisyen", "destek", "personel")):
                record["job"] = record.get("role") or "Personel"
                record["status"] = record.get("status") or "Durum bildirilmemis"
                result.append(record)
        return result

    def focus_personnel(self, t_data):
        try:
            lat = float(t_data.get('lat'))
            lng = float(t_data.get('lng'))
            name = t_data.get('name', 'Personel')
            if isinstance(self.map_view, FieldRadarCanvas):
                self.map_view.focus_coordinates(lat, lng)
                return
            if QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}, 16);")
                self.notify(f"{name} konumuna gidiliyor...", "info")
        except Exception as e:
            self.notify("Konum odaklama hatası!", "error")

    def finish_personnel_duty(self, t_data):
        """Personeli boşa çıkar"""
        try:
             p_id = t_data.get('id')
             name = t_data.get('name', 'Personel')
             if not p_id: return

             # Custom Modern Dialog
             dialog = ModernConfirmDialog(
                 "Görevi Tamamla",
                 f"{name} için görevi sonlandırmak ve durumu 'Boşta' yapmak istiyor musunuz",
                 self.window()
             )
             
             if dialog.exec() == QDialog.DialogCode.Accepted:
                 self.db.cursor.execute("UPDATE personnel SET status='Boşta' WHERE id=?", (p_id,))
                 self.db.conn.commit()
                 self.notify(f"{name} durumu 'Boşta' olarak güncellendi.", "success")
                 self.refresh_data()
        except Exception as e:
             self.notify(f"Hata: {e}", "error")



    def showEvent(self, event):
        super().showEvent(event)
        self._update_responsive_layout()
        # Load map with slight delay to ensure container is ready
        # Using a flag to prevent reloading if already loaded could be good, 
        # but setup_ui calls load_map initially.
        # We will refresh data here. 
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._update_responsive_layout)
        QTimer.singleShot(100, self.refresh_data)

    def notify(self, message, level="info"):
        """Centralized notification proxy"""
        if self.main_window and hasattr(self.main_window, 'show_notification'):
            self.main_window.show_notification(message, level)
        elif hasattr(self.window(), 'show_notification'):
            self.window().show_notification(message, level)
        else:
            # Fallback
            if level == "error": show_error(self.window(), message)
            elif level == "success": show_success(self.window(), message)
            elif level == "warning": show_warning(self.window(), message)
            else: show_info(self.window(), message)
