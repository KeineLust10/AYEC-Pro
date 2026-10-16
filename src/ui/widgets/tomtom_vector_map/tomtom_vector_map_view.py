import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSlot, QTimer, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class _MapBridge(QObject):
    coordinateSelected = pyqtSignal(float, float)
    mapError = pyqtSignal(str)
    mapLoaded = pyqtSignal()

    @pyqtSlot(float, float)
    def mapClicked(self, latitude, longitude):
        self.coordinateSelected.emit(latitude, longitude)

    @pyqtSlot(str)
    def reportMapError(self, message):
        self.mapError.emit(message)

    @pyqtSlot()
    def reportMapLoaded(self):
        self.mapLoaded.emit()


class TomTomVectorMapView(QWidget):
    coordinateSelected = pyqtSignal(float, float)
    mapLoaded = pyqtSignal()
    searchRequested = pyqtSignal(str)
    routeCalculationRequested = pyqtSignal(list)
    routeShareRequested = pyqtSignal(list)
    trafficRequested = pyqtSignal(bool)
    twoDimensionalRequested = pyqtSignal()
    mapError = pyqtSignal(str)

    def __init__(self, api_key, latitude, longitude, parent=None):
        super().__init__(parent)
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        self.api_key = str(api_key or "").strip()
        self.center = (float(latitude), float(longitude))
        self.selected_coordinates = self.center
        self.personnel = []
        self.route_points = []
        self.route_drawing = False
        self._page_ready = False
        self._map_ready = False
        self._pending_js = []
        self._server = None
        self._server_thread = None
        self._traffic_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        toolbar = QFrame(self)
        toolbar.setObjectName("TomTomVectorToolbar")
        toolbar.setStyleSheet(
            "QFrame#TomTomVectorToolbar{background:#0d1727;border:1px solid #243953;"
            "border-radius:8px;}"
            "QLineEdit,QPushButton{min-height:30px;border:1px solid #2b4665;"
            "border-radius:6px;background:#111f33;color:#e2edf8;padding:0 9px;}"
            "QPushButton:hover{border-color:#3b82f6;}"
            "QPushButton:checked{background:#2563eb;color:white;}"
        )
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Adres veya koordinat ara...")
        self.search_input.returnPressed.connect(lambda: self.searchRequested.emit(self.search_input.text()))
        toolbar_layout.addWidget(self.search_input, 1)
        search_button = QPushButton("Ara")
        search_button.clicked.connect(lambda: self.searchRequested.emit(self.search_input.text()))
        toolbar_layout.addWidget(search_button)
        self.route_button = QPushButton("Rota Ciz")
        self.route_button.setCheckable(True)
        self.route_button.toggled.connect(self._set_route_drawing)
        toolbar_layout.addWidget(self.route_button)
        self.finish_route_button = QPushButton("Rotayi Bitir")
        self.finish_route_button.clicked.connect(self.finish_route)
        self.finish_route_button.hide()
        toolbar_layout.addWidget(self.finish_route_button)
        self.clear_route_button = QPushButton("Rotayi Sil")
        self.clear_route_button.clicked.connect(self.clear_route)
        self.clear_route_button.hide()
        toolbar_layout.addWidget(self.clear_route_button)
        self.share_route_button = QPushButton("Rotayi Paylas")
        self.share_route_button.clicked.connect(
            lambda: self.routeShareRequested.emit(list(self.route_points))
        )
        self.share_route_button.hide()
        toolbar_layout.addWidget(self.share_route_button)
        self.traffic_button = QPushButton("Canli Trafik")
        self.traffic_button.setCheckable(True)
        self.traffic_button.toggled.connect(self.trafficRequested.emit)
        toolbar_layout.addWidget(self.traffic_button)
        self.pitch_button = QPushButton("2D / 3D")
        self.pitch_button.setCheckable(True)
        self.pitch_button.toggled.connect(self._set_pitch)
        toolbar_layout.addWidget(self.pitch_button)
        self.refresh_button = QPushButton("Haritayi Yenile")
        self.refresh_button.clicked.connect(self.refresh_map)
        toolbar_layout.addWidget(self.refresh_button)
        self.two_dimensional_button = QPushButton("2D Haritaya Don")
        self.two_dimensional_button.clicked.connect(self.twoDimensionalRequested.emit)
        toolbar_layout.addWidget(self.two_dimensional_button)
        root.addWidget(toolbar)

        self.status_label = QLabel("TomTom WebGL haritasi baslatiliyor...")
        self.status_label.setStyleSheet("color:#91a6c0;padding:2px 4px;")
        root.addWidget(self.status_label)

        self.web_view = QWebEngineView(self)
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled, True
        )
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True
        )
        self.web_view.setMinimumSize(320, 260)
        self.web_view.loadFinished.connect(self._on_page_loaded)
        root.addWidget(self.web_view, 1)

        self._bridge = _MapBridge(self)
        self._bridge.coordinateSelected.connect(self._on_map_clicked)
        self._bridge.mapError.connect(self._show_error)
        self._bridge.mapLoaded.connect(self._on_map_loaded)
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("fieldMapBridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self._start_local_server()

    def _start_local_server(self):
        asset_root = Path(__file__).resolve().parents[4] / "assets" / "tomtom_vector_map"
        if not (asset_root / "index.html").is_file():
            self._show_error("TomTom vector bundle is missing. Build the map assets first.")
            return

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                return

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(asset_root), **kwargs)
        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            self._server.daemon_threads = True
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()
            self.web_view.setUrl(QUrl("http://127.0.0.1:{}/".format(self._server.server_port)))
        except OSError as error:
            self._show_error("Local map server could not start: {}".format(error))

    def _on_page_loaded(self, succeeded):
        if not succeeded:
            self._show_error("TomTom WebGL map could not load its local map assets.")
            return
        self._page_ready = True
        QTimer.singleShot(100, self._initialize_map)

    def _initialize_map(self):
        if not self._page_ready:
            return
        script = (
            "(function(){var s=document.createElement('script');"
            "s.src='qrc:///qtwebchannel/qwebchannel.js';"
            "s.onload=function(){window.initAyecTomTomMap("
            + json.dumps(self.api_key) + "," + str(self.center[0]) + "," + str(self.center[1])
            + ");};s.onerror=function(){window.dispatchEvent(new CustomEvent("
            "'ayec-map-error',{detail:'Qt WebChannel failed to load'}));};"
            "document.head.appendChild(s);})();"
        )
        self.web_view.page().runJavaScript(script)
        QTimer.singleShot(800, self._flush_pending_js)

    def _flush_pending_js(self):
        if not self._page_ready:
            return
        self.web_view.page().runJavaScript(
            "Boolean(window.ayecTomTomMap && window.ayecTomTomMap.flyTo);",
            self._on_map_readiness,
        )

    def _on_map_readiness(self, ready):
        self._map_ready = bool(ready)
        if not ready:
            QTimer.singleShot(500, self._flush_pending_js)
            return
        self.status_label.setText("TomTom vektor haritasi yukleniyor...")
        self._run_js("window.ayecTomTomMap.setPersonnel({});".format(json.dumps(self.personnel)))
        self._run_js("window.ayecTomTomMap.setRoute({});".format(json.dumps(self.route_points)))
        self._run_js("window.ayecTomTomMap.setTraffic({});".format(str(self._traffic_active).lower()))
        for script in self._pending_js:
            self.web_view.page().runJavaScript(script)
        self._pending_js.clear()

    def _on_map_loaded(self):
        self.status_label.setText("TomTom vektor haritasi hazir")
        self.mapLoaded.emit()

    def _run_js(self, script):
        if self._map_ready:
            self.web_view.page().runJavaScript(script)
        else:
            self._pending_js.append(script)

    def _show_error(self, message):
        self.status_label.setText(message)
        self.mapError.emit(message)

    def _on_map_clicked(self, latitude, longitude):
        self.selected_coordinates = (float(latitude), float(longitude))
        self.coordinateSelected.emit(*self.selected_coordinates)
        if self.route_drawing:
            self.route_points.append(self.selected_coordinates)
            self._run_js("window.ayecTomTomMap.setRoute({});".format(json.dumps(self.route_points)))
            self.clear_route_button.show()
            self.finish_route_button.setEnabled(len(self.route_points) >= 2)
            self.status_label.setText("{} rota duragi secildi".format(len(self.route_points)))
        else:
            self._run_js("window.ayecTomTomMap.select({}, {});".format(latitude, longitude))

    def _set_route_drawing(self, active):
        self.route_drawing = bool(active)
        if active:
            self.route_points = []
            self.share_route_button.hide()
            self.finish_route_button.show()
            self.finish_route_button.setEnabled(False)
            self.clear_route_button.show()
            self.status_label.setText("Durak eklemek icin haritaya tiklayin.")
        else:
            self.finish_route_button.hide()

    def finish_route(self):
        if len(self.route_points) < 2:
            self.status_label.setText("Rota icin en az iki durak secin.")
            return
        self.route_button.setChecked(False)
        self.share_route_button.show()
        self.routeCalculationRequested.emit(list(self.route_points))

    def clear_route(self):
        self.route_points = []
        self.route_button.setChecked(False)
        self.finish_route_button.hide()
        self.clear_route_button.hide()
        self.share_route_button.hide()
        self._run_js("window.ayecTomTomMap.clearRoute();")

    def _set_pitch(self, enabled):
        self._run_js("window.ayecTomTomMap.setPitch({});".format(52 if enabled else 0))
        self.pitch_button.setText("3D Acik" if enabled else "2D / 3D")

    def refresh_map(self):
        self._run_js("window.ayecTomTomMap.refresh();")

    def set_traffic_active(self, active):
        self._traffic_active = bool(active)
        self.traffic_button.setChecked(self._traffic_active)
        self._run_js("window.ayecTomTomMap.setTraffic({});".format(str(self._traffic_active).lower()))

    def set_personnel(self, records):
        self.personnel = [dict(row) for row in records]
        self._run_js("window.ayecTomTomMap.setPersonnel({});".format(json.dumps(self.personnel)))

    def set_route(self, points):
        self.route_points = [list(point) for point in points]
        self._run_js("window.ayecTomTomMap.setRoute({});".format(json.dumps(self.route_points)))
        self.clear_route_button.setVisible(len(self.route_points) > 0)
        self.share_route_button.setVisible(len(self.route_points) >= 2)

    def focus_coordinates(self, latitude, longitude):
        self.center = (float(latitude), float(longitude))
        self.selected_coordinates = self.center
        self.coordinateSelected.emit(*self.selected_coordinates)
        self._run_js("window.ayecTomTomMap.flyTo({}, {}, 15);".format(latitude, longitude))
        return True

    def set_selected_coordinates(self, latitude, longitude, zoom=16):
        self.center = (float(latitude), float(longitude))
        self.selected_coordinates = self.center
        self.coordinateSelected.emit(*self.selected_coordinates)
        self._run_js("window.ayecTomTomMap.select({}, {});".format(latitude, longitude))
        self._run_js("window.ayecTomTomMap.flyTo({}, {}, {});".format(latitude, longitude, zoom))
        return True

    def closeEvent(self, event):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        super().closeEvent(event)
