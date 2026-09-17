# -*- coding: utf-8 -*-

DEFAULT_TECHNICAL_SERVICE_PROFILE = "Bilgisayar"

TECHNICAL_SERVICE_PROFILE_ORDER = [
    "Bilgisayar",
    "Cep Telefonu",
    "Akıllı Ev",
    "Güvenlik Sistemleri",
]

TECHNICAL_SERVICE_BASE_CATEGORIES = [
    "Arıza Hızlı Seçimi",
    "İşlem Detayı",
    "Gizli Not",
    "Aksesuar",
    "Cihaz Testi",
]

TECHNICAL_SERVICE_PROFILE_PRESETS = {
    "Bilgisayar": {
        "Arıza Hızlı Seçimi": [
            "GÖRÜNTÜ YOK",
            "AÇILMIYOR",
            "ŞARJ OLMUYOR",
            "ISINMA / FAN SESİ",
            "YAVAŞ ÇALIŞIYOR",
            "MAVİ EKRAN",
            "KLAVYE ÇALIŞMIYOR",
            "PORT / SOKET SORUNU",
        ],
        "İşlem Detayı": [
            "FORMAT ATILDI",
            "PARÇA DEĞİŞTİ",
            "TEMİZLİK YAPILDI",
            "TEST EDİLİYOR",
            "ONAY BEKLİYOR",
        ],
        "Gizli Not": [
            "TEST OK",
            "VERİ YEDEKLENDİ",
            "SIVI TEMASI ŞÜPHELİ",
            "ACİL TESLİM",
        ],
        "Aksesuar": [
            "Güç Adaptörü",
            "Şarj Kablosu",
            "HDMI / Görüntü Kablosu",
            "Mouse",
            "Klavye",
            "Taşıma Çantası",
        ],
        "Cihaz Testi": [
            "LCD Görüntü",
            "Açılış",
            "Klavye",
            "Touchpad",
            "USB Portları",
            "Fan / Soğutma",
            "Batarya",
            "Wifi",
            "Bluetooth",
            "Webcam",
            "Hoparlör",
            "Mikrofon",
        ],
    },
    "Cep Telefonu": {
        "Arıza Hızlı Seçimi": [
            "EKRAN KIRIK",
            "SIVI TEMAS",
            "BATARYA ŞİŞİK",
            "ŞARJ ALMIYOR",
            "KAPANDI AÇILMIYOR",
            "KAMERA SORUNU",
            "SES GELMİYOR",
            "MİKROFON ÇALIŞMIYOR",
        ],
        "İşlem Detayı": [
            "Ekran Değişti",
            "Batarya Değişti",
            "Soket Değişti",
            "Yazılım Güncellendi",
            "Test Ediliyor",
        ],
        "Gizli Not": [
            "TEST OK",
            "FACE ID KONTROL",
            "VERİ YEDEĞİ ALINDI",
            "ACİL TESLİM",
        ],
        "Aksesuar": [
            "SIM Kart",
            "SD Kart",
            "Kılıf",
            "Şarj Aleti",
            "Kutu",
            "Kablo",
        ],
        "Cihaz Testi": [
            "Dokunmatik Ekran",
            "LCD Görüntü",
            "Ön Kamera",
            "Arka Kamera",
            "Ahize (İç Ses)",
            "Hoparlör (Dış Ses)",
            "Mikrofon",
            "Şarj Soketi",
            "WIFI Bağlantısı",
            "Bluetooth",
            "FaceID / Parmak İzi",
            "Yakınlık Sensörü",
            "Sim Kart / Şebeke",
            "Titreşim",
            "Fiziksel Tuşlar",
            "Kasa Durumu",
        ],
    },
    "Akıllı Ev": {
        "Arıza Hızlı Seçimi": [
            "CİHAZ ENERJİ ALMIYOR",
            "AĞA BAĞLANMIYOR",
            "SENSÖR TEPKİ VERMİYOR",
            "UYGULAMA EŞLEŞMİYOR",
            "RÖLE ÇALIŞMIYOR",
            "SES KOMUTU ALGILAMIYOR",
        ],
        "İşlem Detayı": [
            "RESET ATILDI",
            "FİRMWARE GÜNCELLENDİ",
            "AĞ AYARLARI YENİLENDİ",
            "MODÜL DEĞİŞTİ",
            "SAHA TESTİ YAPILDI",
        ],
        "Gizli Not": [
            "MOBİL UYGULAMA ŞİFRESİ GEREKİYOR",
            "WIFI ŞİFRESİ DOĞRULANACAK",
            "TEST OK",
            "SAHA ZİYARETİ GEREKEBİLİR",
        ],
        "Aksesuar": [
            "Adaptör",
            "Montaj Aparatı",
            "Gateway",
            "Sensör",
            "Kurulum Kılavuzu",
            "Data Kablosu",
        ],
        "Cihaz Testi": [
            "Enerji",
            "Wifi",
            "Bluetooth",
            "Zigbee / Hub",
            "Sensör Okuması",
            "Röle Çıkışı",
            "Mobil Uygulama Eşleşmesi",
            "Sesli Asistan Eşleşmesi",
        ],
    },
    "Güvenlik Sistemleri": {
        "Arıza Hızlı Seçimi": [
            "KAMERA GÖRÜNTÜ VERMİYOR",
            "KAYIT YOK",
            "ADAPTÖR ARIZASI",
            "NETWORK BAĞLANTISI YOK",
            "DISK HATASI",
            "GECE GÖRÜŞÜ ÇALIŞMIYOR",
        ],
        "İşlem Detayı": [
            "MONTAJ YAPILDI",
            "KAYIT CİHAZI TEST EDİLDİ",
            "KEŞİF BEKLİYOR",
            "PARÇA BEKLİYOR",
            "UZAK BAĞLANTI AYARLANDI",
        ],
        "Gizli Not": [
            "ŞİFRE PAYLAŞILDI",
            "SAHA TESTİ GEREKİYOR",
            "KABLOLAMA KONTROL EDİLECEK",
            "ACİL SAHA ÇIKIŞI",
        ],
        "Aksesuar": [
            "Adaptör",
            "Montaj Ayağı",
            "BNC / PoE Kablo",
            "Kumanda",
            "Sensör",
            "Kurulum Notu",
        ],
        "Cihaz Testi": [
            "Görüntü",
            "Kayıt",
            "Gece Görüşü",
            "Network",
            "Disk Sağlığı",
            "Alarm Girişi",
            "Uzaktan Erişim",
            "Güç Adaptörü",
        ],
    },
}


def _repair_legacy_text(value):
    """Repair UTF-8 text that was previously decoded as Latin-1."""
    if not isinstance(value, str):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _repair_profile_presets(presets):
    return {
        _repair_legacy_text(profile): {
            _repair_legacy_text(category): [
                _repair_legacy_text(label) for label in labels
            ]
            for category, labels in categories.items()
        }
        for profile, categories in presets.items()
    }


TECHNICAL_SERVICE_PROFILE_ORDER = [
    _repair_legacy_text(value) for value in TECHNICAL_SERVICE_PROFILE_ORDER
]
TECHNICAL_SERVICE_BASE_CATEGORIES = [
    _repair_legacy_text(value) for value in TECHNICAL_SERVICE_BASE_CATEGORIES
]
TECHNICAL_SERVICE_PROFILE_PRESETS = _repair_profile_presets(
    TECHNICAL_SERVICE_PROFILE_PRESETS
)


def normalize_technical_service_profile(profile_name: str | None) -> str:
    value = (profile_name or "").strip()
    if value in TECHNICAL_SERVICE_PROFILE_PRESETS:
        return value
    return DEFAULT_TECHNICAL_SERVICE_PROFILE


def build_profile_category(profile_name: str, base_category: str) -> str:
    profile = normalize_technical_service_profile(profile_name)
    return f"Teknik Servis::{profile}::{base_category}"


def get_profile_preset(profile_name: str) -> dict:
    profile = normalize_technical_service_profile(profile_name)
    return TECHNICAL_SERVICE_PROFILE_PRESETS.get(profile, {})


def get_profile_labels(profile_name: str, base_category: str) -> list[str]:
    preset = get_profile_preset(profile_name)
    return list(preset.get(base_category, []))
