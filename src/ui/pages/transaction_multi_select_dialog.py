from PyQt6.QtWidgets import QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss
from src.ui.widgets.modern_dialog import ModernDialog


class MultiSelectServiceDialog(ModernDialog):
    """Dialog for selecting multiple services at once."""
    def __init__(self, parent, services_data):
        super().__init__(title="Toplu Hizmet Secimi", parent=parent, width=500, height=600)
        self.services_data = services_data
        self.set_footer_visible(False)
        self.setStyleSheet(theme_qss("""
            QDialog { background: @background; }
            QLabel { color: @text; }
            QLineEdit { background: @surface; color: @text; border: 1px solid @border; border-radius: 8px; padding: 8px; }
            QListWidget { background: @surface; color: @text; border: 1px solid @border; border-radius: 8px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid @surface_alt; }
            QListWidget::item:hover { background: @selection_bg; }
            QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background: @accent; color: @selection_text; }
            QPushButton#Primary { background: @accent; color: @selection_text; border: none; }
            QPushButton#Primary:hover { background: @accent_hover; }
        """))
        self.init_ui()

    def init_ui(self):
        layout = self.content_layout

        lbl_info = QLabel("Listeden eklemek istediginiz hizmetleri seciniz.")
        layout.addWidget(lbl_info)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Hizmet ara...")
        self.search.textChanged.connect(self.filter_list)
        layout.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        for s_name, data in self.services_data.items():
            item = QListWidgetItem()
            price = data.get('price', 0)
            item.setText(f"{s_name} - {price} ₺")
            item.setData(Qt.ItemDataRole.UserRole, s_name)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        btn_box = QHBoxLayout()

        btn_select_all = QPushButton("Tumunu Sec")
        btn_select_all.clicked.connect(self.select_all)

        btn_add = QPushButton("Secilenleri Ekle")
        btn_add.setObjectName("Primary")
        btn_add.clicked.connect(self.accept)

        btn_box.addWidget(btn_select_all)
        btn_box.addStretch()
        btn_box.addWidget(btn_add)

        layout.addLayout(btn_box)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)

    def get_selected(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                s_name = item.data(Qt.ItemDataRole.UserRole)
                data = self.services_data.get(s_name)
                if data:
                    selected.append((s_name, data.get('price', 0), data.get('description', '')))
        return selected
