from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QDialog, QFormLayout, QLineEdit, QDateTimeEdit, QComboBox, QFrame, QSplitter, QListWidget, QScrollArea,
                             QGraphicsDropShadowEffect, QApplication)
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from src.utils.theme_colors import tc
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QFont, QColor, QIcon, QAction
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None

import urllib.request
import urllib.parse
import threading
from datetime import datetime

from src.ui.pages.field_service_components import ManualLocationDialog, PersonnelCard, ModernConfirmDialog

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

        # Autocomplete Timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(800) # Increased debounce
        self.search_timer.timeout.connect(self.perform_search)
        self.search_results_data = []
        self._action_buttons = []

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
        if self.QWebEngineView:
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
        if len(text) > 2:
            self.search_timer.start()
        else:
            if hasattr(self, 'list_results'):
                self.list_results.setVisible(False)

    def perform_search(self):
        query = self.address_input.text().strip()
        if len(query) < 3: return
        # Auto search -> is_manual = False
        t = threading.Thread(target=self._search_thread, args=(query, 10, False)) 
        t.daemon = True
        t.start()

    def search_address(self):
        # Traditional "Button Click" search -> SYNC
        query = self.address_input.text().strip()
        if not query: return
        
        # DEBUG: Force visual confirmation
        logger.debug(f"Field service search clicked: {query}")
        self.notify("Arama yapılıyor (Lütfen bekleyin)...", "info")
        QApplication.processEvents() 

        # Check for shared location links
        import re
        coords = re.findall(r'([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)', query)
        if coords:
            lat, lng = coords[0]
            if QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}, 16); addMarker({lat}, {lng}, 'Paylaşılan Konum', 'Link üzerinden aktarıldı');")
            self.notify("Konum bulundu!", "success")
            return

        # SYNC SEARCH (Main Thread)
        results = self._get_search_results(query, 1)
        self.on_search_finished(results, True)

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
        Pure data fetching logic (Nominatim + Photon).
        Returns list of dicts. safe to call from any thread.
        """
        results = []
        import ssl
        import json
        
        # SSL Context for all requests
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # --- ATTEMPT 1: NOMINATIM ---
        try:
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
                p_url = f"https://photon.komoot.io/api/{p_params}"
                
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
        
        return results

    def on_search_finished(self, results, is_manual):
        logger.debug(f"Field service search finished. manual={is_manual} results={len(results)}")
        self.search_results_data = results
        
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
            
            if QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}, 15); addMarker({lat}, {lng}, 'Seçilen', '{name}');")
            
            if hasattr(self, 'list_results'):
                self.list_results.setVisible(False)
            self.address_input.setText(data.get('display_name', ''))

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Main Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {tc('border')}; }}")

        # --- LEFT SIDEBAR (CONTROLS) ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(350)
        self.sidebar.setStyleSheet(f"background-color: {tc('surface')}; border-right: 1px solid {tc('border')};")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(20, 20, 20, 20)
        self.sidebar_layout.setSpacing(15)

        # Title Section
        header = QLabel("Saha Operasyon Merkezi")
        header.setFont(QFont("Outfit", 18, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {tc('text')};")
        self.sidebar_layout.addWidget(header)

        sub_header = QLabel("Canlı Takip ve Görev Yönetimi")
        sub_header.setFont(QFont("Outfit", 10))
        sub_header.setStyleSheet(f"color: {tc('text_muted')}; margin-bottom: 10px;")
        self.sidebar_layout.addWidget(sub_header)

        # Search Box Section
        search_card = QFrame()
        search_card.setStyleSheet(f"background-color: {tc('window')}; border-radius: 12px; border: 1px solid {tc('border')};")
        search_layout = QVBoxLayout(search_card)
        
        search_label = QLabel("Adres ile Konum Bul")
        search_label.setFont(QFont("Outfit", 9, QFont.Weight.Bold))
        search_layout.addWidget(search_label)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Örn: Gönen, Balıkesir (Otomatik)...")
        self.address_input.setFixedHeight(40)
        self.address_input.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {tc('border')};
                border-radius: 8px;
                padding: 0 10px;
                background-color: {tc('surface')};
                color: {tc('text')};
            }}
            QLineEdit:focus {{ border-color: {tc('accent')}; }}
        """)
        # Connect text changed for autocomplete
        self.address_input.textChanged.connect(self.on_search_text_changed)
        self.address_input.returnPressed.connect(self.search_address) # Enter still forces immediate search
        search_layout.addWidget(self.address_input)
        
        # Results List (Hidden by default) for Autocomplete
        self.list_results = QListWidget()
        self.list_results.setVisible(False)
        self.list_results.setMaximumHeight(200)
        self.list_results.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {tc('border')};
                border-radius: 4px;
                background-color: {tc('surface')};
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {tc('border')};
                color: {tc('text')};
            }}
            QListWidget::item:hover {{
                background-color: {tc('surface_alt')};
            }}
        """)
        self.list_results.itemClicked.connect(self.on_result_clicked)
        search_layout.addWidget(self.list_results)

        btn_search = QPushButton("🗺️ Haritada Ara")
        btn_search.setFixedHeight(40)
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_search.clicked.connect(self.search_address) # Manual trigger
        search_layout.addWidget(btn_search)

        self.sidebar_layout.addWidget(search_card)

        # Actions Section
        actions_header = QLabel("Hızlı İşlemler")
        actions_header.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        actions_header.setStyleSheet(f"color: {tc('text_muted')}; margin-top: 10px;")
        self.sidebar_layout.addWidget(actions_header)

        btn_manual = self.create_action_button("📍 Manuel Koordinat Gir", self.manual_input)
        self.sidebar_layout.addWidget(btn_manual)

        btn_home = self.create_action_button("🏠 Eve Dön (Merkez)", self.reset_to_default)
        self.sidebar_layout.addWidget(btn_home)

        btn_whatsapp = self.create_action_button("📱 WhatsApp Konumu Yapıştır", self.paste_whatsapp_link)
        btn_whatsapp.setStyleSheet(f"""
            QPushButton {{
                background-color: {tc('surface')};
                color: {tc('text')};
                border: 1px solid #25d366;
                border-radius: 10px;
                text-align: left;
                padding-left: 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {tc('surface_alt')};
                border-color: #128c7e;
            }}
        """)
        self.sidebar_layout.addWidget(btn_whatsapp)

        btn_share = self.create_action_button("🔗 Konum Bağlantısını Paylaş", self.share_location)
        self.sidebar_layout.addWidget(btn_share)

        btn_assign = self.create_action_button("👤 Seçili Konumu Personele Ata", self.assign_location_to_personnel)
        btn_assign.setStyleSheet(f"""
            QPushButton {{
                background-color: {tc('surface')};
                color: {tc('accent')};
                border: 1px solid {tc('accent')};
                border-radius: 10px;
                text-align: left;
                padding-left: 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {tc('surface_alt')};
                border-color: {tc('accent_hover')};
            }}
        """)
        self.sidebar_layout.addWidget(btn_assign)

        # Personnel Status Section (Dynamic)
        status_header = QLabel("Personel Durumu")
        status_header.setFont(QFont("Outfit", 10, QFont.Weight.Bold))
        status_header.setStyleSheet(f"color: {tc('text_muted')}; margin-top: 15px;")
        self.sidebar_layout.addWidget(status_header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        
        self.sidebar_layout.addWidget(self.scroll_area)

        # Refresh Footer
        btn_refresh = QPushButton("Yenile")
        btn_refresh.setStyleSheet(f"background: {tc('window')}; color: {tc('text')}; border: 1px solid {tc('border')}; border-radius: 6px; padding: 5px;")
        btn_refresh.clicked.connect(self.refresh_data)
        self.sidebar_layout.addWidget(btn_refresh)

        # --- RIGHT MAP AREA ---
        if QWebEngineView:
            self.map_view = QWebEngineView()
            self.map_view.setStyleSheet(f"background-color: {tc('window')};")
        else:
            self.map_view = QLabel("Harita Modülü Yüklü Değil (PyQtWebEngine eksik)")
            self.map_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.map_view.setStyleSheet(f"background-color: {tc('window')}; color: {tc('text_muted')}; font-size: 16px;")
        
        # Add to Splitter
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.map_view)
        self.splitter.setStretchFactor(1, 1) # Map takes more space

        self.main_layout.addWidget(self.splitter)

        # Initial Load (harita yükle; veri ilk gösterimde showEvent/ModernDesktopApp tarafından yüklenir)
        self.load_map()

    def create_action_button(self, text, callback):
        btn = QPushButton(text)
        btn.setFixedHeight(45)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tc('surface')};
                color: {tc('text')};
                border: 1px solid {tc('border')};
                border-radius: 10px;
                text-align: left;
                padding-left: 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {tc('surface_alt')};
                border-color: {tc('accent')};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def load_map(self):
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
        if not QWebEngineView: return
        
        dialog = ManualLocationDialog(self.window()) # Attach to main window for better centering
        if dialog.exec() == QDialog.DialogCode.Accepted:
            coords = dialog.get_coordinates()
            if coords:
                lat, lng = coords
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}); addMarker({lat}, {lng}, 'Manuel Konum', '{lat}, {lng}', 'user');")
                self.notify(f"Konuma gidiliyor: {lat}, {lng}", "success")
            else:
                 self.notify("Geçersiz koordinat formatı.", "error")

    def reset_to_default(self):
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
        match = re.search(r'(:q=|@|:|^|\s)([-+]?\d+\.\d+)[,\s]+([-+]?\d+\.\d+)', text)
        
        if match:
            try:
                lat = float(match.group(2))
                lng = float(match.group(3))
            except ValueError:
                pass

        if lat is not None and lng is not None:
             if QWebEngineView:
                self.map_view.page().runJavaScript(f"flyTo({lat}, {lng}); addMarker({lat}, {lng}, 'WhatsApp Konumu', 'Panodan yapıştırıldı', 'user');")
                self.notify(f"Konum bulundu: {lat}, {lng}", "success")
        else:
            # Fallback to search query
            self.address_input.setText(text)
            self.search_address()
            self.notify("Metin arama kutusuna yapıştırıldı.", "info")

    def share_location(self):
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
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox, QLabel, QMessageBox
        from PyQt6.QtCore import Qt
        from datetime import datetime
        if hasattr(self.db, 'get_field_technicians'):
            techs = self.db.get_field_technicians()
        else:
            techs = []
        if not techs:
            self.notify("Sistemde saha personeli bulunamadı.", "warning")
            return
        dialog = QDialog(self.window())
        dialog.setWindowTitle("Konumu Personele Ata")
        dialog.setFixedSize(400, 500)
        layout = QVBoxLayout(dialog)
        lbl_info = QLabel(f"Seçilen Konum: {lat:.5f}, {lng:.5f}\n\nBu konumu hangi personele atamak istiyorsunuz?")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        list_widget = QListWidget()
        for t in techs:
            item = QListWidgetItem(f"{t['name']} ({t.get('job', 'Personel')})")
            item.setData(Qt.UserRole, t['id'])
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = list_widget.selectedItems()
            if not selected_items: return
            p_id = selected_items[0].data(Qt.UserRole)
            p_name = selected_items[0].text().split('(')[0].strip()
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.cursor.execute("""
                    UPDATE personnel 
                    SET lat=?, lng=?, status='Görevde', last_seen=?
                    WHERE id=?
                """, (lat, lng, now, p_id))
                self.db.conn.commit()
                self.notify(f"{p_name} konumu güncellendi.", "success")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self.refresh_data)
            except Exception as e:
                logger.error(f"Field service update error: {e}")
                self.notify("Veritabanı güncelleme hatası!", "error")

    def refresh_data(self):
        try:
            logger.info("Field service refresh started")

            # Clear existing widgets but KEEP the stretch at the end
            # More standard way:
            while self.scroll_layout.count() > 1:
                item = self.scroll_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if hasattr(self.db, 'get_field_technicians'):
                techs = self.db.get_field_technicians()
            else:
                techs = []
            
            logger.info(f"Field service technicians fetched: {len(techs)}")

            if QWebEngineView:
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

                    try:
                        raw_lat = t.get('lat')
                        raw_lng = t.get('lng')
                        if raw_lat is None or raw_lng is None:
                            logger.debug("Field service skipping %s: no coordinates", name)
                            no_coord_names.append(name)
                            continue
                        lat = float(raw_lat)
                        lng = float(raw_lng)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Field service skipping {name}: coord error {e}")
                        no_coord_names.append(name)
                        continue
                    logger.debug("Field service adding marker for %s at %s, %s", name, lat, lng)

                    card = PersonnelCard(t, self.focus_personnel, self.finish_personnel_duty)
                    # Insert before the stretch (which is now at the last position)
                    self.scroll_layout.insertWidget(self.scroll_layout.count()-1, card)
                    
                    if QWebEngineView:
                        try:
                            # Use repr() to escape special chars in name/job
                            js_code = f"addMarker({lat}, {lng}, {repr(name)}, {repr(job)}, 'personnel');"
                            self.map_view.page().runJavaScript(js_code)
                        except Exception as e:
                            logger.error(f"Field service map JS error: {e}")

                # Koordinatsız personel için uyarı banneri
                if no_coord_names:
                    warn_lbl = QLabel(
                        f"⚠️  {len(no_coord_names)} personelin GPS koordinatı tanımlı değil ve haritada gösterilemiyor: "
                        f"{', '.join(no_coord_names)}. "
                        f"Personel Yönetimi > personel kaydı düzenleyerek konum ekleyebilirsiniz."
                    )
                    warn_lbl.setWordWrap(True)
                    warn_lbl.setStyleSheet(
                        "background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; "
                        "border-radius: 6px; padding: 8px 12px; font-size: 12px;"
                    )
                    self.scroll_layout.insertWidget(0, warn_lbl)

        except Exception as e:
            logger.error(f"Field service refresh error: {e}")
            self.notify(f"Veri yenileme hatası: {e}", "error")

    def focus_personnel(self, t_data):
        try:
            lat = float(t_data.get('lat'))
            lng = float(t_data.get('lng'))
            name = t_data.get('name', 'Personel')
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
        # Load map with slight delay to ensure container is ready
        # Using a flag to prevent reloading if already loaded could be good, 
        # but setup_ui calls load_map initially.
        # We will refresh data here. 
        from PyQt6.QtCore import QTimer
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
