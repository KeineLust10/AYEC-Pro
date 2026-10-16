import os
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer, QUrlQuery
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QListWidget, QDialog, QPushButton, QLabel, QWidget, QLineEdit

from src.ui.widgets.field_radar_canvas import FieldRadarCanvas
from src.ui.pages.field_service_page import FieldServicePage
from src.ui.pages.field_service_components import PersonnelCard
from src.ui.mixins._main_window_nav_mixin import MainWindowNavMixin
from src.utils.page_ids import PageIds
from src.utils.theme_manager import ThemeManager
from src.ui.widgets.modern_dialog import ModernDialog


def _disable_tile_fetch(radar):
    radar._request_tile = lambda *args, **kwargs: None
    radar._request_traffic_tile = lambda *args, **kwargs: None


def test_native_radar_rejects_bad_coordinates_preserves_identity_and_selects_marker():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(39.6, 27.8)
    _disable_tile_fetch(radar)
    assert not radar.map_status.isHidden()
    assert radar.font().family() in {"Inter", "Segoe UI", "Arial"}
    assert radar.font().pixelSize() == 12
    radar._update_map_telemetry()
    assert "OL\u00c7EK: 14.5x" in radar.map_telemetry_label.text()
    assert radar._tile_zoom_scale()[0] == 17
    radar.resize(700, 600)
    source = [{"id": 7, "name": "Actual technician", "lat": 39.6, "lng": 27.8},
              {"id": 8, "lat": None, "lng": 27.8},
              {"id": 9, "lat": 91, "lng": 27.8},
              {"id": 10, "lat": float("nan"), "lng": 27.8}]
    radar.set_personnel(source)
    assert [row["id"] for row in radar.personnel] == [7]
    assert not radar.grab().isNull()
    assert "@" not in radar.zoom_in.styleSheet()
    assert radar.zoom_in.styleSheet() == radar.zoom_out.styleSheet()
    assert "@" not in radar.map_search_input.styleSheet()
    assert "@" not in radar.map_search_button.styleSheet()
    assert "@" not in radar.refresh_map_button.styleSheet()
    clicked = []
    radar.personnelClicked.connect(clicked.append)
    QTest.mouseClick(radar, Qt.MouseButton.LeftButton, pos=QPoint(350, 300))
    assert clicked[0]["id"] == 7
    assert radar.selected_coordinates == (39.6, 27.8)
    assert radar.focus_coordinates(40, 28)
    assert radar.center == (40.0, 28.0)
    assert not radar.focus_coordinates(500, 28)
    assert radar.center == (40.0, 28.0)
    radar.change_zoom(1000)
    assert radar.zoom == 128
    assert radar._tile_zoom_scale() == (19, 1.0)
    radar.change_zoom(0.00001)
    assert radar.zoom == 0.25
    radar.zoom_in.click()
    assert radar.zoom == 0.3125
    radar.zoom_out.click()
    assert radar.zoom == 0.25
    radar.set_personnel([])
    assert radar.personnel == []
    assert not radar.grab().isNull()
    assert radar._hits == []
    QTest.mouseClick(radar, Qt.MouseButton.LeftButton, pos=QPoint(450, 300))
    assert radar.selected_coordinates[1] > radar.center[1]
    radar.close()


def test_hidden_radar_pauses_animation_timer():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    _disable_tile_fetch(radar)
    radar.show()
    app.processEvents()
    assert radar._pulse_timer.isActive()
    radar.hide()
    app.processEvents()
    assert not radar._pulse_timer.isActive()
    radar.show()
    app.processEvents()
    assert radar._pulse_timer.isActive()
    radar.close()


def test_radar_remains_responsive_while_tile_requests_are_pending():
    app = QApplication.instance() or QApplication([])

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class DeferredReply:
        def __init__(self):
            self.finished = Signal()
            self.aborted = False

        def abort(self):
            self.aborted = True

    class DeferredNetwork:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = DeferredReply()
            self.requests.append((request, reply))
            return reply

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._network = DeferredNetwork()
    radar.resize(1000, 700)
    radar.show()
    app.processEvents()
    ticks = []
    heartbeat = QTimer()
    heartbeat.setInterval(10)
    heartbeat.timeout.connect(lambda: ticks.append(True))
    heartbeat.start()
    QTimer.singleShot(180, app.quit)
    app.exec()
    heartbeat.stop()
    assert len(ticks) >= 8
    assert 0 < len(radar._network.requests) <= radar.MAX_PENDING_MAP_TILES
    radar.close()
    assert all(reply.aborted for _request, reply in radar._network.requests)


def test_radar_animation_invalidates_only_marker_region():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    radar.resize(1200, 800)
    damage = radar._pulse_damage()
    assert damage.width() < radar.width() // 4
    assert damage.height() < radar.height() // 4
    assert radar.rect().contains(damage)
    radar.close()


def test_radar_reports_tile_loading_failure_without_hiding_the_map_controls():
    from PyQt6.QtNetwork import QNetworkReply

    app = QApplication.instance() or QApplication([])

    class Reply:
        NetworkError = QNetworkReply.NetworkError

        def error(self):
            return self.NetworkError.UnknownNetworkError

        def readAll(self):
            return b""

        def deleteLater(self):
            pass

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._tile_received((12, 1, 1), Reply(), "osm", radar._base_generation)
    assert "Harita yuklenemedi" in radar.map_status.text()
    assert radar.map_search_button.isEnabled()
    assert radar.refresh_map_button.isEnabled()
    radar.close()


def test_native_page_routes_coordinate_actions_and_reads_personnel_without_migration(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT,is_deleted INTEGER,is_active INTEGER)")
    connection.execute("CREATE TABLE appointments(id INTEGER,customer_name TEXT,phone TEXT,date TEXT,time TEXT,description TEXT,status TEXT,is_deleted INTEGER)")
    connection.executemany("INSERT INTO personnel VALUES(?,?,?,?,?,?,?,?)", [
        (7, "Actual technician", "TEKN\u0130SYEN", 39.6, 27.8, "Gorevde", 0, 1),
        (8, "\u00c7a\u011fr\u0131 GPS", "Saha", None, None, "Bo\u015fta", 0, 1),
        (9, "Deleted", "Saha", 39.6, 27.8, "", 1, 1),
        (10, "Inactive", "Saha", 39.6, 27.8, "", 0, 0),
        (11, "Manager", "Yonetici", 39.6, 27.8, "", 0, 1),
    ])
    connection.executemany("INSERT INTO appointments VALUES(?,?,?,?,?,?,?,?)", [
        (1, "Open Job", "", "2026-10-13", "14:00", "Visit", "Bekliyor", 0),
        (2, "Completed Job", "", "2026-10-12", "10:00", "Closed", "Tamamlandi", 0),
        (3, "Deleted Job", "", "2026-10-13", "15:00", "Deleted", "Bekliyor", 1),
    ])
    def forbidden(*args):
        raise AssertionError("No migration, network request or web map allowed")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default, get_field_technicians=forbidden)
    page = FieldServicePage(db)
    assert page.default_lat == 40.10441
    assert page.default_lng == 27.6564
    assert page.map_view.center == (40.10441, 27.6564)
    monkeypatch.setattr(page, "notify", lambda *args: None)
    monkeypatch.setattr(page, "_get_search_results", forbidden)
    changes = connection.total_changes
    page.refresh_data()
    assert [record["id"] for record in page._read_radar_personnel()] == [7, 8]
    assert [record["id"] for record in page.map_view.personnel] == [7]
    assert page.field_kpi_values[0].text() == "2 Personel"
    assert page.field_kpi_notes[0].text() == "1 GPS kaydi / 2 personel"
    assert page.operation_panel.mode_buttons["teams"].text() == "Ekipler (2)"
    assert page.operation_panel.mode_buttons["jobs"].text() == "\u0130\u015f Emirleri (1)"
    page.operation_panel.mode_buttons["teams"].click()
    assert page.operation_panel.location_card.isHidden()
    assert not page.operation_panel.scroll_area.isHidden()
    assert not page.operation_panel.filter_container.isHidden()
    page.operation_panel.mode_buttons["jobs"].click()
    assert not page.operation_panel.jobs_scroll_area.isHidden()
    job_card = page.operation_panel.jobs_layout.itemAt(0).widget()
    assert job_card.findChild(QLabel).text() == "Open Job"
    page.operation_panel.mode_buttons["customer"].click()
    def visible_cards():
        return [page.scroll_layout.itemAt(index).widget() for index in range(page.scroll_layout.count())
                if isinstance(page.scroll_layout.itemAt(index).widget(), PersonnelCard)]
    assert [card.t_data["id"] for card in visible_cards()] == [7, 8]
    assert not page.location_toggle.isChecked()
    page.location_toggle.click()
    assert not page.location_controls.isHidden()
    assert not page.location_scroll.isHidden()
    assert page.location_scroll.maximumHeight() == 260
    page.location_toggle.click()
    assert page.location_scroll.isHidden()
    finished = []
    monkeypatch.setattr(page, "finish_personnel_duty", finished.append)
    page.operation_panel.mode_buttons["teams"].click()
    page.radar_filter_buttons["warnings"].click()
    assert [card.t_data["id"] for card in visible_cards()] == [8]
    assert page.map_view.personnel == []
    visible_cards()[0].finish_button.click()
    assert finished[0]["id"] == 8
    page.radar_filter_buttons["idle"].click()
    assert [card.t_data["id"] for card in visible_cards()] == [8]
    page.personnel_search.setText("cagri")
    assert [card.t_data["id"] for card in visible_cards()] == [8]
    page.personnel_search.setText("nonexistent")
    assert visible_cards() == []
    page.personnel_search.clear()
    page.radar_filter_buttons["all"].click()
    assert [card.t_data["id"] for card in visible_cards()] == [7, 8]
    assert [record["id"] for record in page.map_view.personnel] == [7]
    shared, assigned = [], []
    monkeypatch.setattr(page, "_open_whatsapp_share", lambda *coords: shared.append(coords))
    monkeypatch.setattr(page, "_show_assignment_dialog", lambda *coords: assigned.append(coords))
    clipboard_text = [""]
    clipboard = SimpleNamespace(text=lambda: clipboard_text[0], setText=lambda value: clipboard_text.__setitem__(0, value))
    monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: clipboard))
    previous = app.clipboard().text()
    try:
        app.clipboard().setText("https://maps.google.com/?q=40.5000,28.2500")
        page.paste_whatsapp_link()
        assert page.map_view.center == (40.5, 28.25)
        page.share_location()
        page.assign_location_to_personnel()
        assert shared == assigned == [(40.5, 28.25)]
        page.copy_map_link_button.click()
        assert clipboard_text[0] == "https://www.google.com/maps?q=40.500000,28.250000"
        app.clipboard().setText("91.0000,28.2500")
        page.paste_whatsapp_link()
        assert page.map_view.center == (40.5, 28.25)
        page.address_input.setText("40.7500,28.5000")
        page.search_address()
        assert page.map_view.center == (40.75, 28.5)
        page.update_default_location(39.7, 27.9)
        page.map_view.focus_coordinates(40.0, 28.0)
        page.map_view.home.click()
        assert page.map_view.center == (39.7, 27.9)
    finally:
        app.clipboard().setText(previous)
    assert connection.total_changes == changes
    page.close()


def test_field_action_buttons_open_task_traffic_and_route(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    refreshes = []
    monkeypatch.setattr(page, "refresh_data", lambda: refreshes.append(True))

    class TaskDialog:
        def __init__(self, database, parent):
            assert database is db
            assert parent is page.window()

        def exec(self):
            return QDialog.DialogCode.Accepted

    import src.ui.pages.appointments_page as appointments_page
    monkeypatch.setattr(appointments_page, "AddAppointmentDialog", TaskDialog)
    page.show()
    app.processEvents()
    page.findChild(QPushButton, "field_action_new_task").click()
    assert refreshes == [True]

    saved_secrets = {}
    monkeypatch.setattr("src.utils.local_secret_store.load_secret", lambda name: saved_secrets.get(name, ""))
    monkeypatch.setattr("src.utils.local_secret_store.save_secret", lambda name, value: saved_secrets.__setitem__(name, value))
    monkeypatch.setattr(page, "_prompt_tomtom_api_key", lambda: "test-key")
    traffic_requests = []
    def begin_traffic(key):
        traffic_requests.append(key)
        page.map_view.traffic_active = True
        page.map_view.trafficReady.emit()
    monkeypatch.setattr(page.map_view, "enable_tomtom_traffic", begin_traffic)
    page.map_view.selected_coordinates = (40.25, 27.75)
    page.findChild(QPushButton, "field_action_live_traffic").click()
    assert page.map_stack.currentWidget() is page.map_view
    assert traffic_requests == ["test-key"]
    assert saved_secrets == {"tomtom_traffic_api_key": "test-key"}
    assert page.map_view.traffic_active
    assert page.live_traffic_active
    page.findChild(QPushButton, "field_action_live_traffic").click()
    assert not page.map_view.traffic_active
    assert not page.live_traffic_active

    warnings = []
    monkeypatch.setattr(page, "notify", lambda message, level="info": warnings.append((message, level)))
    route_button = page.findChild(QPushButton, "field_action_optimize_route")
    route_button.click()
    assert warnings[-1][1] == "warning"

    monkeypatch.setattr(page, "_read_radar_personnel", lambda: [
        {"name": "Near", "lat": 40.11, "lng": 27.66},
        {"name": "Far", "lat": 41.0, "lng": 28.0},
    ])
    route_requests = []
    monkeypatch.setattr(
        page.map_view, "calculate_tomtom_route",
        lambda key, points: route_requests.append((key, points)) or True,
    )
    route_button.click()
    assert page.map_view.route_points == [
        (page.default_lat, page.default_lng), (40.11, 27.66), (41.0, 28.0)
    ]
    assert route_requests == [
        ("test-key", page.map_view.route_points)
    ]
    assert "duz cizgi tahmini" in page.map_view.route_status.text()
    assert warnings[-1][1] == "success"
    page.redraw_route_button.click()
    assert len(route_requests) == 2
    assert route_requests[-1] == ("test-key", page.map_view.route_points)
    page.close()


def test_vector_map_error_returns_to_tomtom_raster_with_route(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    _disable_tile_fetch(page.map_view)
    vector_view = QWidget()
    vector_view.selected_coordinates = (40.2, 27.7)
    vector_view.route_points = [(40.1, 27.6), (40.2, 27.7)]
    page.vector_map_view = vector_view
    page.map_stack.addWidget(vector_view)
    page.map_stack.setCurrentWidget(vector_view)
    page._vector_map_ready = False
    focused = []
    routes = []
    notifications = []
    monkeypatch.setattr(page.map_view, "focus_coordinates", lambda *point: focused.append(point))
    monkeypatch.setattr(page.map_view, "set_route", lambda points: routes.append(points))
    monkeypatch.setattr(page, "notify", lambda *args: notifications.append(args))

    page._check_vector_map_ready()

    assert page.map_stack.currentWidget() is page.map_view
    assert focused == [(40.2, 27.7)]
    assert routes == [[(40.1, 27.6), (40.2, 27.7)]]
    assert page.overview.map_mode_button.text() == "3D Vektor"
    assert notifications
    page.close()
    connection.close()


def test_manual_route_drawing_adds_stops_finishes_and_clears():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    radar.resize(720, 560)
    radar.show()
    app.processEvents()
    radar.draw_route_button.click()
    assert radar.route_drawing
    assert radar.route_status.isVisible()
    QTest.mouseClick(radar, Qt.MouseButton.LeftButton, pos=QPoint(220, 210))
    QTest.mouseClick(radar, Qt.MouseButton.LeftButton, pos=QPoint(470, 340))
    assert len(radar.route_points) == 2
    assert radar.finish_route_button.isEnabled()
    radar.finish_route_button.click()
    assert not radar.route_drawing
    assert len(radar.route_points) == 2
    assert "Taslak rota" in radar.route_status.text()
    radar.clear_route_button.click()
    assert radar.route_points == []
    assert radar.route_status.isHidden()
    radar.close()


def test_tomtom_routing_request_replaces_draft_with_road_geometry():
    from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

    app = QApplication.instance() or QApplication([])

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Reply:
        NetworkError = QNetworkReply.NetworkError

        def __init__(self):
            self.finished = Signal()
            self.payload = b""

        def error(self):
            return self.NetworkError.NoError

        def readAll(self):
            return self.payload

        def attribute(self, attribute):
            if attribute == QNetworkRequest.Attribute.HttpStatusCodeAttribute:
                return 200
            return None

        def deleteLater(self):
            pass

        def abort(self):
            pass

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = Reply()
            self.requests.append((request, reply))
            return reply

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._network = Network()
    stops = [(40.1, 27.6), (40.2, 27.8)]
    radar.set_route(stops)
    assert radar.calculate_tomtom_route("sample-key", stops)
    request, reply = radar._network.requests[0]
    assert request.url().host() == "api.tomtom.com"
    assert "/maps/orbis/routing/calculateRoute/" in request.url().path()
    route_query = dict(QUrlQuery(request.url()).queryItems())
    assert route_query == {
        "apiVersion": "2", "key": "sample-key", "routeType": "fast",
        "traffic": "live", "travelMode": "car"
    }
    assert request.rawHeader(b"TomTom-Api-Key") == b""
    assert request.rawHeader(b"TomTom-Api-Version") == b"2"
    reply.payload = (
        b'{"routes":[{"summary":{"lengthInMeters":2500,"travelTimeInSeconds":420},'
        b'"legs":[{"points":[{"latitude":40.1,"longitude":27.6},'
        b'{"latitude":40.15,"longitude":27.7}]},'
        b'{"points":[{"latitude":40.15,"longitude":27.7},'
        b'{"latitude":40.2,"longitude":27.8}]}]}]}'
    )
    reply.finished.callback()
    assert radar.route_geometry == [(40.1, 27.6), (40.15, 27.7), (40.2, 27.8)]
    assert radar.route_distance_meters == 2500
    assert radar.route_duration_seconds == 420
    assert "TomTom yol rotasi" in radar.route_status.text()
    assert "2.5 km" in radar.route_status.text()
    radar.close()


def test_route_turns_do_not_fill_the_area_between_segments():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    _disable_tile_fetch(radar)
    radar.resize(500, 400)
    radar.set_route([
        (40.101, 27.601),
        (40.101, 27.602),
        (40.099, 27.602),
    ])
    positions = {
        (40.1, 27.6): QPointF(30, 30),
        (40.101, 27.601): QPointF(100, 100),
        (40.101, 27.602): QPointF(300, 100),
        (40.099, 27.602): QPointF(300, 300),
    }
    radar._screen_point = lambda latitude, longitude: positions[
        (round(float(latitude), 3), round(float(longitude), 3))
    ]
    radar.show()
    app.processEvents()
    image = QImage(radar.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    radar.render(image)

    assert image.pixelColor(250, 150) != QColor("#34d399")
    radar.close()


def test_field_map_search_and_manual_refresh_controls():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    searches = []
    radar.searchRequested.connect(searches.append)
    radar.map_search_input.setText("Gonen")
    radar.map_search_button.click()
    assert searches == ["Gonen"]
    assert radar.refresh_map_button.objectName() == "field_map_refresh"
    radar.resize(520, 480)
    radar.show()
    app.processEvents()
    toolbar_rect = radar.map_toolbar.rect()
    route_toolbar_rect = radar.route_toolbar.rect()
    assert not radar.refresh_map_button.isVisible()
    assert not radar.filter_action_button.isVisible()
    for control in (radar.map_search_input, radar.map_search_button,
                    radar.map_mode_toolbar):
        assert toolbar_rect.contains(control.geometry())
    for control in (radar.draw_route_button, radar.finish_route_button,
                    radar.clear_route_button, radar.share_route_button):
        assert route_toolbar_rect.contains(control.geometry())
    radar.refresh_visible_tiles()
    assert radar._force_refresh
    assert not radar.refresh_map_button.isEnabled()
    radar._finish_refresh()
    assert not radar._force_refresh
    assert radar.refresh_map_button.isEnabled()


def test_tomtom_traffic_uses_orbis_overlay_and_never_persists_tiles():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    expected_map_style = FieldRadarCanvas._current_tomtom_style()

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Reply:
        def __init__(self):
            self.finished = Signal()
            self.aborted = False

        def abort(self):
            self.aborted = True

    class Network:
        def __init__(self):
            self.gets = []

        def get(self, request):
            reply = Reply()
            self.gets.append((request, reply))
            return reply

    network = Network()
    radar._network = network
    radar.enable_tomtom_traffic("sample-key")
    assert radar.traffic_active
    assert radar._traffic_connecting
    assert not radar.traffic_legend.isHidden()
    assert radar.traffic_status.text() == "Baglaniyor..."
    radar._request_traffic_tile(12, 1200, 1500)
    traffic_request, _traffic_reply = network.gets[0]
    assert traffic_request.url().host() == "api.tomtom.com"
    assert traffic_request.url().path() == "/maps/orbis/traffic/tile/flow/12/1200/1500.png"
    traffic_query = dict(QUrlQuery(traffic_request.url()).queryItems())
    assert traffic_query == {
        "apiVersion": "1", "key": "sample-key", "style": "dark", "tileSize": "256"
    }
    assert traffic_request.rawHeader(b"TomTom-Api-Key") == b""
    assert traffic_request.rawHeader(b"TomTom-Api-Version") == b"1"
    assert traffic_request.rawHeader(b"Accept") == b"image/png, application/json"
    assert traffic_request.attribute(traffic_request.Attribute.CacheSaveControlAttribute) is False
    radar.resize(600, 500)
    radar.grab()
    hosts = {request.url().host() for request, _reply in network.gets}
    assert "api.tomtom.com" in hosts
    map_requests = [request for request, _reply in network.gets
                    if request.url().path().startswith("/maps/orbis/display/raster/tile/")]
    assert map_requests
    assert map_requests[0].url().query() == f"apiVersion=2&style={expected_map_style}&tileSize=256&geopoliticalView=TR"
    assert map_requests[0].rawHeader(b"TomTom-Api-Key") == b"sample-key"
    assert map_requests[0].rawHeader(b"TomTom-Api-Version") == b"2"
    assert "tile.openstreetmap.org" not in hosts
    map_key = (12, 1200, 1500)
    ready = []
    radar.trafficReady.connect(lambda: ready.append(True))
    radar._traffic_layers_ready()
    assert not ready
    assert radar.traffic_status.text() == "Baglaniyor..."
    radar._tiles[map_key] = QImage(1, 1, QImage.Format.Format_ARGB32)
    radar._traffic_tiles[map_key] = QImage(1, 1, QImage.Format.Format_ARGB32)
    radar._traffic_layers_ready()
    assert ready == [True]
    assert radar.traffic_status.text().startswith("Guncel: ")
    old_traffic_replies = [reply for request, reply in network.gets
                           if "/traffic/tile/flow/" in request.url().path()]
    old_generation = radar._traffic_generation
    radar.refresh_visible_tiles()
    assert radar._traffic_generation == old_generation + 1
    assert radar.traffic_status.text() == "Guncelleniyor..."
    assert not radar._traffic_pending
    assert all(reply.aborted for reply in old_traffic_replies)
    radar.grab()
    assert radar._traffic_pending
    assert all(request_id[0] == radar._traffic_generation for request_id in radar._traffic_pending)
    api_errors = []
    radar.trafficFailed.connect(api_errors.append)
    radar._emit_traffic_api_error(
        b'{"detailedError":{"code":"FORBIDDEN","message":"Key is not enabled"}}',
        "Traffic tile failed", 403)
    assert not radar._traffic_auth_failed
    assert "Key is not enabled" in api_errors[0]
    radar._emit_traffic_api_error(
        b'{"detailedError":{"code":"InvalidReferer","message":"Request contains an invalid Referer header"}}',
        "Traffic tile failed", 403)
    assert not radar._traffic_auth_failed
    assert "alan adi kisitlamasi" in api_errors[1]
    radar._emit_traffic_api_error(
        b'{"detailedError":{"code":"API_KEY_INVALID","message":"Invalid key"}}',
        "Traffic tile failed", 403)
    assert radar._traffic_auth_failed
    radar.disable_tomtom_traffic()
    assert radar.traffic_legend.isHidden()
    assert radar.traffic_status.text() == "Kapali"
    radar.close()


def test_field_map_search_results_open_on_map_and_select_coordinates():
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    assert type(page.overview).__name__ == "FieldMapOverview"
    assert type(page.operation_panel).__name__ == "FieldOperationsPanel"
    assert len(page.overview.metric_cards) == 4
    assert [button.objectName() for button in page.overview.window_buttons] == [
        "field_window_minimize",
        "field_window_maximize",
        "field_window_close",
    ]
    assert all(not button.icon().isNull() for button in page.overview.window_buttons)
    assert "font-size:18.75px" in page.operation_panel.customer_name_value.styleSheet()
    assert "font-size:17.5px" in page.operation_panel.share_preview_label.styleSheet()
    heading = page.overview.layout().itemAt(0).layout()
    title = heading.itemAt(0).layout().itemAt(0).widget()
    assert title.text().endswith("AYEC PRO")
    page.resize(1600, 1000)
    page.show()
    app.processEvents()
    result = {"lat": "40.5", "lon": "28.25", "display_name": "Gonen, Balikesir"}
    page.on_search_finished([result], False)
    app.processEvents()
    assert page.list_results.parent() is page.map_view
    assert page.list_results.isVisible()
    assert page.list_results.geometry().y() > page.map_view.map_toolbar.y()
    page.on_result_clicked(page.list_results.item(0))
    assert page.map_view.center == (40.5, 28.25)
    assert page.map_view.map_search_input.text() == "Gonen, Balikesir"
    assert page.operation_panel.selected_address_label.text() == "Gonen, Balikesir"
    assert page.operation_panel.customer_name_value.text() == "\u0130\u015f emri se\u00e7ilmedi"
    assert page.list_results.isHidden()
    page.close()
    connection.close()


def test_route_share_button_emits_all_planned_stops():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    route = [(40.1, 27.6), (40.2, 27.7), (40.3, 27.8)]
    shared = []
    radar.routeShareRequested.connect(shared.append)
    radar.set_route(route)
    assert not radar.share_route_button.isHidden()
    radar.share_route_button.click()
    assert shared == [route]
    radar.clear_route()
    assert radar.share_route_button.isHidden()
    radar.close()


def test_field_map_empty_state_is_outside_map_center_and_clears_for_route_or_gps():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    radar.resize(900, 640)
    radar.show()
    app.processEvents()
    assert radar.empty_state.isVisible()
    center = radar._screen_point(*radar.center).toPoint()
    assert not radar.empty_state.geometry().contains(center)
    radar.set_personnel([{"id": 1, "name": "Technician", "lat": 40.2, "lng": 27.7}])
    assert radar.empty_state.isHidden()
    radar.set_personnel([])
    radar.set_route([(40.1, 27.6), (40.2, 27.7)])
    assert radar.empty_state.isHidden()
    radar.clear_route()
    assert radar.empty_state.isVisible()
    radar.close()


def test_field_map_compact_route_controls_do_not_overlap_traffic_legend():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    radar.resize(420, 500)
    radar.traffic_legend.show()
    radar.draw_route_button.click()
    radar.add_route_point(40.1, 27.6)
    radar.add_route_point(40.2, 27.7)
    radar.show()
    app.processEvents()
    assert not radar.route_toolbar.geometry().intersects(radar.traffic_legend.geometry())
    assert radar.draw_route_button.x() == 0
    assert radar.route_status.y() > radar.route_toolbar.y()
    radar.close()


def test_manual_map_refresh_does_not_duplicate_a_tile_request():
    app = QApplication.instance() or QApplication([])

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class DeferredReply:
        def __init__(self):
            self.finished = Signal()
            self.aborted = False

        def abort(self):
            self.aborted = True

    class DeferredNetwork:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = DeferredReply()
            self.requests.append((request, reply))
            return reply

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._network = DeferredNetwork()
    radar.refresh_map_button.click()
    radar._request_tile(12, 1200, 1500)
    radar._request_tile(12, 1200, 1500)
    assert len(radar._network.requests) == 1
    radar.close()
    assert radar._network.requests[0][1].aborted


def test_field_map_toolbar_and_location_actions_do_not_overlap():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)
    radar.resize(520, 480)
    radar.show()
    app.processEvents()
    toolbar_rect = radar.map_toolbar.rect()
    assert not radar.refresh_map_button.isVisible()
    assert not radar.filter_action_button.isVisible()
    assert toolbar_rect.contains(radar.map_mode_toolbar.geometry())
    route_toolbar_rect = radar.route_toolbar.rect()
    for control in (radar.draw_route_button, radar.finish_route_button,
                    radar.clear_route_button):
        assert route_toolbar_rect.contains(control.geometry())
    assert not radar.map_search_input.geometry().intersects(radar.map_search_button.geometry())
    assert radar.map_search_input.maximumWidth() == 480
    assert radar.map_search_button.width() == 118
    assert radar.map_telemetry_bar.y() == radar.map_toolbar.y() + radar.map_toolbar.height()
    radar.close()

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    page.resize(1600, 1000)
    page.show()
    page.location_toggle.click()
    app.processEvents()
    assert page.location_scroll.isVisible()
    assert page.location_scroll.height() >= 190
    assert page.location_scroll.height() <= 260
    action_buttons = page.location_controls.findChildren(QPushButton)
    assert len(action_buttons) == 6
    assert all(button.isVisible() for button in action_buttons)
    assert page.location_controls.findChildren(QLineEdit) == []
    location_rect = page.location_scroll.geometry().translated(page.sidebar.pos())
    personnel_rect = page.scroll_area.geometry().translated(page.sidebar.pos())
    assert not location_rect.intersects(personnel_rect)
    assert page.scroll_area.height() > 0
    page.resize(1024, 768)
    app.processEvents()
    assert page.location_scroll.isVisible()
    assert page.location_scroll.height() >= 150
    assert page.scroll_area.height() > 0
    location_rect = page.location_scroll.geometry().translated(page.sidebar.pos())
    personnel_rect = page.scroll_area.geometry().translated(page.sidebar.pos())
    assert not location_rect.intersects(personnel_rect)
    page.close()
    connection.close()


def test_field_map_fits_compact_desktop_window():
    app = QApplication.instance() or QApplication([])
    from PyQt6.QtWidgets import QMainWindow
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    host = QMainWindow()
    host.resize(1024, 768)
    host.setCentralWidget(page)
    host.show()
    app.processEvents()
    assert page.main_layout.minimumSize().width() <= 1024
    assert page.main_layout.minimumSize().height() <= 768
    assert page.overview.height() >= page.overview.layout().sizeHint().height()
    assert all(card.height() >= card.layout().minimumSize().height() for card in page.metric_cards)
    assert page.map_view.height() >= 280
    assert page.sidebar.height() >= 280
    host.close()
    connection.close()


def test_field_map_shell_mode_keeps_sidebar_visible_and_restores_navigation():
    app = QApplication.instance() or QApplication([])
    shell = QWidget()
    header = QWidget(shell)
    sidebar = QWidget(shell)
    top_nav = QWidget(shell)
    status_bar = QWidget(shell)
    assistant_fab = QWidget(shell)
    shell.show()
    app.processEvents()
    window = SimpleNamespace(
        _active_nav_mode="ust_bar",
        _current_page_index=int(PageIds.FIELD_MAP),
        _assistant_fab_enabled=True,
        _set_field_map_reference_theme=lambda _enabled: None,
        app_header=header,
        app_sidebar=sidebar,
        app_top_nav=top_nav,
        shell_status_bar=status_bar,
        assistant_fab=assistant_fab,
    )
    window._set_field_map_shell_mode = lambda enabled: (
        MainWindowNavMixin._set_field_map_shell_mode(window, enabled)
    )

    MainWindowNavMixin.apply_nav_mode(window, "ust_bar")

    assert not header.isVisible()
    assert sidebar.isVisible()
    assert not top_nav.isVisible()
    assert not status_bar.isVisible()
    assert not assistant_fab.isVisible()

    window._current_page_index = int(PageIds.DASHBOARD)
    MainWindowNavMixin.apply_nav_mode(window, "ust_bar")

    assert header.isVisible()
    assert not sidebar.isVisible()
    assert top_nav.isVisible()
    assert status_bar.isVisible()
    assert assistant_fab.isVisible()
    shell.close()


def test_field_map_theme_refresh_uses_theme_manager_without_forcing_dark_palette(monkeypatch):
    sidebar = QWidget()
    page = QWidget()
    refreshed = []
    original_theme = ThemeManager._current_theme

    monkeypatch.setattr(
        ThemeManager,
        "refresh_widget_tree",
        lambda widget, include_root=True: refreshed.append(widget),
    )
    monkeypatch.setattr(
        ThemeManager,
        "apply_theme",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Theme is user-managed")),
    )
    window = SimpleNamespace(
        app_sidebar=sidebar,
        pages={int(PageIds.FIELD_MAP): page},
    )

    MainWindowNavMixin._set_field_map_reference_theme(window, True)

    assert ThemeManager._current_theme == original_theme
    assert refreshed == [sidebar, page]


def test_tomtom_basemap_style_follows_theme_manager():
    original_theme = ThemeManager._current_theme
    try:
        ThemeManager._current_theme = "AYEC"
        assert FieldRadarCanvas._current_tomtom_style() == "street-light"
        ThemeManager._current_theme = "Koyu Mavi"
        assert FieldRadarCanvas._current_tomtom_style() == "street-dark"
    finally:
        ThemeManager._current_theme = original_theme


def test_closing_field_map_cancels_deferred_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    refreshes = []
    monkeypatch.setattr(FieldServicePage, "refresh_data", lambda _self: refreshes.append(True))

    page = FieldServicePage(db)
    page.show()
    app.processEvents()
    page.close()
    QTest.qWait(150)

    assert refreshes == []
    connection.close()


def test_field_map_skips_recent_refreshes_and_resumes_pending_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    refreshes = []

    def record_refresh(page):
        refreshes.append(page)
        page._last_refresh_at = time.monotonic()
        page._refresh_requested = False

    monkeypatch.setattr(FieldServicePage, "refresh_data", record_refresh)
    page = FieldServicePage(db)
    try:
        page.show()
        QTest.qWait(130)
        assert refreshes == [page]

        page.hide()
        page.show()
        QTest.qWait(130)
        assert refreshes == [page]

        page._schedule_refresh(100)
        page.hide()
        QTest.qWait(130)
        assert refreshes == [page]

        page.show()
        deadline = time.monotonic() + 2
        while len(refreshes) < 2 and time.monotonic() < deadline:
            QTest.qWait(50)
        assert refreshes == [page, page]
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        connection.close()


def test_field_map_overview_reflows_after_full_size_window_shows():
    app = QApplication.instance() or QApplication([])
    from PyQt6.QtWidgets import QMainWindow
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT,last_seen TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    host = QMainWindow()
    host.resize(1600, 900)
    host.setCentralWidget(page)
    host.show()
    app.processEvents()
    assert page.overview.height() >= page.overview.layout().sizeHint().height()
    metric_widths = [card.width() for card in page.metric_cards]
    assert max(metric_widths) - min(metric_widths) <= 1
    value_tops = [card.layout().itemAt(1).widget().y() for card in page.metric_cards]
    assert len(set(value_tops)) == 1
    host.close()
    connection.close()


def test_map_tile_requests_have_timeout_and_failed_tiles_back_off(monkeypatch):
    from PyQt6.QtNetwork import QNetworkReply

    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Reply:
        NetworkError = QNetworkReply.NetworkError

        def __init__(self):
            self.finished = Signal()

        def error(self):
            return self.NetworkError.TimeoutError

        def readAll(self):
            return b""

        def deleteLater(self):
            pass

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = Reply()
            self.requests.append((request, reply))
            return reply

    network = Network()
    radar._network = network
    radar._request_tile(12, 1200, 1500)
    request, reply = network.requests[0]
    assert request.transferTimeout() == 12000
    assert request.rawHeader(b"User-Agent") == b"AYEC-Pro/2.0"
    key = (12, 1200, 1500)
    radar._tile_received(key, reply)
    assert radar._tile_retry_after[key] > 0
    radar._request_tile(*key)
    assert len(network.requests) == 1
    radar._tile_retry_after[key] = 0
    radar._request_tile(*key)
    assert len(network.requests) == 2
    radar.close()


def test_map_caches_and_pending_requests_are_bounded():
    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Reply:
        def __init__(self):
            self.finished = Signal()
            self.aborted = False

        def abort(self):
            self.aborted = True

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = Reply()
            self.requests.append((request, reply))
            return reply

    network = Network()
    radar._network = network
    for x in range(radar.MAX_PENDING_MAP_TILES + 20):
        radar._request_tile(12, x, 1)
    assert len(radar._pending_tiles) == radar.MAX_PENDING_MAP_TILES
    assert len(network.requests) == radar.MAX_PENDING_MAP_TILES

    image = QImage(1, 1, QImage.Format.Format_ARGB32)
    for index in range(radar.MAX_BASE_TILES + 10):
        radar._cache_tile(radar._tiles, (12, index, 2), image, radar.MAX_BASE_TILES)
    assert len(radar._tiles) == radar.MAX_BASE_TILES
    assert (12, 0, 2) not in radar._tiles
    assert (12, radar.MAX_BASE_TILES + 9, 2) in radar._tiles
    for index in range(radar.MAX_BASE_TILES + 10):
        radar._cache_tile(radar._tile_retry_after, (12, index, 3), float(index), radar.MAX_BASE_TILES)
    assert len(radar._tile_retry_after) == radar.MAX_BASE_TILES
    assert (12, 0, 3) not in radar._tile_retry_after

    radar.enable_tomtom_traffic("sample-key")
    for x in range(radar.MAX_PENDING_TRAFFIC_TILES + 20):
        radar._request_traffic_tile(12, x, 4)
    assert len(radar._traffic_pending) == radar.MAX_PENDING_TRAFFIC_TILES
    radar.close()
    assert all(reply.aborted for _request, reply in network.requests)


def test_tomtom_transient_tile_failure_retries_tomtom_without_osm_fallback():
    from PyQt6.QtNetwork import QNetworkReply

    app = QApplication.instance() or QApplication([])

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Reply:
        NetworkError = QNetworkReply.NetworkError

        def __init__(self):
            self.finished = Signal()

        def error(self):
            return self.NetworkError.TimeoutError

        def readAll(self):
            return b""

        def attribute(self, _attribute):
            return 503

        def rawHeader(self, _name):
            return b""

        def deleteLater(self):
            pass

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = Reply()
            self.requests.append((request, reply))
            return reply

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._network = Network()
    radar.set_tomtom_api_key("test-key")
    radar._request_tile(14, 9000, 6000)
    key = (14, 9000, 6000)
    request, reply = radar._network.requests[0]

    radar._tile_received(key, reply, "tomtom", radar._base_generation)

    assert request.url().host() == "api.tomtom.com"
    assert len(radar._network.requests) == 1
    assert not radar._tomtom_map_unavailable
    assert radar._tile_retry_after[key] > time.monotonic()
    radar.close()


def test_map_refresh_respects_osm_disk_cache():
    from PyQt6.QtNetwork import QNetworkRequest

    app = QApplication.instance() or QApplication([])
    radar = FieldRadarCanvas(40.1, 27.6)

    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Reply:
        def __init__(self):
            self.finished = Signal()

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = Reply()
            self.requests.append((request, reply))
            return reply

    network = Network()
    radar._network = network
    radar._request_tile(12, 1200, 1500)
    radar._force_refresh = True
    radar._request_tile(12, 1201, 1500)
    assert network.requests[0][0].attribute(
        QNetworkRequest.Attribute.CacheLoadControlAttribute
    ) == QNetworkRequest.CacheLoadControl.PreferCache
    assert network.requests[1][0].attribute(
        QNetworkRequest.Attribute.CacheLoadControlAttribute
    ) == QNetworkRequest.CacheLoadControl.PreferCache
    radar.close()


def test_address_lookup_waits_for_explicit_submit_and_respects_nominatim_rate(monkeypatch):
    import src.ui.pages.field_service_page as field_service_module

    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    requests = []
    monkeypatch.setattr(page, "notify", lambda *args: None)

    class Worker:
        def __init__(self, target, args, daemon):
            self.args = args

        def start(self):
            requests.append(self.args)

    monkeypatch.setattr(field_service_module.threading, "Thread", Worker)
    page.address_input.setText("Gonen, Balikesir")
    app.processEvents()
    assert requests == []
    page.map_view.map_search_button.click()
    assert requests == [("Gonen, Balikesir", 5, True)]

    clock = [10.0]
    sleeps = []
    monkeypatch.setattr(field_service_module.time, "monotonic", lambda: clock[0])
    def advance_clock(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(field_service_module.time, "sleep", advance_clock)
    monkeypatch.setattr(field_service_module, "_NOMINATIM_NEXT_REQUEST_AT", 0.0)
    field_service_module._wait_for_nominatim_slot()
    field_service_module._wait_for_nominatim_slot()
    assert len(sleeps) == 1
    assert abs(sleeps[0] - 1.05) < 1e-9
    page.close()
    connection.close()


def test_photon_fallback_uses_query_parameters(monkeypatch):
    import json
    import urllib.parse
    import urllib.error
    import src.ui.pages.field_service_page as field_service_module

    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def getcode(self):
            return 200

        def read(self):
            return json.dumps({"features": []}).encode("utf-8")

    def open_url(request, **kwargs):
        requests.append(request.full_url)
        if "nominatim.openstreetmap.org" in request.full_url:
            raise urllib.error.URLError("unavailable")
        return Response()

    monkeypatch.setattr(field_service_module.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(field_service_module, "_wait_for_nominatim_slot", lambda: None)
    page._get_search_results("Kadikoy Istanbul", 3)
    photon_url = urllib.parse.urlparse(requests[1])
    assert photon_url.path == "/api/"
    assert urllib.parse.parse_qs(photon_url.query) == {"q": ["Kadikoy Istanbul"], "limit": ["3"]}
    page.close()
    connection.close()


def test_tomtom_key_dialog_has_signup_link_password_field_and_footer(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    dialog_instances = []

    def accept_with_key(dialog):
        dialog_instances.append(dialog)
        dialog.findChild(QLineEdit, "tomtom_traffic_api_key").setText("sample-key")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ModernDialog, "exec", accept_with_key)
    assert page._prompt_tomtom_api_key() == "sample-key"
    dialog = dialog_instances[0]
    assert dialog.footer_layout.count() == 2
    assert "my.tomtom.com" in dialog.findChild(QLabel).text() or any(
        "my.tomtom.com" in label.text() for label in dialog.findChildren(QLabel)
    )
    assert any(
        "Maps Orbis" in label.text() and "OpenStreetMap" in label.text()
        for label in dialog.findChildren(QLabel)
    )
    page.close()


def test_tomtom_successful_map_and_traffic_responses_activate_live_layer():
    from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
    from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

    app = QApplication.instance() or QApplication([])
    source_image = QImage(8, 8, QImage.Format.Format_ARGB32)
    source_image.fill(Qt.GlobalColor.transparent)
    image_bytes = QByteArray()
    image_buffer = QBuffer(image_bytes)
    assert image_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert source_image.save(image_buffer, "PNG")
    image_buffer.close()

    class Signal:
        def connect(self, callback):
            self.callback = callback

        def emit(self):
            self.callback()

    class Reply:
        NetworkError = QNetworkReply.NetworkError

        def __init__(self):
            self.finished = Signal()
            self.deleted = False
            self.payload = image_bytes

        def error(self):
            return self.NetworkError.NoError

        def readAll(self):
            return self.payload

        def attribute(self, attribute):
            if attribute == QNetworkRequest.Attribute.HttpStatusCodeAttribute:
                return 200
            return None

        def deleteLater(self):
            self.deleted = True

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            reply = Reply()
            self.requests.append((request, reply))
            return reply

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._network = Network()
    ready = []
    radar.trafficReady.connect(lambda: ready.append(True))
    radar.enable_tomtom_traffic("sample-key")
    radar._request_tile(12, 1200, 1500)
    radar._request_traffic_tile(12, 1200, 1500)
    map_request, map_reply = radar._network.requests[0]
    traffic_request, traffic_reply = radar._network.requests[1]
    assert map_request.url().host() == "api.tomtom.com"
    assert "/display/raster/tile/" in map_request.url().path()
    assert map_request.rawHeader(b"TomTom-Api-Key") == b"sample-key"
    assert "/traffic/tile/flow/" in traffic_request.url().path()
    traffic_reply.finished.emit()
    assert not ready
    assert (12, 1200, 1500) in radar._traffic_tiles
    map_reply.finished.emit()
    assert ready == [True]
    assert (12, 1200, 1500) in radar._tiles
    assert radar.map_status.isHidden()
    assert radar.traffic_status.text().startswith("Guncel: ")
    assert map_reply.deleted and traffic_reply.deleted
    copyright_request, copyright_reply = radar._network.requests[2]
    assert copyright_request.url().path() == "/maps/orbis/copyrights/caption"
    assert copyright_request.rawHeader(b"TomTom-Api-Key") == b"sample-key"
    copyright_reply.payload = b'{"copyrightsCaption":"TomTom, OpenStreetMap"}'
    copyright_reply.finished.emit()
    assert radar._tomtom_copyright_caption == "TomTom, OpenStreetMap"
    radar._request_tomtom_copyrights()
    assert len(radar._network.requests) == 3
    radar.close()


def test_tomtom_basemap_permission_error_falls_back_to_osm_without_disabling_traffic():
    from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

    app = QApplication.instance() or QApplication([])

    class Signal:
        def connect(self, callback):
            self.callback = callback

        def emit(self):
            self.callback()

    class Reply:
        NetworkError = QNetworkReply.NetworkError

        def __init__(self, status_code):
            self.finished = Signal()
            self.status_code = status_code

        def error(self):
            return self.NetworkError.ContentAccessDenied

        def readAll(self):
            return b'{"detailedError":{"code":"FORBIDDEN"}}'

        def attribute(self, attribute):
            if attribute == QNetworkRequest.Attribute.HttpStatusCodeAttribute:
                return self.status_code
            return None

        def deleteLater(self):
            pass

    class Network:
        def __init__(self):
            self.requests = []

        def get(self, request):
            status = 403 if request.url().host() == "api.tomtom.com" else 200
            reply = Reply(status)
            self.requests.append((request, reply))
            return reply

    radar = FieldRadarCanvas(40.1, 27.6)
    radar._network = Network()
    errors = []
    radar.trafficFailed.connect(errors.append)
    radar.enable_tomtom_traffic("flow-only-key")
    radar._request_tile(12, 1200, 1500)
    tomtom_request, tomtom_reply = radar._network.requests[0]
    assert "/display/raster/tile/" in tomtom_request.url().path()
    tomtom_reply.finished.emit()
    osm_request, _osm_reply = radar._network.requests[1]
    assert osm_request.url().host() == "tile.openstreetmap.org"
    assert radar._tomtom_map_unavailable
    assert radar.traffic_active
    assert not radar._traffic_auth_failed
    assert errors == []
    key = (12, 1200, 1500)
    radar._tiles[key] = QImage(1, 1, QImage.Format.Format_ARGB32)
    radar._traffic_tiles[key] = QImage(1, 1, QImage.Format.Format_ARGB32)
    radar._traffic_layers_ready()
    assert "OSM tabani" in radar.traffic_status.text()
    radar.close()


def test_field_filter_and_quick_route_actions_remain_accessible():
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT)")
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    page.show()
    app.processEvents()
    page.findChild(QPushButton, "field_action_filter").click()
    assert page.personnel_search.hasFocus()
    route_action = next(
        button for button in page.operation_panel.location_action_buttons
        if button.objectName() == "field_location_draw_route"
    )
    page.location_toggle.click()
    app.processEvents()
    route_action.click()
    assert page.map_view.route_drawing
    page.close()
    connection.close()


def test_personnel_card_preserves_focus_and_finish_callbacks():
    app = QApplication.instance() or QApplication([])
    record = {"id": 42, "name": "Actual technician", "role": "Saha", "status": "Gorevde", "lat": 39.6, "lng": 27.8}
    focused, finished = [], []
    card = PersonnelCard(record, focused.append, finished.append)
    card.resize(340, 140)
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    card.finish_button.click()
    assert focused == finished == [record]
    assert not card.grab().isNull()
    card.close()


def test_personnel_card_uses_literal_identity_and_mono_location_data():
    from src.utils.design_system import DesignTokens

    app = QApplication.instance() or QApplication([])
    record = {"id": 42, "name": "<b>Actual technician</b>", "role": "<i>Field role</i>",
              "status": "<b>Assigned</b>", "lat": 39.6, "lng": 27.8,
              "last_seen": "2026-09-21 10:35:00"}
    card = PersonnelCard(record, lambda data: None, lambda data: None)
    labels = {label.text(): label for label in card.findChildren(QLabel)}
    for text in (record["name"], record["role"], "* " + record["status"]):
        label = labels[text]
        assert label.textFormat() == Qt.TextFormat.PlainText
        assert label.font().family() == DesignTokens.FONT_NAME
        assert label.toolTip() == text
        assert label.wordWrap()
    for text in ("GPS: 39.60000, 27.80000", "Son konum: " + record["last_seen"]):
        label = labels[text]
        assert label.textFormat() == Qt.TextFormat.PlainText
        assert label.font().family() == DesignTokens.MONO_FONT_NAME
        assert label.toolTip() == text
    assert card.t_data == record
    card.resize(340, card.sizeHint().height())
    assert not card.grab().isNull()
    card.close()


def test_assignment_dialog_uses_modern_footer_and_writes_only_selected_id(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    original_font = app.font()
    font_path = Path(__file__).resolve().parents[1] / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id >= 0:
        app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE personnel(id INTEGER,name TEXT,role TEXT,lat REAL,lng REAL,status TEXT,last_seen TEXT,is_deleted INTEGER,is_active INTEGER)")
    connection.executemany("INSERT INTO personnel VALUES(?,?,?,?,?,?,?,?,?)", [
        (41, "First technician", "Saha", 39.0, 27.0, "Bosta", "", 0, 1),
        (72, "Selected technician", "Teknisyen", 39.1, 27.1, "Bosta", "", 0, 1),
        (83, "Deleted technician", "Saha", 39.2, 27.2, "Bosta", "", 1, 1),
    ])
    db = SimpleNamespace(cursor=connection.cursor(), conn=connection, get_setting=lambda key, default=None: default)
    page = FieldServicePage(db)
    monkeypatch.setattr(page, "notify", lambda *args: None)
    screenshot = tmp_path / "native_assignment.png"
    def accept_selected(dialog):
        assert isinstance(dialog, ModernDialog)
        picker = dialog.findChild(QListWidget)
        assert picker.count() == 2
        assert dialog.footer_layout.count() == 2
        button = dialog.footer_layout.itemAt(1).widget()
        assert not button.isEnabled()
        picker.setCurrentRow(1)
        assert picker.currentItem().data(Qt.ItemDataRole.UserRole) == 72
        assert button.isEnabled()
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        assert dialog.grab().save(str(screenshot))
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(ModernDialog, "exec", accept_selected)
    page._show_assignment_dialog(40.5, 28.25)
    assert connection.execute("SELECT lat,lng,status FROM personnel WHERE id=72").fetchone() == (40.5, 28.25, "G\u00f6revde")
    assert connection.execute("SELECT lat,lng,status FROM personnel WHERE id=41").fetchone() == (39.0, 27.0, "Bosta")
    assert connection.execute("SELECT lat,lng,status FROM personnel WHERE id=83").fetchone() == (39.2, 27.2, "Bosta")
    assert connection.execute("SELECT last_seen FROM personnel WHERE id=72").fetchone()[0]
    print("Assignment screenshot: " + str(screenshot))
    page.close()
    connection.close()
    app.setFont(original_font)
