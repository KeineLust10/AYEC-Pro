"""Native fleet map with on-demand OpenStreetMap tiles and truthful GPS markers."""

import math
import os
import tempfile
import time
from collections import OrderedDict

from PyQt6.QtCore import QPointF, QRectF, Qt, QUrl, QUrlQuery, pyqtSignal, QStandardPaths, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QImage, QFontDatabase, QPainterPath
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkRequest
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QFrame

from src.utils.theme_colors import tc, theme_qss
from src.utils.theme_manager import ThemeManager
from src.utils.design_system import DesignTokens

_MAP_FONT_ID = -1


class FieldRadarCanvas(QWidget):
    personnelClicked = pyqtSignal(dict)
    selectionChanged = pyqtSignal(float, float)
    homeClicked = pyqtSignal()
    trafficRequested = pyqtSignal(bool)
    searchRequested = pyqtSignal(str)
    trafficReady = pyqtSignal()
    trafficFailed = pyqtSignal(str)
    routeCalculationRequested = pyqtSignal(list)
    routeCalculated = pyqtSignal(list, int, int)
    routeShareRequested = pyqtSignal(list)
    filterRequested = pyqtSignal()
    gpsTrackingRequested = pyqtSignal()
    routeOptimizationRequested = pyqtSignal()
    trafficToggleRequested = pyqtSignal()
    mapModeRequested = pyqtSignal()
    drawRouteRequested = pyqtSignal()

    TILE_SIZE = 256
    TILE_ZOOM = 12
    MAX_BASE_TILES = 80
    MAX_DARK_TILES = 80
    MAX_TRAFFIC_TILES = 80
    MAX_PENDING_MAP_TILES = 16
    MAX_PENDING_TRAFFIC_TILES = 48

    def __init__(self, latitude, longitude, parent=None):
        super().__init__(parent)
        global _MAP_FONT_ID
        if _MAP_FONT_ID == -1:
            font_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "fonts", "Inter-Variable.ttf")
            _MAP_FONT_ID = QFontDatabase.addApplicationFont(os.path.abspath(font_path))
        reference_font = QFont("Inter" if _MAP_FONT_ID >= 0 else "Segoe UI")
        reference_font.setFamilies(["Inter", "Segoe UI", "Arial"] if _MAP_FONT_ID >= 0 else ["Segoe UI", "Arial"])
        reference_font.setPointSize(10)
        reference_font.setPixelSize(12)
        self.setFont(reference_font)
        self.center = (float(latitude), float(longitude))
        self.selected_coordinates = self.center
        self.personnel = []
        self._personnel_total_count = 0
        self._visible_tile_sources = set()
        self._hits = []
        self.zoom = 2 ** 5
        self.selection_visible = False
        self.route_drawing = False
        self.route_points = []
        self.route_geometry = []
        self.route_distance_meters = 0
        self.route_duration_seconds = 0
        self._route_reply = None
        self._route_generation = 0
        self.traffic_active = False
        self._traffic_key = ""
        self._traffic_tiles = OrderedDict()
        self._traffic_pending = set()
        self._traffic_replies = {}
        self._traffic_generation = 0
        self._traffic_auth_failed = False
        self._traffic_connecting = False
        self._traffic_tile_error_reported = False
        self._tiles = OrderedDict()
        self._tile_sources = OrderedDict()
        self._dark_tiles = OrderedDict()
        self._active_tile_style = None
        self._pending_tiles = set()
        self._base_replies = {}
        self._base_generation = 0
        self._tomtom_map_unavailable = False
        self._tomtom_copyright_caption = ""
        self._copyrights_requested = False
        self._copyright_reply = None
        self._tile_retry_after = OrderedDict()
        self._force_refresh = False
        self._refresh_requested_tiles = set()
        self._pulse = 0.0
        self._drag_position = None
        self.setMinimumSize(520, 480)
        self.setMouseTracking(True)
        self._network = QNetworkAccessManager(self)
        self._disk_cache = QNetworkDiskCache(self)
        cache_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        if not cache_root:
            cache_root = os.path.join(tempfile.gettempdir(), "ayecpro-map-cache")
        os.makedirs(cache_root, exist_ok=True)
        self._disk_cache.setCacheDirectory(os.path.join(cache_root, "osm-tiles"))
        self._disk_cache.setMaximumCacheSize(64 * 1024 * 1024)
        self._network.setCache(self._disk_cache)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(90)
        self._pulse_timer.timeout.connect(self._advance_pulse)

        self.navigation = QWidget(self)
        controls = QVBoxLayout(self.navigation)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)
        self.zoom_in = QPushButton("+")
        self.zoom_out = QPushButton("-")
        self.home = QPushButton("O")
        zoom_button_style = theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0;min-height:32px;font-size:25px;}")
        for button, tip in ((self.zoom_in, "Zoom in"), (self.zoom_out, "Zoom out"), (self.home, "Return to center")):
            button.setFixedSize(32, 32)
            button.setToolTip(tip)
            button.setStyleSheet(zoom_button_style)
            controls.addWidget(button)
        # The first stylesheet call can occur while the semantic theme hook is
        # being installed. Reapply it so even the first zoom control is themed.
        self.zoom_in.setStyleSheet(zoom_button_style)
        self.zoom_in.clicked.connect(lambda: self.change_zoom(1.25))
        self.zoom_out.clicked.connect(lambda: self.change_zoom(0.8))
        self.home.clicked.connect(self.homeClicked.emit)
        self.navigation.adjustSize()

        self.map_toolbar = QWidget(self)
        toolbar_layout = QHBoxLayout(self.map_toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(6)
        self.map_search_input = QLineEdit()
        self.map_search_input.setPlaceholderText(
            "Adres, m\u00fc\u015fteri ad\u0131 veya koordinat ara (\u00d6rn: Malko\u00e7 Mh.)..."
        )
        self.map_search_input.setMinimumWidth(90)
        self.map_search_input.setMaximumWidth(480)
        self.map_search_input.setFixedHeight(36)
        self.map_search_input.setStyleSheet(theme_qss("QLineEdit{background:@finance_surface;color:@finance_text;border:1px solid @finance_outline;border-radius:6px;padding:0 12px;font-size:16.25px;}"))
        self.map_search_input.returnPressed.connect(lambda: self.searchRequested.emit(self.map_search_input.text()))
        self.map_search_button = QPushButton("Haritada Bul")
        self.map_search_button.setFixedWidth(118)
        self.map_search_button.setFixedHeight(36)
        self.map_search_button.clicked.connect(lambda: self.searchRequested.emit(self.map_search_input.text()))
        self.map_search_button.setStyleSheet(theme_qss("QPushButton{background:@finance_primary;color:@finance_primary_text;border:1px solid @finance_outline;border-radius:6px;padding:0 8px;font-size:15px;font-weight:700;}"))
        toolbar_layout.addWidget(self.map_search_input, 1)
        toolbar_layout.addWidget(self.map_search_button)
        self.filter_action_button = QPushButton("Filtrele")
        self.filter_action_button.setObjectName("field_action_filter")
        self.filter_action_button.setFixedHeight(36)
        self.filter_action_button.clicked.connect(self.filterRequested.emit)
        self.filter_action_button.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface_alt;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:6px;padding:0 12px;font-size:15px;font-weight:700;}"
        ))
        self.filter_action_button.setParent(self.map_toolbar)
        self.filter_action_button.hide()
        self.map_mode_toolbar = QWidget(self)
        mode_layout = QHBoxLayout(self.map_mode_toolbar)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(4)
        self.map_mode_buttons = {}
        for key, caption, signal in (
            ("gps", "Canl\u0131 GPS Takip", self.gpsTrackingRequested),
            ("ai_route", "AI Rota", self.routeOptimizationRequested),
            ("traffic", "Trafik", self.trafficToggleRequested),
            ("layer", "Katman", self.mapModeRequested),
        ):
            button = QPushButton(caption)
            button.setObjectName("field_map_mode_{}".format(key))
            button.setFixedHeight(34)
            button.setFixedWidth({"gps": 116, "ai_route": 76, "traffic": 72, "layer": 78}[key])
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:@finance_surface_alt;color:@finance_text;"
                "border:1px solid @finance_outline;border-radius:6px;padding:0 4px;"
                "font-size:15px;font-weight:700;}QPushButton:hover{color:@finance_secondary;}"
            ))
            button.clicked.connect(signal.emit)
            mode_layout.addWidget(button)
            self.map_mode_buttons[key] = button
        mode_layout.addStretch(1)
        self.map_mode_toolbar.adjustSize()
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.map_mode_toolbar)
        self.route_toolbar = QWidget(self)
        route_layout = QHBoxLayout(self.route_toolbar)
        route_layout.setContentsMargins(0, 0, 0, 0)
        route_layout.setSpacing(6)
        route_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.draw_route_button = QPushButton("Rota Ciz")
        self.draw_route_button.setObjectName("field_map_draw_route")
        self.draw_route_button.setCheckable(True)
        self.draw_route_button.setFixedWidth(112)
        self.draw_route_button.setFixedHeight(40)
        self.draw_route_button.setToolTip("Haritaya tiklayarak guzergah duraklari secin")
        self.draw_route_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:6px;padding:0 10px;font-size:15px;font-weight:700;}QPushButton:checked{background:@finance_primary;color:@selection_text;}"))
        self.draw_route_button.toggled.connect(self._set_route_drawing)
        self.draw_route_button.hide()
        route_layout.addWidget(self.draw_route_button)
        self.finish_route_button = QPushButton("Rotayi Bitir")
        self.finish_route_button.setObjectName("field_map_finish_route")
        self.finish_route_button.setFixedWidth(112)
        self.finish_route_button.setFixedHeight(34)
        self.finish_route_button.setToolTip("En az iki durakla taslak guzergahi tamamlayin")
        self.finish_route_button.clicked.connect(self.finish_route_drawing)
        self.finish_route_button.setStyleSheet(theme_qss("QPushButton{background:@finance_secondary;color:@finance_primary_text;border:1px solid @finance_outline;border-radius:6px;padding:0 10px;font-size:15px;font-weight:700;}"))
        self.finish_route_button.hide()
        route_layout.addWidget(self.finish_route_button)
        self.clear_route_button = QPushButton("Rotayi Sil")
        self.clear_route_button.setObjectName("field_map_clear_route")
        self.clear_route_button.setFixedWidth(92)
        self.clear_route_button.setFixedHeight(34)
        self.clear_route_button.clicked.connect(self.clear_route)
        self.clear_route_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text_muted;border:1px solid @finance_outline;border-radius:6px;padding:0 10px;font-size:15px;}"))
        self.clear_route_button.hide()
        route_layout.addWidget(self.clear_route_button)
        self.share_route_button = QPushButton("Rotayi Paylas")
        self.share_route_button.setObjectName("field_map_share_route")
        self.share_route_button.setFixedWidth(104)
        self.share_route_button.setFixedHeight(34)
        self.share_route_button.setToolTip("Cizilen rotayi WhatsApp ile paylas")
        self.share_route_button.clicked.connect(
            lambda: self.routeShareRequested.emit(list(self.route_points))
        )
        self.share_route_button.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_primary;color:@finance_primary_text;border:1px solid "
            "@finance_outline;border-radius:6px;padding:0 10px;font-size:15px;font-weight:700;}"
        ))
        self.share_route_button.hide()
        route_layout.addWidget(self.share_route_button)
        self.refresh_map_button = QPushButton("Haritayi Guncelle")
        self.refresh_map_button.setObjectName("field_map_refresh")
        self.refresh_map_button.setFixedHeight(30)
        self.refresh_map_button.setToolTip("Gorunen bolgeyi yenile ve trafik verisini tazele")
        self.refresh_map_button.clicked.connect(self.refresh_visible_tiles)
        self.refresh_map_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:6px;padding:0 12px;font-size:15px;font-weight:700;}"))
        self.refresh_map_button.setParent(self.map_toolbar)
        self.refresh_map_button.hide()
        self.map_toolbar.adjustSize()
        self.route_toolbar.setFixedSize(430, 42)
        self.route_toolbar.hide()

        self.map_telemetry_bar = QFrame(self)
        self.map_telemetry_bar.setObjectName("field_map_telemetry_bar")
        self.map_telemetry_bar.setStyleSheet(theme_qss(
            "QFrame#field_map_telemetry_bar{background:@finance_surface;border:none;}"
            "QLabel{background:transparent;border:none;}"
        ))
        telemetry_layout = QHBoxLayout(self.map_telemetry_bar)
        telemetry_layout.setContentsMargins(10, 2, 10, 2)
        telemetry_layout.setSpacing(10)
        self.map_telemetry_label = QLabel("")
        self.map_telemetry_label.setStyleSheet(theme_qss(
            "color:@finance_text_muted;font-family:Consolas,monospace;font-size:12.5px;font-weight:600;"
        ))
        telemetry_layout.addWidget(self.map_telemetry_label, 1)
        self.map_telemetry_source = QLabel("")
        self.map_telemetry_source.setStyleSheet(theme_qss(
            "color:@finance_secondary;font-family:Consolas,monospace;font-size:12.5px;font-weight:700;"
        ))
        telemetry_layout.addWidget(self.map_telemetry_source)
        self.map_telemetry_bar.setFixedHeight(20)

        self.route_status = QLabel(self)
        self.route_status.setObjectName("field_map_route_status")
        self.route_status.setStyleSheet(theme_qss(
            "QLabel#field_map_route_status{background:@finance_surface;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:8px;padding:8px 12px;font-size:15px;font-weight:700;}"
        ))
        self.route_status.setWordWrap(True)
        self.route_status.hide()

        self.empty_state = QFrame(self)
        self.empty_state.setObjectName("field_map_empty_state")
        self.empty_state.setStyleSheet(theme_qss(
            "QFrame#field_map_empty_state{background:@finance_surface;"
            "border:1px solid @finance_outline;border-radius:9px;}"
        ))
        empty_layout = QHBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(10, 7, 12, 7)
        empty_layout.setSpacing(9)
        empty_icon = QLabel("GPS")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setFixedSize(34, 30)
        empty_icon.setStyleSheet(theme_qss(
            "background:@finance_surface_alt;color:@finance_secondary;border:1px solid @finance_outline;"
            "border-radius:6px;font-size:15px;font-weight:800;"
        ))
        empty_layout.addWidget(empty_icon)
        empty_copy = QVBoxLayout()
        empty_copy.setSpacing(2)
        empty_title = QLabel("Personel GPS kaydi yok")
        empty_title.setStyleSheet(theme_qss("color:@finance_text;font-size:16.25px;font-weight:700;border:none;"))
        empty_hint = QLabel("Haritadaki isaret varsayilan merkezdir.")
        empty_hint.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;border:none;"))
        empty_copy.addWidget(empty_title)
        empty_copy.addWidget(empty_hint)
        empty_layout.addLayout(empty_copy)
        self.empty_state.adjustSize()
        self.empty_state.hide()

        self.map_status = QLabel("Harita yukleniyor...", self)
        self.map_status.setObjectName("field_map_status")
        self.map_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.map_status.setStyleSheet(theme_qss(
            "QLabel#field_map_status{background:@finance_surface;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:8px;padding:10px 16px;font-size:16.25px;}"
        ))
        self.map_status.adjustSize()

        self.traffic_legend = QFrame(self)
        self.traffic_legend.setObjectName("field_traffic_legend")
        self.traffic_legend.setStyleSheet(theme_qss(
            "QFrame#field_traffic_legend{background:@finance_surface;border:1px solid @finance_outline;border-radius:8px;}"
        ))
        legend_layout = QVBoxLayout(self.traffic_legend)
        legend_layout.setContentsMargins(10, 8, 10, 8)
        legend_layout.setSpacing(5)
        legend_title = QLabel("TRAFIK AKISI")
        legend_title.setStyleSheet(theme_qss("color:@finance_text;font-size:15px;font-weight:700;border:none;"))
        legend_layout.addWidget(legend_title)
        self.traffic_status = QLabel("Baglaniyor...")
        self.traffic_status.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;border:none;"))
        legend_layout.addWidget(self.traffic_status)
        for caption, color in (("Akici", "#149f67"), ("Yavas", "#db9200"),
                               ("Yogun", "#ce2203"), ("Kapali yol", "#c6d0d2")):
            row = QHBoxLayout()
            marker = QFrame()
            marker.setFixedSize(10, 10)
            marker.setStyleSheet("background:{};border:none;border-radius:5px;".format(color))
            label = QLabel(caption)
            label.setStyleSheet(theme_qss("color:@finance_text;font-size:15px;border:none;"))
            row.addWidget(marker)
            row.addWidget(label)
            row.addStretch(1)
            legend_layout.addLayout(row)
        self.traffic_legend.adjustSize()
        self.traffic_legend.hide()
        self._update_empty_state()

    def _advance_pulse(self):
        self._pulse = (self._pulse + 0.025) % 1.0
        self.update(self._pulse_damage())

    def _pulse_damage(self):
        center = self._screen_point(*self.center)
        return QRectF(center.x() - 36, center.y() - 36, 194, 74).toAlignedRect().intersected(self.rect())

    def showEvent(self, event):
        super().showEvent(event)
        if not self._pulse_timer.isActive():
            self._pulse_timer.start()

    def hideEvent(self, event):
        self._pulse_timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._pulse_timer.stop()
        self._base_generation += 1
        self._cancel_base_requests()
        self._cancel_copyright_request()
        self._traffic_generation += 1
        self._cancel_traffic_requests()
        super().closeEvent(event)

    def resizeEvent(self, event):
        narrow = self.width() < 760
        for key, button in self.map_mode_buttons.items():
            button.setVisible(not narrow or key == "gps")
        self._position_overlay_controls()
        super().resizeEvent(event)

    def _position_overlay_controls(self):
        route_offset = 48 if self.route_drawing else 0
        self.navigation.move(
            max(12, self.width() - self.navigation.width() - 14), 64 + route_offset
        )
        self.map_toolbar.move(8, 4)
        self.map_toolbar.resize(max(0, self.width() - 16), 36)
        self.map_telemetry_bar.move(0, 40 + route_offset)
        self.map_telemetry_bar.resize(self.width(), 24)
        self.route_toolbar.move(14, 44)
        self.route_toolbar.setFixedWidth(min(430, max(112, self.width() - 28)))
        self.route_status.move(14, 86 + route_offset)
        self.route_status.setMaximumWidth(max(180, self.width() - self.traffic_legend.width() - 52))
        self.route_status.adjustSize()
        self.traffic_legend.move(
            max(12, self.width() - self.traffic_legend.width() - 14), 122 + route_offset
        )
        self.empty_state.move(14, 182)
        self.map_status.move((self.width() - self.map_status.width()) // 2,
                             (self.height() - self.map_status.height()) // 2)

    def _set_map_status(self, message):
        self.map_status.setText(message)
        self.map_status.adjustSize()
        self.map_status.move((self.width() - self.map_status.width()) // 2,
                             (self.height() - self.map_status.height()) // 2)
        self.map_status.setVisible(bool(message))

    @staticmethod
    def valid_coordinates(latitude, longitude):
        try:
            lat, lng = float(latitude), float(longitude)
            return math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180
        except (TypeError, ValueError):
            return False

    def set_personnel(self, records):
        source_records = list(records)
        self._personnel_total_count = len(source_records)
        self.personnel = [dict(row) for row in source_records if self.valid_coordinates(row.get("lat"), row.get("lng"))]
        self._update_empty_state()
        self.update()

    def _update_empty_state(self):
        if hasattr(self, "empty_state"):
            self.empty_state.setVisible(not self.personnel and not self.route_points)

    def focus_coordinates(self, latitude, longitude):
        if not self.valid_coordinates(latitude, longitude):
            return False
        self.center = (float(latitude), float(longitude))
        self.selected_coordinates = self.center
        self.selection_visible = True
        self.selectionChanged.emit(*self.selected_coordinates)
        self.update()
        return True

    def change_zoom(self, factor):
        self.zoom = max(0.25, min(128.0, self.zoom * factor))
        self.update()

    def set_traffic_active(self, active):
        self.traffic_active = bool(active)
        self.trafficRequested.emit(self.traffic_active)
        self.update()

    def enable_tomtom_traffic(self, api_key):
        self._traffic_generation += 1
        self._cancel_traffic_requests()
        self._base_generation += 1
        self._cancel_base_requests()
        self._cancel_copyright_request()
        self._traffic_key = str(api_key or "").strip()
        self._traffic_auth_failed = False
        self._traffic_tile_error_reported = False
        self._tomtom_map_unavailable = False
        self._tomtom_copyright_caption = ""
        self._copyrights_requested = False
        if not self._traffic_key:
            self.trafficFailed.emit("TomTom Traffic API anahtari bos olamaz.")
            return
        self._tiles.clear()
        self._tile_sources.clear()
        self._dark_tiles.clear()
        self._tile_retry_after.clear()
        self._refresh_requested_tiles.clear()
        self._traffic_tiles.clear()
        self.traffic_active = True
        self._traffic_connecting = True
        self._set_map_status("Harita yukleniyor...")
        self.traffic_status.setText("Baglaniyor...")
        self.traffic_legend.show()
        self.trafficRequested.emit(True)
        self.update()

    def set_tomtom_api_key(self, api_key):
        """Use TomTom as the base map without enabling the traffic overlay."""
        key = str(api_key or "").strip()
        if not key:
            return False
        self._traffic_key = key
        self._tomtom_map_unavailable = False
        self._tiles.clear()
        self._tile_sources.clear()
        self._dark_tiles.clear()
        self._tile_retry_after.clear()
        self._refresh_requested_tiles.clear()
        self._base_generation += 1
        self._cancel_base_requests()
        self.update()
        return True

    def _emit_traffic_api_error(self, body, fallback, status_code):
        code = ""
        message = ""
        try:
            import json
            response = json.loads(body.decode("utf-8"))
            details = response.get("detailedError", response.get("error", {}))
            code = str(details.get("code", details.get("status", "")))
            message = str(details.get("message", ""))
        except (ValueError, TypeError, UnicodeDecodeError, AttributeError):
            pass
        normalized_code = code.replace("_", "").replace(" ", "").lower()
        invalid_key_codes = {"apikeyinvalid", "invalidapikey", "apikeynotfound"}
        self._traffic_auth_failed = normalized_code in invalid_key_codes
        detail = " ({})".format(message[:180]) if message else ""
        if normalized_code in {"invalidreferer", "unknownreferer"}:
            detail += " TomTom anahtarinda alan adi kisitlamasi var; masaustu uygulamasi icin bu kisitlamayi kaldirin veya uygulamaya uygun bir anahtar olusturun."
        self.trafficFailed.emit(
            "{}{}. TomTom Traffic Flow urun yetkisini ve API anahtari kullanim limitini kontrol edin.".format(
                fallback, detail
            )
        )

    def _traffic_layers_ready(self):
        if not self._traffic_active_tile_pair():
            return
        suffix = " | OSM tabani" if self._tomtom_map_unavailable else ""
        self.traffic_status.setText("Guncel: {}{}".format(time.strftime("%H:%M:%S"), suffix))
        if self._traffic_connecting:
            self._traffic_connecting = False
            self.trafficReady.emit()

    def _traffic_active_tile_pair(self):
        return any(key in self._tiles for key in self._traffic_tiles)

    def disable_tomtom_traffic(self):
        self._traffic_generation += 1
        self._cancel_traffic_requests()
        self._base_generation += 1
        self._cancel_base_requests()
        self._cancel_copyright_request()
        self.traffic_active = False
        self._traffic_connecting = False
        # Keep the saved TomTom key active for base-map tiles when traffic is off.
        self._tomtom_map_unavailable = False
        self._tomtom_copyright_caption = ""
        self._copyrights_requested = False
        self._tiles.clear()
        self._tile_sources.clear()
        self._dark_tiles.clear()
        self._tile_retry_after.clear()
        self._refresh_requested_tiles.clear()
        self._traffic_tiles.clear()
        self._set_map_status("Harita yukleniyor...")
        self.traffic_status.setText("Kapali")
        self.traffic_legend.hide()
        self.trafficRequested.emit(False)
        self.update()

    def _set_route_drawing(self, active):
        self.route_drawing = bool(active)
        self.route_toolbar.setVisible(self.route_drawing)
        self.draw_route_button.setVisible(self.route_drawing)
        self._position_overlay_controls()
        if self.route_drawing:
            self._cancel_route_request()
            self.route_points = []
            self.route_geometry = []
            self.route_distance_meters = 0
            self.route_duration_seconds = 0
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.route_status.setText("Durak eklemek icin haritaya tiklayin; rotayi bitirince noktalar korunur.")
            self.route_status.show()
            self.finish_route_button.show()
            self.finish_route_button.setEnabled(False)
            self.clear_route_button.show()
            self.share_route_button.hide()
        else:
            self.unsetCursor()
            if self.route_points:
                self._update_route_status()
            elif hasattr(self, "route_status"):
                self.route_status.hide()
            if hasattr(self, "finish_route_button"):
                self.finish_route_button.hide()
            if hasattr(self, "clear_route_button"):
                self.clear_route_button.hide()
            if hasattr(self, "share_route_button"):
                self.share_route_button.hide()
        self.route_status.adjustSize()
        self.update()

    def add_route_point(self, latitude, longitude):
        if not self.valid_coordinates(latitude, longitude):
            return False
        self.route_points.append((float(latitude), float(longitude)))
        self._update_empty_state()
        self.route_geometry = []
        self.route_distance_meters = 0
        self.route_duration_seconds = 0
        self.selected_coordinates = self.route_points[-1]
        self.selection_visible = False
        self.selectionChanged.emit(*self.selected_coordinates)
        self.finish_route_button.setEnabled(len(self.route_points) >= 2)
        self.clear_route_button.show()
        self.share_route_button.hide()
        self.route_status.setText("{} durak secildi - devam edin veya Rotayi Bitir'e basin.".format(
            len(self.route_points)
        ))
        self.route_status.adjustSize()
        self.route_status.show()
        self.update()
        return True

    def finish_route_drawing(self):
        if len(self.route_points) < 2:
            self.route_status.setText("Guzergah icin haritada en az iki durak secin.")
            self.route_status.adjustSize()
            self.route_status.show()
            return
        self.draw_route_button.setChecked(False)
        self._update_route_status()
        self.clear_route_button.show()
        self.share_route_button.show()
        self.routeCalculationRequested.emit(list(self.route_points))
        self.update()

    def clear_route(self):
        self._cancel_route_request()
        self.route_points = []
        self._update_empty_state()
        self.route_geometry = []
        self.route_distance_meters = 0
        self.route_duration_seconds = 0
        self.route_drawing = False
        self.draw_route_button.setChecked(False)
        self.route_status.hide()
        self.finish_route_button.hide()
        self.clear_route_button.hide()
        self.share_route_button.hide()
        self.update()

    def set_route(self, points):
        self._cancel_route_request()
        route = []
        for latitude, longitude in points:
            if self.valid_coordinates(latitude, longitude):
                route.append((float(latitude), float(longitude)))
        self.route_points = route
        self._update_empty_state()
        self.route_geometry = []
        self.route_distance_meters = 0
        self.route_duration_seconds = 0
        self.route_drawing = False
        self.draw_route_button.setChecked(False)
        self.finish_route_button.hide()
        self.clear_route_button.setVisible(len(route) > 0)
        self.share_route_button.setVisible(len(route) >= 2)
        if len(route) >= 2:
            self._update_route_status()
        else:
            self.route_status.setText("Guzergah icin en az iki gecerli konum gerekli.")
            self.route_status.show()
        self.route_status.adjustSize()
        self.update()

    def fit_route(self):
        fit_points = self.route_geometry or self.route_points
        if len(fit_points) < 2:
            return
        normalized = []
        for latitude, longitude in fit_points:
            latitude = max(-85.05112878, min(85.05112878, latitude))
            x = (longitude + 180.0) / 360.0
            y = (1.0 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2.0
            normalized.append((x, y))
        min_x = min(point[0] for point in normalized)
        max_x = max(point[0] for point in normalized)
        min_y = min(point[1] for point in normalized)
        max_y = max(point[1] for point in normalized)
        span_x = max(max_x - min_x, 1.0 / (2 ** self.TILE_ZOOM))
        span_y = max(max_y - min_y, 1.0 / (2 ** self.TILE_ZOOM))
        usable_width = max(160, self.width() - 140)
        usable_height = max(160, self.height() - 150)
        scale = min(usable_width / (self.TILE_SIZE * span_x),
                    usable_height / (self.TILE_SIZE * span_y))
        zoom_level = math.log2(max(1.0, scale))
        self.zoom = max(0.25, min(128.0, 2 ** (zoom_level - self.TILE_ZOOM)))
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        self.center = (
            math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * center_y)))),
            center_x * 360.0 - 180.0,
        )
        self.update()

    def calculate_tomtom_route(self, api_key, points=None):
        waypoints = list(points if points is not None else self.route_points)
        if len(waypoints) < 2:
            self.route_status.setText("Yol rotasi icin en az iki durak secin.")
            self.route_status.show()
            return False
        if len(waypoints) > 25:
            self.route_status.setText("Tek yol rotasinda en fazla 25 durak kullanilabilir.")
            self.route_status.adjustSize()
            self.route_status.show()
            return False
        api_key = str(api_key or "").strip()
        if not api_key:
            self.route_status.setText("TomTom Routing API anahtari bulunamadi; duz cizgi taslagi gosteriliyor.")
            self.route_status.adjustSize()
            self.route_status.show()
            return False
        self._cancel_route_request()
        self._route_generation += 1
        generation = self._route_generation
        self.route_points = [(float(lat), float(lon)) for lat, lon in waypoints]
        self.route_geometry = []
        self.route_distance_meters = 0
        self.route_duration_seconds = 0
        locations = ":".join("{:.6f},{:.6f}".format(lat, lon) for lat, lon in waypoints)
        url = QUrl("https://api.tomtom.com/maps/orbis/routing/calculateRoute/{}/json".format(
            locations))
        query = QUrlQuery()
        query.addQueryItem("apiVersion", "2")
        query.addQueryItem("key", api_key)
        query.addQueryItem("routeType", "fast")
        query.addQueryItem("traffic", "live")
        query.addQueryItem("travelMode", "car")
        url.setQuery(query)
        request = QNetworkRequest(url)
        request.setRawHeader(b"TomTom-Api-Version", b"2")
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(b"User-Agent", b"AYEC-Pro/2.0")
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        request.setAttribute(QNetworkRequest.Attribute.CacheSaveControlAttribute, False)
        self.route_status.setText("TomTom yol rotasi hesaplaniyor; duz cizgi taslagi gecici olarak gosteriliyor.")
        self.route_status.adjustSize()
        self.route_status.show()
        self._route_reply = self._network.get(request)
        reply = self._route_reply
        reply.finished.connect(lambda token=generation, result=reply: self._route_reply_finished(token, result))
        self.update()
        return True

    def _cancel_route_request(self):
        self._route_generation += 1
        reply = self._route_reply
        self._route_reply = None
        if reply is not None:
            reply.abort()

    def _route_reply_finished(self, generation, reply):
        body = bytes(reply.readAll())
        error = reply.error()
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        reply.deleteLater()
        if generation != self._route_generation or reply is not self._route_reply:
            return
        self._route_reply = None
        try:
            import json
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            payload = {}
        routes = payload.get("routes", []) if isinstance(payload, dict) else []
        if error == reply.NetworkError.NoError and routes:
            route = routes[0]
            geometry = []
            for leg in route.get("legs", []):
                for point in leg.get("points", []):
                    latitude = point.get("latitude")
                    longitude = point.get("longitude")
                    if self.valid_coordinates(latitude, longitude):
                        coordinate = (float(latitude), float(longitude))
                        if not geometry or coordinate != geometry[-1]:
                            geometry.append(coordinate)
            summary = route.get("summary", {})
            if len(geometry) >= 2:
                self.route_geometry = geometry
                self.route_distance_meters = int(summary.get("lengthInMeters") or 0)
                self.route_duration_seconds = int(summary.get("travelTimeInSeconds") or 0)
                self.fit_route()
                self._update_route_status()
                self.routeCalculated.emit(
                    list(self.route_geometry), self.route_distance_meters, self.route_duration_seconds
                )
                self.update()
                return
        self.route_geometry = []
        if status_code in {401, 403}:
            message = "TomTom Routing yetkisi reddedildi (HTTP {}). Domain kisiti ve Routing API urun erisimini kontrol edin.".format(
                status_code or "?"
            )
        else:
            message = "Yol rotasi alinamadi; haritadaki taslak duz cizgi olarak korunuyor."
        self.route_status.setText(message)
        self.route_status.adjustSize()
        self.route_status.show()
        self.update()

    def _update_route_status(self):
        if not self.route_points:
            self.route_status.hide()
            return
        if self.route_geometry and self.route_distance_meters:
            duration_minutes = max(1, round(self.route_duration_seconds / 60))
            text = "TomTom yol rotasi  |  {} durak  |  {:.1f} km  |  {} dk (canli trafik)".format(
                len(self.route_points), self.route_distance_meters / 1000.0, duration_minutes
            )
        else:
            distance = sum(
                self._distance_between(first, second)
                for first, second in zip(self.route_points, self.route_points[1:])
            )
            text = "Taslak rota  |  {} durak  |  {:.1f} km duz cizgi tahmini".format(
                len(self.route_points), distance
            )
        self.route_status.setText(text)
        self.route_status.adjustSize()
        self.route_status.show()

    @staticmethod
    def _distance_between(first, second):
        lat1, lon1 = map(math.radians, first)
        lat2, lon2 = map(math.radians, second)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371.0 * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1.0 - value)))

    def refresh_visible_tiles(self):
        self._force_refresh = True
        self._refresh_requested_tiles.clear()
        self._refresh_requested_tiles.update(self._pending_tiles)
        self._dark_tiles.clear()
        self._tile_retry_after.clear()
        if self.traffic_active:
            self._traffic_generation += 1
            self._cancel_traffic_requests()
            self._traffic_tiles.clear()
            self._traffic_connecting = True
            self.traffic_status.setText("Guncelleniyor...")
        else:
            self._tiles.clear()
            self._set_map_status("Harita yenileniyor...")
        self.refresh_map_button.setEnabled(False)
        self.refresh_map_button.setText("Guncelleniyor...")
        self.update()
        QTimer.singleShot(5000, self._finish_refresh)

    def _finish_refresh(self):
        self._force_refresh = False
        self._refresh_requested_tiles.clear()
        self.refresh_map_button.setEnabled(True)
        self.refresh_map_button.setText("Haritayi Guncelle")
        self.update()

    def _cancel_traffic_requests(self):
        replies = list(self._traffic_replies.values())
        self._traffic_replies.clear()
        self._traffic_pending.clear()
        for reply in replies:
            abort = getattr(reply, "abort", None)
            if callable(abort):
                abort()

    def _cancel_base_requests(self):
        replies = list(self._base_replies.values())
        self._base_replies.clear()
        self._pending_tiles.clear()
        for reply in replies:
            abort = getattr(reply, "abort", None)
            if callable(abort):
                abort()

    def _cancel_copyright_request(self):
        reply = self._copyright_reply
        self._copyright_reply = None
        if reply is not None:
            abort = getattr(reply, "abort", None)
            if callable(abort):
                abort()

    def _request_tomtom_copyrights(self):
        if self._copyright_reply is not None or self._copyrights_requested or not self._traffic_key:
            return
        self._copyrights_requested = True
        request = QNetworkRequest(QUrl("https://api.tomtom.com/maps/orbis/copyrights/caption?apiVersion=2"))
        request.setRawHeader(b"TomTom-Api-Key", self._traffic_key.encode("ascii"))
        request.setRawHeader(b"TomTom-Api-Version", b"2")
        request.setTransferTimeout(12000)
        reply = self._network.get(request)
        self._copyright_reply = reply
        reply.finished.connect(lambda current_reply=reply: self._copyrights_received(current_reply))

    def _copyrights_received(self, reply):
        if self._copyright_reply is reply:
            self._copyright_reply = None
        body = bytes(reply.readAll())
        succeeded = reply.error() == reply.NetworkError.NoError
        reply.deleteLater()
        if not succeeded or not self.traffic_active:
            return
        try:
            import json
            response = json.loads(body.decode("utf-8"))
            caption = response.get("copyrightsCaption", "")
        except (ValueError, TypeError, UnicodeDecodeError, AttributeError):
            return
        if isinstance(caption, str) and caption.strip():
            self._tomtom_copyright_caption = caption.strip()
            self.update()

    def _set_center_from_drag(self, delta_x, delta_y):
        zoom, scale = self._tile_zoom_scale()
        center_x, center_y = self._world_point(*self.center, zoom)
        center_x -= delta_x / scale
        center_y -= delta_y / scale
        world_size = self.TILE_SIZE * (2 ** zoom)
        center_x %= world_size
        center_y = min(world_size, max(0.0, center_y))
        longitude = center_x / world_size * 360 - 180
        latitude = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * center_y / world_size))))
        self.center = (latitude, longitude)

    def _tile_zoom_scale(self):
        effective = self._effective_zoom_level()
        base_zoom = max(3, min(19, int(math.floor(effective))))
        return base_zoom, 2 ** (effective - base_zoom)

    def _effective_zoom_level(self):
        return self.TILE_ZOOM + math.log2(self.zoom)

    def _display_zoom_level(self):
        return max(0.25, self._effective_zoom_level() - 2.5)

    def _world_point(self, latitude, longitude, zoom):
        latitude = max(-85.05112878, min(85.05112878, float(latitude)))
        world_size = self.TILE_SIZE * (2 ** zoom)
        x = (float(longitude) + 180.0) / 360.0 * world_size
        sin_lat = math.sin(math.radians(latitude))
        y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * world_size
        return x, y

    def _screen_point(self, latitude, longitude):
        zoom, scale = self._tile_zoom_scale()
        center_x, center_y = self._world_point(*self.center, zoom)
        point_x, point_y = self._world_point(latitude, longitude, zoom)
        world_size = self.TILE_SIZE * (2 ** zoom)
        delta_x = point_x - center_x
        if delta_x > world_size / 2:
            delta_x -= world_size
        elif delta_x < -world_size / 2:
            delta_x += world_size
        return QPointF(self.width() / 2 + delta_x * scale, self.height() / 2 + (point_y - center_y) * scale)

    def _draw_dark_tile(self, painter, image, target, cache_key):
        if image.isNull():
            return
        dark = image.convertToFormat(QImage.Format.Format_Grayscale8)
        dark = dark.convertToFormat(QImage.Format.Format_Indexed8)
        colors = []
        for luminance in range(256):
            if luminance < 40:
                color = "#8c909f"
            elif luminance < 110:
                color = "#56677f"
            elif luminance < 200:
                color = "#1b283b"
            elif luminance < 236:
                color = "#182236"
            elif luminance < 248:
                color = "#111827"
            elif luminance < 253:
                color = "#202d43"
            else:
                color = "#303b54"
            colors.append(QColor(color).rgba())
        dark.setColorTable(colors)
        dark = dark.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        self._cache_tile(self._dark_tiles, cache_key, dark, self.MAX_DARK_TILES)
        painter.drawImage(target, dark)

    def _draw_tomtom_tactical_tile(self, painter, image, target, cache_key):
        if image.isNull():
            return
        dark = image.convertToFormat(QImage.Format.Format_Grayscale8)
        dark = dark.convertToFormat(QImage.Format.Format_Indexed8)
        colors = []
        for luminance in range(256):
            if luminance < 8:
                color = "#080d18"
            elif luminance < 24:
                color = "#0b111d"
            elif luminance < 50:
                color = "#101827"
            elif luminance < 82:
                color = "#182338"
            elif luminance < 116:
                color = "#27364d"
            elif luminance < 150:
                color = "#586981"
            elif luminance < 184:
                color = "#8997aa"
            elif luminance < 216:
                color = "#b4c0ce"
            else:
                color = "#c8d1dd"
            colors.append(QColor(color).rgba())
        dark.setColorTable(colors)
        dark = dark.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        self._cache_tile(self._dark_tiles, cache_key, dark, self.MAX_DARK_TILES)
        painter.drawImage(target, dark)

    @staticmethod
    def _cache_tile(cache, key, image, limit):
        cache[key] = image
        cache.move_to_end(key)
        while len(cache) > limit:
            cache.popitem(last=False)

    @staticmethod
    def _get_cached_tile(cache, key):
        image = cache.get(key)
        if image is not None:
            cache.move_to_end(key)
        return image

    def _request_tile(self, zoom, x, y, force_osm=False):
        columns = 2 ** zoom
        if y < 0 or y >= columns:
            return
        x %= columns
        key = (zoom, x, y)
        if key in self._pending_tiles or (key in self._tiles and not self._force_refresh):
            return
        if self._force_refresh and key in self._refresh_requested_tiles:
            return
        retry_at = self._get_cached_tile(self._tile_retry_after, key) or 0
        if not self._force_refresh and retry_at > time.monotonic():
            return
        if len(self._pending_tiles) >= self.MAX_PENDING_MAP_TILES:
            return
        if self._force_refresh:
            self._refresh_requested_tiles.add(key)
        use_tomtom = bool(self._traffic_key
                          and not self._tomtom_map_unavailable and not force_osm)
        if use_tomtom:
            url = ("https://api.tomtom.com/maps/orbis/display/raster/tile/{1}?apiVersion=2"
                   "&style={0}&tileSize=256&geopoliticalView=TR").format(
                       self._current_tomtom_style(), "{}/{}/{}".format(zoom, x, y))
            source = "tomtom"
        else:
            url = "https://tile.openstreetmap.org/{}/{}/{}.png".format(zoom, x, y)
            source = "osm"
        request = QNetworkRequest(QUrl(url))
        if source == "tomtom":
            request.setRawHeader(b"TomTom-Api-Key", self._traffic_key.encode("ascii"))
            request.setRawHeader(b"TomTom-Api-Version", b"2")
        else:
            request.setRawHeader(b"User-Agent", b"AYEC-Pro/2.0")
        request.setTransferTimeout(12000)
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.PreferCache)
        self._pending_tiles.add(key)
        reply = self._network.get(request)
        generation = self._base_generation
        self._base_replies[key] = reply
        reply.finished.connect(lambda tile_key=key, tile_reply=reply, tile_source=source,
                               tile_generation=generation:
                               self._tile_received(tile_key, tile_reply, tile_source, tile_generation))

    @staticmethod
    def _current_tomtom_style():
        dark_theme = ThemeManager.is_dark_theme(ThemeManager._current_theme)
        return "street-dark" if dark_theme else "street-light"

    def _sync_tile_theme(self):
        style = self._current_tomtom_style()
        if style == self._active_tile_style:
            return
        self._active_tile_style = style
        self._base_generation += 1
        self._tiles.clear()
        self._tile_sources.clear()
        self._dark_tiles.clear()
        self._pending_tiles.clear()
        self._tile_retry_after.clear()
        self._refresh_requested_tiles.clear()
        self._cancel_base_requests()

    def _request_traffic_tile(self, zoom, x, y):
        if not self._traffic_key or not self.traffic_active:
            return
        key = (zoom, x, y)
        request_id = (self._traffic_generation, key)
        if key in self._traffic_tiles or request_id in self._traffic_pending:
            return
        if len(self._traffic_pending) >= self.MAX_PENDING_TRAFFIC_TILES:
            return
        url = QUrl("https://api.tomtom.com/maps/orbis/traffic/tile/flow/{}/{}/{}.png".format(
            zoom, x, y))
        query = QUrlQuery()
        query.addQueryItem("apiVersion", "1")
        query.addQueryItem("key", self._traffic_key)
        query.addQueryItem("style", "dark")
        query.addQueryItem("tileSize", "256")
        url.setQuery(query)
        request = QNetworkRequest(url)
        request.setRawHeader(b"TomTom-Api-Version", b"1")
        request.setRawHeader(b"Accept", b"image/png, application/json")
        request.setTransferTimeout(12000)
        request.setAttribute(QNetworkRequest.Attribute.CacheSaveControlAttribute, False)
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        self._traffic_pending.add(request_id)
        reply = self._network.get(request)
        self._traffic_replies[request_id] = reply
        reply.finished.connect(lambda tile_key=key, request_token=request_id, tile_reply=reply:
                                self._traffic_tile_received(tile_key, request_token, tile_reply))

    def _traffic_tile_received(self, key, request_id, reply):
        self._traffic_pending.discard(request_id)
        self._traffic_replies.pop(request_id, None)
        image = QImage()
        body = bytes(reply.readAll())
        error = reply.error()
        if error == reply.NetworkError.NoError:
            image.loadFromData(body)
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        reply.deleteLater()
        if request_id[0] != self._traffic_generation:
            return
        if not image.isNull() and self.traffic_active:
            self._cache_tile(self._traffic_tiles, key, image, self.MAX_TRAFFIC_TILES)
            self._traffic_layers_ready()
        elif self.traffic_active and not self._traffic_tile_error_reported:
            self._traffic_tile_error_reported = True
            self._traffic_connecting = False
            self._emit_traffic_api_error(body, "TomTom trafik karolari yuklenemedi", status_code)
        self.update()

    def _tile_received(self, key, reply, source="osm", generation=None):
        self._pending_tiles.discard(key)
        self._base_replies.pop(key, None)
        image = QImage()
        body = bytes(reply.readAll())
        if reply.error() == reply.NetworkError.NoError:
            image.loadFromData(body)
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) if source == "tomtom" else None
        retry_header = b""
        if source == "tomtom" and hasattr(reply, "rawHeader"):
            retry_header = bytes(reply.rawHeader(b"Retry-After") or b"")
        reply.deleteLater()
        if generation is not None and generation != self._base_generation:
            return
        if not image.isNull():
            self._cache_tile(self._tiles, key, image, self.MAX_BASE_TILES)
            self._cache_tile(self._tile_sources, key, source, self.MAX_BASE_TILES)
            self._dark_tiles.pop(key, None)
            self._tile_retry_after.pop(key, None)
            self._set_map_status("")
            if self.traffic_active and self._traffic_key:
                if source == "tomtom":
                    self._request_tomtom_copyrights()
                self._traffic_layers_ready()
        elif source == "tomtom":
            if status_code in {401, 403}:
                self._tomtom_map_unavailable = True
                self._request_tile(*key, force_osm=True)
            else:
                retry_delay = 8.0 if status_code == 429 else 2.0
                try:
                    retry_delay = max(2.0, min(60.0, float(retry_header.decode("ascii").strip())))
                except (ValueError, UnicodeDecodeError):
                    pass
                self._cache_tile(
                    self._tile_retry_after, key, time.monotonic() + retry_delay,
                    self.MAX_BASE_TILES
                )
                QTimer.singleShot(int(retry_delay * 1000), self.update)
        else:
            self._cache_tile(self._tile_retry_after, key, time.monotonic() + 10, self.MAX_BASE_TILES)
            if not self._tiles:
                self._set_map_status("Harita yuklenemedi. Baglantiyi kontrol edip yenileyin.")
        self.update()

    def _paint_tiles(self, painter):
        self._sync_tile_theme()
        zoom, scale = self._tile_zoom_scale()
        center_x, center_y = self._world_point(*self.center, zoom)
        left = self.width() / 2 - center_x * scale
        top = self.height() / 2 - center_y * scale
        tile_display_size = self.TILE_SIZE * scale
        first_x = math.floor(-left / tile_display_size)
        last_x = math.floor((self.width() - left) / tile_display_size)
        first_y = math.floor(-top / tile_display_size)
        last_y = math.floor((self.height() - top) / tile_display_size)
        dark_theme = ThemeManager.is_dark_theme(ThemeManager._current_theme)
        painter.fillRect(self.rect(), QColor(tc("finance_canvas")))
        visible_sources = set()
        for tile_x in range(first_x, last_x + 1):
            for tile_y in range(first_y, last_y + 1):
                wrapped_x = tile_x % (2 ** zoom)
                key = (zoom, wrapped_x, tile_y)
                target = QRectF(left + tile_x * tile_display_size, top + tile_y * tile_display_size,
                                tile_display_size + 1, tile_display_size + 1)
                if key in self._tiles:
                    image = self._get_cached_tile(self._tiles, key)
                    source = self._get_cached_tile(self._tile_sources, key) or "osm"
                    visible_sources.add(source)
                    dark_tile = self._get_cached_tile(self._dark_tiles, key)
                    if not dark_theme:
                        painter.drawImage(target, image)
                    elif source == "tomtom":
                        tomtom_cache_key = ("tomtom",) + key
                        dark_tile = self._get_cached_tile(self._dark_tiles, tomtom_cache_key)
                        if dark_tile is not None:
                            painter.drawImage(target, dark_tile)
                        else:
                            self._draw_tomtom_tactical_tile(
                                painter, image, target, tomtom_cache_key
                            )
                    elif dark_tile is not None:
                        painter.drawImage(target, dark_tile)
                    else:
                        self._draw_dark_tile(painter, image, target, key)
                else:
                    self._request_tile(zoom, wrapped_x, tile_y)
                    painter.fillRect(target, QColor(tc("finance_canvas")))
                if self.traffic_active and self._traffic_key:
                    self._request_traffic_tile(zoom, wrapped_x, tile_y)
                    traffic_tile = self._get_cached_tile(self._traffic_tiles, key)
                    if traffic_tile is not None:
                        painter.drawImage(target, traffic_tile)
        tint = QColor(4, 10, 20, 72) if dark_theme else QColor(255, 255, 255, 22)
        painter.fillRect(self.rect(), tint)
        self._visible_tile_sources = visible_sources
        grid_color = QColor(tc("finance_outline"))
        grid_color.setAlpha(48 if dark_theme else 64)
        grid_pen = QPen(grid_color, 1)
        painter.setPen(grid_pen)
        grid_step = 40
        for x in range(0, self.width(), grid_step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_step):
            painter.drawLine(0, y, self.width(), y)
        if self.traffic_active:
            if visible_sources == {"tomtom"}:
                base_attribution = self._tomtom_copyright_caption or "Map \u00a9 TomTom"
            else:
                base_attribution = self._tomtom_copyright_caption or "\u00a9 OpenStreetMap contributors"
            attribution = "{} | Traffic \u00a9 TomTom".format(base_attribution)
        elif visible_sources == {"tomtom"}:
            attribution = self._tomtom_copyright_caption or "Map \u00a9 TomTom"
        else:
            attribution = "\u00a9 OpenStreetMap contributors"
        self.map_telemetry_source.setText(
            ("TOMTOM DARK" if dark_theme else "TOMTOM") if "tomtom" in visible_sources else
            ("TOMTOM BAGLANIYOR" if self._traffic_key and not self._tomtom_map_unavailable else "YEDEK HARITA")
        )
        attribution_width = min(max(260, painter.fontMetrics().horizontalAdvance(attribution) + 16), max(260, self.width() - 32))
        attribution_box = QRectF(self.width() - attribution_width - 12, self.height() - 28, attribution_width, 20)
        painter.fillRect(attribution_box, QColor(tc("finance_surface")))
        painter.setPen(QColor(tc("finance_text")))
        painter.drawText(attribution_box.adjusted(6, 0, -6, 0),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, attribution)

    def _update_map_telemetry(self):
        latitude, longitude = self.center
        self.map_telemetry_label.setText(
            "MERKEZ: {:.5f}, {:.5f}  |  OL\u00c7EK: {:.1f}x  |  GPS: {}/{}".format(
                latitude, longitude, self._display_zoom_level(),
                len(self.personnel), self._personnel_total_count
            )
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._update_map_telemetry()
        self._paint_tiles(painter)
        self._hits = []
        labels = []
        center_point = self._screen_point(*self.center)
        route_screen_points = [self._screen_point(*coordinates)
                               for coordinates in (self.route_geometry or self.route_points)]
        route_starts_at_center = any(
            math.hypot(point.x() - center_point.x(), point.y() - center_point.y()) < 20
            for point in route_screen_points
        )
        pulse_radius = 8 + self._pulse * 22
        pulse_color = QColor(tc("finance_secondary", default="#10b981"))
        pulse_color.setAlpha(int(130 * (1 - self._pulse)))
        if not route_starts_at_center:
            painter.setPen(QPen(pulse_color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center_point, pulse_radius, pulse_radius)
            painter.setPen(QPen(QColor(tc("finance_secondary")), 2))
            painter.setBrush(QColor(tc("finance_success_bg")))
            painter.drawEllipse(center_point, 9, 9)
            painter.setBrush(QColor(tc("finance_secondary")))
            painter.drawEllipse(center_point, 4, 4)
            center_label = QRectF(center_point.x() + 14, center_point.y() + 8, 142, 22)
            painter.fillRect(center_label, QColor(tc("finance_surface")))
            painter.setPen(QColor(tc("finance_text")))
            painter.drawText(center_label, Qt.AlignmentFlag.AlignCenter, "Varsayilan merkez")

        if len(route_screen_points) > 1:
            route_path = QPainterPath(route_screen_points[0])
            for point in route_screen_points[1:]:
                route_path.lineTo(point)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            halo_color = QColor(tc("finance_secondary"))
            halo_color.setAlpha(76)
            halo = QPen(halo_color, 7, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(halo)
            painter.drawPath(route_path)
            route_pen = QPen(QColor(tc("finance_secondary")), 3, Qt.PenStyle.CustomDashLine,
                             Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            route_pen.setDashPattern([2.5, 2.0])
            painter.setPen(route_pen)
            painter.drawPath(route_path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(tc("finance_secondary")))
            for first, second in zip(route_screen_points, route_screen_points[1:]):
                midpoint = QPointF(
                    (first.x() + second.x()) / 2,
                    (first.y() + second.y()) / 2,
                )
                painter.drawEllipse(midpoint, 3.5, 3.5)
        for index, coordinates in enumerate(self.route_points, 1):
            point = self._screen_point(*coordinates)
            if not self.rect().adjusted(12, 52, -12, -48).contains(point.toPoint()):
                continue
            painter.setPen(QPen(QColor(tc("finance_text")), 2))
            painter.setBrush(QColor(tc("finance_primary")))
            painter.drawEllipse(point, 12, 12)
            painter.setPen(QColor(tc("finance_primary_text")))
            painter.drawText(QRectF(point.x() - 10, point.y() - 10, 20, 20),
                             Qt.AlignmentFlag.AlignCenter, str(index))
        for row in self.personnel:
            point = self._screen_point(row["lat"], row["lng"])
            if not self.rect().adjusted(18, 58, -18, -60).contains(point.toPoint()):
                continue
            painter.setPen(QPen(QColor(tc("finance_secondary")), 2))
            painter.setBrush(QColor(tc("finance_success_bg")))
            painter.drawEllipse(point, 14, 14)
            painter.setBrush(QColor(tc("finance_secondary")))
            painter.drawEllipse(point, 5, 5)
            name = str(row.get("name") or "Personel")
            width = min(220, max(110, painter.fontMetrics().horizontalAdvance(name) + 20))
            label = QRectF(point.x() - width / 2, point.y() - 48, width, 24)
            for _ in range(6):
                if not any(label.intersects(previous_label) for previous_label in labels):
                    break
                label.translate(0, -27)
            labels.append(QRectF(label))
            painter.fillRect(label, QColor(tc("finance_surface")))
            painter.setPen(QColor(tc("finance_text")))
            painter.drawText(label, Qt.AlignmentFlag.AlignCenter, painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, width - 12))
            self._hits.append((QRectF(point.x() - 18, point.y() - 18, 36, 36), row))

        painter.setPen(QColor(tc("finance_text_muted")))
        painter.drawText(QRectF(18, 12, self.width() - 36, 40), Qt.AlignmentFlag.AlignLeft,
                         "SAHA RADARI  |  {} GPS kaydi  |  {}".format(
                             len(self.personnel), "CANLI TRAFIK" if self.traffic_active else "FILO IZLEME"))
        if self.selection_visible:
            point = self._screen_point(*self.selected_coordinates)
            painter.setPen(QPen(QColor(tc("warning")), 2))
            painter.setBrush(QColor(tc("finance_tertiary_bg")))
            painter.drawEllipse(point, 8, 8)
        coordinate_font = QFont("Inter" if _MAP_FONT_ID >= 0 else "Consolas")
        coordinate_font.setFamilies(["Inter", "Consolas", "Arial"] if _MAP_FONT_ID >= 0 else ["Consolas", "Arial"])
        coordinate_font.setPointSize(10)
        coordinate_font.setPixelSize(11)
        painter.setFont(coordinate_font)
        painter.setPen(QColor(tc("finance_text_muted")))
        painter.drawText(QRectF(16, self.height() - 42, self.width() - 32, 30), Qt.AlignmentFlag.AlignLeft,
                         "Merkez: {:.5f}, {:.5f}  |  Olcek: {:.2f}x".format(
                             *self.center, self._display_zoom_level()))
        painter.end()

    def _coordinate_from_position(self, position):
        zoom, scale = self._tile_zoom_scale()
        center_x, center_y = self._world_point(*self.center, zoom)
        world_size = self.TILE_SIZE * (2 ** zoom)
        x = center_x + (position.x() - self.width() / 2) / scale
        y = center_y + (position.y() - self.height() / 2) / scale
        x %= world_size
        x_fraction = x / world_size
        y_fraction = min(1.0, max(0.0, y / world_size))
        longitude = x_fraction * 360.0 - 180.0
        latitude = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y_fraction))))
        return latitude, longitude

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.route_drawing:
                for area, record in reversed(self._hits):
                    if area.contains(event.position()):
                        self.add_route_point(record["lat"], record["lng"])
                        event.accept()
                        return
                self.add_route_point(*self._coordinate_from_position(event.position()))
                event.accept()
                return
            for area, record in reversed(self._hits):
                if area.contains(event.position()):
                    self.selected_coordinates = (float(record["lat"]), float(record["lng"]))
                    self.selection_visible = True
                    self.selectionChanged.emit(*self.selected_coordinates)
                    self.personnelClicked.emit(dict(record))
                    self.update()
                    return
            self._drag_position = event.position()
            latitude, longitude = self._coordinate_from_position(event.position())
            self.selected_coordinates = (latitude, longitude)
            self.selection_visible = True
            self.selectionChanged.emit(*self.selected_coordinates)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            current = event.position()
            delta = current - self._drag_position
            self._set_center_from_drag(delta.x(), delta.y())
            self._drag_position = current
            self.update()
        for area, record in self._hits:
            if area.contains(event.position()):
                self.setToolTip("{}\n{}, {}".format(record.get("name", "Personel"), record["lat"], record["lng"]))
                return
        self.setToolTip("")
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.change_zoom(factor)
        event.accept()
