# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.navigation_config import (
    MODULE_REQUIREMENTS as NAV_MODULE_REQUIREMENTS,
    PAGE_LABELS as NAV_PAGE_LABELS,
    get_menu_sections,
)
from src.utils.page_config import PAGE_MAPPING
from src.utils.sector_config import SECTOR_PAGES, SectorType, get_sector_manager
from src.utils.system_config import SystemConfig
from src.utils.theme_colors import tc, theme_qss


PAGE_LABELS = {
    40: "Genel Bakış",
    41: "Durum Paneli",
    60: "Ara\u00e7 Par\u00e7a Sto\u011fu",
    62: "Teknisyen Paneli",
    61: "Saha Haritası",
    30: "Randevular",
    65: "Lojistik & Garanti Yönetimi",
    201: "İş / Servis Takibi Raporları",
    170: "AI Asistan",
    21: "Müşteri Listesi",
    25: "Sözleşmeler",
    90: "Hatırlatıcılar",
    120: "Duyurular",
    26: "Çalışma Ortakları",
    50: "Stok Yönetimi",
    140: "Hizmet Tanımları",
    66: "Emanet (Konsinye) Cihazlar",
    145: "Cihaz Bilgisi & Markalar",
    146: "\u00dcr\u00fcn Grubu Y\u00f6netimi",
    147: "Rapor C\u00fcmle Kal\u0131plar\u0131",
    150: "Sales Hub",
    250: "Mobil Stok",
    300: "PC Builder",
    200: "Proje Yönetimi",
    202: "Proje Arşivi",
    101: "Gelir / Gider",
    105: "Banka Hesapları",
    106: "Çek / Senet",
    115: "E-Fatura",
    10: "Personel",
    160: "Bilgi Bankası",
    130: "Ayarlar",
    135: "Log Kayıtları",
    180: "Yedekleme",
    70: "Destek",
    261: "Kullanım Kılavuzu",
    210: "Araç Bakım Takibi",
}


MODULE_REQUIREMENTS = {
    10: "personnel",
    21: "crm",
    25: "crm",
    26: "crm",
    30: "operations",
    41: "operations",
    50: "stock",
    60: "operations",
    61: "operations",
    65: "operations",
    66: "stock",
    90: "crm",
    101: "finance",
    105: "finance",
    106: "finance",
    115: "finance",
    120: "crm",
    140: "stock",
    145: "stock",
    146: "stock",
    147: "stock",
    150: "stock",
    170: "asistan",
    200: "projects",
    201: "operations",
    202: "projects",
    210: "operations",
    250: "stock",
    300: "stock",
}

PAGE_LABELS = NAV_PAGE_LABELS
MODULE_REQUIREMENTS = NAV_MODULE_REQUIREMENTS


class PageLayoutEditorWidget(QWidget):
    layout_updated = pyqtSignal()

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.db = main_window.db if main_window else None
        self.sector_manager = get_sector_manager(self.db) if self.db else None
        self.toggles = {}
        self.labels = {}
        self._apply_sector_labels()
        self.init_ui()
        self.set_current_page()

    def _apply_sector_labels(self):
        try:
            sector = SystemConfig.get_current_sector(self.db) if self.db else "teknik_servis"
        except Exception:
            sector = "teknik_servis"
        PAGE_LABELS[50] = "Yedek Par\u00e7a" if sector == "otomotiv" else "Stok Y\u00f6netimi"
        PAGE_LABELS[60] = "Yedek Par\u00e7a"
        PAGE_LABELS[140] = "\u0130\u015f\u00e7ilik Ekle"

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(10)

        self.btn_guide_toggle = QPushButton("AYEC Pro Arayüz Düzenleme Rehberi")
        self.btn_guide_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guide_toggle.setCheckable(True)
        self.btn_guide_toggle.clicked.connect(self.toggle_guide)
        self.btn_guide_toggle.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @surface_alt;
                    color: @text;
                    text-align: left;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                    border: 1px solid @border;
                }
                QPushButton:hover { background-color: @surface; border-color: @accent_hover; }
                QPushButton:checked {
                    background-color: @selection_bg;
                    color: @selection_text;
                    border-color: @accent;
                    border-bottom-left-radius: 0;
                    border-bottom-right-radius: 0;
                }
                """
            )
        )
        self.main_layout.addWidget(self.btn_guide_toggle)

        self.guide_box = QFrame()
        self.guide_box.setVisible(False)
        self.guide_box.setStyleSheet(
            theme_qss(
                """
                QFrame {
                    background-color: @surface_alt;
                    border: 1px solid @border;
                    border-top: none;
                    border-bottom-left-radius: 6px;
                    border-bottom-right-radius: 6px;
                }
                """
            )
        )
        guide_layout = QVBoxLayout(self.guide_box)
        guide_layout.setContentsMargins(12, 8, 12, 10)
        lbl_guide = QLabel(
            "Bu panel menü görünürlüğü ve menü adı ayarlarını yönetir.\n"
            "• Aktif Sektör Menüleri: Toggle düğmesi ile gösterilebilir/gizlenebilir.\n"
            "• Pasif (Sektör Dışı) Menüler: Pasif renkte kilitli görünür."
        )
        lbl_guide.setWordWrap(True)
        lbl_guide.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        guide_layout.addWidget(lbl_guide)
        self.main_layout.addWidget(self.guide_box)

        lbl_section = QLabel("Menü Bileşenleri")
        lbl_section.setStyleSheet(theme_qss("font-weight: 800; color: @text; font-size: 13px;"))
        self.main_layout.addWidget(lbl_section)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 8, 0, 0)
        self.btn_reset = QPushButton("Varsayılana Dön")
        self.btn_reset.setFixedHeight(38)
        self.btn_reset.clicked.connect(self.reset_to_default)
        self.btn_reset.setStyleSheet(theme_qss("QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:6px;font-weight:700;font-size:12px;}"))
        self.btn_apply = QPushButton("Değişiklikleri Uygula")
        self.btn_apply.setFixedHeight(38)
        self.btn_apply.clicked.connect(self.save_layout)
        self.btn_apply.setStyleSheet(theme_qss("QPushButton{background:@accent;color:@selection_text;border-radius:6px;font-weight:700;font-size:12px;}"))
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_apply)
        self.main_layout.addLayout(btn_layout)

    def toggle_guide(self):
        self.guide_box.setVisible(self.btn_guide_toggle.isChecked())

    def _is_page_enabled_by_module(self, page_id):
        module_name = MODULE_REQUIREMENTS.get(int(page_id))
        if not module_name or not self.db:
            return True
        return SystemConfig.is_module_active(self.db, module_name)

    def _visible_groups(self):
        try:
            sector = SystemConfig.get_current_sector(self.db) if self.db else "teknik_servis"
        except Exception:
            sector = "teknik_servis"
        groups = get_menu_sections(sector)

        normalized = []
        for title, page_ids in groups:
            valid = [
                pid for pid in page_ids 
                if self._is_page_enabled_by_module(pid)
            ]
            if valid:
                normalized.append((title, valid))
        return normalized

    def set_current_page(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.toggles = {}
        self.labels = {}

        try:
            sector_str = SystemConfig.get_current_sector(self.db) if self.db else "teknik_servis"
        except Exception:
            sector_str = "teknik_servis"

        try:
            sector_enum = SectorType(sector_str)
            allowed_sector_pages = SECTOR_PAGES.get(sector_enum, SECTOR_PAGES[SectorType.TEKNIK_SERVIS])
        except Exception:
            allowed_sector_pages = None

        for section_title, page_ids in self._visible_groups():
            self.add_section_header(section_title)
            for page_id in page_ids:
                is_sector_supported = (allowed_sector_pages is None) or (page_id in allowed_sector_pages)
                self.add_toggle_item(
                    page_id, 
                    PAGE_LABELS.get(page_id, f"Sayfa {page_id}"),
                    is_sector_supported=is_sector_supported
                )

    def add_section_header(self, title):
        lbl = QLabel(title)
        lbl.setStyleSheet(theme_qss("color: @disabled_text; font-weight: 800; font-size: 11px; margin-top: 6px; margin-bottom: 2px;"))
        self.list_layout.addWidget(lbl)

    def add_toggle_item(self, page_id, default_name, is_sector_supported=True):
        row = QFrame()
        row.setFixedHeight(36)
        
        custom_name = self.db.get_internal_setting(f"menu_label_page_{page_id}", "") if self.db else ""
        effective_name = custom_name.strip() or default_name

        if is_sector_supported:
            row.setStyleSheet(theme_qss("background: @surface; border-radius: 6px; border: 1px solid @border;"))
            lbl_text = effective_name
        else:
            row.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 6px; border: 1px solid @border; opacity: 0.65;"))
            lbl_text = f"{effective_name}  (Pasif - Sektör Dışı)"

        h = QHBoxLayout(row)
        h.setContentsMargins(10, 2, 8, 2)

        lbl = QLabel(lbl_text)
        if is_sector_supported:
            lbl.setStyleSheet(theme_qss("border: none; color: @text; font-weight: 600; font-size: 12px;"))
        else:
            lbl.setStyleSheet(theme_qss("border: none; color: @disabled_text; font-weight: 500; font-size: 12px;"))

        btn_rename = QPushButton("Adı Düzenle")
        btn_rename.setFixedHeight(24)
        btn_rename.setEnabled(is_sector_supported)
        if is_sector_supported:
            btn_rename.setStyleSheet(theme_qss("QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:4px;padding:0 8px;font-size:11px;font-weight:700;}"))
        else:
            btn_rename.setStyleSheet(theme_qss("QPushButton{background:transparent;color:@disabled_text;border:1px solid @border;border-radius:4px;padding:0 8px;font-size:11px;}"))

        btn_rename.clicked.connect(
            lambda checked=False, pid=page_id, dname=default_name, label_widget=lbl: self.rename_menu_item(pid, dname, label_widget)
        )

        toggle = AnimatedToggle(active_color=tc("success"))
        toggle.setFixedHeight(22)

        if is_sector_supported:
            state = self.db.get_internal_setting(f"menu_visible_page_{page_id}", "1") if self.db else "1"
            toggle.setChecked(state == "1")
            toggle.setEnabled(True)
            self.toggles[int(page_id)] = toggle
            self.labels[int(page_id)] = (lbl, default_name)
        else:
            toggle.setChecked(False)
            toggle.setEnabled(False)

        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(btn_rename)
        h.addWidget(toggle)
        self.list_layout.addWidget(row)

    def rename_menu_item(self, page_id, default_name, label_widget):
        if not self.db:
            return
        current = self.db.get_internal_setting(f"menu_label_page_{page_id}", "") or ""
        value, ok = QInputDialog.getText(self, "Menü Adını Düzenle", f"Sayfa {page_id} menüsü:", text=current or default_name)
        if not ok:
            return
        new_name = (value or "").strip()
        if new_name == default_name:
            new_name = ""
        self.db.set_internal_setting(f"menu_label_page_{page_id}", new_name)
        label_widget.setText(new_name or default_name)
        if self.main_window and hasattr(self.main_window, "refresh_side_menu"):
            self.main_window.refresh_side_menu()
            self.layout_updated.emit()

    def save_layout(self):
        if not self.db:
            return
        changes = False
        for page_id, toggle in self.toggles.items():
            key = f"menu_visible_page_{page_id}"
            value = "1" if toggle.isChecked() else "0"
            old_value = self.db.get_internal_setting(key, "1")
            if value != old_value:
                self.db.set_internal_setting(key, value)
                changes = True

        if self.main_window and hasattr(self.main_window, "refresh_side_menu"):
            self.main_window.refresh_side_menu()
            self.layout_updated.emit()

        if self.main_window and hasattr(self.main_window, "show_notification"):
            msg = "Menü görünürlüğü güncellendi." if changes else "Menü ayarları kaydedildi."
            self.main_window.show_notification(msg, "success")

    def reset_to_default(self):
        if self.db:
            for page_id in self.toggles.keys():
                self.db.set_internal_setting(f"menu_label_page_{page_id}", "")
        for page_id, toggle in self.toggles.items():
            toggle.setChecked(True)
            if page_id in self.labels:
                label_widget, default_name = self.labels[page_id]
                label_widget.setText(default_name)
        self.save_layout()
