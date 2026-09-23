# -*- coding: utf-8 -*-

_TECHNICAL_STATUS_TILE_DEFS = [
    ("test", "Tamir Edilenler", "Tamir Edildi", "T", "#05A85B", "#008B4A"),
    ("tamirde", "Tamirde Olanlar", "Tamiri Devam Etmekte", "D", "#F39C12", "#C97700"),
    ("bekliyor", "\u0130\u015fleme Al\u0131nacaklar", "\u0130\u015fleme Al\u0131nmad\u0131", "\u0130", "#1E88E5", "#001A33"),
    ("iptal", "\u0130ptal / \u0130ade", "\u0130ptal \u0130ade", "X", "#E24A3B", "#B7372B"),
    ("kargo", "Kargoya Verilenler", "Kargoya Verildi", "K", "#D41462", "#B20F50"),
    ("teslim", "Teslim Edilenler", "Teslim Edildi", "E", "#0891B2", "#075985"),
    ("parca", "Par\u00e7a Bekleyenler", "Par\u00e7a Bekliyor", "P", "#0E7AB4", "#075F8D"),
    ("borclu", "Bor\u00e7lu Olanlar", "Borcu Var", "B", "#625DA8", "#4F4A8E"),
]

_AUTOMOTIVE_STATUS_TILE_DEFS = [
    ("test", "KONTROLÜ TAMAMLANAN", "Kontrol Tamamlandı", "K", "#05A85B", "#008B4A"),
    ("tamirde", "SERVİSTEKİ ARAÇLAR", "İş Emri Devam Ediyor", "S", "#F39C12", "#C97700"),
    ("bekliyor", "SIRAYA ALINACAKLAR", "Servise Alınmadı", "A", "#1E88E5", "#001A33"),
    ("iptal", "İPTAL / İADE", "İptal İade", "X", "#E24A3B", "#B7372B"),
    ("kargo", "DIŞ SERVİSE GİDENLER", "Dış Servise Verildi", "D", "#D41462", "#B20F50"),
    ("teslim", "TESLİM EDİLEN ARAÇLAR", "Teslim Edildi", "T", "#0891B2", "#075985"),
    ("parca", "PARÇA BEKLEYEN ARAÇ", "Parça Bekliyor", "P", "#0E7AB4", "#075F8D"),
    ("borclu", "BORÇLU ARAÇLAR", "Borcu Var", "B", "#625DA8", "#4F4A8E"),
]

_TECHNICAL_FILTER_BUTTONS = [
    ("add_device", "Cihaz Ekle", "+", "#7AC943", "add"),
    ("all", "Tüm Cihazlar", "=", "#B000FF", "filter"),
    ("today", "Randevulu", "R", "#D41462", "filter"),
    ("pending_approval", "Onay Bekleyen", "OK", "#795548", "filter"),
    ("test", "Test Sürecinde", "O", "#607D8B", "filter"),
    ("waiting", "İşleme Alınacak", ">", "#1E88E5", "filter"),
    ("active", "Tamirde", "*", "#F39C12", "filter"),
    ("done", "Teslim Edilen", "-", "#14B8D4", "filter"),
    ("part", "Parça Bekleyen", "P", "#0E7AB4", "filter"),
    ("debt", "Borçlu", "TL", "#625DA8", "filter"),
    ("cargo_waiting", "Kargosu Beklenen", "K", "#D41462", "filter"),
    ("invoiced", "Faturas\u0131 Kesilen", "F+", "#05A85B", "filter"),
    ("uninvoiced", "Faturas\u0131 Kesilmeyen", "F-", "#E24A3B", "filter"),
    ("external_out", "Onar\u0131ma Giden", "G", "#795548", "filter"),
    ("external_return", "Onar\u0131mdan Gelen", "D", "#0891B2", "filter"),
]

_AUTOMOTIVE_FILTER_BUTTONS = [
    ("add_device", "Araç Ekle", "+", "#7AC943", "add"),
    ("all", "Tüm Araçlar", "=", "#B000FF", "filter"),
    ("today", "Randevulu", "R", "#D41462", "filter"),
    ("pending_approval", "Onay Bekleyen", "OK", "#795548", "filter"),
    ("test", "Kontrol Sürecinde", "O", "#607D8B", "filter"),
    ("waiting", "Servise Alınacak", ">", "#1E88E5", "filter"),
    ("active", "Serviste", "*", "#F39C12", "filter"),
    ("done", "Teslim Edilen", "-", "#14B8D4", "filter"),
    ("part", "Parça Bekleyen", "P", "#0E7AB4", "filter"),
    ("debt", "Borçlu", "TL", "#625DA8", "filter"),
    ("cargo_waiting", "Kargosu Beklenen", "K", "#D41462", "filter"),
    ("invoiced", "Faturas\u0131 Kesilen", "F+", "#05A85B", "filter"),
    ("uninvoiced", "Faturas\u0131 Kesilmeyen", "F-", "#E24A3B", "filter"),
    ("external_out", "Onar\u0131ma Giden", "G", "#795548", "filter"),
    ("external_return", "Onar\u0131mdan Gelen", "D", "#0891B2", "filter"),
]

_TECHNICAL_TABLE_HEADERS = [
    "TAKİP NO", "İŞLEMLER", "MÜŞTERİ", "ÜRÜN GRUBU", "MARKA", "MODEL",
    "ALIŞ TARİHİ", "TESLİM TARİHİ", "SERVİS", "ÜCRET", "DURUM", "ACİLİYET",
]

_AUTOMOTIVE_TABLE_HEADERS = [
    "İŞ EMRİ NO", "İŞLEMLER", "MÜŞTERİ", "ARAÇ TÜRÜ", "MARKA", "MODEL",
    "GİRİŞ TARİHİ", "TESLİM TARİHİ", "SERVİS", "ÜCRET", "DURUM", "ÖNCELİK",
]

_AUTOMOTIVE_TABLE_HEADERS = [
    "\u0130\u015e EMR\u0130 NO", "\u0130\u015eLEMLER", "M\u00dc\u015eTER\u0130", "ARA\u00c7 T\u00dcR\u00dc", "MARKA", "MODEL",
    "G\u0130R\u0130\u015e TAR\u0130H\u0130", "TESL\u0130M DURUMU", "SERV\u0130S", "\u00dcCRET", "DURUM", "\u00d6NCEL\u0130K",
]

_TECHNICAL_TABLE_TITLES = {
    "all": "Servis Listesi",
    "today": "Randevulu Servisler",
    "pending_approval": "Onay Bekleyen Servisler",
    "test": "Test Sürecindeki Cihazlar",
    "waiting": "İşleme Alınacak Cihazlar",
    "active": "Tamirdeki Cihazlar",
    "done": "Teslim Edilen Cihazlar",
    "part": "Parça Bekleyen Cihazlar",
    "debt": "Borçlu Servisler",
    "cargo_waiting": "Kargosu Beklenen Servisler",
    "invoiced": "Faturas\u0131 Kesilen Servisler",
    "uninvoiced": "Faturas\u0131 Kesilmeyen Servisler",
    "external_out": "Onar\u0131ma Giden Servisler",
    "external_return": "Onar\u0131mdan Gelen Servisler",
}

_AUTOMOTIVE_TABLE_TITLES = {
    "all": "İş Emri Listesi",
    "today": "Randevulu Araçlar",
    "pending_approval": "Onay Bekleyen İş Emirleri",
    "test": "Kontrol Sürecindeki Araçlar",
    "waiting": "Servise Alınacak Araçlar",
    "active": "Servisteki Araçlar",
    "done": "Teslim Edilen Araçlar",
    "part": "Parça Bekleyen Araçlar",
    "debt": "Borçlu Araçlar",
    "cargo_waiting": "Kargosu Beklenen Ara\u00e7lar",
    "invoiced": "Faturas\u0131 Kesilen Ara\u00e7lar",
    "uninvoiced": "Faturas\u0131 Kesilmeyen Ara\u00e7lar",
    "external_out": "Onar\u0131ma Giden Ara\u00e7lar",
    "external_return": "Onar\u0131mdan Gelen Ara\u00e7lar",
}


def get_status_tile_defs(sector):
    return _AUTOMOTIVE_STATUS_TILE_DEFS if sector == "otomotiv" else _TECHNICAL_STATUS_TILE_DEFS


def get_filter_button_defs(sector):
    return _AUTOMOTIVE_FILTER_BUTTONS if sector == "otomotiv" else _TECHNICAL_FILTER_BUTTONS


def get_table_headers(sector):
    return _AUTOMOTIVE_TABLE_HEADERS if sector == "otomotiv" else _TECHNICAL_TABLE_HEADERS


def get_table_title(sector, category="all"):
    titles = _AUTOMOTIVE_TABLE_TITLES if sector == "otomotiv" else _TECHNICAL_TABLE_TITLES
    return titles.get(category, titles["all"])


def get_record_kind_label(sector):
    return "Araç" if sector == "otomotiv" else "Cihaz"


def get_empty_state_message(sector):
    return "Bu filtrede araç bulunmuyor." if sector == "otomotiv" else "Bu filtrede cihaz bulunmuyor."
