"""Shared existing desktop page permissions for account editors and previews."""

import json

USER_PERMISSION_SECTIONS = (
    ("GENEL", ((40, "Genel Bak\u0131\u015f"),)),
    ("SERV\u0130S OPERASYON", (
        (41, "Durum Paneli"), (62, "Teknisyen Paneli"),
        (61, "Saha Haritas\u0131"), (30, "Randevular"),
        (65, "Lojistik & Garanti Y\u00f6netimi"),
        (201, "\u0130\u015f/Servis Takibi Raporlar\u0131"), (170, "AI Asistan"),
    )),
    ("M\u00dc\u015eTER\u0130", (
        (21, "M\u00fc\u015fteri Listesi"), (26, "\u00c7al\u0131\u015fma Ortaklar\u0131"),
        (25, "S\u00f6zle\u015fmeler"), (90, "Hat\u0131rlat\u0131c\u0131lar"), (120, "Duyurular"),
    )),
    ("T\u0130CAR\u0130", (
        (200, "Proje Y\u00f6netimi"), (202, "Proje Ar\u015fivi"),
        (50, "Stok Y\u00f6netimi"), (60, "Ara\u00e7 Par\u00e7a Sto\u011fu"),
        (150, "Sales Hub"), (140, "Hizmet Tan\u0131mlar\u0131"),
        (146, "\u00dcr\u00fcn Grubu Y\u00f6netimi"),
        (147, "Rapor C\u00fcmle Kal\u0131plar\u0131"),
        (145, "Cihaz Bilgisi & Markalar"), (66, "Emanet (Konsinye) Cihazlar"),
        (250, "Mobil Stok"), (300, "PC Builder"),
    )),
    ("F\u0130NANS", (
        (101, "Gelir / Gider"), (105, "Banka Hesaplar\u0131"),
        (106, "\u00c7ek / Senet"), (115, "E-Fatura"),
    )),
    ("PERSONEL", ((10, "Personel"),)),
    ("S\u0130STEM", (
        (160, "Bilgi Bankas\u0131"), (130, "Ayarlar"),
        (135, "Log Kay\u0131tlar\u0131"), (180, "Yedekleme"),
        (261, "Kullan\u0131m K\u0131lavuzu"), (70, "Destek"),
    )),
)


def parse_saved_page_permissions(raw_permissions):
    """Decode the existing saved formats; None means absent or invalid data."""
    if not raw_permissions:
        return None
    try:
        saved = json.loads(raw_permissions)
        if isinstance(saved, dict) and saved.get("mode") == "all":
            return {page_id for _section, entries in USER_PERMISSION_SECTIONS for page_id, _title in entries}
        if isinstance(saved, dict) and isinstance(saved.get("pages"), list):
            return {int(value) for value in saved["pages"]}
        if isinstance(saved, list):
            return {int(value) for value in saved}
        if isinstance(saved, dict):
            legacy_map = {
                "dashboard": {40}, "customers": {21, 25, 90, 120},
                "services": {41, 60, 61, 30}, "stock": {50, 140, 146, 147},
                "financial": {101}, "backup": {180}, "settings": {130}, "logs": {135},
            }
            return set().union(*(pages for key, pages in legacy_map.items() if saved.get(key)))
    except (TypeError, ValueError):
        return None
    return None
