import os
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QFileDialog, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.logger import logger
from src.utils.toast_notification import show_error, show_success, show_warning



class VehicleMaintenancePhotoGalleryDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    PHOTO_LABELS = [
        "Yag Filtresi",
        "Hava Filtresi",
        "Eski Parca",
        "Yeni Parca",
        "Genel Gorunum",
    ]

    def __init__(self, db, card_id, title_suffix="", parent=None):
        super().__init__(title=f"Bakim Foto Galerisi - {title_suffix or card_id}", parent=parent, width=960, height=720)
        self.db = db
        self.card_id = int(card_id)
        self.image_rows = []
        self.current_index = 0
        self.set_footer_visible(False)
        self._load_images()
        self._build_ui()

    def _load_images(self):
        self.image_rows = list(self.db.get_vehicle_maintenance_photos(self.card_id) or [])

    def _build_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Bakim Fotograflari")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        self.btn_add = QPushButton("Fotograf Ekle")
        self.btn_add.clicked.connect(self._add_photos)
        self.btn_delete = QPushButton("Seciliyi Sil")
        self.btn_delete.clicked.connect(self._delete_current)
        header.addWidget(self.btn_delete)
        header.addWidget(self.btn_add)
        layout.addLayout(header)

        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("Yeni fotograf etiketi"))
        self.cmb_label = QComboBox()
        self.cmb_label.addItems(self.PHOTO_LABELS)
        label_row.addWidget(self.cmb_label)
        label_row.addStretch()
        layout.addLayout(label_row)

        self.preview_shell = QFrame()
        self.preview_shell.setStyleSheet("background-color: #111827; border-radius: 12px;")
        self.preview_shell.setMinimumHeight(420)
        self.preview_shell.setMaximumHeight(420)
        self.preview_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        preview_layout = QVBoxLayout(self.preview_shell)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        self.display_frame = QLabel()
        self.display_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_frame.setStyleSheet("background: transparent;")
        self.display_frame.setMinimumWidth(0)
        self.display_frame.setMinimumHeight(0)
        self.display_frame.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.display_frame.setScaledContents(False)
        preview_layout.addWidget(self.display_frame)
        layout.addWidget(self.preview_shell)

        bottom = QHBoxLayout()
        self.lbl_caption = QLabel("")
        self.lbl_caption.setWordWrap(True)
        self.lbl_counter = QLabel("0 / 0")
        self.lbl_counter.setFixedWidth(90)
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_prev = QPushButton("Onceki")
        btn_prev.clicked.connect(self._show_prev)
        btn_next = QPushButton("Sonraki")
        btn_next.clicked.connect(self._show_next)
        bottom.addWidget(self.lbl_caption, 1)
        bottom.addWidget(btn_prev)
        bottom.addWidget(self.lbl_counter)
        bottom.addWidget(btn_next)
        layout.addLayout(bottom)

        self._show_image(0)

    def _show_image(self, index):
        if not self.image_rows:
            self.display_frame.setPixmap(QPixmap())
            self.display_frame.setText("Bu bakim karti icin henuz fotograf yok.\nDegisen parcalari veya arac durumunu ekleyebilirsiniz.")
            self.display_frame.setStyleSheet("background: transparent; color: #cbd5e1; font-size: 16px;")
            self.lbl_counter.setText("0 / 0")
            self.lbl_caption.setText("Fotograf aciklamasi yok.")
            return

        index = max(0, min(index, len(self.image_rows) - 1))
        self.current_index = index
        row = self.image_rows[index]
        image_path = row["photo_path"]
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            shell_rect = self.preview_shell.contentsRect().adjusted(8, 8, -8, -8)
            available_size = shell_rect.size()
            if available_size.width() <= 0 or available_size.height() <= 0:
                available_size = self.preview_shell.size()
            self.display_frame.setFixedSize(available_size)
            scaled = pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.display_frame.setPixmap(scaled)
            self.display_frame.setText("")
            self.display_frame.setStyleSheet("background: transparent;")
        else:
            self.display_frame.setPixmap(QPixmap())
            self.display_frame.setText(f"Resim yuklenemedi:\n{image_path}")
        self.lbl_counter.setText(f"{index + 1} / {len(self.image_rows)}")
        self.lbl_caption.setText(row["photo_label"] or os.path.basename(image_path))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_image(self.current_index)

    def _show_prev(self):
        if self.image_rows:
            self._show_image((self.current_index - 1) % len(self.image_rows))

    def _show_next(self):
        if self.image_rows:
            self._show_image((self.current_index + 1) % len(self.image_rows))

    def _add_photos(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Bakim Fotograf Sec",
            "",
            "Resim Dosyalari (*.jpg *.jpeg *.png *.bmp *.webp)",
        )
        if not file_paths:
            return
        target_dir = os.path.join(os.getcwd(), "assets", "maintenance_photos")
        os.makedirs(target_dir, exist_ok=True)
        added_count = 0
        existing_count = len(self.image_rows)
        for offset, source_path in enumerate(file_paths, start=1):
            try:
                ext = os.path.splitext(source_path)[1]
                new_name = f"maintenance_{self.card_id}_{existing_count + offset}{ext}"
                dest_path = os.path.join(target_dir, new_name)
                shutil.copy2(source_path, dest_path)
                label = self.cmb_label.currentText().strip() or f"Bakim Fotograf {existing_count + offset}"
                self.db.add_vehicle_maintenance_photo(self.card_id, dest_path, label)
                added_count += 1
            except Exception as exc:
                logger.error("VehicleMaintenancePhotoGalleryDialog copy error: %s", exc)
        self._load_images()
        if self.image_rows:
            self._show_image(len(self.image_rows) - 1)
        if added_count:
            show_success(self, f"{added_count} fotograf eklendi.")
        else:
            show_warning(self, "Fotograf eklenemedi.")

    def _delete_current(self):
        if not self.image_rows:
            show_warning(self, "Silinecek fotograf yok.")
            return
        row = self.image_rows[self.current_index]
        path = row["photo_path"]
        if not self.db.delete_vehicle_maintenance_photo(row["id"]):
            show_error(self, "Fotograf kaydi silinemedi.")
            return
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as exc:
            logger.error("VehicleMaintenancePhotoGalleryDialog file delete error: %s", exc)
        self._load_images()
        self._show_image(max(0, self.current_index - 1))
        show_success(self, "Fotograf silindi.")


    def _wire_ui_signals(self):
        self.cmb_label.currentIndexChanged.connect(self._on_ui_widget_changed)
