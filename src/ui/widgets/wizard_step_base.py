# -*- coding: utf-8 -*-

"""
Wizard Step Base Class
Her wizard adımı için temel sınıf
"""
from PyQt6.QtWidgets import QWidget
from abc import ABCMeta, abstractmethod
from typing import Dict, Tuple

class WizardMeta(type(QWidget), ABCMeta):
    pass

class WizardStepBase(QWidget, metaclass=WizardMeta):
    """
    Base class for wizard steps
    Her adım bu sınıftan türetilmeli
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    @abstractmethod
    def setup_ui(self):
        """Setup step UI - Alt sınıflarda implement edilmeli"""
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, str]:
        """
        Validate step data
        
        Returns:
            (is_valid, error_message) tuple
            - is_valid: True if validation passes
            - error_message: Error message if validation fails, empty string otherwise
        """
        pass
    
    @abstractmethod
    def get_data(self) -> Dict:
        """
        Return step data as dictionary
        
        Returns:
            Dictionary containing all step data
        """
        pass
    
    @abstractmethod
    def set_data(self, data: Dict):
        """
        Load data into step UI
        
        Args:
            data: Dictionary containing step data
        """
        pass
    
    def on_show(self):
        """
        Called when step becomes visible
        Override if needed
        """
        pass
    
    def on_hide(self):
        """
        Called when step becomes hidden
        Override if needed
        """
        pass
