# voice_training_widget.py - Facade module for backward compatibility
# This file re-exports all components from the modularized voice training system

from .voice_training_base import VoiceTrainingWidget
from .voice_healthcheck_dialog import VoiceHealthcheckResultDialog
from .voice_scenario_editor import VoiceScenarioEditorDialog

__all__ = [
    "VoiceTrainingWidget",
    "VoiceHealthcheckResultDialog",
    "VoiceScenarioEditorDialog",
]
