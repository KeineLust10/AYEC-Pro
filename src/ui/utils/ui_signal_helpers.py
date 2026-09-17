# -*- coding: utf-8 -*-
"""Shared handlers for auto-wired UI controls."""


def on_ui_widget_changed(owner, *args):
    """Generic change handler used by _wire_ui_signals patches."""
    if getattr(owner, "_suppress_ui_handlers", False):
        return
    if hasattr(owner, "save_data"):
        owner.save_data()
        return
    if hasattr(owner, "_sync_criteria_preview"):
        owner._sync_criteria_preview()
