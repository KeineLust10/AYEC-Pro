# -*- coding: utf-8 -*-
# _sip_utils.py
# Genel yardımcı metodlar — StockImportParser mixin'i.

import re
import unicodedata


class _SipUtils:
    """Genel metin/sayı yardımcıları. _SipConstants ile birlikte kullanılır."""

    # ── Türkçe karakter normalleştirme ────────────────────────────────────────
    @classmethod
    def _normalize_key(cls, value):
        key = str(value or "").strip().lower()
        for src, dst in {
            "\u0131": "i", "\u011f": "g", "\u00fc": "u",
            "\u015f": "s", "\u00f6": "o", "\u00e7": "c",
            "\u00e4\u00b1": "i", "\u00e4\u0178": "g",
            "\u00e3\u00bc": "u", "\u00e5\u0178": "s",
            "\u00e3\u00b6": "o", "\u00e3\u00a7": "c",
        }.items():
            key = key.replace(src, dst)
        key = key.translate(str.maketrans({"/": " ", "_": " ", "-": " "}))
        key = unicodedata.normalize("NFKD", key)
        key = "".join(char for char in key if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", key).strip()

        # Legacy normalization kept below for source compatibility.
        single_char_map = str.maketrans(
            {
                "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
                "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c",
                "/": " ", "_": " ", "-": " ",
            }
        )
        key = key.translate(single_char_map)
        for src, dst in {
            "ä±": "i", "äÿ": "g", "ã¼": "u", "åÿ": "s",
            "ã¶": "o", "ã§": "c", "ı": "i",
            "\u00c4\u0178": "g", "ü": "u", "\u00c5\u0178": "s",
            "ö": "o", "ç": "c",
        }.items():
            key = key.replace(src.lower(), dst)
        return re.sub(r"\s+", " ", key).strip()

    # ── Sayı dönüşümleri ──────────────────────────────────────────────────────
    @staticmethod
    def _to_int(value):
        try:
            text = str(value).strip()
            if not text:
                return 0
            text = re.sub(r"[^\d.,-]", "", text)
            if not text:
                return 0
            if "," in text and "." in text:
                text = text.replace(".", "").replace(",", ".")
            elif "." in text and "," not in text:
                parts = text.split(".")
                if (len(parts) > 1
                        and all(p.isdigit() for p in parts)
                        and all(len(p) == 3 for p in parts[1:])):
                    text = "".join(parts)
            else:
                text = text.replace(",", ".")
            return int(float(text))
        except Exception:
            return 0

    @staticmethod
    def _to_float(value):
        try:
            text = str(value).strip()
            if not text:
                return 0.0
            text = re.sub(r"[₺$€£¥]", "", text)
            text = re.sub(r"\b(TRY|TL|USD|EUR|GBP)\b", "", text, flags=re.IGNORECASE)
            text = text.strip()
            text = re.sub(r"[^\d,.\-]", "", text)
            if not text:
                return 0.0
            if "," in text and "." in text:
                last_comma = text.rfind(",")
                last_dot   = text.rfind(".")
                if last_comma > last_dot:
                    text = text.replace(".", "").replace(",", ".")
                else:
                    text = text.replace(",", "")
            elif "." in text:
                dot_pos   = text.rfind(".")
                after_dot = text[dot_pos + 1:]
                before_dot = text[:dot_pos].replace(".", "")
                if len(after_dot) == 3 and before_dot.isdigit():
                    text = text.replace(".", "")
            else:
                text = text.replace(",", ".")
            return float(text)
        except Exception:
            return 0.0

    # ── Para birimi ───────────────────────────────────────────────────────────
    @classmethod
    def _detect_currency(cls, text):
        lowered = cls._normalize_key(text)
        if re.search(r"\beur\b", lowered) or "€" in text:
            return "EUR"
        if re.search(r"\busd\b", lowered) or "$" in text:
            return "USD"
        if re.search(r"\btry\b", lowered) or re.search(r"\btl\b", lowered) or "₺" in text:
            return "TRY"
        return "TRY"

    @classmethod
    def _normalize_currency(cls, currency_value, text_hint=""):
        cur = str(currency_value or "").strip().upper()
        if cur in {"TL", "TRY", "USD", "EUR", "GBP"}:
            return "TRY" if cur == "TL" else cur
        detected = cls._detect_currency(str(text_hint or ""))
        return detected or "TRY"

    # ── OCR metin temizliği ───────────────────────────────────────────────────
    @classmethod
    def _cleanup_ocr_line(cls, value):
        text = str(value or "").strip()
        if not text:
            return ""
        text = text.replace("\u00a0", " ")
        text = re.sub(r"\s+", " ", text)
        text = text.replace(" ,", ",").replace(" .", ".")
        return text.strip()

    # ── Metin yardımcıları ────────────────────────────────────────────────────
    @classmethod
    def _extract_number_after(cls, text, labels):
        lowered = cls._normalize_key(text)
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*[:=\-]?\s*([\d.,]+)", lowered)
            if match:
                return match.group(1)
        return ""

    @classmethod
    def _extract_text_after(cls, text, labels):
        lowered = cls._normalize_key(text)
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*[:=\-]?\s*([^\|,;]+)", lowered)
            if match:
                return text[match.start(1): match.end(1)].strip()
        return ""

    @classmethod
    def _extract_price_and_currency(cls, cell_value):
        """'31,50 USD' → ('31,50', 'USD'), '82,50' → ('82,50', '')"""
        text = str(cell_value or "").strip()
        m = re.search(r"(USD|EUR|TRY|TL)\s*$", text, flags=re.IGNORECASE)
        currency = m.group(1).upper() if m else ""
        price_str = re.sub(r"\s*(USD|EUR|TRY|TL)\s*$", "", text, flags=re.IGNORECASE).strip()
        if currency in ("TL",):
            currency = "TRY"
        return price_str, currency

    @classmethod
    def _extract_qty_and_unit(cls, cell_value):
        """'10 Adet' → ('10', 'Adet'), '4' → ('4', '')"""
        text = str(cell_value or "").strip()
        m = re.match(
            r"^\s*(\d+(?:[.,]\d+)?)\s*(adet|ad\.|ad\b|pcs|piece|mt|m\b)?",
            text, flags=re.IGNORECASE
        )
        if m:
            return m.group(1), (m.group(2) or "").strip()
        return text, ""

    # ── Sütun keşfi ──────────────────────────────────────────────────────────
    @classmethod
    def _match_column_names(cls, columns):
        matched = {}
        for col in columns or []:
            normalized = cls._normalize_key(col)
            alias = cls.COLUMN_ALIASES.get(normalized)
            if not alias:
                direct = str(col or "").strip()
                if direct in cls.FIELD_ORDER:
                    alias = direct
                elif normalized in cls.FIELD_ORDER:
                    alias = normalized
            if alias and alias not in matched:
                matched[alias] = str(col)
        return matched

    @classmethod
    def _detect_columns_from_rows(cls, rows):
        ordered = []
        for row in rows or []:
            for key in row.keys():
                if key not in ordered:
                    ordered.append(key)
        return ordered

    @classmethod
    def _looks_like_internal_rows(cls, raw_rows):
        if not raw_rows:
            return False
        keys = set()
        for row in raw_rows[:5]:
            keys.update(str(key or "").strip() for key in row.keys())
        field_hits = sum(1 for field in cls.FIELD_ORDER if field in keys)
        return field_hits >= 3

    @classmethod
    def _dedupe_rows(cls, rows):
        result = []
        seen = set()
        for row in rows:
            key = (
                str(row.get("name") or "").strip(),
                row.get("stock") or 0,
                row.get("purchase_price") or 0.0,
                str(row.get("currency") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(row)
        return result

    @classmethod
    def _score_parse_result(cls, parsed):
        raw_rows = parsed.get("raw_rows") or []
        if not raw_rows:
            return 0.0
        score = float(len(raw_rows))
        for row in raw_rows:
            if str(row.get("name") or "").strip():
                score += 0.2
            if row.get("stock", 0):
                score += 0.1
            if row.get("purchase_price", 0.0):
                score += 0.1
        return score

    @classmethod
    def _score_row(cls, row, raw_row=None):
        score = 0.0
        flags = []
        name = str(row.get("name") or "").strip()
        if len(name) >= 3:
            score += 0.32
        else:
            flags.append("Urun adi zayif")
        if re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name):
            score += 0.10
        else:
            flags.append("Metin OCR kalitesi dusuk")
        stock = float(row.get("stock") or 0)
        if stock > 0:
            score += 0.18
        else:
            flags.append("Adet yok")
        purchase_price = float(row.get("purchase_price") or 0.0)
        if purchase_price > 0:
            score += 0.18
        else:
            flags.append("Alis fiyati yok")
        if str(row.get("brand") or "").strip():
            score += 0.08
        category = str(row.get("category") or "").strip()
        if category and category.lower() != "genel":
            score += 0.05
        if str(row.get("code") or "").strip():
            score += 0.04
        if str(row.get("vehicle_brand") or "").strip():
            score += 0.025
        if str(row.get("vehicle_model") or "").strip():
            score += 0.025
        if str(row.get("supplier") or "").strip():
            score += 0.015
        if str(row.get("position") or "").strip():
            score += 0.015
        normalized_name = cls._normalize_key(name)
        if cls._matches_invoice_skip_label(normalized_name):
            flags.append("Toplam veya meta satiri olabilir")
            score -= 0.45
        if len(name) > 110:
            flags.append("Satir cok uzun")
            score -= 0.15
        if name.count("[") + name.count("]") >= 2:
            flags.append("OCR satiri gurultulu")
            score -= 0.25
        if raw_row:
            raw_join = " ".join(str(v or "") for v in raw_row.values())
            normalized_raw = cls._normalize_key(raw_join)
            if any(
                token in normalized_raw
                for token in ("vkn", "vergi dairesi", "iban", "mersis", "web sitesi")
            ):
                flags.append("Firma veya meta satiri olabilir")
                score -= 0.35
        score = max(0.0, min(1.0, score))
        if score < cls.LOW_CONFIDENCE_THRESHOLD and "Dusuk guven" not in flags:
            flags.append("Dusuk guven")
        return score, flags

    # ── XML yardımcıları ─────────────────────────────────────────────────────
    @staticmethod
    def _xml_local_name(tag):
        return str(tag).split("}", 1)[-1] if "}" in str(tag) else str(tag)

    @classmethod
    def _find_xml_nodes(cls, root, local_name):
        return [node for node in root.iter() if cls._xml_local_name(node.tag) == local_name]

    @classmethod
    def _find_xml_node(cls, root, local_name):
        for node in root.iter():
            if cls._xml_local_name(node.tag) == local_name:
                return node
        return None

    @classmethod
    def _find_xml_text(cls, root, local_name):
        node = cls._find_xml_node(root, local_name)
        return cls._xml_text(node)

    @staticmethod
    def _xml_text(node):
        if node is None or node.text is None:
            return ""
        return str(node.text).strip()
