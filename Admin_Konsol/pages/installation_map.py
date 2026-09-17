"""Installation map for the AYEC Pro platform operator."""
import html
import json

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    QComboBox, QLineEdit, QFrame,
)

import api_client
from product_catalog import product_code

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, product_code=""):
        super().__init__()
        self.product_code = product_code

    def run(self):
        try:
            self.done.emit(api_client.companies(product_code=self.product_code))
        except Exception as exc:
            self.error.emit(str(exc))


class _RefreshLocations(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.refresh_company_locations())
        except Exception as exc:
            self.error.emit(str(exc))


class _SaveLocation(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, payload: dict):
        super().__init__()
        self._tenant_id = tenant_id
        self._payload = payload

    def run(self):
        try:
            self.done.emit(api_client.update_company(self._tenant_id, self._payload))
        except Exception as exc:
            self.error.emit(str(exc))


class InstallationMapPage(QWidget):
    def __init__(self):
        super().__init__()
        self._thread = None
        self._build_ui()
        self.reload()

    def set_product_filter(self, product_name: str):
        self._product_filter = product_code(product_name)
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title_row = QHBoxLayout()
        title = QLabel("Kurulum Haritasi")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self._refresh_button = QPushButton("Konumlari Yenile")
        self._refresh_button.setObjectName("primaryBtn")
        self._refresh_button.clicked.connect(self.refresh_locations)
        title_row.addWidget(self._refresh_button)
        self._reload_button = QPushButton("Verileri Yenile")
        self._reload_button.setObjectName("secondaryBtn")
        self._reload_button.clicked.connect(self.reload)
        title_row.addWidget(self._reload_button)
        layout.addLayout(title_row)

        self._summary = QLabel("Kurulu firmalar yukleniyor...")
        self._summary.setObjectName("metricSub")
        layout.addWidget(self._summary)

        self._location_panel = QFrame()
        self._location_panel.setObjectName("card")
        location_row = QHBoxLayout(self._location_panel)
        location_row.setContentsMargins(14, 10, 14, 10)
        location_row.setSpacing(8)
        location_row.addWidget(QLabel("Konum bekleyen firma:"))
        self._company_picker = QComboBox()
        self._company_picker.setMinimumWidth(220)
        self._company_picker.currentIndexChanged.connect(self._select_company)
        location_row.addWidget(self._company_picker, 1)
        self._address_input = QLineEdit()
        self._address_input.setPlaceholderText("Kurulum adresi")
        self._address_input.setMinimumWidth(260)
        location_row.addWidget(self._address_input, 2)
        self._latitude_input = QLineEdit()
        self._latitude_input.setPlaceholderText("Enlem, ornek: 39.6484")
        self._latitude_input.setMaximumWidth(160)
        location_row.addWidget(self._latitude_input)
        self._longitude_input = QLineEdit()
        self._longitude_input.setPlaceholderText("Boylam, ornek: 27.8826")
        self._longitude_input.setMaximumWidth(160)
        location_row.addWidget(self._longitude_input)
        self._save_location_button = QPushButton("Konumu Kaydet")
        self._save_location_button.setObjectName("primaryBtn")
        self._save_location_button.clicked.connect(self.save_location)
        location_row.addWidget(self._save_location_button)
        layout.addWidget(self._location_panel)

        if QWebEngineView:
            self._map = QWebEngineView()
            layout.addWidget(self._map, 1)
        else:
            self._map = QTextBrowser()
            self._map.setOpenExternalLinks(True)
            layout.addWidget(self._map, 1)

    def reload(self):
        self._reload_button.setEnabled(False)
        thread = _FetchCompanies(getattr(self, "_product_filter", ""))
        thread.done.connect(self._render_companies)
        thread.error.connect(self._load_failed)
        thread.finished.connect(lambda: self._reload_button.setEnabled(True))
        thread.start()
        self._thread = thread

    def refresh_locations(self):
        self._refresh_button.setEnabled(False)
        self._summary.setText("Eksik konumlar adreslerinden kontrol ediliyor...")
        thread = _RefreshLocations()
        thread.done.connect(self._locations_refreshed)
        thread.error.connect(self._load_failed)
        thread.finished.connect(lambda: self._refresh_button.setEnabled(True))
        thread.start()
        self._thread = thread

    def _locations_refreshed(self, result: dict):
        updated = int(result.get("updated") or 0)
        skipped = int(result.get("skipped") or 0)
        self._summary.setText(f"{updated} firma konumlandi, {skipped} firma icin konum bulunamadi.")
        self.reload()

    def _select_company(self):
        company = self._company_picker.currentData()
        if not isinstance(company, dict):
            self._address_input.clear()
            self._latitude_input.clear()
            self._longitude_input.clear()
            return
        self._address_input.setText(str(company.get("company_address") or ""))
        latitude = company.get("installation_lat")
        longitude = company.get("installation_lng")
        self._latitude_input.setText("" if latitude is None else str(latitude))
        self._longitude_input.setText("" if longitude is None else str(longitude))

    def save_location(self):
        company = self._company_picker.currentData()
        if not isinstance(company, dict):
            self._summary.setText("Konum girilecek bir firma secin.")
            return
        address = self._address_input.text().strip()
        latitude_text = self._latitude_input.text().strip().replace(",", ".")
        longitude_text = self._longitude_input.text().strip().replace(",", ".")
        payload = {"company_address": address}
        if bool(latitude_text) != bool(longitude_text):
            self._summary.setText("Enlem ve boylam birlikte girilmelidir.")
            return
        if latitude_text:
            try:
                latitude = float(latitude_text)
                longitude = float(longitude_text)
            except ValueError:
                self._summary.setText("Enlem ve boylam sayisal olmalidir.")
                return
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                self._summary.setText("Enlem veya boylam araligi gecersiz.")
                return
            payload["installation_lat"] = latitude
            payload["installation_lng"] = longitude
        elif not address:
            self._summary.setText("Adres veya enlem-boylam bilgisi girin.")
            return
        self._save_location_button.setEnabled(False)
        self._summary.setText("Firma konumu kaydediliyor...")
        thread = _SaveLocation(str(company.get("id") or ""), payload)
        thread.done.connect(self._location_saved)
        thread.error.connect(self._load_failed)
        thread.finished.connect(lambda: self._save_location_button.setEnabled(True))
        thread.start()
        self._thread = thread

    def _location_saved(self, _result: dict):
        self._summary.setText("Firma konumu kaydedildi. Harita yenileniyor...")
        self.reload()

    def _load_failed(self, error: str):
        self._summary.setText(f"Harita verisi alinamadi: {error}")

    def _render_companies(self, companies: list):
        located = [
            item for item in companies
            if item.get("installation_lat") is not None and item.get("installation_lng") is not None
        ]
        missing = len(companies) - len(located)
        self._summary.setText(
            f"{len(companies)} firma kayitli. {len(located)} konum haritada, {missing} konum bekliyor."
        )
        self._company_picker.blockSignals(True)
        self._company_picker.clear()
        pending = [item for item in companies if item not in located]
        for company in pending:
            label = str(company.get("company_name") or "Adsiz firma")
            self._company_picker.addItem(label, company)
        self._location_panel.setVisible(bool(pending))
        self._company_picker.blockSignals(False)
        self._select_company()
        if QWebEngineView:
            self._map.setHtml(self._map_html(located))
            return
        lines = ["<h2>Kurulum Haritasi</h2>"]
        for company in companies:
            name = html.escape(str(company.get("company_name") or "-"))
            address = html.escape(str(company.get("company_address") or "Adres kayitli degil"))
            lines.append(f"<p><b>{name}</b><br>{address}</p>")
        self._map.setHtml("".join(lines))

    @staticmethod
    def _map_html(companies: list) -> str:
        payload = json.dumps(companies, ensure_ascii=True).replace("</", "<\\/")
        return f"""<!doctype html>
<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\">
<style>html,body,#map{{height:100%;margin:0;background:#0f1117}} .leaflet-popup-content{{font:13px Segoe UI,Arial;color:#172033}} .company{{font-weight:700;font-size:15px}}</style>
</head><body><div id=\"map\"></div><script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
<script>
const companies={payload};
const map=L.map('map').setView([39.0,35.0],6);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'&copy; OpenStreetMap'}}).addTo(map);
function esc(v){{const n=document.createElement('span');n.textContent=String(v||'-');return n.innerHTML;}}
const bounds=[];
companies.forEach(c=>{{const p=[Number(c.installation_lat),Number(c.installation_lng)];if(!Number.isFinite(p[0])||!Number.isFinite(p[1]))return;
const details='<div class=\"company\">'+esc(c.company_name)+'</div><div><b>Yetkili:</b> '+esc(c.contact_name)+'</div><div><b>Telefon:</b> '+esc(c.phone)+'</div><div><b>E-posta:</b> '+esc(c.email)+'</div><div><b>Adres:</b> '+esc(c.company_address)+'</div><div><b>Lisans:</b> '+esc(c.license_type)+'</div>';
L.marker(p).addTo(map).bindPopup(details);bounds.push(p);}});
if(bounds.length===1)map.setView(bounds[0],13);else if(bounds.length>1)map.fitBounds(bounds,{{padding:[32,32]}});
</script></body></html>"""
