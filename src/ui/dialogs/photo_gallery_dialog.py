import os
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.logger import logger
from src.utils.toast_notification import show_error, show_success


class PhotoGalleryDialog(ModernDialog):
    def __init__(self, db, tracking_no, parent=None, read_only=False, stage=None, *args, **kwargs):
        if isinstance(db, str) and not isinstance(tracking_no, str):
            db, tracking_no = tracking_no, db
        super().__init__(title=f"Fotograf Galerisi - {tracking_no}", parent=parent, width=900, height=700)
        self.db = db
        self.tracking_no = tracking_no
        self.read_only = bool(read_only)
        self.stage = stage
        self.image_paths = []
        self.current_index = 0
        self.set_footer_visible(False)
        self.load_images_from_db()
        self.init_ui()

    def load_images_from_db(self):
        try:
            self.image_paths = []
            rows = []
            if hasattr(self.db, "get_photos"):
                rows = self.db.get_photos(self.tracking_no, self.stage) or []
                if not rows:
                    rows = self.db.get_photos(self.tracking_no) or []
            for row in rows:
                path = row[1] if len(row) > 1 else ""
                if path and os.path.exists(path) and path not in self.image_paths:
                    self.image_paths.append(path)
        except Exception as exc:
            logger.error("PhotoGalleryDialog image load error: %s", exc)

    def init_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel(f"Cihaz Fotograflari (#{self.tracking_no})")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        if not self.read_only:
            btn_add = QPushButton("Fotograf Ekle")
            btn_add.clicked.connect(self.add_photo_dialog)
            header_layout.addWidget(btn_add)
        layout.addLayout(header_layout)

        self.display_frame = QLabel()
        self.display_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_frame.setStyleSheet("background-color: #1E293B; border-radius: 10px;")
        self.display_frame.setMinimumHeight(450)
        layout.addWidget(self.display_frame, 1)

        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_prev = QPushButton("Onceki")
        btn_prev.clicked.connect(self.show_prev)
        self.lbl_counter = QLabel("0 / 0")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_counter.setFixedWidth(80)
        btn_next = QPushButton("Sonraki")
        btn_next.clicked.connect(self.show_next)
        controls_layout.addWidget(btn_prev)
        controls_layout.addWidget(self.lbl_counter)
        controls_layout.addWidget(btn_next)
        layout.addLayout(controls_layout)

        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        btn_close = QPushButton("Kaydet ve Kapat" if not self.read_only else "Kapat")
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)
        layout.addLayout(footer_layout)
        self.show_image(0)

    def show_image(self, index):
        if not self.image_paths:
            self.display_frame.setText("Bu kayit icin fotograf bulunamadi.")
            self.display_frame.setStyleSheet("background-color: #E2E8F0; color: #64748B; font-size: 16px; border-radius: 10px;")
            self.lbl_counter.setText("0 / 0")
            return
        index = max(0, min(index, len(self.image_paths) - 1))
        self.current_index = index
        pixmap = QPixmap(self.image_paths[index])
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.display_frame.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.display_frame.setPixmap(scaled_pixmap)
            self.display_frame.setStyleSheet("background-color: #1E293B; border-radius: 10px;")
        else:
            self.display_frame.setText(f"Resim yuklenemedi:\n{self.image_paths[index]}")
        self.lbl_counter.setText(f"{index + 1} / {len(self.image_paths)}")

    def show_prev(self):
        if self.image_paths:
            self.show_image((self.current_index - 1) % len(self.image_paths))

    def show_next(self):
        if self.image_paths:
            self.show_image((self.current_index + 1) % len(self.image_paths))

    def add_photo_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Fotograf Sec", "", "Resim Dosyalari (*.jpg *.jpeg *.png *.bmp)")
        if not file_paths:
            return
        target_dir = os.path.join(os.getcwd(), "assets", "device_photos")
        os.makedirs(target_dir, exist_ok=True)
        added_paths = []
        for fp in file_paths:
            try:
                ext = os.path.splitext(fp)[1]
                new_filename = f"{self.tracking_no}_{len(self.image_paths) + len(added_paths) + 1}{ext}"
                dest = os.path.join(target_dir, new_filename)
                shutil.copy2(fp, dest)
                added_paths.append(dest)
            except Exception as exc:
                logger.error("PhotoGalleryDialog copy error: %s", exc)
        try:
            if not hasattr(self.db, "add_photo"):
                raise AttributeError("db add_photo unavailable")
            for path in added_paths:
                self.db.add_photo(self.tracking_no, path, "", self.stage or "İşlem")
            self.load_images_from_db()
            self.show_image(len(self.image_paths) - 1)
            show_success(self, f"{len(added_paths)} fotograf eklendi.")
        except Exception as exc:
            show_error(self, f"Veritabani guncellenemedi: {exc}")
