from src.ui.pages.stock_page import StockPage


class AutomotiveStockPage(StockPage):
    CATEGORY_GROUPS = {
        "Bak\u0131m Sarflar\u0131": {
            "motor ya\u011f\u0131", "motor yagi", "\u015fanz\u0131man ya\u011f\u0131", "sanziman yagi",
            "hidrolik", "antifriz", "ya\u011f filtresi", "yag filtresi",
            "hava filtresi", "polen filtresi", "yak\u0131t filtresi", "yakit filtresi",
            "katk\u0131", "katki", "kimyasal", "sarf", "bak\u0131m kiti", "bakim kiti",
        },
        "Motor / Mekanik": {
            "motor", "mekanik", "triger", "devirdaim", "kay\u0131\u015f", "kayis",
            "kasnak", "buji", "ate\u015fleme", "atesleme", "so\u011futma", "sogutma",
            "turbo", "supap", "subap", "conta",
        },
        "Fren / Y\u00fcr\u00fcyen": {
            "fren", "balata", "disk", "amortis\u00f6r", "amortisor",
            "s\u00fcspansiyon", "suspansiyon", "rot", "sal\u0131ncak", "salincak",
            "rulman", "aks", "lastik", "jant", "y\u00fcr\u00fcyen", "yuruyen",
        },
        "Elektrik / Aksesuar": {
            "ak\u00fc", "aku", "far", "ampul", "sens\u00f6r", "sensor", "elektrik",
            "elektronik", "aksesuar", "teyp", "kamera", "mod\u00fcl", "modul",
        },
    }

    def _detect_automotive_mode(self):
        return True

    def _normalize_ui_texts(self):
        super()._normalize_ui_texts()
        self.hero_title.setText("Yedek Par\u00e7a Y\u00f6netimi")
        self.hero_subtitle.setText(
            "Otomotiv yedek par\u00e7a, stok hareketleri ve al\u0131m "
            "kay\u0131tlar\u0131n\u0131 bu alandan y\u00f6netin."
        )
        self.hero_badge.setText("OTOMOT\u0130V YEDEK PAR\u00c7A")
        self.tabs.setTabText(0, "Yedek Par\u00e7a Durumu")
        self.tabs.setTabText(1, "Par\u00e7a Hareketleri")
        if hasattr(self, "tab_guide"):
            self.tabs.setTabText(
                self.tabs.indexOf(self.tab_guide), "Nas\u0131l Kullan\u0131l\u0131r?"
            )
        if hasattr(self, "search_inp"):
            self.search_inp.setPlaceholderText(
                "Par\u00e7a ad\u0131, OEM kodu veya stok kodu ile ara..."
            )
        if hasattr(self, "btn_critical"):
            self.btn_critical.setText("Kritik Par\u00e7alar")

        from PyQt6.QtWidgets import QPushButton

        for button in self.findChildren(QPushButton):
            if "Yeni \u00dcr\u00fcn Ekle" in button.text() or "Yeni Urun Ekle" in button.text():
                button.setText("Yeni Par\u00e7a Ekle")
        if hasattr(self, "stock_empty_state"):
            try:
                self.stock_empty_state.set_title("Yedek Par\u00e7a Yok")
                self.stock_empty_state.set_message(
                    "Envanter bo\u015f veya filtreye uygun par\u00e7a bulunamad\u0131."
                )
            except Exception:
                pass
