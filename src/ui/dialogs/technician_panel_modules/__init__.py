# -*- coding: utf-8 -*-

"""
Technician Panel Package  
Bu __init__.py technician_panel.py dosyasını tekrar export eder
"""

# technician_panel.py dialogs klasöründe, bizim paketin DIŞINDA
# Absolute path ile import et
import sys
import os

# Parent module'ü al
from src.ui.dialogs import technician_panel as tp_module

# Re-export
TechnicianPanel = tp_module.TechnicianPanel

# Dialog'ları da re-export et
try:
    from .dialogs.image_gallery_dialog import ImageGalleryDialog
    from .dialogs.manual_product_dialog import ModernManualProductDialog
except ImportError:
    # Henüz modülerleştirilmemiş dialog'lar için fallback
    try:
        ImageGalleryDialog = getattr(tp_module, 'ImageGalleryDialog', None)
        ModernManualProductDialog = getattr(tp_module, 'ModernManualProductDialog', None)
    except Exception:
        ImageGalleryDialog = None
        ModernManualProductDialog = None

__all__ = ['TechnicianPanel', 'ImageGalleryDialog', 'ModernManualProductDialog']
