from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QPushButton, QTextEdit, QVBoxLayout

from src.ui.dialogs.modern_input_dialog import ModernInputDialog
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.logger import logger
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_info, show_warning


class TemplateManagerDialog(ModernDialog):
    def __init__(self, db, parent=None):
        super().__init__(title="Mesaj Sablonlari Yoneticisi", parent=parent, width=700, height=500)
        self.db = db
        self.set_footer_visible(False)
        self.setStyleSheet(
            theme_qss(
                """
                QDialog {
                    background-color: @surface_alt;
                    border-radius: 15px;
                }
                QPushButton {
                    background-color: @warning;
                    color: @selection_text;
                    border-radius: 6px;
                    padding: 6px;
                }
                QPushButton:hover { background-color: @warning; }
                """
            )
        )
        self.init_ui()
        self.load_templates()

    def init_ui(self):
        layout = self.content_layout
        root = QHBoxLayout()

        left_layout = QVBoxLayout()
        self.list_templates = QListWidget()
        self.list_templates.itemClicked.connect(self.on_template_select)
        left_layout.addWidget(QLabel("Sablonlar:"))
        left_layout.addWidget(self.list_templates)
        btn_add = QPushButton("Yeni Sablon")
        btn_add.clicked.connect(self.add_template)
        left_layout.addWidget(btn_add)
        btn_del = QPushButton("Sil")
        btn_del.clicked.connect(self.delete_template)
        left_layout.addWidget(btn_del)
        root.addLayout(left_layout, 33)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Sablon Icerigi:"))
        self.txt_content = QTextEdit()
        right_layout.addWidget(self.txt_content)
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.save_template)
        right_layout.addWidget(btn_save)
        root.addLayout(right_layout, 66)
        layout.addLayout(root)

    def load_templates(self):
        self.list_templates.clear()
        try:
            self.db.cursor.execute("SELECT id, name FROM whatsapp_templates")
            for template in self.db.cursor.fetchall():
                self.list_templates.addItem(template[1])
        except Exception as exc:
            logger.error(f"Template load error: {exc}")

    def on_template_select(self, item):
        try:
            self.db.cursor.execute("SELECT content FROM whatsapp_templates WHERE name=?", (item.text(),))
            row = self.db.cursor.fetchone()
            if row:
                self.txt_content.setText(row[0])
        except Exception as exc:
            show_error(self, f"Sablon yuklenemedi: {exc}")

    def add_template(self):
        name, ok = ModernInputDialog.get_text(self, "Yeni Sablon", "Sablon Adi:")
        if ok and name:
            try:
                self.db.cursor.execute("INSERT INTO whatsapp_templates (name, content) VALUES (?, ?)", (name, ""))
                self.db.conn.commit()
                self.load_templates()
            except Exception as exc:
                show_warning(self, str(exc))

    def save_template(self):
        item = self.list_templates.currentItem()
        if not item:
            return
        try:
            self.db.cursor.execute("UPDATE whatsapp_templates SET content=? WHERE name=?", (self.txt_content.toPlainText(), item.text()))
            self.db.conn.commit()
            show_info(self, "Sablon kaydedildi.")
        except Exception as exc:
            show_error(self, str(exc))

    def delete_template(self):
        item = self.list_templates.currentItem()
        if not item:
            return
        if SimpleConfirmDialog(self, "Onay", "Silmek istediginize emin misiniz").exec():
            try:
                self.db.cursor.execute("DELETE FROM whatsapp_templates WHERE name=?", (item.text(),))
                self.db.conn.commit()
                self.load_templates()
                self.txt_content.clear()
            except Exception as exc:
                show_error(self, f"Sablon silinemedi: {exc}")
