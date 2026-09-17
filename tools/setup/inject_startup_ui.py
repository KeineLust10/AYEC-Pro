"""Script to add startup and shortcut settings to system_identity_settings.py"""
import os

path = r"C:\Users\Admin\Desktop\AYEC Pro\src\ui\pages\settings_widgets\system_identity_settings.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = "        scroll.setWidget(container)"

new_code = """
        # 5. Baslangic & Kisayol Ayarlari
        group_startup = QGroupBox("5. Baslangic & Kisayol Ayarlari")
        group_startup.setStyleSheet(theme_qss("font-weight: bold; padding-top: 20px;"))
        startup_layout = QVBoxLayout(group_startup)
        
        # Windows Startup Toggle
        h_startup = QHBoxLayout()
        lbl_startup = QLabel("Windows Baslangicinda Otomatik Calistir")
        lbl_startup.setStyleSheet(theme_qss("font-weight: normal;"))
        from src.ui.widgets.animated_toggle import AnimatedToggle
        self.toggle_startup = AnimatedToggle(active_color=tc("primary"))
        
        if self.main_window and hasattr(self.main_window, 'is_in_windows_startup'):
            self.toggle_startup.setChecked(self.main_window.is_in_windows_startup())
            self.toggle_startup.toggled.connect(self.main_window.toggle_windows_startup)
            
        h_startup.addWidget(lbl_startup)
        h_startup.addStretch()
        h_startup.addWidget(self.toggle_startup)
        startup_layout.addLayout(h_startup)
        
        # Shortcut Buttons
        h_shortcuts = QHBoxLayout()
        h_shortcuts.setSpacing(10)
        
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtCore import Qt
        btn_desktop = QPushButton("Masaustu Kisayolu Olustur")
        btn_desktop.setStyleSheet(theme_qss("background-color: @surface_alt; color: @text; padding: 8px; border-radius: 4px; font-weight: normal; border: 1px solid @border;"))
        btn_desktop.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.main_window and hasattr(self.main_window, 'create_desktop_shortcut'):
            btn_desktop.clicked.connect(lambda: show_success(self, "Basarili", "Masaustu kisayolu olusturuldu.") if self.main_window.create_desktop_shortcut() else None)
        
        btn_start_menu = QPushButton("Baslangic Menusune Ekle")
        btn_start_menu.setStyleSheet(theme_qss("background-color: @surface_alt; color: @text; padding: 8px; border-radius: 4px; font-weight: normal; border: 1px solid @border;"))
        btn_start_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.main_window and hasattr(self.main_window, 'create_start_menu_shortcut'):
            btn_start_menu.clicked.connect(lambda: show_success(self, "Basarili", "Baslangic Menusu kisayolu olusturuldu.") if self.main_window.create_start_menu_shortcut() else None)
        
        h_shortcuts.addWidget(btn_desktop)
        h_shortcuts.addWidget(btn_start_menu)
        h_shortcuts.addStretch()
        startup_layout.addLayout(h_shortcuts)
        
        self.container_layout.addWidget(group_startup)

"""

if target in content:
    content = content.replace(target, new_code + target, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS")
else:
    print("FAILED")
