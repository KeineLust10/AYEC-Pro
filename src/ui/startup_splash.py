"""Animated startup window for AYEC Pro."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget

from src.utils.path_helper import PathHelper


class StartupSplash(QWidget):
    """Show startup phases while the desktop application prepares."""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(460, 390)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(
            "QWidget { background: #101827; color: #eef4ff; }"
            "QLabel#brand { color: #f5f8ff; font-size: 25px; font-weight: 700; }"
            "QLabel#phase { color: #b9c7dc; font-size: 13px; }"
            "QLabel#hint { color: #73839c; font-size: 10px; }"
            "QProgressBar { background: #1b2b40; border: 0; height: 4px; }"
            "QProgressBar::chunk { background: #38bdf8; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(10)
        layout.addStretch(1)

        self.animation = QLabel(self)
        self.animation.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.animation.setFixedSize(220, 220)
        layout.addWidget(self.animation, 0, Qt.AlignmentFlag.AlignHCenter)

        self._movie = None
        animation_path = PathHelper.get_resource_path(
            os.path.join("assets", "startup_loading.gif")
        )
        if os.path.isfile(animation_path):
            self._movie = QMovie(animation_path)
            self._movie.setScaledSize(self.animation.size())
            self.animation.setMovie(self._movie)
            self._movie.start()
        else:
            icon_path = PathHelper.get_resource_path(
                os.path.join("assets", "app_icon.png")
            )
            self.animation.setPixmap(QPixmap(icon_path).scaled(
                160,
                160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

        self.brand = QLabel("AYEC Pro", self)
        self.brand.setObjectName("brand")
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.brand)

        self.phase = QLabel("Program baslatiliyor...", self)
        self.phase.setObjectName("phase")
        self.phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phase.setMinimumHeight(24)
        layout.addWidget(self.phase)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        layout.addStretch(1)

        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())

    def set_phase(self, message):
        self.phase.setText(str(message or ""))
        self.phase.repaint()
        QApplication.processEvents()

    def stop_animation(self):
        if self._movie is not None:
            self._movie.stop()
