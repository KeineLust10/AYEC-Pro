"""
Shared modern dialog entrypoint for legacy imports.
"""

from src.ui.widgets.modern_dialog import ModernDialog as _SharedModernDialog


class ModernDialog(_SharedModernDialog):
    def __init__(self, parent=None, title="Dialog", width=500, height=400, blur_background=False):
        super().__init__(
            title=title,
            parent=parent,
            width=width,
            height=height,
            blur_background=blur_background,
        )
