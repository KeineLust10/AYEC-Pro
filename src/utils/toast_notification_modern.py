# -*- coding: utf-8 -*-
"""
Modern Toast Notification Helpers - AYEC Pro
Redirects all toast calls to ModernToast Manager
"""

from src.utils.logger import logger

def _get_modern_toast_manager():
    """Ana penceredeki ModernToast Manager'ı bul"""
    from PyQt6.QtWidgets import QApplication
    for widget in QApplication.topLevelWidgets():
        if hasattr(widget, "toast") and hasattr(widget.toast, "show_success"):
            return widget.toast
    return None


class ModernToast:
    """ModernToast wrapper for backwards compatibility and easier usage"""
    def __init__(self, parent=None):
        self.parent = parent

    def show_success(self, message, duration=3000):
        show_success(self.parent, message, duration)

    def show_error(self, message, duration=4000):
        show_error(self.parent, message, duration)

    def show_warning(self, message, duration=3500):
        show_warning(self.parent, message, duration)

    def show_info(self, message, duration=3000):
        show_info(self.parent, message, duration)

def show_success(parent, message, duration=3000):
    """Başarı bildirimi göster"""
    manager = _get_modern_toast_manager()
    if manager:
        try:
            manager.show_success(message, duration)
            return
        except Exception as e:
            logger.debug("ModernToast success path failed: %s", e)
    
    # Fallback: Import old toast
    from src.utils.toast_notification import ToastNotification
    toast = ToastNotification(parent, message, "success", duration)
    toast.show_notification()


def show_error(parent, message, duration=4000):
    """Hata bildirimi göster"""
    manager = _get_modern_toast_manager()
    if manager:
        try:
            manager.show_error(message, duration)
            return
        except Exception as e:
            logger.debug("ModernToast error path failed: %s", e)
    
    from src.utils.toast_notification import ToastNotification
    toast = ToastNotification(parent, message, "error", duration)
    toast.show_notification()


def show_warning(parent, message, duration=3500):
    """Uyarı bildirimi göster"""
    manager = _get_modern_toast_manager()
    if manager:
        try:
            manager.show_warning(message, duration)
            return
        except Exception as e:
            logger.debug("ModernToast warning path failed: %s", e)
    
    from src.utils.toast_notification import ToastNotification
    toast = ToastNotification(parent, message, "warning", duration)
    toast.show_notification()


def show_info(parent, message, duration=3000):
    """Bilgi bildirimi göster"""
    manager = _get_modern_toast_manager()
    if manager:
        try:
            manager.show_info(message, duration)
            return
        except Exception as e:
            logger.debug("ModernToast info path failed: %s", e)
    
    from src.utils.toast_notification import ToastNotification
    toast = ToastNotification(parent, message, "info", duration)
    toast.show_notification()
