from fastapi import APIRouter


router = APIRouter()


@router.get("/menu")
def get_menu_tree():
    """
    Desktop menü yapısının web karşılığı.
    Frontend navigasyonu bu endpoint'i referans alarak dinamik menü üretebilir.
    """
    return {
        "sections": [
            {
                "key": "operation",
                "title": "Operasyon",
                "groups": [
                    {
                        "title": "Servis Yönetimi",
                        "items": [
                            {"index": 41, "path": "/service-board", "label": "Durum Paneli"},
                            {"index": 60, "path": "/technician-panel", "label": "Teknisyen Paneli"},
                            {"index": 61, "path": "/field-service-map", "label": "Saha Haritası"},
                            {"index": 30, "path": "/appointments", "label": "Randevular"},
                            {"index": 150, "path": "/transactions/new", "label": "Yeni İşlem"},
                            {"index": 145, "path": "/device-brands", "label": "Cihaz Bilgisi & Markalar"},
                            {"index": 65, "path": "/external-tracking", "label": "Lojistik & Garanti Yönetimi"},
                            {"index": 201, "path": "/job-service-tracking", "label": "İş/Servis Takibi Raporları"},
                        ],
                    }
                ],
            },
            {
                "key": "customer",
                "title": "Müşteri",
                "groups": [
                    {
                        "title": "Müşteri Hub",
                        "items": [
                            {"index": 21, "path": "/customers", "label": "Müşteri Listesi"},
                            {"index": 25, "path": "/contracts", "label": "Sözleşmeler"},
                            {"index": 90, "path": "/reminders", "label": "Hatırlatıcılar"},
                            {"index": 120, "path": "/announcements", "label": "Duyurular"},
                            {"index": 26, "path": "/partners", "label": "Çalışma Ortaklarımız"},
                        ],
                    }
                ],
            },
            {
                "key": "commercial",
                "title": "Ticari",
                "groups": [
                    {
                        "title": "Stok & Satış",
                        "items": [
                            {"index": 50, "path": "/stock", "label": "Stok Yönetimi"},
                            {"index": 220, "path": "/pos", "label": "Hızlı Satış (POS)"},
                            {"index": 140, "path": "/service-definitions", "label": "Hizmet Tanımları"},
                        ],
                    },
                    {
                        "title": "Proje Yönetimi",
                        "items": [
                            {"index": 200, "path": "/projects", "label": "Projeler"},
                        ],
                    },
                ],
            },
            {
                "key": "finance",
                "title": "Finans",
                "groups": [
                    {
                        "title": "Finans",
                        "items": [
                            {"index": 101, "path": "/accounting", "label": "Gelir / Gider"},
                            {"index": 105, "path": "/bank-accounts", "label": "Banka Hesapları"},
                            {"index": 106, "path": "/check-notes", "label": "Çek / Senet"},
                            {"index": 115, "path": "/invoices/create", "label": "Fatura Kes (E-Fatura)"},
                        ],
                    }
                ],
            },
            {
                "key": "system",
                "title": "Sistem",
                "groups": [
                    {
                        "title": "Araçlar",
                        "items": [
                            {"index": 160, "path": "/knowledge-base", "label": "Bilgi Bankası"},
                            {"index": 130, "path": "/settings", "label": "Ayarlar"},
                            {"index": 135, "path": "/audit-log", "label": "Log Kayıtları"},
                            {"index": 180, "path": "/backup", "label": "Yedekleme"},
                            {"index": 70, "path": "/support", "label": "Destek"},
                        ],
                    }
                ],
            },
        ]
    }


@router.get("/page-map")
def get_page_map():
    """
    Desktop index -> web route eşlemesi.
    """
    return {
        "map": {
            10: "/personnel",
            21: "/customers",
            25: "/contracts",
            26: "/partners",
            30: "/appointments",
            40: "/dashboard",
            41: "/service-board",
            42: "/service-status",
            45: "/summary",
            50: "/stock",
            60: "/technician-panel",
            61: "/field-service-map",
            65: "/external-tracking",
            70: "/support",
            90: "/reminders",
            101: "/accounting",
            105: "/bank-accounts",
            106: "/check-notes",
            111: "/finance-reports",
            115: "/invoices/create",
            120: "/announcements",
            130: "/settings",
            135: "/audit-log",
            140: "/service-definitions",
            145: "/device-brands",
            150: "/transactions/new",
            160: "/knowledge-base",
            170: "/ai-assistant",
            180: "/backup",
            200: "/projects",
            201: "/job-service-tracking",
            220: "/pos",
            250: "/mobile-guide",
        }
    }

