# -*- coding: utf-8 -*-

"""
Customer Manager
Müşteri yönetimi business logic
"""
from datetime import datetime

from src.utils.currency_helper import CurrencyHelper


class CustomerManager:
    """Müşteri yönetim sınıfı"""
    
    def __init__(self, db):
        """
        Args:
            db: Database instance
        """
        self.db = db
    
    def get_customers(self, filter_type=None):
        """
        Müşterileri getir
        
        Args:
            filter_type: Filtre tipi (None, "DEBTORS", etc.)
        
        Returns:
            list: Müşteri listesi
        """
        if filter_type == "DEBTORS":
            try:
                return self.db.get_customers_with_debt()
            except Exception:
                return self.db.get_customers()
        else:
            return self.db.get_customers()
    
    def get_customer_balance(self, customer_id):
        """
        Müşteri bakiyesini getir
        
        Args:
            customer_id: Müşteri ID'si
        
        Returns:
            float: Bakiye tutarı
        """
        try:
            return self.db.get_customer_balance(customer_id) or 0.00
        except Exception:
            return 0.00
    
    def format_balance(self, balance):
        """
        Bakiye formatla
        
        Args:
            balance: Bakiye tutarı
        
        Returns:
            tuple: (formatted_text, label_text, color)
        """
        if balance < 0:
            formatted = CurrencyHelper.format_try_for_display(
                abs(balance),
                db=self.db,
                include_try_reference=False,
            )
            label = "(Borç)"
            color = "#e74c3c"  # Red
        elif balance > 0:
            formatted = CurrencyHelper.format_try_for_display(
                balance,
                db=self.db,
                include_try_reference=False,
            )
            label = "(Alacak)"
            color = "#27ae60"  # Green
        else:
            formatted = CurrencyHelper.format_try_for_display(
                0,
                db=self.db,
                include_try_reference=False,
            )
            label = ""
            color = "#95a5a6"  # Gray
        
        return formatted, label, color
    
    def search_customers(self, customers, search_term):
        """
        Müşterileri ara
        
        Args:
            customers: Müşteri listesi
            search_term: Arama terimi
        
        Returns:
            list: Filtrelenmiş müşteri listesi
        """
        if not search_term:
            return customers
        
        search_lower = search_term.lower()
        filtered = []
        
        for customer in customers:
            # customer: (id, name, phone, email, ...)
            name = str(customer[1] if len(customer) > 1 else "").lower()
            phone = str(customer[2] if len(customer) > 2 else "").lower()
            email = str(customer[3] if len(customer) > 3 else "").lower()
            
            if (search_lower in name or 
                search_lower in phone or 
                search_lower in email):
                filtered.append(customer)
        
        return filtered
