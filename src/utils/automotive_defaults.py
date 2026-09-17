# -*- coding: utf-8 -*-

"""Shared automotive presets for technician panel and quick note editor."""

AUTOMOTIVE_ACCESSORY_CATEGORY = "Otomotiv Araç Kabul"
AUTOMOTIVE_FAULT_CATEGORY = "Otomotiv Arıza Hızlı Seçimi"
AUTOMOTIVE_PROCESS_CATEGORY = "Otomotiv İşlem Detayı"
AUTOMOTIVE_CHECKLIST_CATEGORY = "Otomotiv Kontrol Listesi"

AUTOMOTIVE_CATEGORIES = [
    AUTOMOTIVE_FAULT_CATEGORY,
    AUTOMOTIVE_PROCESS_CATEGORY,
    "Gizli Not",
    AUTOMOTIVE_ACCESSORY_CATEGORY,
    AUTOMOTIVE_CHECKLIST_CATEGORY,
]

AUTOMOTIVE_PRESET = {
    AUTOMOTIVE_FAULT_CATEGORY: [
        "MOTOR ARIZA LAMBASI YANIYOR",
        "YAĞ KAÇAĞI VAR",
        "ŞANZIMAN GEÇİŞ SORUNU",
        "FREN SESİ VAR",
        "DİREKSİYON TİTREŞİMİ",
        "HARARET YÜKSELİYOR",
        "MARŞ BASIYOR ÇALIŞMIYOR",
        "AKÜ ZAYIF / ŞARJ SORUNU",
    ],
    AUTOMOTIVE_PROCESS_CATEGORY: [
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
    AUTOMOTIVE_ACCESSORY_CATEGORY: [
        "RUHSAT",
        "YEDEK ANAHTAR",
        "STEPNE",
        "BİJON ANAHTARI",
        "KRİKO",
        "SERVİS KİTAPÇIĞI",
    ],
    AUTOMOTIVE_CHECKLIST_CATEGORY: [
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

APPROVAL_STATUS_TO_DB = {label: value for label, value in APPROVAL_STATUS_CHOICES}
APPROVAL_STATUS_FROM_DB = {value: label for label, value in APPROVAL_STATUS_CHOICES}


def approval_label_to_db(value):
    text = str(value or "").strip()
    return APPROVAL_STATUS_TO_DB.get(text, text or "Bekleme")


def approval_db_to_label(value):
    text = str(value or "").strip()
    return APPROVAL_STATUS_FROM_DB.get(text, text or "Beklemede")


def ensure_automotive_fast_notes(db):
    """Seed missing automotive note categories without replacing user data."""
    inserted = 0
    for category, labels in AUTOMOTIVE_PRESET.items():
        if db.get_fast_notes(category):
            continue
        for order, label in enumerate(labels):
            db.cursor.execute(
                "INSERT INTO fast_notes "
                "(category, label, is_active, display_order) VALUES (?, ?, 1, ?)",
                (category, label, order),
            )
            inserted += 1
    if inserted:
        db.conn.commit()
    return inserted
