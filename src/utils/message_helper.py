"""
Global message helpers and a central bridge from QMessageBox to modern dialogs.
"""

from PyQt6.QtWidgets import QApplication, QMessageBox

from src.ui.components.message_box import ModernConfirm, ModernMessage
from src.ui.widgets.toast_notification import show_toast

_HOOKS_INSTALLED = False


def styled_message_box(parent, icon_type, title, text, details=None, buttons=QMessageBox.StandardButton.Ok):
    message = str(text or "")
    if details:
        message = f"{message}\n\n{details}"

    if icon_type == QMessageBox.Icon.Question or buttons != QMessageBox.StandardButton.Ok:
        result = ModernConfirm.ask(parent, message, str(title or "Onay"))
        if buttons == (QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No):
            return QMessageBox.StandardButton.Yes if result else QMessageBox.StandardButton.No
        return QMessageBox.StandardButton.Ok if result else QMessageBox.StandardButton.Cancel

    if icon_type == QMessageBox.Icon.Warning:
        return ModernMessage.show_warning(parent, message, str(title or "Uyari"))
    if icon_type == QMessageBox.Icon.Critical:
        return ModernMessage.show_error(parent, message, str(title or "Hata"))
    if icon_type == QMessageBox.Icon.Information:
        return ModernMessage.show_info(parent, message, str(title or "Bilgi"))
    return ModernMessage.show_info(parent, message, str(title or "Bilgi"))


def _find_toast_host():
    for widget in QApplication.topLevelWidgets():
        if getattr(widget, "toast", None):
            return widget
        if widget.objectName() == "ModernDesktopApp":
            return widget
    return None


def show_info(parent, title, message):
    main_window = _find_toast_host()
    full_msg = f"<b>{title}</b><br>{message}" if title else message
    if main_window and hasattr(main_window, "toast"):
        main_window.toast.show_toast(full_msg, "info")
    else:
        show_toast(parent, full_msg, toast_type="info")


def show_warning(parent, title, message):
    main_window = _find_toast_host()
    full_msg = f"<b>{title}</b><br>{message}" if title else message
    if main_window and hasattr(main_window, "toast"):
        main_window.toast.show_toast(full_msg, "warning")
    else:
        show_toast(parent, full_msg, toast_type="warning")


def show_error(parent, title, message):
    main_window = _find_toast_host()
    full_msg = f"<b>{title}</b><br>{message}" if title else message
    if main_window and hasattr(main_window, "toast"):
        main_window.toast.show_toast(full_msg, "error", duration=5000)
    else:
        show_toast(parent, full_msg, toast_type="error", duration=5000)


def show_success(parent, title, message):
    main_window = _find_toast_host()
    full_msg = f"<b>{title}</b><br>{message}" if title else message
    if main_window and hasattr(main_window, "toast"):
        main_window.toast.show_toast(full_msg, "success")
    else:
        show_toast(parent, full_msg, toast_type="success")


def show_question(parent, title, message):
    return styled_message_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        message,
        buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )


def install_modern_messagebox_hooks():
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return

    def _information(parent, title, text, *args, **kwargs):
        return ModernMessage.show_info(parent, str(text), str(title or "Bilgi"))

    def _warning(parent, title, text, *args, **kwargs):
        return ModernMessage.show_warning(parent, str(text), str(title or "Uyari"))

    def _critical(parent, title, text, *args, **kwargs):
        return ModernMessage.show_error(parent, str(text), str(title or "Hata"))

    def _question(parent, title, text, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, default_button=QMessageBox.StandardButton.No, *args, **kwargs):
        _ = (buttons, default_button)
        result = ModernConfirm.ask(parent, str(text), str(title or "Onay"))
        return QMessageBox.StandardButton.Yes if result else QMessageBox.StandardButton.No

    QMessageBox.information = staticmethod(_information)
    QMessageBox.warning = staticmethod(_warning)
    QMessageBox.critical = staticmethod(_critical)
    QMessageBox.question = staticmethod(_question)
    _HOOKS_INSTALLED = True
