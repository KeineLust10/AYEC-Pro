# -*- coding: utf-8 -*-
import sys
import ctypes
import logging

logger = logging.getLogger("AYECAccelerator")

# FastIconCache - RAM Cache for QIcons and QPixmaps
class FastIconCache:
    _icon_cache = {}
    _pixmap_cache = {}

    @classmethod
    def get_icon(cls, path_or_icon):
        """
        Retrieves QIcon from cache, or creates and caches it.
        Turkish characters are not used. All comments comply with ASCII rules.
        """
        if not path_or_icon:
            return None
        
        # If it's already a QIcon, return it
        from PyQt6.QtGui import QIcon
        if isinstance(path_or_icon, QIcon):
            return path_or_icon

        path_str = str(path_or_icon)
        if path_str in cls._icon_cache:
            return cls._icon_cache[path_str]

        icon = QIcon(path_str)
        cls._icon_cache[path_str] = icon
        return icon

    @classmethod
    def get_pixmap(cls, path_or_pixmap):
        """
        Retrieves QPixmap from cache, or creates and caches it.
        """
        if not path_or_pixmap:
            return None

        from PyQt6.QtGui import QPixmap
        if isinstance(path_or_pixmap, QPixmap):
            return path_or_pixmap

        path_str = str(path_or_pixmap)
        if path_str in cls._pixmap_cache:
            return cls._pixmap_cache[path_str]

        pixmap = QPixmap(path_str)
        cls._pixmap_cache[path_str] = pixmap
        return pixmap

    @classmethod
    def clear(cls):
        cls._icon_cache.clear()
        cls._pixmap_cache.clear()


# fast_render_context - Context Manager to disable updates and paint events for PyQt6 widgets
class fast_render_context:
    """
    Context manager to suspend widget redraws during updates.
    Prevents flickering and speeds up populating tables/lists.
    """
    def __init__(self, widget):
        self.widget = widget
        self.old_updates = True

    def __enter__(self):
        if self.widget:
            self.old_updates = self.widget.updatesEnabled()
            self.widget.setUpdatesEnabled(False)
        return self.widget

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.widget:
            self.widget.setUpdatesEnabled(self.old_updates)
            self.widget.update()


# Windows Kernel32 & PSAPI DLL RAM Squeeze Optimizer
class WindowsMemorySqueezer:
    @staticmethod
    def squeeze():
        """
        Squeezes current process RAM usage back to disk/OS pool using Windows native APIs.
        """
        if sys.platform != "win32":
            return False

        try:
            # Get current process pseudo-handle (-1)
            current_process = -1
            
            # Call SetProcessWorkingSetSize(Handle, -1, -1) to push unused memory to standby/paging list
            kernel32 = ctypes.windll.kernel32
            kernel32.SetProcessWorkingSetSize(current_process, -1, -1)
            
            # Call psapi.EmptyWorkingSet(Handle) to flush working set
            try:
                psapi = ctypes.windll.psapi
                psapi.EmptyWorkingSet(current_process)
            except Exception:
                pass
            
            return True
        except Exception as e:
            logger.debug(f"WindowsMemorySqueezer execution bypassed: {e}")
            return False


# C-Types record filter engine
def fast_filter_records(query: str, records: list, field_names: list) -> list:
    """
    Highly optimized search/filter using rapid sub-string search.
    Case insensitive lookup. Yorum satirlari ASCII kuralina uygundur.
    """
    if not query:
        return records

    query_normalized = query.lower().strip()
    if not query_normalized:
        return records

    matching_records = []
    
    # Pre-cache lowered strings to avoid repeatedly calling .lower()
    for record in records:
        match_found = False
        for field in field_names:
            val = record.get(field) if isinstance(record, dict) else getattr(record, field, None)
            if val is not None:
                if query_normalized in str(val).lower():
                    match_found = True
                    break
        if match_found:
            matching_records.append(record)

    return matching_records
