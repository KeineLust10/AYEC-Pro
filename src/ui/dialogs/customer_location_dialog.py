from PyQt6.QtWidgets import QLabel

from src.services.tomtom_geocoder import TomTomGeocoder
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.tomtom_vector_map.tomtom_vector_map_view import TomTomVectorMapView
from src.utils.theme_colors import theme_qss


class CustomerLocationDialog(ModernDialog):
    """TomTom map picker used by the customer address form."""

    def __init__(self, api_key, latitude, longitude, address_query="", parent=None):
        super().__init__(
            "M\u00fc\u015fteri Konumu Se\u00e7",
            parent,
            width=1050,
            height=740,
        )
        self.selected_coordinates = (float(latitude), float(longitude))
        self.geocoder = TomTomGeocoder(api_key, self)
        self.geocoder.resolved.connect(self._on_geocode_result)

        self.location_label = QLabel(self._coordinate_text())
        self.location_label.setStyleSheet(
            theme_qss("color: @text_muted; padding: 4px 2px; font-weight: 600;")
        )
        self.add_widget(self.location_label)

        self.map_view = TomTomVectorMapView(
            api_key,
            self.selected_coordinates[0],
            self.selected_coordinates[1],
            self,
        )
        for name in (
            "route_button",
            "finish_route_button",
            "clear_route_button",
            "share_route_button",
            "traffic_button",
            "pitch_button",
            "two_dimensional_button",
        ):
            getattr(self.map_view, name).hide()
        self.map_view.set_selected_coordinates(*self.selected_coordinates)
        self.map_view.coordinateSelected.connect(self._on_coordinate_selected)
        self.map_view.searchRequested.connect(self._search_address)
        self.map_view.mapError.connect(self._on_map_error)
        self.add_widget(self.map_view)

        self.add_button("\u0130ptal", variant="secondary", callback=self.reject)
        self.add_button(
            "Konumu Kullan",
            variant="primary",
            callback=self.accept,
        )
        if address_query.strip():
            self.map_view.search_input.setText(address_query.strip())
            self.geocoder.geocode(address_query, "picker-search")

    def _coordinate_text(self):
        lat, lon = self.selected_coordinates
        return "Se\u00e7ili konum: {:.6f}, {:.6f}".format(lat, lon)

    def _on_coordinate_selected(self, latitude, longitude):
        self.selected_coordinates = (float(latitude), float(longitude))
        self.location_label.setText(self._coordinate_text())

    def _search_address(self, query):
        if str(query or "").strip():
            self.map_view.status_label.setText("Adres TomTom'da aran\u0131yor...")
            self.geocoder.geocode(query, "picker-search")

    def _on_geocode_result(self, request_id, result, error):
        if request_id != "picker-search":
            return
        if error or not result:
            self.map_view.status_label.setText(
                "Adres bulunamad\u0131: {}".format(error or "Sonu\u00e7 yok")
            )
            return
        position = result.get("position") or {}
        latitude = position.get("lat")
        longitude = position.get("lon")
        if latitude is None or longitude is None:
            self.map_view.status_label.setText("TomTom koordinat d\u00f6nd\u00fcrmedi.")
            return
        self.map_view.set_selected_coordinates(latitude, longitude)
        self._on_coordinate_selected(latitude, longitude)
        self.map_view.status_label.setText("Adres bulundu; haritadan noktay\u0131 hassasla\u015ft\u0131rabilirsiniz.")

    def _on_map_error(self, message):
        self.location_label.setText("Harita durumu: {}".format(message))

    def closeEvent(self, event):
        self.map_view.close()
        super().closeEvent(event)
