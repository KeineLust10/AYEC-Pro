import json

from PyQt6.QtCore import QObject, QUrl, QUrlQuery, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class TomTomGeocoder(QObject):
    """Asynchronous TomTom geocoding client for customer address workflows."""

    resolved = pyqtSignal(str, object, str)

    def __init__(self, api_key, parent=None):
        super().__init__(parent)
        self.api_key = str(api_key or "").strip()
        self.network = QNetworkAccessManager(self)

    def geocode(self, address, request_id=""):
        query = str(address or "").strip()
        if not query:
            self.resolved.emit(str(request_id), None, "Adres bos.")
            return
        encoded = bytes(QUrl.toPercentEncoding(query)).decode("ascii")
        self._request("/geocode/{}.json".format(encoded), request_id, geocode=True)

    def reverse_geocode(self, latitude, longitude, request_id=""):
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            self.resolved.emit(str(request_id), None, "Koordinat gecersiz.")
            return
        self._request(
            "/reverseGeocode/{:.7f},{:.7f}.json".format(lat, lon),
            request_id,
            geocode=False,
        )

    def _request(self, path, request_id, geocode):
        if not self.api_key:
            self.resolved.emit(str(request_id), None, "TomTom API anahtari bulunamadi.")
            return
        url = QUrl("https://api.tomtom.com/search/2" + path)
        params = QUrlQuery()
        params.addQueryItem("key", self.api_key)
        params.addQueryItem("language", "tr-TR")
        if geocode:
            params.addQueryItem("countrySet", "TR")
            params.addQueryItem("limit", "1")
        else:
            params.addQueryItem("view", "TR")
        url.setQuery(params)
        request = QNetworkRequest(url)
        request.setTransferTimeout(12000)
        reply = self.network.get(request)
        reply.setProperty("tomtomRequestId", str(request_id))
        reply.finished.connect(lambda current=reply: self._finish(current))

    def _finish(self, reply):
        request_id = str(reply.property("tomtomRequestId") or "")
        error = ""
        result = None
        try:
            response_body = bytes(reply.readAll())
            if reply.error() != QNetworkReply.NetworkError.NoError:
                error = reply.errorString()
                try:
                    payload = json.loads(response_body.decode("utf-8"))
                    error = str(payload.get("error") or error)
                except (ValueError, TypeError, AttributeError):
                    pass
            else:
                payload = json.loads(response_body.decode("utf-8"))
                results = payload.get("results") or payload.get("addresses") or []
                if results:
                    result = results[0]
                else:
                    error = "Bu adres icin konum bulunamadi."
        except (ValueError, TypeError, AttributeError) as exc:
            error = str(exc)
        finally:
            reply.deleteLater()
        self.resolved.emit(request_id, result, error)
