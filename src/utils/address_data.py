# -*- coding: utf-8 -*-

"""
Balıkesir - Gönen Adres Veritabanı
Mahalleler, caddeler ve sokaklar için otomatik tamamlama verisi
"""

# Gönen Mahalleleri
GONEN_MAHALLELER = [
    "Akçaköy",
    "Atatürk",
    "Bahçelievler",
    "Cumhuriyet",
    "Dere",
    "Esentepe",
    "Fevzipaşa",
    "Gökçeağaç",
    "Güzelyurt",
    "İhsaniye",
    "Kale",
    "Karaağaç",
    "Karacaören",
    "Kaynarca",
    "Koyunbaba",
    "Kurşunlu",
    "Medet",
    "Müsellim",
    "Sarıköy",
    "Şahinler",
    "Tavşançalı",
    "Ören",
    "Yeniköy"
]

# Gönen Ana Caddeleri
GONEN_CADDELER = [
    "Atatürk Caddesi",
    "Cumhuriyet Caddesi",
    "İstiklal Caddesi",
    "Kaplıca Caddesi",
    "Sahil Caddesi",
    "İnönü Caddesi",
    "Fevzipaşa Caddesi",
    "Millet Caddesi",
    "Hürriyet Caddesi",
    "Barbaros Caddesi",
    "Çeşme Caddesi",
    "Altın Caddesi",
    "Yeni Caddesi",
    "Park Caddesi",
    "Hastane Caddesi"
]

# Balıkesir İlçeleri
BALIKESIR_ILCELER = [
    "Altıeylül",
    "Karesi",
    "Ayvalık",
    "Balya",
    "Bandırma",
    "Bigadiç",
    "Burhaniye",
    "Dursunbey",
    "Edremit",
    "Erdek",
    "Gömeç",
    "Gönen",
    "Havran",
    "İvrindi",
    "Kepsut",
    "Manyas",
    "Marmara",
    "Savaştepe",
    "Sındırgı",
    "Susurluk"
]

def get_mahalleler(ilce="Gönen"):
    """İlçeye göre mahalle listesi döndürür"""
    if ilce == "Gönen":
        return GONEN_MAHALLELER
    return []

def get_caddeler(ilce="Gönen", mahalle=None):
    """İlçe ve mahalleye göre cadde listesi döndürür"""
    _ = mahalle
    if ilce == "Gönen":
        return GONEN_CADDELER
    return []

def get_ilceler():
    """Balıkesir ilçelerini döndürür"""
    return BALIKESIR_ILCELER
