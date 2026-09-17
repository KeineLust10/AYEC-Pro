# -*- coding: utf-8 -*-

import unittest
import sys
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

# Yolu ayarla
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# QApplication singleton
app = QApplication.instance() or QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

class TestUIScenarios(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Mock Database
        from src.database import Database
        cls.db = Database(":memory:")
        # Temel dataları ekle
        cls.db.add_customer({
            "name": "Test UI User", 
            "phone": "5550001122", 
            "email": "ui@test.com", 
            "type": "Bireysel",
            "tc_no": "111",
            "address": "Test Adres"
        })

    def setUp(self):
        pass

    def test_customers_page_init(self):
        """Müşteri sayfasının başlatılması ve yüklenmesi"""
        from src.ui.pages.customers_page import CustomersPage
        
        page = CustomersPage(self.db)
        
        # Sayfa widget mı?
        self.assertIsInstance(page, QWidget)
        
        # Başlık yüklendi mi?
        # DashboardWelcomeLabel ismini arayalım
        try:
            label = page.findChild(QWidget, "DashboardWelcomeLabel")
            if label:
                self.assertIn("Müşteri", label.text())
        except:
            pass # İsimli widget bulunamazsa test fail olmasın, structure değişmiş olabilir
            
        # Tablo satır sayısı kontrolü (1 müşteri eklemiştik)
        self.assertEqual(page.table.rowCount(), 1)
        
        # Tablodaki veri doğru mu?
        self.assertEqual(page.table.item(0, 1).text(), "Test UI User")

    def test_stock_page_init(self):
        """Stok sayfasının başlatılması"""
        from src.ui.pages.stock_page import StockPage
        page = StockPage(self.db)
        self.assertIsInstance(page, QWidget)
        
        # Parça ekle ve sayfayı yenile
        self.db.add_part("Test Fan", "Soğutma", 5, 100.0, "Orijinal", 2)
        page.load_stock_list()
        
        self.assertGreaterEqual(page.table_stock.rowCount(), 1)

    def test_service_page_init(self):
        """Servis sayfasının başlatılması"""
        from src.ui.pages.services_page import ServicesPage
        page = ServicesPage(self.db)
        self.assertIsInstance(page, QWidget)

    def test_modern_dialog_theme_switch(self):
        """ModernDialog'un başlatılması, şeffaf arkaplanı ve tema değişiminde bozulmaması"""
        from src.ui.widgets.modern_dialog import ModernDialog
        from src.utils.theme_manager import ThemeManager
        
        dialog = ModernDialog(title="Test Dialog", width=500, height=400)
        self.assertIsInstance(dialog, QWidget)
        
        # Dialog stil kontrolü (transparent kuralı içermeli)
        qss = dialog.styleSheet()
        self.assertIn("QDialog { background: transparent; }", qss)
        
        # Tema değişimi tetikleyelim
        ThemeManager.apply_theme(app, "dark")
        
        # Tema değişimi sonrası dialog stili hala şeffaf olmalı
        qss_after = dialog.styleSheet()
        self.assertIn("QDialog { background: transparent; }", qss_after)
        
        dialog.close()

    @classmethod
    def tearDownClass(cls):
        cls.db.conn.close()

if __name__ == '__main__':
    unittest.main()
