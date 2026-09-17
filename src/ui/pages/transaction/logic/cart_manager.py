# -*- coding: utf-8 -*-

"""
Sepet Yönetimi Modülü
Cart operations: add, remove, update, clear
"""
import uuid
from datetime import datetime


class CartManager:
    """Sepet yönetim sınıfı"""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, service_name, price, qty=1, description="", date=None):
        """
        Sepete yeni kalem ekle
        
        Args:
            service_name: Hizmet adı
            price: Birim fiyat
            qty: Miktar
            description: Açıklama
            date: Tarih (dd.MM.yyyy formatında)
        
        Returns:
            dict: Eklenen item
        """
        if date is None:
            date = datetime.now().strftime("%d.%m.%Y")
        
        item = {
            'id': str(uuid.uuid4()),
            'service': service_name,
            'description': description,
            'price': price,
            'qty': qty,
            'date': date
        }
        
        self.items.append(item)
        return item
    
    def remove_item(self, item_id):
        """
        Sepetten kalem çıkar
        
        Args:
            item_id: Silinecek kalemin ID'si
        
        Returns:
            bool: Başarılı olursa True
        """
        initial_count = len(self.items)
        self.items = [item for item in self.items if item.get('id') != item_id]
        return len(self.items) < initial_count
    
    def update_item(self, item_id, **kwargs):
        """
        Sepet kalemini güncelle
        
        Args:
            item_id: Güncellenecek kalemin ID'si
            **kwargs: Güncellenecek alanlar (price, qty, description, etc.)
        
        Returns:
            bool: Başarılı olursa True
        """
        for item in self.items:
            if item.get('id') == item_id:
                item.update(kwargs)
                return True
        return False
    
    def get_item(self, item_id):
        """ID'ye göre kalem getir"""
        for item in self.items:
            if item.get('id') == item_id:
                return item
        return None
    
    def clear(self):
        """Sepeti temizle"""
        self.items = []
    
    def get_total_count(self):
        """Toplam kalem sayısı"""
        return len(self.items)
    
    def get_items_by_date(self):
        """
        Kalemleri tarihe göre grupla
        
        Returns:
            dict: {date: [items]}
        """
        grouped = {}
        for item in self.items:
            date = item.get('date', '')
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(item)
        return grouped
    
    def get_sorted_dates(self):
        """Tarihleri sıralı getir (yeni -> eski)"""
        dates = set(item.get('date', '') for item in self.items)
        
        def date_sorter(d_str):
            try:
                return datetime.strptime(d_str, "%d.%m.%Y")
            except ValueError:
                return datetime.min
        
        return sorted(dates, key=date_sorter, reverse=True)
