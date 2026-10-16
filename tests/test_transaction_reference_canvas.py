import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QDate, QEvent, QObject, QPoint, QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFrame, QLabel
from PyQt6.QtGui import QFontMetrics

from src.database import Database
from src.ui.pages.new_transaction_v2_page import NewTransactionV2Page
from src.ui.widgets.transaction_reference_card import TransactionReferenceCard
from src.ui.widgets.financial_reference_controls import FinancialReferenceActionButton, FinancialReferenceIconButton, ReferenceMetricValueLabel
from src.utils.design_system import DesignTokens
from src.utils.theme_manager import ThemeManager


def test_transaction_creation_does_not_show_orphan_labels(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / 'orphan_labels.db'))
    shown_orphans = []

    class ShowObserver(QObject):
        def eventFilter(self, watched, event):
            if event.type() == QEvent.Type.Show and isinstance(watched, QLabel):
                if watched.isWindow() and (
                    watched.text() == 'Musteri secilmedi'
                    or watched.objectName() == 'TransactionCartSubtotal'
                ):
                    shown_orphans.append(watched.objectName() or watched.text())
            return False

    observer = ShowObserver()
    app.installEventFilter(observer)
    monkeypatch.setattr(NewTransactionV2Page, 'update_exchange_rates', lambda self: None)
    settings = QSettings(str(tmp_path / 'orphan_labels.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    app.removeEventFilter(observer)
    try:
        assert not shown_orphans
        assert page.customer_title.parentWidget() is not None
        assert page.lbl_subtotal.parentWidget() is not None
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_offer_composer_reference_density_tracks_viewport_height(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    monkeypatch.setattr(NewTransactionV2Page, 'update_exchange_rates', lambda self: None)
    db = Database(str(tmp_path / 'offer_density.db'))
    settings = QSettings(str(tmp_path / 'offer_density.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1320, 880)
        page.show()
        QTest.qWait(30)
        cart_icon = page.findChild(FinancialReferenceIconButton, 'TransactionCartIcon')
        assert cart_icon is not None and cart_icon.isVisible()
        assert cart_icon.width() == 28
        assert page.customer_panel.height() == 72
        assert page.catalog_search.height() == 32
        assert page.catalog_filter_buttons['all'].height() == 22
        assert page.reference_body_layout.stretch(1) == 28
        assert page.reference_summary_panel.height() == 360

        page.resize(1320, 1226)
        QTest.qWait(30)
        assert page.customer_panel.height() == 198
        assert page.catalog_search.height() == 50
        assert page.catalog_filter_buttons['all'].height() == 32
        assert page.reference_body_layout.stretch(1) == 35
        assert page.reference_summary_panel.minimumHeight() == 430
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_transaction_panels_drafts_and_original_action_connections(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    old_theme = ThemeManager._current_theme
    calls = []
    for method in ('save_transaction', 'save_and_pay', 'create_proforma', 'open_multi_select_v2'):
        monkeypatch.setattr(
            NewTransactionV2Page, method,
            lambda self, checked=False, name=method: calls.append(name),
        )
    monkeypatch.setattr(NewTransactionV2Page, 'update_exchange_rates', lambda self: None)
    db = Database(str(tmp_path / 'cart.db'))
    settings = QSettings(str(tmp_path / 'draft.ini'), QSettings.Format.IniFormat)
    other_settings = QSettings(str(tmp_path / 'other.ini'), QSettings.Format.IniFormat)
    other_settings.setValue(NewTransactionV2Page._DRAFT_KEY, 'untouched')
    page = NewTransactionV2Page(db, draft_settings=settings)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        ThemeManager.apply_theme(app, 'Koyu Mavi', window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page.resize(1320, 1226)
        page.show()
        QTest.qWait(50)
        panels = page.findChildren(QFrame, 'TransactionReferencePanel')
        assert len(panels) == 4
        assert all('border-radius: 6px' in panel.styleSheet() for panel in panels)
        for date, expected_height in ((page.date_edit, 32), (page.date_edit_transaction, 38)):
            assert date.height() == expected_height
            assert date.calendarPopup()
            assert date.displayFormat() == 'dd.MM.yyyy'
            QTest.mouseClick(date, Qt.MouseButton.LeftButton, pos=QPoint(date.width() - 12, date.height() // 2))
            app.processEvents()
            assert date.calendarWidget().isVisible()
            date.calendarWidget().window().hide()
        for combo in (
            page.cmb_customer, page.cmb_currency, page.cmb_service_types,
            page.cmb_product_domain, page.cmb_parts, page.inp_desc, page.cmb_vat,
        ):
            assert combo.property('referenceChevron')
            assert combo.height() >= 36
        assert panels[1].width() > panels[2].width()
        assert page.findChild(QFrame, 'TransactionGrandTotal').height() == 54
        assert not page.findChild(QFrame, 'TransactionLineAmount').isVisible()
        original_total = page.lbl_total.text()
        for amount in ('9,540.00 TRY', '-123,456,789.99 TRY', '1,031.70 USD\n50,554.67 TRY'):
            page.lbl_total.setText(amount)
            first = amount.splitlines()[0]
            font = page.lbl_total.amount_font(first, page.lbl_total.primary_size)
            assert QFontMetrics(font).horizontalAdvance(first) <= page.lbl_total.contentsRect().width()
            assert page.lbl_total.toolTip() == amount
        page.lbl_total.setText(original_total)
        assert page.btn_pay.mapTo(page, page.btn_pay.rect().topLeft()).y() > 850
        assert page.btn_offer.y() < page.btn_proforma.y() < page.btn_pay.y()
        for button, glyph, hint in (
            (page.btn_pay, 'collection', 'F12'),
            (page.btn_proforma, 'pdf', 'F10'),
            (page.btn_account, 'customer', 'F8'),
            (page.btn_offer, 'pdf', 'F5'),
        ):
            assert isinstance(button, FinancialReferenceActionButton)
            assert button.glyph == glyph
            assert button.key_hint == hint
            assert button.centered_inline and not button.stacked
            content_width = button.fontMetrics().horizontalAdvance(button.text()) + 26
            if hint:
                content_width += button.key_hint_width() + 8
            assert content_width + 10 <= button.width()
        for stepper in (page.inp_qty, page.inp_price, page.inp_discount):
            assert stepper.height() == 38
            assert '@' not in stepper.styleSheet()
            for control in (stepper.decrease, stepper.spn_counted, stepper.increase):
                assert stepper.rect().contains(control.geometry())
                assert '@' not in control.styleSheet()
            original = stepper.value()
            QTest.mouseClick(stepper.increase, Qt.MouseButton.LeftButton)
            assert stepper.value() == original + 1
            QTest.mouseClick(stepper.decrease, Qt.MouseButton.LeftButton)
            assert stepper.value() == original
        for button in (page.btn_pay, page.btn_proforma, page.btn_account, page.btn_offer, page.btn_bulk):
            assert button.isVisible()
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert calls == [
            'save_and_pay', 'create_proforma', 'save_transaction',
            'create_proforma', 'open_multi_select_v2',
        ]
        assert all(not button.isVisible() for button in page.reference_command_buttons)
        assert page.btn_save.isVisible() is False
        page._save_reference_draft()
        assert settings.contains(page._DRAFT_KEY)
        assert [
            page.reference_offer_shortcut.key().toString(),
            page.reference_account_shortcut.key().toString(),
            page.reference_proforma_shortcut.key().toString(),
            page.reference_payment_shortcut.key().toString(),
        ] == ['F5', 'F8', 'F10', 'F12']
        page.activateWindow()
        app.setActiveWindow(page)
        page.cmb_customer.setFocus()
        QTest.qWait(20)
        key_calls = len(calls)
        for key in (Qt.Key.Key_F5, Qt.Key.Key_F8, Qt.Key.Key_F10, Qt.Key.Key_F12):
            QTest.keyClick(page.cmb_customer, key)
        assert len(calls) == key_calls + 4, calls[-4:]
        assert calls[-4:] == [
            'create_proforma', 'save_transaction', 'create_proforma', 'save_and_pay',
        ]
        QTest.keyClick(page.catalog_search, Qt.Key.Key_F2)
        assert calls[-1] == 'open_multi_select_v2'
        assert page.btn_add_to_cart.height() == 52
        assert page.btn_add_to_cart.width() >= 180
        assert page.btn_bulk.y() < page.catalog_search.y() + page.catalog_search.height()
        assert page.catalog_tabs.currentIndex() == 0
        assert page.catalog_tabs.isHidden()
        assert page.catalog_details.parentWidget() is not None
        assert page.btn_catalog_details.parentWidget() is not None
        assert not page.btn_catalog_details.isWindow()
        assert page.btn_catalog_details.window() is page.window()
        assert not page.catalog_details.isWindow()
        assert page.catalog_details.windowFlags() & Qt.WindowType.Window == Qt.WindowType.Widget
        page.btn_catalog_details.click()
        app.processEvents()
        assert page.catalog_details.isVisible()
        assert not page.catalog_details.isWindow()
        assert page.catalog_details.geometry().intersects(page.catalog_details.parentWidget().rect())
        assert not page.catalog_cards_scroll.isVisible()
        assert page.toggle_offer_approval.parentWidget().height() <= 44
        page.btn_catalog_details.click()
        app.processEvents()
        assert not page.catalog_details.isVisible()
        assert page.catalog_cards_scroll.isVisible()
        page.catalog_tabs.setCurrentIndex(1)
        assert page.cmb_service_types.isVisible()
        assert not page.cmb_parts.isVisible()
        page.catalog_tabs.setCurrentIndex(0)
        assert not page.catalog_details.isVisible()
        before = db.conn.total_changes
        page.cmb_service_types.addItem('Camera installation', {
            'id': 1, 'name': 'Camera installation', 'type': 'service', 'price': 85,
        })
        page.cmb_service_types.setCurrentIndex(page.cmb_service_types.count() - 1)
        assert page.catalog_tabs.currentIndex() == 1
        assert page.cmb_service_types.isVisible()
        page._last_item_type = 'service'
        page.inp_price.setValue(85)
        page.inp_qty.setValue(4)
        page.inp_desc.setCurrentText('Existing wiring')
        assert '340.00' in page.lbl_line_total.text()
        assert page.lbl_line_total.toolTip() == page.lbl_line_total.text()
        QTest.mouseClick(page.btn_add_to_cart, Qt.MouseButton.LeftButton)
        assert len(page.cart_items) == 1
        assert page.cart_items[0]['price'] == 85
        assert page.cart_items[0]['qty'] == 4
        assert page.cart_table.topLevelItem(0).child(0).data(0, Qt.ItemDataRole.UserRole) == page.cart_items[0]['id']
        assert json.loads(settings.value(page._DRAFT_KEY))['cart_items'] == page.cart_items
        assert '1 kalem' in page.command_context.text()
        assert other_settings.value(page._DRAFT_KEY) == 'untouched'
        app.processEvents()
        card = next(card for card in page.findChildren(TransactionReferenceCard) if card.isVisible())
        assert not page.cart_table.isVisible()
        assert page.cart_scroll.isVisible()
        assert card.title.text() == 'Camera installation'
        assert card.description.text() == 'Existing wiring'
        assert '340.00' in card.amount.text()
        assert '340.00' in page.stat_total.value_label.text()
        assert '408.00' in page.lbl_total.text()
        assert page.stat_vat.value_label.text().startswith('+')
        page.inp_discount.setValue(10)
        assert page.stat_discount.value_label.text().startswith('-')
        assert '330.00' in page.stat_total.value_label.text()
        assert '396.00' in page.lbl_total.text()
        page.inp_discount.setValue(0)
        page.cmb_vat.setCurrentText('%10')
        app.processEvents()
        card = next(card for card in page.findChildren(TransactionReferenceCard) if card.isVisible())
        assert card.kind_label.text() == 'Hizmet'
        assert card.tax.text() == 'KDV: %10'
        assert card.title.textFormat() == Qt.TextFormat.PlainText
        page.cmb_vat.setCurrentText('%20')
        app.processEvents()
        card = next(card for card in page.findChildren(TransactionReferenceCard) if card.isVisible())
        assert card.tax.text() == 'KDV: %20'
        for control in (card.minus, card.plus, card.edit, card.remove, card.amount, card.title):
            assert card.rect().contains(control.geometry())
        assert page.cart_scroll.horizontalScrollBar().maximum() == 0
        QTest.mouseClick(card.plus, Qt.MouseButton.LeftButton)
        assert page.cart_items[0]['qty'] == 5
        assert page.reference_cart_count.text() == '1 Kalem | 5 Adet'
        app.processEvents()
        card = next(card for card in page.findChildren(TransactionReferenceCard) if card.isVisible())
        assert '425.00' in card.amount.text()
        QTest.mouseClick(card.minus, Qt.MouseButton.LeftButton)
        assert page.cart_items[0]['qty'] == 4
        mapped = []
        for method in ('edit_quantity_context', 'edit_price_context', 'add_description_context', 'copy_service_context'):
            monkeypatch.setattr(page, method, lambda checked=False, name=method: mapped.append(
                (name, page.cart_table.currentItem().data(0, Qt.ItemDataRole.UserRole))
            ))
        app.processEvents()
        card = next(card for card in page.findChildren(TransactionReferenceCard) if card.isVisible())
        QTest.mouseClick(card.edit, Qt.MouseButton.LeftButton)
        for action in page._reference_cart_menu.actions():
            action.trigger()
        page._reference_cart_menu.close()
        assert [name for name, _ in mapped] == [
            'edit_quantity_context', 'edit_price_context', 'add_description_context', 'copy_service_context',
        ]
        assert all(item_id == page.cart_items[0]['id'] for _, item_id in mapped)
        monkeypatch.setattr(page, 'on_currency_changed', lambda text: setattr(page, 'current_exchange_rate', 2))
        page.cmb_currency.setCurrentIndex(1)
        app.processEvents()
        card = next(card for card in page.findChildren(TransactionReferenceCard) if card.isVisible())
        assert '170.00' in card.amount.text()
        assert card.try_reference.isVisible()
        assert '340.00' in card.try_reference.text()
        assert not page.stat_subtotal.reference_label.isVisible()
        assert '340.00' in page.stat_subtotal.reference_label.text()
        assert '170.00' in page.stat_total.value_label.text()
        for box in (page.stat_subtotal, page.stat_discount, page.stat_vat, page.stat_total):
            amount = box.value_label
            assert isinstance(amount, ReferenceMetricValueLabel)
            assert amount.primary_size == 15
            font = amount.amount_font(amount.text(), amount.primary_size)
            assert font.family() == DesignTokens.MONO_FONT_NAME
            assert QFontMetrics(font).horizontalAdvance(amount.text()) <= amount.contentsRect().width() - 4
            assert amount.toolTip() == amount.text()
            assert amount.textFormat() == Qt.TextFormat.PlainText
            assert box.reference_label.font().family() == DesignTokens.MONO_FONT_NAME
        assert '204.00' in page.lbl_total.text()
        assert '1 USD = 2.0000 TRY' in page.reference_cart_rate.text()
        subtotal_y = page.lbl_subtotal.mapTo(page, page.lbl_subtotal.rect().topLeft()).y()
        assert 600 < subtotal_y < 750
        assert page.cart_items[0]['price'] == 85
        QTest.mouseClick(card.remove, Qt.MouseButton.LeftButton)
        assert page.cart_items == []
        assert page.reference_cart_count.text() == '0 Kalem | 0 Adet'
        assert page.cart_empty_state.isVisible()
        assert not page.cart_scroll.isVisible()
        assert json.loads(settings.value(page._DRAFT_KEY))['cart_items'] == []
        page._clear_draft()
        assert not settings.contains(page._DRAFT_KEY)
        assert db.conn.total_changes == before
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        ThemeManager.apply_theme(app, old_theme, animate=False)
        db.close()


@pytest.mark.parametrize('key', [Qt.Key.Key_Return, Qt.Key.Key_Enter])
def test_reference_enter_adds_actual_cart_item_without_database_write(monkeypatch, tmp_path, key):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(NewTransactionV2Page, '_deferred_load_exchange_rates', lambda self: None)
    db = Database(str(tmp_path / 'enter_cart.db'))
    settings = QSettings(str(tmp_path / 'enter_cart.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1320, 1226)
        page.show()
        QTest.qWait(50)
        page.cmb_service_types.addItem('Keyboard selected service', {
            'id': 17, 'type': 'service', 'name': 'Keyboard selected service', 'price': 125,
        })
        page.cmb_service_types.setCurrentIndex(page.cmb_service_types.count() - 1)
        page.inp_qty.setValue(3)
        page.inp_price.setValue(125)
        page.activateWindow()
        app.setActiveWindow(page)
        page.inp_qty.spn_counted.setFocus()
        QTest.qWait(20)
        writes = db.conn.total_changes
        QTest.keyClick(page.inp_qty.spn_counted, key)
        assert len(page.cart_items) == 1
        assert page.cart_items[0]['item_id'] == 17
        assert page.cart_items[0]['qty'] == 3
        assert page.cart_items[0]['price'] == 125
        assert json.loads(settings.value(page._DRAFT_KEY))['cart_items'] == page.cart_items
        assert db.conn.total_changes == writes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


@pytest.mark.parametrize('item_type', ['part', 'service'])
def test_catalog_reload_keeps_selected_id_and_user_edits(monkeypatch, tmp_path, item_type):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(NewTransactionV2Page, '_deferred_load_exchange_rates', lambda self: None)
    db = Database(str(tmp_path / 'catalog_reload.db'))
    part_id = db.conn.execute(
        'INSERT INTO parts(name,category,price,currency,stock) VALUES (?,?,?,?,?)',
        ('Security CCTV camera', 'Security', 3740, 'TRY', 12),
    ).lastrowid
    service_id = db.conn.execute(
        'INSERT INTO services(name,price,currency,description) VALUES (?,?,?,?)',
        ('Installation service', 3740, 'TRY', 'Original note'),
    ).lastrowid
    db.conn.execute(
        'INSERT INTO exchange_rates(currency,buying_rate,selling_rate,effective_date,created_at) '
        'VALUES (?,?,?,?,?)', ('USD', 43.98, 44, '2026-10-02', '2026-10-02'),
    )
    db.conn.commit()
    settings = QSettings(str(tmp_path / 'catalog_reload.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    try:
        app.processEvents()
        page.load_services()
        combo = page.cmb_parts if item_type == 'part' else page.cmb_service_types
        selected_id = part_id if item_type == 'part' else service_id
        index = next(i for i in range(combo.count()) if combo.itemData(i)['id'] == selected_id)
        if item_type == 'part':
            page.resize(1280, 1024)
            page.catalog_tabs.setCurrentIndex(0)
            page.show()
            app.processEvents()
            card = page.catalog_cards_layout.itemAt(0).widget()
            card.show()
            page.catalog_cards_layout.activate()
            app.processEvents()
            assert card.accessibleName().startswith('Security CCTV camera')
            assert card.minimumWidth() == 0
            assert card.width() <= page.catalog_cards_scroll.viewport().width()
            card.click()
            assert combo.currentIndex() == index
            assert page.inp_price.value() == 3740
            assert 'Security CCTV camera' in page.inp_desc.currentText()
        else:
            combo.setCurrentIndex(index)
        page.inp_price.setValue(3960)
        page.inp_qty.setValue(3)
        page.inp_desc.setCurrentText('Edited quote note')
        changes = []
        combo.currentIndexChanged.connect(changes.append)
        catalog_rows = {
            table: [tuple(row) for row in db.conn.execute(f'SELECT * FROM {table} ORDER BY id')]
            for table in ('parts', 'services')
        }
        page.cmb_currency.setCurrentIndex(1)
        assert combo.currentData()['id'] == selected_id
        assert page._last_item_type == item_type
        assert changes == []
        assert page.inp_price.value() == 3960
        assert page.inp_price.text() == '90.00'
        assert page.inp_qty.value() == 3
        assert page.inp_desc.currentText() == 'Edited quote note'
        combo.blockSignals(True)
        page.load_services()
        assert combo.signalsBlocked()
        combo.blockSignals(False)
        assert combo.currentData()['id'] == selected_id
        # The existing service schema helper performs normalization UPDATEs.
        # Reloads must preserve catalog values; adding a quote line is read-only.
        assert catalog_rows == {
            table: [tuple(row) for row in db.conn.execute(f'SELECT * FROM {table} ORDER BY id')]
            for table in ('parts', 'services')
        }
        writes = db.conn.total_changes
        page.btn_add_to_cart.click()
        assert page.cart_items[0]['item_id'] == selected_id
        assert page.cart_items[0]['type'] == item_type
        assert page.cart_items[0]['price'] == 3960
        assert page.cart_items[0]['qty'] == 3
        assert page.cart_items[0]['description'] == 'Edited quote note'
        assert db.conn.total_changes == writes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_selected_currency_inputs_keep_original_try_cart_and_discount_contract(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(NewTransactionV2Page, '_deferred_load_exchange_rates', lambda self: None)
    monkeypatch.setattr(NewTransactionV2Page, 'on_currency_changed', lambda self, text: None)
    db = Database(str(tmp_path / 'currency_input.db'))
    settings = QSettings(str(tmp_path / 'currency_input.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    try:
        app.processEvents()
        page.cmb_service_types.addItem('Selected service', {
            'id': 17, 'type': 'service', 'name': 'Selected service', 'price': 3740,
        })
        page.cmb_service_types.setCurrentIndex(page.cmb_service_types.count() - 1)
        page.inp_qty.setValue(2)
        page.inp_discount.setValue(440)
        page.current_exchange_rate = 44
        page.cmb_currency.setCurrentIndex(1)
        page.update_totals()
        assert page.inp_price.text() == '85.00'
        assert page.inp_price.value() == 3740
        assert page.inp_discount.text() == '10.00'
        assert page.inp_discount.value() == 440
        assert '170.00' in page.lbl_line_total.text()
        writes = db.conn.total_changes
        page.inp_price.spn_counted.setText('90.00')
        page.btn_add_to_cart.click()
        assert page.cart_items[0]['price'] == 3960
        assert page.cart_items[0]['qty'] == 2
        assert page.update_totals() == (7920, 440, 1496, 8976, 7480)
        assert '204.00' in page.lbl_total.text()
        assert json.loads(settings.value(page._DRAFT_KEY))['discount_try'] == 440
        assert db.conn.total_changes == writes
        page.cmb_currency.setCurrentIndex(0)
        page.update_totals()
        assert page.inp_discount.text() == '440.00'
        assert page.inp_discount.value() == 440
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_first_customer_preview_uses_real_balance_tax_and_currency(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(NewTransactionV2Page, '_deferred_load_exchange_rates', lambda self: None)
    monkeypatch.setattr(NewTransactionV2Page, 'on_currency_changed', lambda self, text: None)
    db = Database(str(tmp_path / 'customer_preview.db'))
    db.cursor.execute(
        'INSERT INTO customers(name,phone,tax_number,tax_office) VALUES (?,?,?,?)',
        ('First Company', '5550000000', '1234567890', 'Test Office'),
    )
    customer_id = db.cursor.lastrowid
    for currency, amount in (('TRY', 200), ('USD', 50)):
        db.cursor.execute(
            'INSERT INTO currency_transactions(customer_id,transaction_type,amount,currency) VALUES (?,?,?,?)',
            (customer_id, 'DEBIT', amount, currency),
        )
    db.conn.commit()
    settings = QSettings(str(tmp_path / 'customer_preview.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1320, 1226)
        page.show()
        QTest.qWait(50)
        page.load_customers()
        writes = db.conn.total_changes
        page.cmb_customer.setCurrentIndex(0)
        assert page.cmb_customer.currentData() == customer_id
        assert page.customer_preview.isVisible()
        assert page.customer_title.text() == 'First Company'
        assert '1234567890 / Test Office' in page.customer_preview.toolTip()
        assert 'Cari bakiye (TRY): -200.00' in page.customer_preview.text()
        page.cmb_currency.setCurrentIndex(1)
        assert 'Cari bakiye (USD): -50.00' in page.customer_preview.text()
        assert 'First Company' in page.command_context.text()
        page.cmb_customer.setCurrentIndex(-1)
        page._refresh_customer_preview()
        assert not page.customer_preview.isVisible()
        assert db.conn.total_changes == writes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_saved_reference_draft_restores_all_visible_financial_fields(monkeypatch, tmp_path):
    from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(NewTransactionV2Page, '_deferred_load_exchange_rates', lambda self: None)
    monkeypatch.setattr(ModernConfirmDialog, 'exec', lambda self: 1)
    monkeypatch.setattr(NewTransactionV2Page, 'on_currency_changed', lambda self, text: None)
    db = Database(str(tmp_path / 'restore.db'))
    settings = QSettings(str(tmp_path / 'restore.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, draft_settings=settings)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        app.processEvents()
        page.cart_items = [{
            'id': 'saved-1', 'item_id': 1, 'type': 'service', 'service': 'Saved service',
            'description': 'Saved description', 'price': 85.0, 'qty': 4, 'date': '2026-09-30',
        }]
        page.cmb_currency.setCurrentIndex(1)
        page.current_exchange_rate = 2
        page.inp_discount.setValue(10)
        page.cmb_vat.setCurrentText('%10')
        page.date_edit.setDate(QDate(2026, 9, 30))
        page.date_edit_transaction.setDate(QDate(2026, 10, 1))
        page.toggle_offer_approval.setChecked(False)
        page._save_reference_draft()
        stored = json.loads(settings.value(page._DRAFT_KEY))
        assert stored['currency'] == 'USD'
        assert stored['exchange_rate'] == 2
        assert stored['discount_try'] == 10
        assert stored['vat'] == '%10'
        assert stored['include_approval'] is False
        page.cart_items = []
        page.cmb_currency.setCurrentIndex(0)
        page.current_exchange_rate = 1
        page.inp_discount.setValue(0)
        page.cmb_vat.setCurrentText('%20')
        page.date_edit.setDate(QDate(2026, 10, 2))
        page.date_edit_transaction.setDate(QDate(2026, 10, 2))
        page.toggle_offer_approval.setChecked(True)
        writes = db.conn.total_changes
        settings.setValue(page._DRAFT_KEY, json.dumps(stored))
        page._restore_draft()
        assert page.cart_items == stored['cart_items']
        assert page._parse_currency_code(page.cmb_currency.currentText()) == 'USD'
        assert page.current_exchange_rate == 2
        assert page.inp_discount.value() == 10
        assert page.cmb_vat.currentText() == '%10'
        assert page.date_edit.date() == QDate(2026, 9, 30)
        assert page.date_edit_transaction.date() == QDate(2026, 10, 1)
        assert not page.toggle_offer_approval.isChecked()
        assert page.update_totals() == (340, 10, 33, 363, 330)
        assert '165.00' in page.stat_total.value_label.text()
        assert '181.50' in page.lbl_total.text()
        assert db.conn.total_changes == writes
        settings.setValue(page._DRAFT_KEY, json.dumps({
            'customer': '', 'cart_items': stored['cart_items'],
        }))
        page.cart_items = []
        page._restore_draft()
        assert page.cart_items == stored['cart_items']
        assert page.current_exchange_rate == 2
        page.cmb_customer.addItem('Other customer', 999)
        page.cmb_customer.setCurrentIndex(page.cmb_customer.count() - 1)
        page._restore_reference_draft_fields({'customer_id': 123, 'customer': 'Other customer'})
        assert page.cmb_customer.currentData() != 999
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


@pytest.mark.parametrize('sector', ['teknik_servis', 'otomotiv'])
def test_new_customer_command_uses_existing_sector_dialog_and_exact_saved_id(monkeypatch, tmp_path, sector):
    from src.ui.dialogs import automotive_customer_dialog, technical_service_customer_dialog
    from src.utils.system_config import SystemConfig

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(NewTransactionV2Page, '_deferred_load_exchange_rates', lambda self: None)
    monkeypatch.setattr(SystemConfig, 'get_current_sector', lambda db: sector)
    db = Database(str(tmp_path / 'new_customer.db'))
    db.cursor.executemany(
        'INSERT INTO customers(name,phone) VALUES (?,?)',
        [('Original customer', '5550000001'), ('Saved customer', '5550000002')],
    )
    db.conn.commit()
    ids = [row[0] for row in db.cursor.execute('SELECT id FROM customers ORDER BY id').fetchall()]
    refreshed = []
    owner = SimpleNamespace(sector_manager=object(), refresh_loaded_page=refreshed.append)
    settings = QSettings(str(tmp_path / 'new_customer.ini'), QSettings.Format.IniFormat)
    page = NewTransactionV2Page(db, owner, draft_settings=settings)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    accepted = [False]
    dialogs = []

    class ExistingSectorDialog:
        saved_customer_id = ids[1]

        def __init__(self, database, parent, sector_manager=None):
            assert database is db
            assert parent is page
            assert sector_manager is owner.sector_manager
            dialogs.append(sector)

        def exec(self):
            return int(accepted[0])

    target = technical_service_customer_dialog if sector == 'teknik_servis' else automotive_customer_dialog
    name = 'TechnicalServiceCustomerDialog' if sector == 'teknik_servis' else 'AutomotiveCustomerDialog'
    monkeypatch.setattr(target, name, ExistingSectorDialog)
    try:
        page.resize(1320, 1226)
        page.show()
        QTest.qWait(50)
        page.cmb_customer.setCurrentIndex(page.cmb_customer.findData(ids[0]))
        writes = db.conn.total_changes
        QTest.mouseClick(page.btn_new_customer, Qt.MouseButton.LeftButton)
        assert page.cmb_customer.currentData() == ids[0]
        assert not refreshed
        accepted[0] = True
        QTest.mouseClick(page.btn_new_customer, Qt.MouseButton.LeftButton)
        assert page.cmb_customer.currentData() == ids[1]
        assert page.customer_title.text() == 'Saved customer'
        assert 'Saved customer' in page.command_context.text()
        assert refreshed == [40]
        assert dialogs == [sector, sector]
        assert db.conn.total_changes == writes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
