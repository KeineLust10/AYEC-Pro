# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, 
                             QFormLayout, QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, 
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, 
                             QSpinBox, QScrollArea, QToolButton, QAbstractItemView, QMenu, 
                             QGridLayout, QInputDialog, QProgressDialog, QApplication)
from PyQt6.QtCore import Qt, QDate, QEvent, QTimer
from PyQt6.QtGui import QColor, QFont, QAction
import json
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error
from src.utils.language_manager import LanguageManager
from src.ui.dialogs.base_modern_dialog import BaseModernDialog


class AddUnitDialog(BaseModernDialog):
    """Akıllı ev projesi için basit blok/daire ekleme dialogu."""
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent, title="🏠 Blok ve Daire Oluştur", width=560, height=420)
        self.db = db
        self.project_id = project_id
        self.setup_unit_ui()

    def setup_unit_ui(self):
        content = self.content_layout
        content.setSpacing(14)

        header_lbl = QLabel("🏠 Blok / Daire Yapısı Oluştur")
        header_lbl.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text;"))
        content.addWidget(header_lbl)

        form = QFormLayout()
        form.setSpacing(12)

        spin_qss = theme_qss(
            DesignTokens.get_input_qss() + """
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                background: @surface_alt;
                border-left: 1px solid @border;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: @border;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            """
        )

        # Blok sayısı
        self.spin_block_count = QSpinBox()
        self.spin_block_count.setRange(1, 26)
        self.spin_block_count.setValue(1)
        self.spin_block_count.setFixedHeight(36)
        self.spin_block_count.setStyleSheet(spin_qss)
        form.addRow("Blok Sayısı:", self.spin_block_count)

        # Her blokta kaç daire
        self.spin_unit_count = QSpinBox()
        self.spin_unit_count.setRange(1, 200)
        self.spin_unit_count.setValue(5)
        self.spin_unit_count.setFixedHeight(36)
        self.spin_unit_count.setStyleSheet(spin_qss)
        form.addRow("Her Blokta Daire Sayısı:", self.spin_unit_count)

        # Adlandırma
        self.cmb_naming = QComboBox()
        self.cmb_naming.addItems(["Harfli (A, B, C)", "Sayılı (1, 2, 3)", "Özel"])
        self.cmb_naming.setFixedHeight(36)
        self.cmb_naming.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        form.addRow("Blok Adlandırma:", self.cmb_naming)

        # Özel adlar
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("Örn: A Blok,B Blok,C Blok")
        self.txt_custom.setFixedHeight(36)
        self.txt_custom.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.txt_custom.setVisible(False)
        form.addRow("Özel Adlar (virgülle):", self.txt_custom)

        content.addLayout(form)

        # Önizleme
        self.lbl_preview = QLabel()
        self.lbl_preview.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        self.lbl_preview.setWordWrap(True)
        content.addWidget(self.lbl_preview)

        content.addStretch()

        # Butonlar
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("✅ Oluştur")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_save.clicked.connect(self.save)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        content.addLayout(btn_row)

        # Bağlantılar
        self.cmb_naming.currentIndexChanged.connect(self._on_naming_changed)
        self.spin_block_count.valueChanged.connect(self._update_preview)
        self.spin_unit_count.valueChanged.connect(self._update_preview)
        self.cmb_naming.currentIndexChanged.connect(self._update_preview)
        self.txt_custom.textChanged.connect(self._update_preview)
        self._update_preview()

    def _on_naming_changed(self):
        self.txt_custom.setVisible(self.cmb_naming.currentText() == "Özel")
        self._update_preview()

    def _get_block_names(self):
        count = self.spin_block_count.value()
        naming = self.cmb_naming.currentText()
        if naming.startswith("Harfli"):
            return [chr(ord('A') + i) for i in range(count)]
        elif naming.startswith("Sayılı"):
            return [str(i + 1) for i in range(count)]
        else:
            custom = [n.strip() for n in self.txt_custom.text().split(",") if n.strip()]
            while len(custom) < count:
                custom.append(f"Blok{len(custom) + 1}")
            return custom[:count]

    def _update_preview(self):
        names = self._get_block_names()
        unit_count = self.spin_unit_count.value()
        sample = [f"{n}: {unit_count} daire" for n in names[:4]]
        if len(names) > 4:
            sample.append(f"...+{len(names) - 4} blok")
        total = len(names) * unit_count
        self.lbl_preview.setText("Önizleme: " + ",  ".join(sample) + f"  →  Toplam {total} daire")

    def save(self):
        block_names = self._get_block_names()
        unit_count = self.spin_unit_count.value()
        created = 0
        for block in block_names:
            for i in range(unit_count):
                unit_no = f"{block}-{i + 1}"
                data = {
                    'project_id': self.project_id,
                    'block_name': block,
                    'floor_no': '0',
                    'unit_no': unit_no,
                    'status': 'Bekliyor',
                    'price': 0,
                    'unit_type': '',
                    'area': 0,
                    'unit_price': 0,
                    'total_price': 0,
                    'description': '',
                    'parent_unit_id': None,
                    'unit_kind': 'Daire',
                }
                self.db.add_project_unit(data)
                created += 1
        show_success(self.parent(), f"{created} daire oluşturuldu.")
        self.accept()

class AddSubDialog(BaseModernDialog):
    """Ekip üyesi / taşeron ekleme dialogu — akıllı ev odaklı."""
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent, title="👥 Ekip Üyesi Ekle", width=440, height=500)
        self.db = db
        self.project_id = project_id
        self.setup_sub_ui()

    def setup_sub_ui(self):
        content = self.content_layout
        content.setSpacing(12)

        header_lbl = QLabel("👥 Yeni Ekip Üyesi / Taşeron")
        header_lbl.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text;"))
        content.addWidget(header_lbl)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet(theme_qss("color: @text_muted; font-weight: bold; font-size: 11px;"))
            return l

        def _inp(placeholder=""):
            i = QLineEdit()
            i.setPlaceholderText(placeholder)
            i.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            i.setFixedHeight(40)
            return i

        # Ad Soyad / Firma
        content.addWidget(_lbl("Ad Soyad / Firma Adı *"))
        self.txt_name = _inp("Örn. Ahmet Yılmaz veya TechEv Çözümleri")
        content.addWidget(self.txt_name)

        # Uzmanlık alanı (combobox, düzenlenebilir)
        content.addWidget(_lbl("Uzmanlık Alanı"))
        self.cmb_job = QComboBox()
        self.cmb_job.setEditable(True)
        self.cmb_job.addItems([
            "Elektrik Tesisatı",
            "Ağ / IT Altyapısı",
            "Akıllı Ev Yazılımı",
            "Güvenlik Sistemleri",
            "Ses / Görüntü Sistemleri",
            "Mekanik / HVAC",
            "Aydınlatma Kontrolü",
            "Genel İşçilik",
        ])
        self.cmb_job.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.cmb_job.setFixedHeight(40)
        content.addWidget(self.cmb_job)

        # Ücret
        content.addWidget(_lbl("Ücret (TL) — opsiyonel"))
        self.spin_total = QDoubleSpinBox()
        self.spin_total.setRange(0, 100_000_000)
        self.spin_total.setSuffix(" TL")
        self.spin_total.setDecimals(2)
        self.spin_total.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.spin_total.setFixedHeight(40)
        content.addWidget(self.spin_total)

        # İletişim
        content.addWidget(_lbl("İletişim (telefon / e-posta)"))
        self.txt_contact = _inp("Örn. 05xx xxx xx xx veya ornek@mail.com")
        content.addWidget(self.txt_contact)

        content.addStretch()

        # Butonlar
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("👥 Ekip Üyesini Kaydet")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success")))
        btn_save.clicked.connect(self.save)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        content.addLayout(btn_row)

    def save(self):
        if not self.txt_name.text().strip():
            from src.utils.toast_notification import show_error
            show_error(self.parent(), "Ad / Firma alanı zorunludur.")
            return
        data = {
            'project_id': self.project_id,
            'name': self.txt_name.text().strip(),
            'job_type': self.cmb_job.currentText().strip(),
            'total_contract_amount': self.spin_total.value(),
            'contact_info': self.txt_contact.text().strip()
        }
        self.db.add_subcontractor(data)
        self.accept()

    def _wire_ui_signals(self):
        self.cmb_job.currentIndexChanged.connect(self._update_preview)
