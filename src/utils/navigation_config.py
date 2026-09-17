"""Canonical navigation metadata shared by desktop, web, and mobile UIs."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple


PAGE_LABELS: Dict[int, str] = {
    10: "Personel Y\u00f6netimi",
    21: "M\u00fc\u015fteri Listesi",
    25: "Bak\u0131m S\u00f6zle\u015fmeleri",
    26: "\u00c7al\u0131\u015fma Ortaklar\u0131",
    30: "Randevular",
    40: "Genel Bak\u0131\u015f",
    41: "Durum Paneli",
    50: "Stok Y\u00f6netimi",
    51: "Depo ve Ara\u00e7 Stoklar\u0131",
    60: "Yedek Par\u00e7a",
    61: "Saha Haritas\u0131",
    62: "Teknisyen Paneli",
    65: "Lojistik & Garanti Y\u00f6netimi",
    66: "Emanet (Konsinye) Cihazlar",
    70: "Destek Merkezi",
    90: "Hat\u0131rlat\u0131c\u0131lar",
    101: "Gelir / Gider",
    105: "Banka Hesaplar\u0131",
    106: "\u00c7ek / Senet",
    115: "E-Fatura",
    120: "Duyurular",
    130: "Sistem Ayarlar\u0131",
    135: "Log Kay\u0131tlar\u0131",
    140: "\u0130\u015f\u00e7ilik Ekle",
    145: "Marka Adlar\u0131 Y\u00f6netimi",
    146: "\u00dcr\u00fcn Grubu Y\u00f6netimi",
    147: "Rapor C\u00fcmle Kal\u0131plar\u0131",
    150: "Teklif Olu\u015ftur",
    160: "Bilgi Bankas\u0131",
    170: "AI Asistan",
    180: "Yedekleme Merkezi",
    200: "Proje Y\u00f6netimi",
    201: "\u0130\u015f / Servis Takibi Raporlar\u0131",
    202: "Proje Ar\u015fivi",
    210: "Ara\u00e7 Bak\u0131m Takibi",
    250: "Mobil Stok",
    261: "Kullan\u0131m K\u0131lavuzu",
    300: "PC Builder",
    313: "T\u00fcm Teklifler",
    314: "Teklif Raporlar\u0131",
}


MODULE_REQUIREMENTS: Dict[int, str] = {
    10: "personnel",
    21: "crm",
    25: "crm",
    26: "crm",
    30: "operations",
    41: "operations",
    50: "stock",
    51: "stock",
    60: "operations",
    61: "operations",
    65: "operations",
    66: "stock",
    90: "crm",
    101: "finance",
    105: "finance",
    106: "finance",
    115: "finance",
    120: "crm",
    140: "stock",
    145: "stock",
    146: "stock",
    147: "stock",
    150: "stock",
    170: "asistan",
    200: "projects",
    201: "operations",
    202: "projects",
    210: "operations",
    250: "stock",
    300: "stock",
    313: "stock",
    314: "stock",
}


TECHNICAL_MENU_SECTIONS: Sequence[Tuple[str, Sequence[int]]] = (
    ("Servis Y\u00f6netimi", (40, 41, 62, 61, 30, 65, 201)),
    ("Servis Y\u00f6netim Ayar\u0131", (146, 145, 147, 140)),
    ("M\u00fc\u015fteri Hub", (21, 26, 25, 90, 120)),
    ("Proje Y\u00f6netimi", (200, 202)),
    ("Stok / Sipari\u015f", (50, 51, 66, 250, 300)),
    ("Teklif Y\u00f6netimi", (150, 313, 314)),
    ("Finans", (101, 105, 106, 115)),
    ("\u0130K ve Personel", (10,)),
    ("Sistem Yard\u0131mc\u0131lar\u0131", (130, 135, 160, 180, 261, 70)),
)


AUTOMOTIVE_MENU_SECTIONS: Sequence[Tuple[str, Sequence[int]]] = (
    ("Servis Y\u00f6netimi", (40, 210, 41, 62, 30)),
    ("Servis Y\u00f6netim Ayar\u0131", (146, 145, 147, 140)),
    ("M\u00fc\u015fteri Hub", (21, 26, 25, 90, 120)),
    ("Stok / Sipari\u015f", (60, 51, 66)),
    ("Teklif Y\u00f6netimi", (150, 313, 314)),
    ("Finans", (101, 105, 106, 115)),
    ("\u0130K ve Personel", (10,)),
    ("Sistem Yard\u0131mc\u0131lar\u0131", (130, 135, 160, 180, 261, 70)),
)


PAGE_WEB_ROUTES: Dict[int, str] = {
    10: "personnel",
    21: "customers",
    25: "contracts",
    26: "partners",
    30: "appointments",
    40: "dashboard",
    41: "service-status",
    50: "stock",
    51: "stock-locations",
    60: "stock",
    61: "field-map",
    62: "technician",
    65: "logistics",
    66: "loaner-devices",
    70: "support",
    90: "reminders",
    101: "accounting",
    105: "bank-accounts",
    106: "checks-notes",
    115: "e-invoice",
    120: "announcements",
    130: "settings",
    135: "logs",
    140: "service-defs",
    145: "brand-management",
    146: "product-groups",
    147: "report-templates",
    150: "offer-create",
    160: "knowledge-base",
    180: "backup",
    200: "projects",
    201: "service-reports",
    202: "project-archive",
    210: "vehicle-maintenance",
    250: "mobile-stock",
    261: "user-manual",
    300: "pc-builder",
    313: "offers",
    314: "offer-reports",
}


def get_menu_sections(sector: str) -> Sequence[Tuple[str, Sequence[int]]]:
    if str(sector or "").strip().lower() == "otomotiv":
        return AUTOMOTIVE_MENU_SECTIONS
    return TECHNICAL_MENU_SECTIONS


def iter_menu_page_ids(sector: str) -> Iterable[int]:
    for _title, page_ids in get_menu_sections(sector):
        yield from page_ids


def build_web_navigation(db, sector: str) -> List[dict]:
    groups: List[dict] = []
    for index, (title, page_ids) in enumerate(get_menu_sections(sector)):
        items = []
        for page_id in page_ids:
            if db and db.get_internal_setting(f"menu_visible_page_{page_id}", "1") != "1":
                continue
            label = PAGE_LABELS.get(page_id, f"Sayfa {page_id}")
            if db:
                custom = db.get_internal_setting(f"menu_label_page_{page_id}", "")
                label = str(custom or "").strip() or label
            items.append(
                {
                    "id": PAGE_WEB_ROUTES.get(page_id, f"page-{page_id}"),
                    "label": label,
                    "page_id": page_id,
                }
            )
        if items:
            groups.append(
                {
                    "id": f"group-{index}",
                    "title": title,
                    "items": items,
                }
            )
    return groups
