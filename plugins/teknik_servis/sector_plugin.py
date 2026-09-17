# -*- coding: utf-8 -*-
"""
Teknik Servis Sektör Plugin'i - BaseSector implementasyonu
Genel amaçlı elektronik cihaz ve teknik servis yönetimi
"""

from typing import List, Dict, Any
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from interfaces import BaseSector


class SectorPlugin(BaseSector):
    """
    Genel teknik servis yönetimi için sektör plugin'i.
    Elektronik cihazlar, beyaz eşya, küçük ev aletleri vb.
    """

    @property
    def sector_id(self) -> str:
        return "teknik_servis"

    @property
    def sector_name(self) -> str:
        return "Teknik Servis"

    @property
    def sector_icon(self) -> str:
        return "🔧"

    # Teknik servis kategorileri
    CATEGORIES = [
        "Arıza Tespiti",
        "Parça Değişimi",
        "Yazılım Güncelleme",
        "Bakım",
        "Garanti İşlemi",
    ]

    PRESETS = {
        "Arıza Tespiti": [
            "Cihaz Açılmıyor",
            "Ekran Sorunu",
            "Ses Problemi",
            "Şarj Olmuyor",
            "Isınma Sorunu",
            "Bağlantı Problemi",
        ],
        "Parça Değişimi": [
            "Ekran Değişti",
            "Batarya Değişti",
            "Şarj Soketi Değişti",
            "Kasa Değişti",
            "Anakart Onarımı",
        ],
        "Yazılım Güncelleme": [
            "Firmware Güncellendi",
            "Format Atıldı",
            "Ayarlar Sıfırlandı",
        ],
        "Bakım": [
            "Genel Temizlik",
            "Toz Alma",
            "Termal Macun Değişimi",
            "Fan Temizliği",
        ],
        "Garanti İşlemi": [
            "Garanti Kapsamında",
            "Garanti Dışı",
            "İmha",
        ],
    }

    CHECKLIST_TEMPLATES = {
        "servis_kabul": [
            {"name": "Aksesuar Kontrolu", "required": False},
            {"name": "Cihaz Fiziksel Durum", "required": True},
            {"name": "Seri No Dogrulama", "required": False},
        ],
        "cihaz_testleri": [
            {"name": "Guc Acilisi", "required": True},
            {"name": "Ekran Kontrolu", "required": False},
            {"name": "Ses Testi", "required": False},
            {"name": "Port Baglanti Kontrolu", "required": False},
        ],
    }

    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Teknik servis menü öğeleri"""
        return [
            {
                "id": "dashboard",
                "title": "Ana Ekran",
                "icon": "🏠",
                "page_class": "DashboardPage",
            },
            {
                "id": "service_board",
                "title": "Servis Panosu",
                "icon": "📋",
                "page_class": "ServiceBoardPage",
            },
            {
                "id": "stock",
                "title": "Stok Yönetimi",
                "icon": "📦",
                "page_class": "StockPage",
            },
            {
                "id": "customers",
                "title": "Müşteriler",
                "icon": "👥",
                "page_class": "CustomersPage",
            },
            {
                "id": "technician",
                "title": "Teknisyen Paneli",
                "icon": "👨‍🔧",
                "page_class": "TechnicianPanel",
            },
        ]

    def get_dashboard_widget(self, parent=None, db=None) -> QWidget:
        """Teknik servis dashboard widget'ı"""
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        header = QLabel(f"{self.sector_icon} {self.sector_name} - Dashboard")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px;")
        layout.addWidget(header)
        
        info = QLabel("Genel teknik servis modu aktif.")
        info.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(info)
        
        layout.addStretch()
        return widget

    def get_stock_columns(self) -> List[Dict[str, Any]]:
        """Teknik servis stok tablosu için 10 kolon"""
        return [
            {"name": "id", "title": "ID", "width": 60, "visible": True, "editable": False},
            {"name": "code", "title": "Stok Kodu", "width": 120, "visible": True, "editable": True},
            {"name": "name", "title": "Parça Adı", "width": 250, "visible": True, "editable": True},
            {"name": "category", "title": "Kategori", "width": 150, "visible": True, "editable": True},
            {"name": "quantity", "title": "Miktar", "width": 80, "visible": True, "editable": True},
            {"name": "unit", "title": "Birim", "width": 60, "visible": True, "editable": True},
            {"name": "purchase_price", "title": "Alış Fiyatı", "width": 100, "visible": True, "editable": True},
            {"name": "sale_price", "title": "Satış Fiyatı", "width": 100, "visible": True, "editable": True},
            {"name": "location", "title": "Raf Yeri", "width": 100, "visible": True, "editable": True},
            {"name": "min_stock", "title": "Min. Stok", "width": 80, "visible": True, "editable": True},
        ]

    def get_customer_form_fields(self) -> List[Dict[str, Any]]:
        """Teknik servis müşteri form alanları"""
        return [
            {
                "name": "device_type",
                "title": "Cihaz Tipi",
                "type": "select",
                "required": False,
                "options": [
                    "", "Telefon", "Tablet", "Bilgisayar", "Laptop",
                    "Televizyon", "Beyaz Eşya", "Klima", "Diğer"
                ],
            },
            {
                "name": "device_brand",
                "title": "Marka",
                "type": "text",
                "required": False,
            },
            {
                "name": "device_model",
                "title": "Model",
                "type": "text",
                "required": False,
            },
        ]

    def get_service_form_fields(self) -> List[Dict[str, Any]]:
        """Teknik servis kayıt form alanları"""
        return [
            {
                "name": "device_type",
                "title": "Cihaz Tipi",
                "type": "select",
                "required": True,
                "options": [
                    "Telefon", "Tablet", "Bilgisayar", "Laptop",
                    "Televizyon", "Beyaz Eşya", "Klima", "Diğer"
                ],
            },
            {
                "name": "serial_no",
                "title": "Seri No",
                "type": "text",
                "required": False,
            },
            {
                "name": "warranty_status",
                "title": "Garanti Durumu",
                "type": "select",
                "required": True,
                "options": ["Garantili", "Garanti Dışı", "Bilinmiyor"],
            },
        ]

    def get_quick_categories(self) -> Dict[str, Any]:
        """Hızlı not kategorileri"""
        return {
            "categories": self.CATEGORIES,
            "presets": self.PRESETS,
        }

    def get_page_overrides(self) -> Dict[str, str]:
        return {
            "technician_panel": "TechnicianPanel",
            "stock_dialog": "AddStockDialog",
            "customer_dialog": "AddCustomerDialog",
            "service_dialog": "NewServiceDialog",
        }

    def get_extension_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "customer": self.get_customer_form_fields(),
            "service": self.get_service_form_fields(),
            "stock": [],
        }

    def get_form_descriptors(self, entity: str) -> List[Dict[str, Any]]:
        if entity == "customer":
            return [
                {
                    "id": "device_identity",
                    "title": "Cihaz Bilgileri",
                    "fields": self.get_customer_form_fields(),
                }
            ]
        if entity == "service":
            return [
                {
                    "id": "service_acceptance",
                    "title": "Servis Kabul Formu",
                    "fields": self.get_service_form_fields(),
                },
                {
                    "id": "job_card",
                    "title": "Is Emri ve Durum",
                    "fields": [
                        {
                            "name": "estimated_date",
                            "title": "Tahmini Teslim Tarihi",
                            "type": "date",
                            "required": False,
                            "storage": "core",
                        },
                        {
                            "name": "inspection_summary",
                            "title": "Test / Kontrol Ozeti",
                            "type": "multiline",
                            "required": False,
                            "storage": "core",
                            "placeholder": "Teknik tespit ve kontrol ozeti",
                        },
                    ],
                },
            ]
        return super().get_form_descriptors(entity)

    def get_checklist_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.CHECKLIST_TEMPLATES

    def get_maintenance_card_sections(self) -> List[Dict[str, Any]]:
        return []

    def map_core_to_extension_payload(self, entity: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {field["name"] for field in self.get_extension_schema().get(entity, [])}
        return {
            key: value
            for key, value in (form_data or {}).items()
            if key in allowed
        }

    def is_feature_available(self, feature_name: str) -> bool:
        """Teknik servis özellikleri"""
        tech_features = {
            "devices",
            "serial_numbers",
            "warranty_tracking",
            "quick_categories",
        }
        return feature_name in tech_features

    def get_sectoral_stats(self, db) -> Dict[str, Any]:
        """Teknik servis istatistikleri"""
        stats = {
            "title": "Teknik Servis İstatistikleri",
            "widgets": [
                {"id": "pending_repair", "title": "Bekleyen", "icon": "!", "color": "warning"},
                {"id": "delivered_today", "title": "Bugün Teslim", "icon": "+", "color": "success"},
                {"id": "service_revenue", "title": "Servis Cirosu", "icon": "$", "color": "accent"},
                {"id": "critical_parts", "title": "Kritik Parça", "icon": "#", "color": "danger"},
            ]
        }
        return stats

    def initialize_database(self, db):
        """Veritabanı başlatma"""
        try:
            if hasattr(db, "ensure_sector_extension_tables"):
                db.ensure_sector_extension_tables()
        except Exception as e:
            print(f"[TeknikServisPlugin] Database init warning: {e}")
