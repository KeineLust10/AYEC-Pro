import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QTabWidget, QWidget
from src.utils._theme_widget_repair import _fix_mojibake_text, repair_widget_texts

APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize("text", [
    "K\u00e2rl\u0131l\u0131k", "K\u00e2r / M\u00fc\u015fteri", "\u00d6deme \u20ac 150",
    "Geli\u015fmi\u015f \u0130\u015f Takibi", "\u00c2det", "\u015eirket - \u00e2lim",
])
def test_valid_unicode_is_never_dropped_by_theme_repair(text):
    assert _fix_mojibake_text(text) == text


def test_reversible_mojibake_is_still_repaired():
    assert _fix_mojibake_text("M\u00c3\u00bcsteri") == "M\u00fcsteri"


def test_widget_repair_preserves_labels_and_navigation():
    text = "K\u00e2rl\u0131l\u0131k"
    label = QLabel(text)
    tabs = QTabWidget()
    tabs.addTab(QWidget(), text)
    repair_widget_texts(label)
    repair_widget_texts(tabs)
    assert label.text() == text
    assert tabs.tabText(0) == text
    label.close()
    tabs.close()
