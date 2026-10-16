import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QBoxLayout

from src.database import Database
from src.ui.pages.finance.bank_loans_widget import LoansWidget
from src.utils.theme_manager import ThemeManager


def test_bank_loans_layout_fits_mobile_and_restores_desktop(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "loans_responsive.db"))
    loan_id = db.add_loan(
        bank_name="Reference Bank",
        principal=100000,
        interest_rate=24,
        months=36,
        start_date="2026-07-01",
        loan_title="Reference Contract",
        description="Mobile layout fixture",
        total_payment=115642,
    )
    for installment_no in range(1, 13):
        month_index = 10 + installment_no
        db.add_loan_installment(
            {
                "loan_id": loan_id,
                "installment_no": installment_no,
                "due_date": f"{2026 + month_index // 12:04d}-{month_index % 12 + 1:02d}-01",
                "amount": 3921.47,
            }
        )
    page = LoansWidget(db, None)
    try:
        page.resize(390, 900)
        page.show()
        app.processEvents()

        assert page.width() == 390
        assert page.filters_scroll.width() <= page.width()
        assert page.loan_schedule_panel.width() <= page.width()
        assert page.content_widget.width() <= page.width()
        assert page.content_scroll.verticalScrollBar().maximum() > 0
        assert page.installment_table.rowCount() == 11
        assert page.filters_scroll.height() >= 240
        assert page.contract_layout.direction() == QBoxLayout.Direction.TopToBottom
        assert [page.metrics_layout.getItemPosition(index)[:2] for index in range(4)] == [
            (0, 0), (0, 1), (1, 0), (1, 1)
        ]

        page.resize(1280, 800)
        app.processEvents()

        assert page.width() == 1280
        assert page.filters_scroll.height() == 54
        assert page.contract_layout.direction() == QBoxLayout.Direction.LeftToRight
        assert [page.metrics_layout.getItemPosition(index)[:2] for index in range(4)] == [
            (0, 0), (0, 1), (0, 2), (0, 3)
        ]
    finally:
        page.close()
        db.close()
        app.processEvents()


def test_bank_loan_controls_follow_light_and_dark_theme(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "loans_theme.db"))
    page = LoansWidget(db, None)
    previous_theme = ThemeManager._current_theme
    try:
        page.resize(1280, 800)
        page.show()
        for theme_name in ("AYEC", "Koyu Mavi"):
            ThemeManager.apply_theme(app, theme_name, animate=False)
            page.apply_theme_styles()
            app.processEvents()
            text_color = ThemeManager.get_palette_color(theme_name, "text").lower()
            window_color = ThemeManager.get_palette_color(theme_name, "window").lower()
            assert text_color in page.loan_search.styleSheet().lower()
            assert text_color in page.installment_table.styleSheet().lower()
            assert window_color in page.installment_table.styleSheet().lower()
            assert "@text" not in page.installment_table.styleSheet()
            assert "@surface" not in page.loan_search.styleSheet()
    finally:
        ThemeManager.apply_theme(app, previous_theme, animate=False)
        page.close()
        db.close()
        app.processEvents()
