from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtWidgets import QMenu

from src.utils.logger import logger


_INSTALLED = False
_ORIGINAL_QMENU_EXEC: Callable[..., Any] | None = None
_ORIGINAL_QMENU_POPUP: Callable[..., Any] | None = None


def install_context_menu_guard() -> None:
    """Install a global re-entry guard for QMenu.exec.

    Right-click handlers across the app mostly use ``QMenu.exec(...)``.
    This wrapper prevents accidental nested/re-entrant exec calls on the
    same QMenu instance and logs failures instead of freezing the UI flow.
    """

    global _INSTALLED, _ORIGINAL_QMENU_EXEC, _ORIGINAL_QMENU_POPUP
    if _INSTALLED:
        return

    original_exec = getattr(QMenu, "exec", None)
    if original_exec is None:
        logger.warning("Context menu guard skipped: QMenu.exec not available")
        return

    _ORIGINAL_QMENU_EXEC = original_exec
    _ORIGINAL_QMENU_POPUP = getattr(QMenu, "popup", None)

    def guarded_exec(menu_self: QMenu, *args: Any, **kwargs: Any) -> Any:
        if getattr(menu_self, "_ayec_exec_busy", False):
            logger.debug("Context menu re-entry blocked")
            return None

        setattr(menu_self, "_ayec_exec_busy", True)
        try:
            return _ORIGINAL_QMENU_EXEC(menu_self, *args, **kwargs)
        except Exception as exc:
            logger.error("Context menu exec failed: %s", exc, exc_info=True)
            return None
        finally:
            try:
                setattr(menu_self, "_ayec_exec_busy", False)
            except Exception:
                pass

    QMenu.exec = guarded_exec

    if _ORIGINAL_QMENU_POPUP is not None:

        def guarded_popup(menu_self: QMenu, *args: Any, **kwargs: Any) -> Any:
            if getattr(menu_self, "_ayec_popup_busy", False):
                logger.debug("Context menu popup re-entry blocked")
                return None
            setattr(menu_self, "_ayec_popup_busy", True)
            try:
                return _ORIGINAL_QMENU_POPUP(menu_self, *args, **kwargs)
            except Exception as exc:
                logger.error("Context menu popup failed: %s", exc, exc_info=True)
                return None
            finally:
                try:
                    setattr(menu_self, "_ayec_popup_busy", False)
                except Exception:
                    pass

        QMenu.popup = guarded_popup

    _INSTALLED = True
    logger.info("Context menu guard installed")
