# -*- coding: utf-8 -*-
"""
Otomotiv Sektör Plugin'i - BaseSector implementasyonu
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
    Otomotiv servisleri için sektör plugin'i.
    Araç yönetimi, plaka takibi, otomotiv stok yönetimi.
    """

    # Sektör tanımlamaları
    @property
    def sector_id(self) -> str:
        return "otomotiv"

    @property
    def sector_name(self) -> str:
        return "Otomotiv Servis"

    @property
    def sector_icon(self) -> str:
        return "🚗"

    # Otomotiv kategorileri
    ACCESSORY_CATEGORY = "Otomotiv Araç Kabul"
    FAULT_CATEGORY = "Otomotiv Arıza Hızlı Seçimi"
    PROCESS_CATEGORY = "Otomotiv İşlem Detayı"
    CHECKLIST_CATEGORY = "Otomotiv Kontrol Listesi"

    CATEGORIES = [
        FAULT_CATEGORY,
        PROCESS_CATEGORY,
        "Gizli Not",
        ACCESSORY_CATEGORY,
        CHECKLIST_CATEGORY,
    ]

    PRESETS = {
        FAULT_CATEGORY: [
            "MOTOR ARIZA LAMBASI YANIYOR",
            "YAĞ KAÇAĞI VAR",
            "ŞANZIMAN GEÇİŞ SORUNU",
            "FREN SESİ VAR",
            "DİREKSİYON TİTREŞİMİ",
            "HARARET YÜKSELİYOR",
            "MARŞ BASIYOR ÇALIŞMIYOR",
            "AKÜ ZAYIF / ŞARJ SORUNU",
        ],
        PROCESS_CATEGORY: [
            "YAĞ DEĞİŞTİ",
            "FİLTRELER DEĞİŞTİ",
            "BALATA DEĞİŞTİ",
            "ARIZA KODU SİLİNDİ",
            "TEST SÜRÜŞÜ YAPILDI",
            "MÜŞTERİ ONAYI BEKLİYOR",
            "PARÇA BEKLENİYOR",
            "TESLİME HAZIR",
        ],
        "Gizli Not": [
            "TEST OK",
            "İKİNCİ KONTROL GEREKİYOR",
            "PARÇA TEDARİĞİ BEKLENİYOR",
            "ACİL TESLİM",
        ],
        ACCESSORY_CATEGORY: [
            "RUHSAT",
            "YEDEK ANAHTAR",
            "STEPNE",
            "BİJON ANAHTARI",
            "KRİKO",
            "SERVİS KİTAPÇIĞI",
        ],
        CHECKLIST_CATEGORY: [
            "FREN KONTROLÜ",
            "LASTİK BASINCI",
            "AKÜ VOLTAJI",
            "SIVI SEVİYELERİ",
            "SÜSPANSİYON KONTROLÜ",
            "AYDINLATMA TESTİ",
            "OBD TARAMASI",
            "YOL TESTİ",
        ],
    }

    APPROVAL_STATUS_CHOICES = [
        ("Beklemede", "Bekleme"),
        ("Müşteri Onayı Bekliyor", "Musteri Onayi Bekliyor"),
        ("Onaylandı", "Onaylandi"),
        ("Reddedildi", "Reddedildi"),
    ]

    CHECKLIST_TEMPLATES = {
        "servis_kabul": [
            {"name": "Yakit Seviyesi", "required": False},
            {"name": "Ikaz Lambalari", "required": False},
            {"name": "Ruhsat Teslimi", "required": False},
            {"name": "Yedek Anahtar", "required": False},
            {"name": "Kaporta Gorunumu", "required": False},
            {"name": "Dis Aydinlatma", "required": False},
        ],
        "bakim_oncesi": [
            {"name": "Motor Yagi", "required": True},
            {"name": "Fren Balatalari", "required": False},
            {"name": "Aku Durumu", "required": False},
            {"name": "Sivi Seviyeleri", "required": True},
            {"name": "Lastik Durumu", "required": False},
            {"name": "OBD Taramasi", "required": False},
        ],
        "bakim_sonrasi": [
            {"name": "Yol Testi", "required": False},
            {"name": "Ariza Lambasi Kontrolu", "required": True},
            {"name": "Servis Bakim Isigi Reset", "required": False},
            {"name": "Teslim Oncesi Temizlik", "required": False},
            {"name": "Musteri Bilgilendirme", "required": True},
            {"name": "Fatura Hazirligi", "required": False},
        ],
    }

    MAINTENANCE_CARD_SECTIONS = [
        {
            "id": "periodic_maintenance",
            "title": "Periyodik Bakim Plani",
            "description": "Periyodik bakim, filtre ve yag degisim kalemleri.",
            "items": [
                {"type": "oil_change", "label": "Yag Degisimi", "days": 90, "km": 10000},
                {"type": "oil_filter", "label": "Yag Filtresi", "days": 90, "km": 10000},
                {"type": "air_filter", "label": "Hava Filtresi", "days": 180, "km": 15000},
                {"type": "cabin_filter", "label": "Polen Filtresi", "days": 180, "km": 15000},
            ],
        },
        {
            "id": "safety_controls",
            "title": "Guvenlik ve Sivi Kontrolleri",
            "description": "Fren, aku ve sivilar gibi koruyucu kontrol kalemleri.",
            "items": [
                {"type": "brake_fluid", "label": "Fren Hidroligi", "days": 365, "km": 40000},
                {"type": "antifreeze", "label": "Antifriz", "days": 365, "km": 30000},
                {"type": "glass_water", "label": "Cam Suyu", "days": 30, "km": 0},
                {"type": "spark_plugs", "label": "Buji Kontrolu", "days": 365, "km": 30000},
            ],
        },
        {
            "id": "long_term_parts",
            "title": "Uzun Donem Parca Takibi",
            "description": "Yuksek kilometreli araclardaki uzun donem degisim kalemleri.",
            "items": [
                {"type": "timing_belt", "label": "Triger Kayisi", "days": 730, "km": 90000},
                {"type": "timing_chain", "label": "Triger Zinciri", "days": 1095, "km": 120000},
            ],
        },
    ]

    AUTOMOTIVE_MODULES = [
        {"id": "checkup_form", "title": "Ekspertiz / Check-Up", "entry": "service_acceptance"},
        {"id": "quotation_approval", "title": "Teklif / Onay", "entry": "service_acceptance"},
        {"id": "vehicle_history_360", "title": "Arac Gecmisi 360", "entry": "vehicle_and_customer"},
        {"id": "warranty_campaign", "title": "Garanti / Kampanya", "entry": "vehicle_maintenance"},
        {"id": "tire_suspension_card", "title": "Lastik ve Yuruyen Aksam", "entry": "vehicle_maintenance"},
        {"id": "battery_electrical_test", "title": "Aku / Elektrik Testi", "entry": "technician"},
        {"id": "maintenance_template_manager", "title": "Bakim Sablonlari", "entry": "vehicle_maintenance"},
        {"id": "delivery_form", "title": "Teslim Formu", "entry": "technician"},
        {"id": "parts_request", "title": "Parca Talep / Satin Alma", "entry": "technician"},
        {"id": "damage_schema_canvas", "title": "Arac Kabul Semasi", "entry": "service_acceptance"},
    ]

    CHECKUP_TEMPLATES = {
        "hizli_ekspertiz": [
            {"group": "Sivi Kontrolleri", "label": "Motor Yagi", "status": "iyi"},
            {"group": "Sivi Kontrolleri", "label": "Antifriz", "status": "iyi"},
            {"group": "Aydinlatma", "label": "Far ve Stoplar", "status": "iyi"},
            {"group": "Yuruyen Aksam", "label": "Balata / Disk", "status": "uyari"},
            {"group": "Elektronik", "label": "OBD Hata Lambalari", "status": "iyi"},
        ],
        "agir_bakim_kontrolu": [
            {"group": "Motor", "label": "Triger Durumu", "status": "uyari"},
            {"group": "Yuruyen Aksam", "label": "Amortisorler", "status": "uyari"},
            {"group": "Lastik", "label": "Dis Derinligi", "status": "iyi"},
            {"group": "Elektrik", "label": "Aku / Sarj", "status": "iyi"},
        ],
    }

    QUOTE_FORM_DESCRIPTORS = [
        {"name": "quote_no", "title": "Teklif No", "type": "text", "required": False},
        {"name": "discount_amount", "title": "Iskonto", "type": "number", "required": False},
        {"name": "approval_status", "title": "Onay Durumu", "type": "select", "required": True, "options": ["Beklemede", "Kismi Onay", "Onaylandi", "Reddedildi"]},
        {"name": "approval_note", "title": "Onay Notu", "type": "multiline", "required": False},
    ]

    DELIVERY_FORM_DESCRIPTORS = [
        {"name": "exit_odometer", "title": "Cikis KM", "type": "number", "required": False},
        {"name": "fuel_level_exit", "title": "Cikis Yakit", "type": "select", "required": False, "options": ["Bos", "1/4", "1/2", "3/4", "Tam"]},
        {"name": "delivery_note", "title": "Teslim Notu", "type": "multiline", "required": False},
        {"name": "delivered_to", "title": "Teslim Alan Kisi", "type": "text", "required": False},
    ]

    HISTORY_SECTIONS = [
        {"id": "services", "title": "Servis Gecmisi"},
        {"id": "maintenance", "title": "Bakim Gecmisi"},
        {"id": "quotes", "title": "Teklif / Onay"},
        {"id": "delivery", "title": "Teslim ve Fatura"},
        {"id": "damage", "title": "Hasar Kayitlari"},
        {"id": "parts_requests", "title": "Parca Talepleri"},
    ]

    TEMPLATE_OVERRIDE_ENTITIES = [
        "maintenance_templates",
        "checkup_templates",
    ]

    def get_menu_items(self) -> List[Dict[str, Any]]:
        """
        Otomotiv sektörü için sidebar menü öğeleri
        """
        return [
            {
                "id": "dashboard",
                "title": "Ana Ekran",
                "icon": "🏠",
                "page_class": "DashboardPage",
            },
            {
                "id": "vehicles",
                "title": "Araçlar",
                "icon": "🚗",
                "page_class": "VehicleMaintenancePage",
            },
            {
                "id": "service_board",
                "title": "Servis Panosu",
                "icon": "🔧",
                "page_class": "ServiceBoardPage",
            },
            {
                "id": "stock",
                "title": "Yedek Parça",
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
        """
        Otomotiv dashboard widget'ı
        Şimdilik basit bir placeholder, ileride özel widget eklenecek
        """
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        header = QLabel(f"{self.sector_icon} {self.sector_name} - Dashboard")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px;")
        layout.addWidget(header)
        
        info = QLabel("Otomotiv sektörü aktif. Araç yönetimi ve servis takibi kullanılabilir.")
        info.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(info)
        
        layout.addStretch()
        return widget

    def get_stock_columns(self) -> List[Dict[str, Any]]:
        """
        Otomotiv stok tablosu için 14 kolon
        """
        return [
            {"name": "id", "title": "ID", "width": 60, "visible": True, "editable": False},
            {"name": "code", "title": "Stok Kodu", "width": 120, "visible": True, "editable": True},
            {"name": "name", "title": "Parça Adı", "width": 200, "visible": True, "editable": True},
            {"name": "category", "title": "Kategori", "width": 120, "visible": True, "editable": True},
            {"name": "oem_no", "title": "OEM No", "width": 120, "visible": True, "editable": True},
            {"name": "cross_ref", "title": "Cross Ref", "width": 120, "visible": True, "editable": True},
            {"name": "vehicle_brand", "title": "Araç Marka", "width": 100, "visible": True, "editable": True},
            {"name": "vehicle_model", "title": "Araç Model", "width": 100, "visible": True, "editable": True},
            {"name": "quantity", "title": "Miktar", "width": 80, "visible": True, "editable": True},
            {"name": "unit", "title": "Birim", "width": 60, "visible": True, "editable": True},
            {"name": "purchase_price", "title": "Alış Fiyatı", "width": 100, "visible": True, "editable": True},
            {"name": "sale_price", "title": "Satış Fiyatı", "width": 100, "visible": True, "editable": True},
            {"name": "location", "title": "Raf Yeri", "width": 100, "visible": True, "editable": True},
            {"name": "min_stock", "title": "Min. Stok", "width": 80, "visible": True, "editable": True},
        ]

    def get_customer_form_fields(self) -> List[Dict[str, Any]]:
        """
        Müşteri kartı için otomotiv özel alanlar
        """
        return [
            {
                "name": "vehicle_plate",
                "title": "Araç Plakası",
                "type": "text",
                "required": False,
                "placeholder": "34 ABC 123",
            },
            {
                "name": "vehicle_vin",
                "title": "Şasi No (VIN)",
                "type": "text",
                "required": False,
                "placeholder": "WBA...",
            },
            {
                "name": "vehicle_brand",
                "title": "Marka",
                "type": "select",
                "required": False,
                "options": [
                    "", "Audi", "BMW", "Citroën", "Dacia", "Fiat", "Ford", 
                    "Honda", "Hyundai", "Kia", "Mercedes", "Nissan", 
                    "Opel", "Peugeot", "Renault", "Seat", "Skoda", 
                    "Toyota", "Volkswagen", "Volvo", "Diğer"
                ],
            },
            {
                "name": "vehicle_model",
                "title": "Model",
                "type": "text",
                "required": False,
            },
            {
                "name": "vehicle_year",
                "title": "Model Yılı",
                "type": "number",
                "required": False,
            },
            {
                "name": "vehicle_engine",
                "title": "Motor Tipi",
                "type": "text",
                "required": False,
                "placeholder": "1.6 TDI",
            },
        ]

    def get_service_form_fields(self) -> List[Dict[str, Any]]:
        """
        Yeni servis kaydı formu için alanlar
        """
        return [
            {
                "name": "vehicle_plate",
                "title": "Plaka",
                "type": "text",
                "required": True,
            },
            {
                "name": "vehicle_vin",
                "title": "Şasi No",
                "type": "text",
                "required": False,
            },
            {
                "name": "current_km",
                "title": "Güncel KM",
                "type": "number",
                "required": False,
            },
            {
                "name": "service_type",
                "title": "Servis Tipi",
                "type": "select",
                "required": True,
                "options": [
                    "Periyodik Bakım",
                    "Motor Arıza",
                    "Şanzıman",
                    "Fren Sistemi",
                    "Elektrik/Elektronik",
                    "Kaporta/Boya",
                    "Diğer"
                ],
            },
        ]

    def get_quick_categories(self) -> Dict[str, Any]:
        """
        Hızlı not kategorileri ve preset'leri
        """
        return {
            "categories": self.CATEGORIES,
            "presets": self.PRESETS,
        }

    def get_page_overrides(self) -> Dict[str, str]:
        return {
            "vehicle_maintenance": "VehicleMaintenancePage",
            "technician_panel": "TechnicianPanel",
            "stock_dialog": "AddStockDialog",
            "customer_dialog": "AddCustomerDialog",
            "service_dialog": "NewServiceDialog",
        }

    def get_extension_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "customer": self.get_customer_form_fields(),
            "service": self.get_service_form_fields(),
            "stock": [
                {"name": "oem_code", "title": "OEM No", "type": "text", "required": False},
                {"name": "equivalent_code", "title": "Cross Ref", "type": "text", "required": False},
                {"name": "compatible_models", "title": "Uyumlu Modeller", "type": "text", "required": False},
            ],
        }

    def get_form_descriptors(self, entity: str) -> List[Dict[str, Any]]:
        if entity == "customer":
            return [
                {
                    "id": "vehicle_identity",
                    "title": "Arac Kimligi",
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
                    "title": "Is Emri ve Onay",
                    "fields": [
                        {
                            "name": "approval_status",
                            "title": "Onay Durumu",
                            "type": "select",
                            "required": True,
                            "storage": "core",
                            "options": [label for label, _ in self.APPROVAL_STATUS_CHOICES],
                        },
                        {
                            "name": "estimated_date",
                            "title": "Tahmini Teslim Tarihi",
                            "type": "date",
                            "required": False,
                            "storage": "core",
                        },
                        {
                            "name": "invoice_ready",
                            "title": "Fatura Hazir",
                            "type": "checkbox",
                            "required": False,
                            "storage": "core",
                            "column": "invoice_ready_at",
                        },
                    ],
                },
                {
                    "id": "inspection",
                    "title": "Inspection / Kontrol Ozeti",
                    "fields": [
                        {
                            "name": "inspection_summary",
                            "title": "Inspection Ozeti",
                            "type": "multiline",
                            "required": False,
                            "storage": "core",
                            "placeholder": "Kontrol ve ekspertiz sonucunu ozetleyin",
                        }
                    ],
                },
            ]
        return super().get_form_descriptors(entity)

    def get_checklist_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.CHECKLIST_TEMPLATES

    def get_maintenance_card_sections(self) -> List[Dict[str, Any]]:
        return self.MAINTENANCE_CARD_SECTIONS

    def get_automotive_modules(self) -> List[Dict[str, Any]]:
        return self.AUTOMOTIVE_MODULES

    def get_checkup_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.CHECKUP_TEMPLATES

    def get_quote_form_descriptors(self) -> List[Dict[str, Any]]:
        return self.QUOTE_FORM_DESCRIPTORS

    def get_delivery_form_descriptors(self) -> List[Dict[str, Any]]:
        return self.DELIVERY_FORM_DESCRIPTORS

    def get_history_sections(self) -> List[Dict[str, Any]]:
        return self.HISTORY_SECTIONS

    def get_template_override_entities(self) -> List[str]:
        return self.TEMPLATE_OVERRIDE_ENTITIES

    def map_core_to_extension_payload(self, entity: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {field["name"] for field in self.get_extension_schema().get(entity, [])}
        payload = {}
        for key, value in (form_data or {}).items():
            if key not in allowed:
                continue
            if key in {"vehicle_plate", "vehicle_vin"} and value:
                payload[key] = str(value).strip().upper()
            else:
                payload[key] = value
        return payload

    def is_feature_available(self, feature_name: str) -> bool:
        """
        Otomotiv sektöründe bulunan özellikler
        """
        automotive_features = {
            "vehicles",           # Araç yönetimi
            "plates",             # Plaka takibi
            "chassis",            # Şasi no takibi
            "vehicle_maintenance", # Araç bakım takibi
            "quick_categories",   # Hızlı kategoriler
            "oem_parts",          # OEM parça no
            "vehicle_compatibility", # Araç uyumu
            "mileage",            # KM takibi
        }
        return feature_name in automotive_features

    def get_sectoral_stats(self, db) -> Dict[str, Any]:
        """
        Otomotiv sektörü için dashboard istatistikleri
        """
        stats = {
            "title": "Otomotiv Servis İstatistikleri",
            "widgets": [
                {"id": "pending_repair", "title": "Açık İş Emirleri", "icon": "A", "color": "warning"},
                {"id": "delivered_today", "title": "Bugün Teslim Edilen", "icon": "+", "color": "success"},
                {"id": "inspection_due", "title": "Yaklaşan Muayene", "icon": "M", "color": "accent"},
                {"id": "approval_pending", "title": "Onay Bekleyen", "icon": "O", "color": "warning"},
            ]
        }
        
        # Veritabanından gerçek değerleri çek (varsa)
        if db:
            try:
                # Açık iş emirleri
                cursor = db._cursor
                cursor.execute("SELECT COUNT(*) FROM servisler WHERE durum IN ('Bekliyor', 'Tamirde')")
                stats["pending_count"] = cursor.fetchone()[0]
                
                # Bugün teslim edilenler
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                cursor.execute(
                    "SELECT COUNT(*) FROM servisler WHERE DATE(teslim_tarihi) = ?",
                    (today,)
                )
                stats["delivered_today"] = cursor.fetchone()[0]
                
            except Exception as e:
                print(f"[OtomotivPlugin] İstatistik hatası: {e}")
        
        return stats

    def initialize_database(self, db):
        """
        Otomotiv için gerekli tablo/index yapılandırmaları
        """
        try:
            if hasattr(db, "ensure_sector_extension_tables"):
                db.ensure_sector_extension_tables()
            if hasattr(db, "migrate_legacy_automotive_extensions"):
                db.migrate_legacy_automotive_extensions()
        except Exception as e:
            print(f"[OtomotivPlugin] Database init warning: {e}")

    # Yardımcı metodlar
    def get_presets_for_category(self, category: str) -> List[str]:
        """Belirli bir kategori için preset'leri döndür"""
        return self.PRESETS.get(category, [])

    def approval_label_to_db(self, value: str) -> str:
        """Onay durumunu veritabanı formatına çevir"""
        text = str(value or "").strip()
        status_map = {label: db_val for label, db_val in self.APPROVAL_STATUS_CHOICES}
        return status_map.get(text, text or "Bekleme")

    def approval_db_to_label(self, value: str) -> str:
        """Veritabanı değerini görünen formata çevir"""
        text = str(value or "").strip()
        status_map = {db_val: label for label, db_val in self.APPROVAL_STATUS_CHOICES}
        return status_map.get(text, text or "Beklemede")
