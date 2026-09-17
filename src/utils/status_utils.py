# -*- coding: utf-8 -*-

import unicodedata


CANONICAL_DEVICE_STATUSES = [
    "Bekliyor",
    "Tamirde",
    "Parça Bekliyor",
    "Test Sürecinde",
    "Teslim Edildi",
    "İptal",
]


STATUS_ALIASES = {
    "Bekliyor": "Bekliyor",
    "Beklemede": "Bekliyor",
    "İşleme Alınacak": "Bekliyor",
    "Isleme Alinacak": "Bekliyor",
    "İşleme Alınacak": "Bekliyor",
    "Kayit": "Bekliyor",
    "Kayıt": "Bekliyor",
    "Kayıt": "Bekliyor",
    "Yeni Kayit": "Bekliyor",
    "Yeni Kayıt": "Bekliyor",
    "Yeni Kayıt": "Bekliyor",
    "None": "Bekliyor",
    "NONE": "Bekliyor",
    "Bilinmiyor": "Bekliyor",
    None: "Bekliyor",
    "Tamirde": "Tamirde",
    "Serviste": "Tamirde",
    "İşlemde": "Tamirde",
    "Islemde": "Tamirde",
    "İşlemde": "Tamirde",
    "Onarımda": "Tamirde",
    "Onarımda": "Tamirde",
    "Onarimda": "Tamirde",
    "Parça Bekliyor": "Parça Bekliyor",
    "Parca Bekliyor": "Parça Bekliyor",
    "Parça Bekliyor": "Parça Bekliyor",
    "Sipariş Geçildi": "Parça Bekliyor",
    "Siparis Gecildi": "Parça Bekliyor",
    "Sipari\u00c5\u0178 Geçildi": "Parça Bekliyor",
    "Parça": "Parça Bekliyor",
    "Parca": "Parça Bekliyor",
    "Parça": "Parça Bekliyor",
    "Test Sürecinde": "Test Sürecinde",
    "Test Surecinde": "Test Sürecinde",
    "Test Sürecinde": "Test Sürecinde",
    "Test Aşaması": "Test Sürecinde",
    "Test Asamasi": "Test Sürecinde",
    "Test A\u00c5\u0178aması": "Test Sürecinde",
    "Kontrol Ediliyor": "Test Sürecinde",
    "Onay Bekleyen": "Test Sürecinde",
    "Onay Bekliyor": "Test Sürecinde",
    "Kabul Edildi": "Bekliyor",
    "Hazır": "Teslim Edildi",
    "Hazir": "Teslim Edildi",
    "Hazır": "Teslim Edildi",
    "Bitti": "Teslim Edildi",
    "Tamamlandı": "Teslim Edildi",
    "Tamamlandı": "Teslim Edildi",
    "Tamamlandi": "Teslim Edildi",
    "Tamir Edildi": "Teslim Edildi",
    "Teslime Hazır": "Teslim Edildi",
    "Teslime Hazir": "Teslim Edildi",
    "Teslime Hazır": "Teslim Edildi",
    "Teslim": "Teslim Edildi",
    "Teslim Edildi": "Teslim Edildi",
    "Teslim Alındı": "Teslim Edildi",
    "Teslim Alindi": "Teslim Edildi",
    "Teslim Alındı": "Teslim Edildi",
    "Müşteriye Teslim": "Teslim Edildi",
    "Musteriye Teslim": "Teslim Edildi",
    "Müşteriye Teslim": "Teslim Edildi",
    "Kapandı": "Teslim Edildi",
    "Kapandi": "Teslim Edildi",
    "Kapandı": "Teslim Edildi",
    "Kapalı": "Teslim Edildi",
    "Kapali": "Teslim Edildi",
    "Kapalı": "Teslim Edildi",
    "İptal": "İptal",
    "Iptal": "İptal",
    "İptal": "İptal",
    "İptal Edildi": "İptal",
    "Iptal Edildi": "İptal",
    "İptal Edildi": "İptal",
    "İptal İade": "İptal",
    "Iptal Iade": "İptal",
    "İptal İade": "İptal",
    "İade Edildi": "İptal",
    "Iade Edildi": "İptal",
    "İade Edildi": "İptal",
}

STATUS_ALIASES["Test Ediliyor"] = "Test S\u00fcrecinde"
STATUS_ALIASES.update({
    "S\u0131raya Al\u0131nacak": "Bekliyor",
    "Siraya Alinacak": "Bekliyor",
    "Servise Al\u0131nacak": "Bekliyor",
    "Servise Alinacak": "Bekliyor",
})


def _status_key(status):
    if status is None:
        return ""
    value = str(status).strip()
    value = (
        value.replace("İ", "I")
        .replace("ı", "i")
        .replace("İ", "I")
        .replace("ı", "i")
    )
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.casefold().split())


_STATUS_ALIASES_BY_KEY = {
    _status_key(alias): canonical
    for alias, canonical in STATUS_ALIASES.items()
    if alias is not None
}


def normalize_device_status(status):
    value = str(status).strip() if status is not None else None
    if value in STATUS_ALIASES:
        return STATUS_ALIASES[value]
    return _STATUS_ALIASES_BY_KEY.get(_status_key(value), value or "Bekliyor")


def is_active_device_status(status):
    return normalize_device_status(status) not in {"Teslim Edildi", "İptal"}
