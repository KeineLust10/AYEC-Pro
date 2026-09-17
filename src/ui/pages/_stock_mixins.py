# -*- coding: utf-8 -*-
# _stock_mixins.py
# Ortak fonksiyonlar ve sabitler mixini


class StockPageConstantsMixin:
    """Sabitler için mixin."""
    CATEGORY_GROUPS = {
        "Bilgisayar Bileşenleri": {
            "anakart",
            "aydınlatma hub",
            "depolama",
            "ekran kartı",
            "güç kaynağı",
            "hdd",
            "işlemci",
            "işlemci soğutucu",
            "kasa",
            "klavye",
            "monitor",
            "monitör",
            "monitor/ekran",
            "monitör/ekran",
            "mouse",
            "ram",
            "ram (bellek)",
            "ssd",
            "ssd / m.2",
            "ssd - m.2",
            "ssd - sata",
            "termal pasta",
            "işletim sistemi",
            "kablo yönetimi",
            "yazilim",
            "yazılım",
            "aksesuar",
            "kablo",
            "pc",
            "pc parçaları",
            "pc parcalari",
            "bilgisayar",
            "bilgisayar bileşenleri",
            "bilgisayar bilesenleri",
        },
        "Akıllı Ev Sistemleri": {
            "akıllı aydınlatma",
            "akıllı ev aletleri",
            "akıllı kamera",
            "akıllı kilit",
            "akıllı priz",
            "akıllı röle",
            "akıllı zil",
            "clima kontrolü",
            "iklim kontrolü",
            "klima kontrolü",
            "merkez hub",
            "sensör",
            "ses asistanı",
            "ev şarj",
            "ev sarj",
            "enerji yönetimi",
            "termostat",
            "otomasyon",
            "akıllı ev",
            "akilli ev",
            "akıllı ev sistemleri",
            "akilli ev sistemleri",
        },
        "Güvenlik Sistemleri": {
            "alarm paneli",
            "geçiş kontrol",
            "gecis kontrol",
            "ups/güç",
            "ups/guc",
            "ups",
            "güvenlik kamera",
            "kamera sistemi",
            "nvr",
            "dvr",
            "nvr / dvr",
            "ip kamera",
            "ptz kamera",
            "interkom",
            "kontrol paneli",
            "yangın",
            "kamera",
            "güvenlik",
            "guvenlik",
            "kamera güvenlik",
            "kamera guvenlik",
            "güvenlik sistemleri",
            "guvenlik sistemleri",
        },
    }


class StockPageUtilitiesMixin:
    """Yardımcı fonksiyonlar mixini."""

    def _extract_automotive_meta(self, description):
        meta = {
            "supplier": "",
            "vehicle_brand": "",
            "vehicle_model": "",
            "position": "",
        }
        for raw_line in str(description or "").splitlines():
            line = raw_line.strip()
            if line.startswith("[OTO_SUPPLIER]"):
                meta["supplier"] = line.replace("[OTO_SUPPLIER]", "", 1).strip()
            elif line.startswith("[OTO_VEHICLE_BRAND]"):
                meta["vehicle_brand"] = line.replace(
                    "[OTO_VEHICLE_BRAND]", "", 1
                ).strip()
            elif line.startswith("[OTO_VEHICLE_MODEL]"):
                meta["vehicle_model"] = line.replace(
                    "[OTO_VEHICLE_MODEL]", "", 1
                ).strip()
            elif line.startswith("[OTO_POSITION]"):
                meta["position"] = line.replace("[OTO_POSITION]", "", 1).strip()
        return meta

    def _normalize_category(self, value):
        text = str(value or "").strip().lower()
        replacements = {
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text

    def _get_category_filters(self, selected_category):
        if not selected_category or selected_category == "Tümü":
            return "Tümü"

        target_values = {
            self._normalize_category(item)
            for item in self.CATEGORY_GROUPS.get(selected_category, set())
        }
        if not target_values:
            return selected_category

        matched_categories = []
        for raw_category in self._raw_categories:
            normalized = self._normalize_category(raw_category)
            if normalized in target_values or any(
                normalized.startswith(target) or target.startswith(normalized)
                for target in target_values
            ):
                matched_categories.append(raw_category)

        return matched_categories or [selected_category]

    def _cat_style(self, active):
        if active:
            return "background: @accent; color: @selection_text; border-radius: 15px; padding: 6px 15px; font-weight: bold;"
        return "background: @surface; color: @text_muted; border: 1px solid @border; border-radius: 15px; padding: 6px 15px;"

