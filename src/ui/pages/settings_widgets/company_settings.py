# -*- coding: utf-8 -*-

"""
Company Settings Widget
Firma ayarlari widget'i - moduler surum.

Bu dosya geriye uyumluluk saglar ve ilgili alt modulleri bir araya getirir.
"""

# Geriye uyumluluk icin tum siniflari export et
from src.ui.pages.settings_widgets.company_settings_dialog import CompanySettingsDialog
from src.ui.pages.settings_widgets.proforma_guide import ProformaGuideWidget, _StepAnimCanvas
from src.ui.pages.settings_widgets.proforma_designer import (
    ProformaTemplateCanvas,
    ProformaTemplateDesignerDialog,
)

# Ana widget
from src.ui.pages.settings_widgets.company_settings_base import CompanySettingsWidget

__all__ = [
    "CompanySettingsWidget",
    "CompanySettingsDialog",
    "ProformaGuideWidget",
    "_StepAnimCanvas",
    "ProformaTemplateCanvas",
    "ProformaTemplateDesignerDialog",
]
