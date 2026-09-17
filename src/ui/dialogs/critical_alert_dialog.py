from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QFrame

from src.ui.widgets.modern_dialog import ModernDialog, NoWheelScrollArea
from src.utils.theme_colors import theme_qss


class CriticalAlertDialog(ModernDialog):
    def __init__(self, notifications, parent=None):
        super().__init__(title="Acil Durum Bildirimleri", parent=parent, width=640, height=680)
        self.notifications = notifications
        self.set_footer_visible(False)
        self.setStyleSheet(
            theme_qss(
                """
                QDialog { background-color: @surface_alt; }
                QLabel { color: @danger; }
                """
            )
        )
        self._build_ui()

    def _build_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        icon_lbl = QLabel("Acil")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(theme_qss("font-size: 28px; font-weight: 700;"))
        layout.addWidget(icon_lbl)

        title = QLabel("Dikkat Gerektiren Durumlar")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        sub = QLabel(f"Asagidaki {len(self.notifications)} kritik bildirim incelenmeyi bekliyor.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(theme_qss("background: @surface; border-radius: 8px; border: 1px solid @danger;"))
        content_w = QWidget()
        vbox = QVBoxLayout(content_w)

        for notification in self.notifications:
            frame = QFrame()
            frame.setStyleSheet(
                theme_qss(
                    "background: @surface_alt; border-bottom: 1px solid @border; border-radius: 4px; padding: 5px;"
                )
            )
            fl = QVBoxLayout(frame)
            title_label = QLabel(notification["title"])
            title_label.setStyleSheet(theme_qss("font-weight: bold; color: @danger;"))
            content_label = QLabel(notification["content"])
            content_label.setWordWrap(True)
            fl.addWidget(title_label)
            fl.addWidget(content_label)
            vbox.addWidget(frame)

        vbox.addStretch()
        scroll.setWidget(content_w)
        layout.addWidget(scroll)

        btn_ok = QPushButton("Tamam")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFixedHeight(45)
        btn_ok.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @danger;
                    color: @selection_text;
                    font-weight: bold;
                    border-radius: 8px;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: @danger; }
                """
            )
        )
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)
