"""Patch ThemeManager._apply_raw to defer refresh_all_widgets."""
import re

path = r"C:\Users\Admin\Desktop\AYEC Pro\src\utils\theme_manager.py"
with open(path, 'rb') as f:
    content = f.read()

old = (
    b"    @classmethod\r\n"
    b"    def _apply_raw(cls, app, theme_name):\r\n"
    b"        cls._last_palette = cls.current_palette()\r\n"
    b"        cls._current_theme = cls.normalize_theme_name(theme_name)\r\n"
    b"        cls._install_stylesheet_patch()\r\n"
    b"        app.setPalette(cls._build_palette(cls._current_theme))\r\n"
    b"        app.setStyleSheet(cls.get_stylesheet(cls._current_theme))\r\n"
    b"        cls.refresh_all_widgets(app)"
)

new = (
    b"    @classmethod\r\n"
    b"    def _apply_raw(cls, app, theme_name, deferred_refresh=True):\r\n"
    b"        # Apply palette and QSS instantly so UI looks correct immediately.\r\n"
    b"        # Heavy per-widget refresh is deferred via QTimer to prevent UI freeze.\r\n"
    b"        cls._last_palette = cls.current_palette()\r\n"
    b"        cls._current_theme = cls.normalize_theme_name(theme_name)\r\n"
    b"        cls._install_stylesheet_patch()\r\n"
    b"        app.setPalette(cls._build_palette(cls._current_theme))\r\n"
    b"        app.setStyleSheet(cls.get_stylesheet(cls._current_theme))\r\n"
    b"        if deferred_refresh:\r\n"
    b"            # Defer so UI can repaint before heavy iteration (prevents freeze)\r\n"
    b"            QTimer.singleShot(0, lambda: cls.refresh_all_widgets(app))\r\n"
    b"        else:\r\n"
    b"            cls.refresh_all_widgets(app)"
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'wb') as f:
        f.write(content)
    print("SUCCESS: _apply_raw patched")
else:
    print("ERROR: old content not found")
    # Show surrounding area
    idx = content.find(b"_apply_raw")
    print(repr(content[idx:idx+400]))
