# -*- coding: utf-8 -*-
# Bu dosya: StockImportParser için tüm sabit tanımları.
# _SipConstants — StockImportParser'a mixin olarak eklenir.


class _SipConstants:
    TESSERACT_CANDIDATES = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    FIELD_ORDER = [
        "name",
        "brand",
        "category",
        "condition",
        "unit",
        "stock",
        "purchase_price",
        "price",
        "line_total",
        "currency",
        "code",
        "oem_code",
        "equivalent_code",
        "compatible_models",
        "vehicle_brand",
        "vehicle_model",
        "supplier",
        "position",
        "shelf",
        "desc",
    ]

    FIELD_LABELS = {
        "name": "Urun Adi",
        "brand": "Marka",
        "category": "Kategori",
        "stock": "Stok Miktari (Miktar)",
        "purchase_price": "Alis Fiyati (Birim)",
        "price": "Satis Fiyati",
        "line_total": "Mal Hizmet Tutari",
        "currency": "PB",
        "code": "Kod",
        "oem_code": "OEM",
        "equivalent_code": "Muadil",
        "compatible_models": "Marka / Model",
        "vehicle_brand": "Arac Marka",
        "vehicle_model": "Arac Model",
        "supplier": "Tedarikci",
        "position": "Parca Konumu",
        "shelf": "Raf",
        "desc": "Aciklama",
        "condition": "Urun Durumu",
        "unit": "Urun Birim",
    }

    COLUMN_ALIASES = {
        "urun adi": "name", "urun": "name", "ad": "name", "adi": "name",
        "name": "name", "product name": "name", "product": "name",
        "item": "name", "item name": "name", "urunadi": "name",
        "parca adi": "name", "parca": "name", "malzeme": "name",
        "mal hizmet": "name", "mal/hizmet": "name", "hizmet": "name",
        "aciklama": "name", "açıklama": "name", "description": "name",
        "ticari mal": "name", "ticariMal": "name", "kalem": "name",
        "kalemleri": "name", "urun/hizmet": "name", "urun / hizmet": "name",
        "mal / hizmet": "name", "cins": "name", "cins/marka": "name",
        "tanim": "name", "tanım": "name", "urun tanimi": "name",
        "parca tanimi": "name", "service": "name", "goods": "name",
        "goods/service": "name",
        "marka": "brand", "brand": "brand", "marka model": "brand",
        "model": "compatible_models", "uyumlu marka / model": "compatible_models",
        "uyumlu arac / motor": "compatible_models", "uyumlu arac": "compatible_models",
        "kategori": "category", "category": "category", "cat": "category",
        "urun grubu": "category", "urun gurubu": "category",
        "parca kategorisi": "category",
        "stok": "stock", "miktar": "stock", "stock": "stock",
        "quantity": "stock", "adet": "stock", "qty": "stock",
        "miktar/adet": "stock", "miktar / adet": "stock",
        "siparis miktari": "stock", "mal miktari": "stock",
        "teslim miktari": "stock", "pcs": "stock", "piece": "stock",
        "count": "stock", "no": "stock", "no.": "stock",
        "sira": "stock",
        "urun durumu": "condition", "condition": "condition",
        "urun birim": "unit", "unit": "unit",
        "alis fiyati": "purchase_price", "alis": "purchase_price",
        "purchase price": "purchase_price", "cost": "purchase_price",
        "maliyet": "purchase_price", "birim maliyet": "purchase_price",
        "birim fiyat": "purchase_price", "fatura birim fiyat": "purchase_price",
        "mal hizmet tutari": "line_total", "mal/hizmet tutari": "line_total",
        "mal hizmet tutarı": "line_total", "mal/hizmet tutarı": "line_total",
        "tutar": "line_total",
        "birim fiyati": "purchase_price", "birim alis fiyati": "purchase_price",
        "birim bedel": "purchase_price", "bedel": "purchase_price",
        "unit price": "purchase_price", "unit cost": "purchase_price",
        "fiyat": "purchase_price", "kdvsiz birim fiyat": "purchase_price",
        "kdv haric birim fiyat": "purchase_price", "net birim fiyat": "purchase_price",
        "net fiyat": "purchase_price", "birim tutari": "purchase_price",
        "birim tutar": "purchase_price",
        "mal/hizmet birim fiyati": "purchase_price",
        "mal hizmet birim fiyati": "purchase_price",
        "toplam fiyat": "line_total", "line total": "line_total",
        "amount": "line_total",
        "satis fiyati": "price", "satis": "price", "sale price": "price",
        "price": "price", "selling price": "price",
        "barkod": "code", "barcode": "code", "kod": "code", "code": "code",
        "sku": "code", "stok / parca kodu": "code", "stok kodu": "code",
        "urun kodu": "code", "parca kodu": "code",
        "oem kod": "oem_code", "oem": "oem_code",
        "muadil kod": "equivalent_code", "muadil": "equivalent_code",
        "alternatif kod": "equivalent_code",
        "raf": "shelf", "konum": "shelf", "shelf": "shelf",
        "location": "shelf", "raf / goz": "shelf",
        "not": "desc", "notlar": "desc", "notes": "desc", "desc": "desc",
        "pb": "currency", "para birimi": "currency", "currency": "currency",
        "birim": "currency", "doviz": "currency", "doviz birimi": "currency",
        "döviz": "currency", "döviz birimi": "currency",
        "para br": "currency", "para br.": "currency", "vergi tipi": "currency",
        "arac marka": "vehicle_brand", "arac markasi": "vehicle_brand",
        "vehicle brand": "vehicle_brand",
        "arac model": "vehicle_model", "arac modeli": "vehicle_model",
        "vehicle model": "vehicle_model",
        "tedarikci": "supplier", "tedarikçi": "supplier", "supplier": "supplier",
        "satici": "supplier",
        "parca konumu": "position", "parca pozisyonu": "position",
        "pozisyon": "position", "position": "position",
    }

    LABEL_ALIASES = {
        "urun adi": "name", "parca adi": "name", "ad": "name",
        "mal hizmet": "name", "mal/hizmet": "name", "mal / hizmet": "name",
        "urun/hizmet": "name", "ticari mal": "name", "kalem": "name",
        "tanim": "name", "tanım": "name", "cins": "name",
        "marka": "brand", "marka model": "brand",
        "model": "compatible_models", "kategori": "category",
        "urun grubu": "category", "urun gurubu": "category", "urun durumu": "condition",
        "condition": "condition", "urun birim": "unit", "unit": "unit",
        "parca kategorisi": "category",
        "adet": "stock", "miktar": "stock", "miktar/adet": "stock",
        "miktar / adet": "stock", "stok": "stock", "qty": "stock",
        "quantity": "stock",
        "alis fiyati": "purchase_price", "birim alis fiyati": "purchase_price",
        "birim fiyat": "purchase_price", "birim fiyati": "purchase_price",
        "birim bedel": "purchase_price", "fiyat": "purchase_price",
        "bedel": "purchase_price", "tutar": "line_total",
        "birim tutar": "purchase_price", "birim tutari": "purchase_price",
        "mal hizmet tutari": "line_total", "mal/hizmet tutari": "line_total",
        "mal hizmet tutarı": "line_total", "mal/hizmet tutarı": "line_total",
        "mal hizmet birim fiyati": "purchase_price",
        "mal/hizmet birim fiyati": "purchase_price",
        "kdvsiz birim fiyat": "purchase_price", "net birim fiyat": "purchase_price",
        "unit price": "purchase_price", "amount": "line_total",
        "satis fiyati": "price", "barkod": "code", "stok kodu": "code",
        "parca kodu": "code", "oem kod": "oem_code",
        "muadil kod": "equivalent_code", "uyumlu arac": "compatible_models",
        "uyumlu arac / motor": "compatible_models",
        "raf": "shelf", "konum": "shelf", "aciklama": "desc", "not": "desc",
        "para birimi": "currency", "pb": "currency", "doviz": "currency",
        "doviz birimi": "currency", "döviz": "currency", "para br": "currency",
        "arac marka": "vehicle_brand", "arac model": "vehicle_model",
        "tedarikci": "supplier", "parca konumu": "position",
    }

    DOCUMENT_LABEL_ALIASES = {
        "senaryo": "invoice_scenario",
        "fatura tipi": "invoice_type",
        "fatura no": "invoice_no",
        "fatura tarihi": "invoice_date",
        "fatura tipi / senaryo": "invoice_type",
    }

    IMAGE_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".ppm",
    }
    SUPPORTED_EXTENSIONS = {
        ".xlsx", ".xls", ".csv", ".pdf", ".docx", ".xml",
        ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".ppm",
    }
    LOW_CONFIDENCE_THRESHOLD = 0.55

    BRAND_HINTS = {
        "dahua", "hikvision", "tp-link", "tplink", "ubiquiti", "mikrotik",
        "cisco", "huawei", "zyxel", "siemens", "schneider", "abb", "philips",
        "samsung", "lg", "sony", "bosch", "intel", "amd", "asus", "msi",
        "gigabyte", "corsair", "kingston", "crucial", "seagate", "wd",
        "sandisk", "lenovo", "dell", "hp", "acer", "canon", "epson",
        "brother", "xiaomi", "oppo", "vivo", "apple", "baseus", "anker",
        "honeywell", "paradox", "ajax", "sline", "sunny",
    }

    GENERIC_NAME_TOKENS = {
        "adet", "stok", "parca", "urun", "hizmet", "kablo", "set",
        "paket", "genel", "aciklama", "model", "kod", "oem",
    }

    PROFILE_FIELDS = {
        "default": [
            "name", "brand", "category", "condition", "unit", "stock",
            "purchase_price", "price",
            "line_total", "currency", "code", "oem_code", "equivalent_code",
            "compatible_models", "vehicle_brand", "vehicle_model", "supplier",
            "position", "shelf", "desc",
        ],
        "teknik_servis": [
            "name", "brand", "category", "condition", "unit", "stock",
            "purchase_price", "price",
            "line_total", "currency", "code", "compatible_models", "shelf", "desc",
        ],
        "otomotiv": [
            "name", "brand", "category", "condition", "unit", "stock",
            "purchase_price", "price",
            "line_total", "currency", "code", "oem_code", "equivalent_code",
            "compatible_models", "vehicle_brand", "vehicle_model", "supplier",
            "position", "shelf", "desc",
        ],
    }

    INVOICE_SKIP_LABELS = (
        "toplam tutar", "hesaplanan kdv", "vergiler dahil toplam tutar",
        "odenecek tutar", "ödenecek tutar", "mal hizmet toplam tutari",
        "toplam iskonto", "kdv tutari", "kdv orani", "kdv matrah", "matrah",
        "kdv", "vergi tutari", "vergi matrahi", "tevkifat", "tevkifat tutari",
        "diger vergiler", "diğer vergiler", "stopaj", "iskonto", "iskonto tutari",
        "indirim", "indirim tutari", "genel toplam", "ara toplam", "net toplam",
        "brut toplam",
        "odeme notu", "ödeme notu", "odeme kosulu", "ödeme koşulu",
        "odeme sekli", "ödeme şekli", "vade tarihi", "siparis tarihi",
        "fatura tarihi", "teslim tarihi", "ihracat kayit no", "irsaliye no",
        "irsaliye tarihi", "sevk tarihi",
        "vkn", "mersis", "web sitesi", "vergi dairesi", "firma tipi",
        "fatura no", "belge no", "ettn", "siparis no", "referans no",
        "e-fatura", "e-arsiv", "e-irsaliye",
        "tarih", "seri", "sira", "satici", "alici", "gonderen",
        "alıcı", "gönderen",
        "doviz kuru", "döviz kuru", "doviz", "kur", "sayın", "sayin",
        "tel", "telefon", "fax", "e-posta", "eposta", "iban", "banka",
        "hesap no", "swift", "garanti", "vakifbank", "qnb", "halkbankasi",
        "akbank", "isbank", "ziraat", "yapi kredi", "tckn", "tc kimlik",
        "unvan", "adres", "sanayi tic", "limited sirketi", "anonim sirketi",
        "ltd sti", "a s ", "mal hizmet toplam", "vergiler dahil", "odenecek",
        "yazı ile", "yazi ile", "aciklama aras", "cari bakiye", "dvz kur",
        "fatura vadesi",
        "ioplam iutarg", "ioplam tutar", "malhizmet ioplam",
    )

    # Fatura tablo header satırını tespit etmek için kullanılan anahtar kelimeler
    _INVOICE_HEADER_KEYS = (
        ("mal hizmet", "miktar"),
        ("mal hizmet", "birim fiyat"),
        ("mal hizmet", "tutar"),
        ("aciklama", "miktar"),
        ("aciklama", "birim fiyat"),
        ("urun", "miktar"),
        ("urun", "birim fiyat"),
        ("kalem", "miktar"),
        ("kalem", "birim fiyat"),
    )

    # Fatura tablo sonu (özet) satırlarını tespit etmek için
    _INVOICE_FOOTER_KEYS = (
        "mal hizmet toplam", "malhizmet toplam",
        "malhizmet ioplam",  # OCR bozukluk: "Toplam" → "Ioplam"
        "toplam tutar", "kdv matrahi", "odenecek tutar",
        "hesaplanan kdv", "vergiler dahil", "genel toplam", "net toplam",
        "ioplam iutarg",    # OCR: "Toplam Tutarı" bozuk okunabilir
        "ioplam tutar",
    )
