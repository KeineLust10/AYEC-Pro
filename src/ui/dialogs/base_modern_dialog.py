from src.ui.widgets.modern_dialog import ModernDialog


class BaseModernDialog(ModernDialog):
    """
    Backward-compatible alias over the shared modern dialog shell.
    Existing dialogs can keep importing BaseModernDialog while using the
    same modern card layout and footer system as the rest of the app.
    """

    def __init__(self, parent=None, title="Dialog", width=600, height=400):
        super().__init__(title=title, parent=parent, width=width, height=height)
