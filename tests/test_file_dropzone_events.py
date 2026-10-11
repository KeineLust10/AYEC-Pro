from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMenu

from src.ui.pages.appointments_page import CalendarTable
from src.ui.dialogs.loan_wizard_steps.step3_document_upload import DropZoneWidget
from src.ui.widgets.kanban_board import KanbanCard, KanbanColumn


class _DropMimeData:
    def __init__(self, urls=None, text=None):
        self._urls = urls or []
        self._text = text

    def hasUrls(self):
        return bool(self._urls)

    def hasText(self):
        return self._text is not None

    def text(self):
        return self._text or ""

    def urls(self):
        return self._urls


class _DropEvent:
    def __init__(self, urls=None, text=None, position=None):
        self._mime = _DropMimeData(urls, text)
        self._position = position
        self.accepted = False
        self.ignored = False

    def mimeData(self):
        return self._mime

    def position(self):
        return self._position

    def acceptProposedAction(self):
        self.accepted = True
        self.ignored = False

    def ignore(self):
        self.ignored = True
        self.accepted = False


def test_file_dropzone_accepts_local_files_and_emits_them(tmp_path):
    app = QApplication.instance() or QApplication([])
    zone = DropZoneWidget("Upload", "Drop a file")
    zone.show()
    app.processEvents()
    source = QUrl.fromLocalFile(str(tmp_path / "invoice.pdf")).toLocalFile()
    event = _DropEvent([QUrl.fromLocalFile(source)])
    entered_stylesheet = zone.styleSheet()
    received = []
    zone.filesDropped.connect(received.append)

    try:
        zone.dragEnterEvent(event)
        assert event.accepted
        assert zone.styleSheet() != entered_stylesheet

        drop = _DropEvent([QUrl.fromLocalFile(source)])
        zone.dropEvent(drop)
        assert drop.accepted
        assert received == [[source]]
        assert not zone._drop_active
    finally:
        zone.close()
        zone.deleteLater()
        app.processEvents()


def test_file_dropzone_rejects_nonlocal_urls():
    app = QApplication.instance() or QApplication([])
    zone = DropZoneWidget("Upload", "Drop a file")
    event = _DropEvent([QUrl("https://example.invalid/file.pdf")])
    received = []
    zone.filesDropped.connect(received.append)

    zone.dropEvent(event)

    assert event.ignored
    assert not received
    zone.deleteLater()
    app.processEvents()


def test_calendar_table_drag_and_drop_maps_numeric_service_to_cell():
    from PyQt6.QtCore import QPointF

    app = QApplication.instance() or QApplication([])
    table = CalendarTable()
    table.setColumnCount(3)
    table.setRowCount(1)
    table.resize(360, 160)
    table.show()
    app.processEvents()
    event = _DropEvent(text="42", position=QPointF(180, 60))
    received = []
    table.itemDropped.connect(lambda *values: received.append(values))

    table.dragEnterEvent(event)
    assert event.accepted
    table.dropEvent(event)

    assert event.accepted
    assert received == [(42, 0, 1)]
    table.close()
    table.deleteLater()
    app.processEvents()


def test_kanban_column_rejects_empty_drop_payload():
    app = QApplication.instance() or QApplication([])
    column = KanbanColumn("Repair", "Tamir", "#2563eb")
    event = _DropEvent(text="")
    received = []
    column.card_dropped.connect(lambda *values: received.append(values))

    column.dropEvent(event)

    assert event.ignored
    assert not received
    column.deleteLater()
    app.processEvents()


def test_kanban_card_right_click_actions_keep_tracking_identity(monkeypatch):
    app = QApplication.instance() or QApplication([])
    card = KanbanCard({"tracking_no": "SRV-0042", "status": "Tamirde"})
    card.resize(280, 190)
    card.show()
    app.processEvents()
    menus = []
    calls = []
    card.clicked.connect(lambda tracking: calls.append(("view", tracking)))
    card.action_triggered.connect(lambda action, tracking: calls.append((action, tracking)))
    monkeypatch.setattr(QMenu, "exec", lambda menu, *_args: menus.append(menu))

    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse,
        QPoint(8, 8),
        card.mapToGlobal(QPoint(8, 8)),
    )
    QApplication.sendEvent(card, event)
    assert len(menus) == 1
    actions = menus[0].actions()
    assert len(actions) == 8
    actions[0].trigger()
    actions[1].menu().actions()[1].trigger()
    actions[3].trigger()
    assert calls == [
        ("view", "SRV-0042"),
        ("update_status:Tamirde", "SRV-0042"),
        ("print_barcode", "SRV-0042"),
    ]
    card.close()
    card.deleteLater()
    app.processEvents()
