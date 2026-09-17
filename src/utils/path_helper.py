import os
import sys

class PathHelper:
    APP_NAME = "AYEC Pro"

    @staticmethod
    def get_bundle_dir():
        """Return the directory that contains packaged application resources."""
        bundle_dir = getattr(sys, "_MEIPASS", "")
        if bundle_dir:
            return os.path.abspath(bundle_dir)
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    @staticmethod
    def get_resource_path(*parts):
        """Build an absolute path for a bundled or source resource."""
        return os.path.join(PathHelper.get_bundle_dir(), *parts)

    @staticmethod
    def get_app_icon():
        """Return a QIcon with multi-resolution .ico and .png formats for Windows taskbar & titlebar."""
        try:
            from PyQt6.QtGui import QIcon
            icon = QIcon()
            ico_path = PathHelper.get_resource_path("assets", "app_icon.ico")
            png_path = PathHelper.get_resource_path("assets", "app_icon.png")
            if os.path.isfile(ico_path):
                icon.addFile(ico_path)
            if os.path.isfile(png_path):
                icon.addFile(png_path)
            return icon
        except Exception:
            from PyQt6.QtGui import QIcon
            return QIcon()

    @staticmethod
    def apply_windows_taskbar_icon(widget):
        """Apply the native icon after a Qt window receives its Windows handle."""
        if os.name != "nt":
            return
        icon_path = PathHelper.get_resource_path("assets", "app_icon.ico")
        if not os.path.isfile(icon_path):
            return
        try:
            import ctypes
            from ctypes import wintypes

            image_icon = 1
            icon_small = 0
            icon_big = 1
            load_from_file = 0x0010
            default_size = 0x0040
            user32 = ctypes.windll.user32
            user32.LoadImageW.argtypes = (
                wintypes.HINSTANCE,
                wintypes.LPCWSTR,
                wintypes.UINT,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            )
            user32.LoadImageW.restype = ctypes.c_void_p
            user32.SendMessageW.argtypes = (
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )
            user32.SendMessageW.restype = wintypes.LPARAM
            small_handle = user32.LoadImageW(
                None, icon_path, image_icon, 16, 16, load_from_file | default_size
            )
            large_handle = user32.LoadImageW(
                None, icon_path, image_icon, 32, 32, load_from_file | default_size
            )
            window_handle = int(widget.winId())
            if small_handle:
                user32.SendMessageW(
                    window_handle, 0x0080, icon_small, small_handle
                )
            if large_handle:
                user32.SendMessageW(
                    window_handle, 0x0080, icon_big, large_handle
                )
            widget._ayec_windows_icon_handles = (small_handle, large_handle)
        except Exception:
            pass

    @staticmethod
    def _is_frozen():
        """PyInstaller/Nuitka packaged run detection."""
        return bool(getattr(sys, "frozen", False))

    @staticmethod
    def get_app_data_dir():
        """Get the absolute path to the AppData directory for the application."""
        if os.name == 'nt': # Windows
            base_dir = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        else: # Linux/Mac (fallback)
            base_dir = os.path.expanduser('~/.local/share')

        path = os.path.join(base_dir, PathHelper.APP_NAME, "Data")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def get_db_path(db_name="ayecpro.db"):
        """Get the full path to the database file in AppData."""
        return os.path.join(PathHelper.get_app_data_dir(), db_name)

    @staticmethod
    def get_log_path(log_name="app_debug.log"):
        """Get the full path to the log file in AppData."""
        log_dir = os.path.join(PathHelper.get_app_data_dir(), "Logs")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, log_name)

    @staticmethod
    def migrate_if_needed(db_name="ayecpro.db"):
        """Migrate database from local root to NEW AppData if needed."""
        from src.utils.logger import logger  # lazy import to avoid circular dependency
        appdata_db = PathHelper.get_db_path(db_name)

        if os.name == "nt":
            local_root = os.environ.get(
                "LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")
            )
        else:
            local_root = os.path.expanduser("~/.local/share")
        legacy_paths = (
            os.path.join(local_root, PathHelper.APP_NAME, db_name),
            os.path.join(os.getcwd(), db_name),
        )
        if not os.path.exists(appdata_db):
            for legacy_db in legacy_paths:
                if not os.path.exists(legacy_db):
                    continue
                try:
                    import shutil

                    shutil.copy2(legacy_db, appdata_db)
                    logger.info("Database migrated to: %s", appdata_db)
                    break
                except Exception as e:
                    logger.error("Database migration error: %s", e)

        return False
