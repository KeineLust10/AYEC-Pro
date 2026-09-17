import json
import threading
import urllib.parse
import urllib.request
import webbrowser

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout

_QWEBENGINE_IMPORT_ERROR = None


def get_webengine_classes():
    global _QWEBENGINE_IMPORT_ERROR
    try:
        from PyQt6.QtWebChannel import QWebChannel as _QWebChannel
        from PyQt6.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
        return _QWebEngineView, _QWebChannel
    except Exception as exc:
        _QWEBENGINE_IMPORT_ERROR = exc
        return None, None


def get_webengine_error_message():
    if _QWEBENGINE_IMPORT_ERROR is None:
        return "Harita modulu su an yuklenemedi."
    text = str(_QWEBENGINE_IMPORT_ERROR)
    lowered = text.lower()
    if "qtwebenginewidgets must be imported" in lowered or "aa_shareopenglcontexts" in lowered:
        return "Harita motoru gec yuklenmis. Uygulamayi tamamen kapatip yeniden acin."
    if "no module named" in lowered or "cannot import name" in lowered:
        return "PyQt6-WebEngine kurulu degil ya da aktif ortamda yuklenemedi."
    return f"Harita modulu yuklenemedi: {text}"

from src.ui.components.message_box import ModernMessage
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.logger import logger


class MapBridge(QObject):
    location_received = pyqtSignal(float, float, str)

    @pyqtSlot(float, float, str)
    def receive_location(self, lat, lng, address):
        self.location_received.emit(lat, lng, address)


class LocationPickerDialog(ModernDialog):
    location_selected = pyqtSignal(float, float, str)
    search_finished = pyqtSignal(list)

    def __init__(self, parent=None, current_lat=None, current_lng=None):
        super().__init__(title="Saha Operasyon & Konum Secimi", parent=parent, width=900, height=700)
        self.QWebEngineView, self.QWebChannel = get_webengine_classes()

        default_lat = 39.6484
        default_lng = 27.8826
        if parent and hasattr(parent, "db"):
            try:
                default_lat = float(parent.db.get_setting("map_default_lat", "39.6484"))
                default_lng = float(parent.db.get_setting("map_default_lng", "27.8826"))
            except Exception as exc:
                logger.debug("LocationPicker default map settings fallback used: %s", exc)

        self.current_lat = current_lat if current_lat is not None else default_lat
        self.current_lng = current_lng if current_lng is not None else default_lng
        self.selected_lat = self.current_lat
        self.selected_lng = self.current_lng
        self.selected_address = ""
        self.search_results_data = []

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(600)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_finished.connect(self.on_search_finished)

        self.setup_content()

    def setup_content(self):
        search_container = QVBoxLayout()
        search_container.setSpacing(8)

        header_row = QHBoxLayout()
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Adres ara (Otomatik tamamlama)...")
        self.inp_search.setStyleSheet(DesignTokens.get_input_qss())
        self.inp_search.textChanged.connect(self.on_search_text_changed)

        self.btn_search = QPushButton("Ara")
        self.btn_search.setStyleSheet(DesignTokens.get_button_qss("primary"))
        self.btn_search.clicked.connect(self.perform_search)

        header_row.addWidget(self.inp_search)
        header_row.addWidget(self.btn_search)
        search_container.addLayout(header_row)

        self.list_results = QListWidget()
        self.list_results.setVisible(False)
        self.list_results.setMaximumHeight(200)
        self.list_results.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #dfe6e9;
                border-radius: 8px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f2f6;
            }
            QListWidget::item:hover {
                background-color: #f1f5f9;
            }
            """
        )
        self.list_results.itemClicked.connect(self.on_result_clicked)
        search_container.addWidget(self.list_results)

        self.add_layout(search_container)

        if self.QWebEngineView and self.QWebChannel:
            self.webview = self.QWebEngineView()
            self.channel = self.QWebChannel()
            self.bridge = MapBridge()
            self.bridge.location_received.connect(self.on_location_received)
            self.channel.registerObject("pythonConnector", self.bridge)
            self.webview.page().setWebChannel(self.channel)
            self.webview.setHtml(self.get_html_content())
            self.add_widget(self.webview)
        else:
            self.webview = None
            fallback = QLabel(
                "Arama sonuclariyla konum secmeye devam edebilirsiniz.\n"
                f"{get_webengine_error_message()}"
            )
            fallback.setWordWrap(True)
            fallback.setMinimumHeight(400)
            fallback.setStyleSheet(
                "background: #f1f2f6; color: #636e72; padding: 20px; border-radius: 8px; font-weight: bold;"
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.add_widget(fallback)

        self.lbl_info = QLabel("Henuz konum secilmedi.")
        self.lbl_info.setStyleSheet("color: #666; font-weight: bold;")
        self.add_widget(self.lbl_info)

        self.btn_whatsapp = self.add_button(
            "WhatsApp Konum Paylas", "success", self.share_whatsapp
        )
        self.footer_layout.addStretch()
        self.btn_cancel = self.add_button("Iptal", "secondary", self.reject)
        self.btn_confirm = self.add_button(
            "Konumu Onayla", "primary", self.confirm_location
        )

    def on_search_text_changed(self, text):
        if len(text) > 2:
            self.search_timer.start()
        else:
            self.list_results.setVisible(False)

    def perform_search(self):
        query = self.inp_search.text().strip()
        if len(query) < 3:
            return
        worker = threading.Thread(target=self._search_thread, args=(query,), daemon=True)
        worker.start()

    def _search_thread(self, query):
        try:
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "format": "json",
                    "addressdetails": 1,
                    "limit": 10,
                    "countrycodes": "tr",
                }
            )
            url = f"https://nominatim.openstreetmap.org/search?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "AYECPro/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.getcode() == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    self.search_finished.emit(data)
                    return
        except Exception as exc:
            logger.error("Location search error: %s", exc)
        self.search_finished.emit([])

    def on_search_finished(self, results):
        self.search_results_data = results
        self.list_results.clear()
        if not results:
            self.list_results.setVisible(False)
            return

        for item in results:
            self.list_results.addItem(item.get("display_name", "Bilinmeyen Adres"))
        self.list_results.setVisible(True)

    def on_result_clicked(self, item):
        row = self.list_results.row(item)
        if row < 0 or row >= len(self.search_results_data):
            return

        data = self.search_results_data[row]
        lat = float(data["lat"])
        lng = float(data["lon"])
        address = data.get("display_name", "")
        safe_address = address.replace("'", "")

        if self.webview:
            self.webview.page().runJavaScript(
                f"updateMarker({lat}, {lng}, '{safe_address}'); map.setView([{lat}, {lng}], 15);"
            )
        else:
            self.on_location_received(lat, lng, address)

        self.list_results.setVisible(False)
        self.inp_search.setText(address)

    def on_location_received(self, lat, lng, address):
        self.selected_lat = lat
        self.selected_lng = lng
        self.selected_address = address
        self.lbl_info.setText(f"Secilen: {address[:50]}... ({lat:.5f}, {lng:.5f})")

    def share_whatsapp(self):
        if not self.selected_lat:
            ModernMessage.show_warning(self, "Lutfen once bir konum secin.", "Uyari")
            return

        maps_url = f"https://www.google.com/maps?q={self.selected_lat},{self.selected_lng}"
        msg = f"*Servis Konumu*\nAdres: {self.selected_address}\nHarita: {maps_url}"
        url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def confirm_location(self):
        self.location_selected.emit(self.selected_lat, self.selected_lng, self.selected_address)
        self.accept()

    def get_html_content(self):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Harita</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                html, body, #map {{ height: 100%; margin: 0; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                let bridge = null;
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    bridge = channel.objects.pythonConnector;
                }});

                const map = L.map('map').setView([{self.current_lat}, {self.current_lng}], 13);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap contributors'
                }}).addTo(map);

                let marker = null;

                function updateMarker(lat, lng, address) {{
                    if (marker) {{
                        map.removeLayer(marker);
                    }}
                    marker = L.marker([lat, lng]).addTo(map).bindPopup(address).openPopup();
                    if (bridge) {{
                        bridge.receive_location(lat, lng, address);
                    }}
                }}

                updateMarker({self.current_lat}, {self.current_lng}, 'Mevcut Konum');

                map.on('click', function(e) {{
                    updateMarker(e.latlng.lat, e.latlng.lng, 'Secilen Konum');
                }});
            </script>
        </body>
        </html>
        """
