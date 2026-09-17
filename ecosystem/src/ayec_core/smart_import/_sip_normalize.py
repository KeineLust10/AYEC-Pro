# -*- coding: utf-8 -*-
# _sip_normalize.py
# Satır normalizasyon & filtreleme mixin'i.

import re


class _SipNormalize:
    """
    Satır normalizasyon ve filtreleme işlemleri.
    _SipUtils, _SipConstants ile birlikte kullanılır.
    """

    # ── Ürün adı temizleme ─────────────────────────────────────────────────
    @classmethod
    def _clean_ocr_name(cls, name):
        """OCR gürültüsünü temizle: tekrar eden hece, anlamsız karakter dizileri."""
        if not name:
            return name
        name = re.sub(r"^[\s\W\d]+", "", name).strip()
        normalized_hint = cls._normalize_key(name)
        if "nakliye" in normalized_hint or "nakiye" in normalized_hint:
            return "NAKLIYE BEDELI"
        if "aski" in normalized_hint and (
            "fiber" in normalized_hint or "kablo" in normalized_hint
        ):
            name = re.sub(r"\bASK\b", "ASKI", name, flags=re.IGNORECASE)
            name = re.sub(r"\bTELL[İI]\b", "TELLI", name, flags=re.IGNORECASE)
            name = re.sub(r"\bKAGLO\b|\bKAELO\b", "KABLO", name, flags=re.IGNORECASE)

        _PRODUCT_START_PATTERNS = [
            r"\b(Dahua|Hikvision|Reolink|Bosch|Samsung|Gabble|GABBLE|Cisco|TP-Link|Axis|Hanwha)\b",
            r"\b(FTP|UTP|CAT[56]|SFP)\b",
        ]
        for pat in _PRODUCT_START_PATTERNS:
            m = re.search(pat, name, re.IGNORECASE)
            if m and m.start() > 5:
                candidate = name[m.start():].strip()
                if len(candidate) >= 4:
                    name = candidate
                    break

        name = re.sub(r"[^\w\s\-/.,()%&+:ÇĞİÖŞÜçğıöşü]", " ", name)
        tokens = name.split()
        cleaned_tokens = []
        for tok in tokens:
            alpha = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü]", "", tok)
            if len(alpha) > 18:
                continue
            cleaned_tokens.append(tok)
        if not cleaned_tokens:
            return name
        return " ".join(cleaned_tokens).strip()

    @classmethod
    def _clean_invoice_item_name(cls, name, desc=""):
        cleaned = re.sub(r"\s+", " ", str(name or "")).strip(" -|,.;")
        if not cleaned:
            return cleaned
        normalized = cls._normalize_key(cleaned)
        if "nakliye" in normalized or "nakiye" in normalized or "nakli" in normalized:
            return "NAKLIYE BEDELI"
        if "bedeli" in normalized and len(normalized.split()) <= 3:
            return "NAKLIYE BEDELI"
        if ("fiber" in normalized or "kablo" in normalized) and (
            "aski" in normalized or "ask" in normalized
        ):
            desc_text = re.sub(r"\s+", " ", str(desc or "")).strip()
            if not re.match(r"^\d+\s+", cleaned):
                desc_match = re.match(r"^\s*(\d{2,4})\s+CORE\b", desc_text, re.IGNORECASE)
                if desc_match and normalized.startswith("core"):
                    cleaned = f"{desc_match.group(1)} {cleaned}"
            cleaned = re.sub(r"\bASK\b", "ASKI", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bASK[İI]\b", "ASKI", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\bTELL[İI]\b", "TELLI", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(
                r"\bKAGLO\b|\bKAELO\b|\bKABLOO\b", "KABLO", cleaned, flags=re.IGNORECASE
            )
        # OCR gurultu temizleme: bilinen marka/urun kelimesinden once gelen carpik metin
        # Ornek: "2 BmniSuLi IP IR BuLit Kamera Dahua IPC-..." -> "Dahua IPC-..."
        _PRODUCT_START_PATTERNS = [
            r"\b(Dahua|Hikvision|Reolink|Bosch|Samsung|Gabble|GABBLE|Cisco|TP-Link|Axis|Hanwha|Uniview|Uniview|Milesight)\b",
            r"\b(IPC|NVR|DVR|PTZ|XVR)-[A-Z0-9]",
            r"\b(FTP|UTP|CAT[56789]|SFP|STP)\b",
            r"\b(ORTAM|Ortam)\b",
        ]
        for pat in _PRODUCT_START_PATTERNS:
            m = re.search(pat, cleaned, re.IGNORECASE)
            if m and m.start() > 4:
                candidate = cleaned[m.start():].strip()
                if len(candidate) >= 6:
                    cleaned = candidate
                    break
        # Basindaki sura numarasi / rakam artigi temizle (ornek: "1 " veya "01 ")
        cleaned = re.sub(r"^\s*\d{1,3}\s+(?=[A-Za-zÇĞİÖŞÜçğıöşü])", "", cleaned).strip()
        return cleaned

    @classmethod
    def _is_ocr_noise_name(cls, name):
        """Ürün adının OCR gürültüsü olup olmadığını tespit eder."""
        if not name or len(name) < 3:
            return False
        tokens = name.split()
        if len(tokens) < 2:
            return False
        single_char = sum(1 for t in tokens if len(re.sub(r"[^A-Za-z]", "", t)) == 1)
        if single_char / len(tokens) > 0.4:
            return True
        if len(tokens) >= 3 and tokens[0] == tokens[1]:
            return True
        avg_len = (
            sum(len(re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü]", "", t)) for t in tokens)
            / len(tokens)
        )
        if avg_len < 2.5 and len(tokens) > 4:
            return True
        return False

    @classmethod
    def _extract_name_from_desc(cls, desc):
        text = str(desc or "").strip()
        if not text:
            return ""
        text = re.sub(r"^[^A-Za-zÇĞİÖŞÜçğıöşü0-9]+", "", text)
        text = re.sub(r"^\d+\s*[:.\\-]?\s*", "", text)
        text = re.split(r"\b\d+\s*adet\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
        text = re.split(r"\s+[0-9]{1,3}(?:[.,][0-9]{2,})+\s*", text, maxsplit=1)[0]
        text = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü0-9 /._-]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" -|,.;")
        letters = len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", text))
        return text if letters >= 5 else ""

    # ── Marka çıkarma ──────────────────────────────────────────────────────
    @classmethod
    def _infer_brand_from_name(cls, name, current_brand=""):
        raw_name = str(name or "").strip()
        if not raw_name:
            return "", raw_name
        if str(current_brand or "").strip():
            return str(current_brand or "").strip(), raw_name
        cleaned = re.sub(r"^[^A-Za-zÇĞİÖŞÜçğıöşü]+", "", raw_name).strip()
        if not cleaned:
            return "", raw_name
        tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9._/-]+", cleaned)
        if not tokens:
            return "", raw_name
        brand = ""
        token0_norm = cls._normalize_key(tokens[0])
        token1_norm = cls._normalize_key(tokens[1]) if len(tokens) > 1 else ""
        pair_norm = f"{token0_norm}-{token1_norm}" if token1_norm else token0_norm
        _is_product_code = bool(re.match(
            r"^[A-Z]{2,5}-[A-Z0-9]{2,}|^[A-Z]{2,}\d{2,}|^\d{2,}[A-Z]{2,}",
            tokens[0], re.IGNORECASE
        ))
        if _is_product_code:
            return "", raw_name
        if pair_norm in cls.BRAND_HINTS:
            brand = f"{tokens[0]}-{tokens[1]}" if len(tokens) > 1 else tokens[0]
        elif token0_norm in cls.BRAND_HINTS:
            brand = tokens[0]
        else:
            first_alpha = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü]", "", tokens[0])
            first_norm = cls._normalize_key(first_alpha)
            if (
                first_alpha
                and 2 <= len(first_alpha) <= 14
                and first_norm not in cls.GENERIC_NAME_TOKENS
                and not re.match(r"^\d+$", tokens[0])
            ):
                brand = tokens[0]
        if not brand:
            return "", raw_name
        brand_pattern = re.escape(brand).replace(r"\-", "[- ]")
        name_wo_brand = re.sub(
            rf"^\s*{brand_pattern}\s*[-_/]*\s*", "", cleaned, flags=re.IGNORECASE
        ).strip()
        if not name_wo_brand:
            name_wo_brand = cleaned
        pretty_brand = (
            brand.strip().upper() if len(brand) <= 4 else brand.strip().title()
        )
        return pretty_brand, name_wo_brand

    # ── Satır normalizasyonu ───────────────────────────────────────────────
    @classmethod
    def _normalize_row(cls, raw_row):
        row = {field: "" for field in cls.FIELD_ORDER}
        row.update({field: raw_row.get(field, "") for field in row.keys()})
        row["name"] = str(row["name"] or "").strip()
        row["desc"] = str(row["desc"] or "").strip()
        _from_invoice    = raw_row.get("_from_invoice", False)
        _manual_sale_price = raw_row.get("_manual_sale_price", False)

        if _from_invoice:
            row["name"] = cls._clean_invoice_item_name(row["name"], row["desc"])
        else:
            row["name"] = cls._clean_ocr_name(row["name"])
            if cls._is_ocr_noise_name(row["name"]) and row["desc"]:
                better = cls._extract_name_from_desc(row["desc"])
                if better and not cls._is_ocr_noise_name(better):
                    row["name"] = better
            if len(row["name"]) < 5 and row["desc"]:
                better_name = cls._extract_name_from_desc(row["desc"])
                if better_name:
                    row["name"] = better_name

        row["brand"] = str(row["brand"] or "").strip()
        if not _from_invoice:
            inferred_brand, cleaned_name = cls._infer_brand_from_name(
                row["name"], row["brand"]
            )
            if cleaned_name:
                row["name"] = cleaned_name
            if inferred_brand and not row["brand"]:
                row["brand"] = inferred_brand

        row["category"]         = str(row["category"] or "Genel").strip() or "Genel"
        row["condition"]        = str(row["condition"] or "").strip()
        row["unit"]             = str(row["unit"] or "").strip()
        row["currency"]         = str(row["currency"] or "TRY").strip().upper() or "TRY"
        row["code"]             = str(row["code"] or "").strip()
        row["oem_code"]         = str(row["oem_code"] or "").strip()
        row["equivalent_code"]  = str(row["equivalent_code"] or "").strip()
        row["compatible_models"]= str(row["compatible_models"] or "").strip()
        row["vehicle_brand"]    = str(row["vehicle_brand"] or "").strip()
        row["vehicle_model"]    = str(row["vehicle_model"] or "").strip()
        row["supplier"]         = str(row["supplier"] or "").strip()
        row["position"]         = str(row["position"] or "").strip()
        row["shelf"]            = str(row["shelf"] or "").strip()
        row["stock"]            = cls._to_int(row["stock"])
        row["purchase_price"]   = cls._to_float(row["purchase_price"])
        row["price"]            = cls._to_float(row["price"])
        row["line_total"]       = cls._to_float(row.get("line_total"))

        if (
            _from_invoice
            and row["line_total"] > 0
            and row["stock"] > 0
            and row["purchase_price"] > 0
        ):
            expected_unit = row["line_total"] / row["stock"]
            if expected_unit > 0 and row["purchase_price"] > expected_unit * 10:
                row["purchase_price"] = round(expected_unit, 4)

        if row["purchase_price"] <= 0 and row["price"] > 0:
            row["purchase_price"] = row["price"]
        if row["price"] <= 0 and row["purchase_price"] > 0 and not _manual_sale_price:
            row["price"] = row["purchase_price"]
        if row["stock"] <= 0:
            row["stock"] = 1
        row["currency"] = cls._normalize_currency(
            row["currency"], f"{row.get('desc', '')} {row.get('name', '')}"
        )
        # Fatura islem bayraklarini sakla — downstream (load_rows, normalize_mapped_rows) icin gerekli
        if _from_invoice:
            row["_from_invoice"] = True
        if _manual_sale_price:
            row["_manual_sale_price"] = True
        return row

    # ── Satır eşleme ──────────────────────────────────────────────────────
    @classmethod
    def _normalize_mapped_rows(cls, raw_rows, mapping, invoice_mode=False):
        rows = []
        for raw in raw_rows or []:
            item = {}
            for field in cls.FIELD_ORDER:
                source_column = mapping.get(field)
                if source_column:
                    item[field] = raw.get(source_column, "")
            # Fatura isle bayraklarini kopyala — _normalize_row icin gerekli
            for flag in ("_from_invoice", "_manual_sale_price", "_confidence", "_flags"):
                if flag in raw:
                    item[flag] = raw[flag]
            invoice_like = invoice_mode and (
                bool(item.get("name"))
                and bool(item.get("stock"))
                and (bool(item.get("purchase_price")) or bool(item.get("line_total")))
            )
            if invoice_like:
                item["_manual_sale_price"] = True
                item["_from_invoice"] = True
            row = cls._normalize_row(item)
            if row.get("name"):
                if not row.get("purchase_price") and row.get("price"):
                    row["purchase_price"] = row["price"]
                score, flags = cls._score_row(row, raw)
                row["_confidence"] = score
                row["_flags"] = flags
                rows.append(row)
        return rows


    # ── Satır filtreleme ──────────────────────────────────────────────────
    @classmethod
    def _filter_core_rows(cls, rows):
        SKIP_PATTERNS = (
            "kdv", "toplam", "matrah", "tevkifat", "stopaj",
            "iskonto tutari", "indirim tutari",
            "odeme kosu", "odeme sekl", "odeme notu",
            "fatura no", "fatura tarihi", "belge no",
            "irsaliye no", "sevk tarihi", "vade tarihi",
            "ettn", "vkn tckn", "mersis no", "vergi dairesi",
            "e-fatura", "e-arsiv", "e-irsaliye",
            "seri no", "sira no",
            "sanayi tic", "ltd sti", "limited sirket", "anonim sirket",
            "a.s.", " a.s", "san. tic", "san.tic",
            "doviz kuru", "dvz kur", "cari bakiye", "yazi ile", "fatura vadesi",
            "vergiler dahil", "odenecek tutar", "mal hizmet toplam",
            "web site", "e-posta", "iban", "swift", "hesap no",
            "garanti bbva", "vakifbank", "qnb", "halkbank", "akbank", "isbank", "ziraat",
            # Ek: hizmet/mal toplam özet satırları
            "hizmet toplam", "mal toplam", "genel toplam", "net toplam",
            "ara toplam", "brut toplam", "vergiler", "odenecek",
            "malhizmet toplam", "mal hizmet tutar",
        )
        # Regex tabanlı özet satır desenleri
        SKIP_REGEX = (
            r"^toplam",             # "Toplam ..." ile başlayan
            r"^kdv",                # "KDV ..." ile başlayan
            r"toplam\s+tutar",      # "... Toplam Tutar"
            r"mal\s+hizmet\s+top",  # "Mal Hizmet Toplam"
            r"hizmet\s+top",        # "Hizmet Toplam"
            r"odenecek",            # "Ödenecek"
            r"\bkdv\s+matr",        # "KDV Matrah"
            r"\bmatrah\b",          # "Matrah"
            r"\btevkifat\b",        # "Tevkifat"
            r"vergiler\s+dahil",    # "Vergiler Dahil"
        )
        filtered = []
        for row in rows or []:
            name = str(row.get("name") or "").strip()
            if len(name) < 3:
                continue
            normalized_name = cls._normalize_key(name)

            # Regex tabanlı özet satır kontrolü
            if any(re.search(pat, normalized_name) for pat in SKIP_REGEX):
                continue

            if re.search(
                r"[0-9a-f]{8}[\-\s][0-9a-f]{4}[\-\s][0-9a-f]{4}", name, re.IGNORECASE
            ):
                continue
            normalized_for_firm = cls._normalize_key(name)
            if re.search(
                r"\bltd\.?\s*sti\.?\b|\ba\.?\s*s\.?\b|\bsan\.?\s*tic\b|\bsanay\b",
                normalized_for_firm,
            ):
                continue
            if re.search(r"\bmah\.?\b|\bcad\.?\b|\bsok\.?\b|\bno\s*:\s*\d", normalized_for_firm):
                continue
            if cls._matches_invoice_skip_label(normalized_name):
                continue
            if any(pat in normalized_name for pat in SKIP_PATTERNS):
                continue
            if re.match(r"^[\d\s\.,\-\+\*\/\%]+$", name):
                continue
            if re.search(
                r"\bltd\.?\s*şti\.?\b|\ba\.?\s*ş\.?\b|\b(tic\.?\s*ltd|san\.?\s*tic)\b",
                name, re.IGNORECASE,
            ):
                continue
            stock = float(row.get("stock") or 0)
            purchase_price = float(row.get("purchase_price") or 0.0)
            price = float(row.get("price") or 0.0)
            if stock < 0:
                continue
            if purchase_price > 1_000_000 or price > 1_000_000:
                continue
            if purchase_price <= 0 and price <= 0 and stock <= 0:
                if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name)) < 5:
                    continue
                row["stock"] = row.get("stock") or 1
            letters = len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name))
            digits  = len(re.findall(r"\d", name))
            invoice_like = bool(row.get("_from_invoice")) or float(row.get("line_total") or 0.0) > 0
            if letters < 3:
                continue
            if letters < digits and not invoice_like:
                continue
            name_words   = name.strip().split()
            short_alpha  = [w for w in name_words if len(w) <= 2 and w.isalpha()]
            if len(name_words) >= 6 and len(short_alpha) >= 4:
                continue
            alpha_tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{2,}", name)
            if not alpha_tokens:
                continue
            first_token = cls._normalize_key(alpha_tokens[0])
            if first_token in cls.GENERIC_NAME_TOKENS and len(alpha_tokens) == 1:
                continue
            if not str(row.get("brand") or "").strip():
                inferred, _ = cls._infer_brand_from_name(name)
                if inferred:
                    row["brand"] = inferred
            filtered.append(row)
        return filtered

    @classmethod
    def _filter_selected_area_rows(cls, rows):
        filtered = []
        seen = set()
        for row in rows or []:
            if cls._invoice_row_problem(row):
                continue
            key = (
                cls._normalize_key(row.get("name") or ""),
                float(row.get("stock") or 0),
                round(float(row.get("purchase_price") or 0.0), 4),
                round(float(row.get("line_total") or 0.0), 4),
            )
            if key in seen:
                continue
            seen.add(key)
            filtered.append(row)
        return filtered

    # ── Satır kalite değerlendirmesi ──────────────────────────────────────
    @classmethod
    def _invoice_row_problem(cls, row):
        name = str(row.get("name") or "").strip()
        desc = str(row.get("desc") or "").strip()
        normalized = cls._normalize_key(f"{name} {desc}")
        normalized_name = cls._normalize_key(name)
        summary_tokens = (
            "toplam", "kdv", "matrah", "tevkifat", "odenecek", "vergiler",
            "hesaplanan", "mal hizmet toplam", "hizmet toplam", "fatura",
            "irsaliye", "banka", "iban", "siparis", "ettn", "vkn", "adres",
            "telefon", "e posta", "vergi dairesi", "doviz kuru",
        )
        if any(token in normalized for token in summary_tokens):
            return "Belge ozeti veya footer satiri"
        name_noise_tokens = (
            "belge", "elge", "balikesir", "gonen", "gönen", "banka",
            "siparis", "sipariş", "sayin", "sayın",
        )
        if any(token in normalized_name for token in name_noise_tokens):
            return "Belge metni urun adi gibi algilandi"
        words = [w for w in re.split(r"\s+", name) if w]
        letters = len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name))
        if letters < 3:
            return "Urun adi zayif"
        if len(words) == 1:
            token = normalized_name
            has_digit = bool(re.search(r"\d", name))
            if len(token) < 6 and not has_digit:
                return "Tek kelimelik OCR gurultusu"
            if token in {"ban", "bedeli", "hizmet", "hizmetler", "lanbi"}:
                return "Urun olmayan tekil ifade"
        stock = float(row.get("stock") or 0)
        purchase_price = float(row.get("purchase_price") or 0.0)
        line_total = float(row.get("line_total") or 0.0)
        if stock <= 0:
            return "Miktar yok"
        if purchase_price <= 0:
            return "Birim fiyat yok"
        if stock > 100_000:
            return "Miktar gercek disi"
        if purchase_price > 1_000_000 or line_total > 100_000_000:
            return "Tutar gercek disi"
        if line_total > 0:
            expected_total = stock * purchase_price
            if expected_total <= 0:
                return "Tutar kontrol edilemedi"
            ratio = line_total / expected_total
            # %45 ile %165 arası kabul edilebilir (KDV vb. hesaba katılır)
            if ratio < 0.45 or ratio > 1.65:
                return "Miktar, birim fiyat ve tutar uyumsuz"
        return ""

    @classmethod
    def _selected_area_row_quality(cls, row):
        problem = cls._invoice_row_problem(row)
        if problem:
            return -10.0
        score = 4.0
        name          = str(row.get("name") or "").strip()
        stock         = float(row.get("stock") or 0)
        purchase_price = float(row.get("purchase_price") or 0.0)
        line_total    = float(row.get("line_total") or 0.0)
        if len(name) >= 8:
            score += 1.0
        if len(name.split()) >= 2:
            score += 1.0
        if re.search(r"\d", name):
            score += 0.5
        if stock > 0 and purchase_price > 0:
            score += 2.0
        if line_total > 0:
            expected_total = max(stock * purchase_price, 0.01)
            ratio = line_total / expected_total
            if 0.85 <= ratio <= 1.15:
                score += 3.0
            elif 0.65 <= ratio <= 1.35:
                score += 1.5
        if str(row.get("currency") or "").strip():
            score += 0.5
        return score

    # ── Profil eşleme ─────────────────────────────────────────────────────
    @classmethod
    def build_profile_mapping(cls, detected_columns, profile_name):
        profile_key = str(profile_name or "default").strip().lower()
        allowed = cls.PROFILE_FIELDS.get(profile_key, cls.PROFILE_FIELDS["default"])
        matched = cls._match_column_names(detected_columns or [])
        return {field: source for field, source in matched.items() if field in allowed}
