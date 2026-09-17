# -*- coding: utf-8 -*-
# _sip_invoice_line.py
# Satır-düzeyi fatura parse mixin'i.
# Her ürün satırını metin bloğundan çıkaran yardımcı metodlar.

import re


class _SipInvoiceLine:
    """
    Fatura satır parse işlemleri.
    _SipUtils, _SipConstants, _SipNormalize ile birlikte kullanılır.
    """

    # ── OCR satır temizleme ────────────────────────────────────────────────
    @classmethod
    def _cleanup_ocr_invoice_line(cls, line):
        line = cls._cleanup_ocr_line(line)
        if not line:
            return ""
        replacements = {
            "TY": "TL", "THY": "TL", "T¥": "TL",
            "Adee": "Adet", "Aded": "Adet", "Adot": "Adet", "Ades": "Adet",
            "det}": "adet ", "det]": "adet ", "adet|": "adet ",
            "stk": "stok", "swok": "stok", "sokt": "stok",
            "stoki": "stok", "stokd": "stok",
        }
        for old, new in replacements.items():
            line = line.replace(old, new)
        line = re.sub(r"\s+", " ", line).strip(" -|")
        return line

    # ── Firma adı / ETTN tespiti ───────────────────────────────────────────
    @classmethod
    def _is_firm_name_line(cls, line):
        normalized = cls._normalize_key(line)
        if re.search(
            r"\bltd\.?\s*sti\.?\b|\ba\.?\s*s\.?\b|\bsan\.?\s*tic\b|\bsanay\b",
            normalized,
        ):
            return True
        if re.search(r"[0-9a-f]{8}[\-\s][0-9a-f]{4}", line, re.IGNORECASE):
            return True
        if re.search(r"\b[0-9a-f]{6,}[\-\s]+[0-9a-f]{4,}", line, re.IGNORECASE):
            return True
        if re.search(r"\bettn\b", normalized):
            return True
        if re.search(r"\bmah\.?\b|\bcad\.?\b|\bsok\.?\b|\bno\s*:\s*\d", normalized):
            return True
        words = line.strip().split()
        if len(words) >= 4 and sum(1 for w in words if w.isupper() and len(w) > 1) >= 3:
            return True
        short_tokens = [w for w in words if len(w) <= 2 and w.isalpha()]
        if len(words) >= 6 and len(short_tokens) >= 4:
            return True
        return False

    # ── Ürün adı / sayısal satır yardımcıları ─────────────────────────────
    @classmethod
    def _looks_like_product_name(cls, line):
        normalized = cls._normalize_key(line)
        if len(line) < 6:
            return False
        if any(
            token in normalized
            for token in ("fatura", "senaryo", "duzenleme", "siparis", "bakiye",
                          "vadesi", "banka", "web sitesi")
        ):
            return False
        letters = len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", line))
        digits  = len(re.findall(r"\d", line))
        return letters >= 5 and letters >= digits

    @classmethod
    def _looks_like_numeric_invoice_line(cls, line):
        normalized = cls._normalize_key(line)
        if (
            "adet" not in normalized
            and "usd" not in normalized
            and "tl" not in normalized
            and "eur" not in normalized
        ):
            return False
        money_count = len(re.findall(r"\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?", line))
        return money_count >= 2

    # ── Ürün kodu maskeleme ────────────────────────────────────────────────
    @classmethod
    def _unit_suffix_pattern(cls):
        return (
            r"(?<!\w)(\d+(?:[.,]\d+)?)\s*"
            r"(mp|megapixel|megapiksel|"
            r"mt?|metre|meter|mm|cm|km|kg|gr\b|g\b|lt?|litre|liter|ml|mtr|mts|"
            r"pcs|db|m2|m3|ft|inch|ghz|mhz|hz|w\b|watt|v\b|volt|a\b|amper|k\b|"
            r"fps|tbps|mbps|gbps|tb|gb|mb|kb)(?!\w)"
        )

    @classmethod
    def _mask_product_codes(cls, line):
        masked = line
        masks  = []
        for match in re.finditer(cls._unit_suffix_pattern(), masked):
            placeholder = f"<<UNIT{len(masks)}>>"
            masks.append((placeholder, match.group(0)))
            masked = masked.replace(match.group(0), placeholder, 1)
        code_pattern = (
            r"(?<![A-Za-z0-9])"
            r"(?:"
            r"[A-Z]{2,}-[A-Z0-9]{2,}(?:-[A-Z0-9]+)*"
            r"|[A-Z]{2,}\d{2,}[A-Za-z0-9]*"
            r"|\d{2,}[A-Z]{2,}[A-Za-z0-9]*"
            r"|[A-Z]\d+[A-Z][A-Za-z0-9]+"
            r"|\d{1,2}[A-Z]{2,4}\b"
            r")"
            r"(?![A-Za-z0-9])"
        )
        for match in re.finditer(code_pattern, masked, flags=re.IGNORECASE):
            placeholder = f"<<CODE{len(masks)}>>"
            masks.append((placeholder, match.group(0)))
            masked = masked.replace(match.group(0), placeholder, 1)
        return masked, masks

    @classmethod
    def _unmask_product_codes(cls, line, masks):
        for placeholder, original in masks:
            line = line.replace(placeholder, original)
        return line

    # ── Para tokenları ────────────────────────────────────────────────────
    @classmethod
    def _invoice_amount_tokens_after_quantity(cls, text):
        text    = str(text or "")
        pattern = r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
        matches = list(re.finditer(pattern, text))
        if not matches:
            return []
        candidates = []
        for match in matches:
            raw   = match.group(0)
            left  = text[max(0, match.start() - 3): match.start()]
            right = text[match.end(): match.end() + 12]
            context = f"{left}{raw}{right}".lower()
            is_percent       = "%" in left or "%" in right[:3]
            is_tax_or_discount = any(
                key in context for key in ("kdv oran", "iskonto oran", "indirim oran")
            )
            if is_percent or is_tax_or_discount:
                continue
            candidates.append(raw)
        return candidates or [m.group(0) for m in matches]

    # ── Tek satır OCR fatura parse ─────────────────────────────────────────
    @classmethod
    def _parse_single_invoice_row_text(cls, row_text):
        line = cls._cleanup_ocr_line(row_text)
        if not line:
            return None
        normalized = cls._normalize_key(line)
        if cls._matches_invoice_skip_label(normalized):
            return None
        line = re.sub(r"^\s*\d{1,3}[\.)\-\:\s]+\s*", "", line).strip()
        normalized = cls._normalize_key(line)
        if "mal hizmet" in normalized or "birim fiyat" in normalized:
            return None
        return cls._parse_numbered_invoice_block(f"1 {line}")

    # ── Numaralı fatura satır bloğu parse ─────────────────────────────────
    @classmethod
    def _parse_numbered_invoice_block(cls, block):
        """
        Fatura satırı parse eder.
        Sütun düzeni: [Sıra No] [Mal Hizmet] [Miktar] [Birim Fiyatı] [Toplam]
        """
        raw = cls._cleanup_ocr_line(block)
        if not raw:
            return None

        line = re.sub(r"^\s*\d{1,3}[\.)\-\:\s]+\s*", "", raw).strip()
        if len(line) < 6:
            return None

        cur_matches = re.findall(r"\b(USD|EUR|TRY|TL|₺|\$|€)\b", line, re.IGNORECASE)
        currency = cur_matches[-1].upper() if cur_matches else cls._detect_currency(line)
        if currency in ("TL", "₺"):
            currency = "TRY"
        if currency == "$":
            currency = "USD"
        if currency == "€":
            currency = "EUR"

        adet_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*"
            r"(?:adet|adot|adee|ades|aded|acetl?|acel|ad\s*et|adt|adeti)\b",
            line, re.IGNORECASE
        )

        if adet_match:
            qty_val     = adet_match.group(1)
            name_end    = adet_match.start()
            raw_name    = line[:name_end].strip(" -|;:")
            after_adet  = line[adet_match.end():].strip()
            prices_all  = cls._invoice_amount_tokens_after_quantity(after_adet)
            unit_value  = prices_all[0] if prices_all else qty_val
            total_value = prices_all[-1] if len(prices_all) >= 2 else unit_value
        else:
            num_matches = list(re.finditer(
                r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?", line
            ))
            if not num_matches:
                return None
            price_indices = [
                i for i, m in enumerate(num_matches)
                if "," in m.group(0) or (
                    "." in m.group(0) and not m.group(0).endswith(".")
                )
            ]
            if not price_indices:
                if len(num_matches) >= 2:
                    total_value = num_matches[-1].group(0)
                    unit_value  = num_matches[-2].group(0)
                    qty_val     = "1"
                    name_end    = num_matches[-2].start()
                    raw_name    = line[:name_end].strip(" -|;:")
                else:
                    raw_name    = line.split(num_matches[0].group(0))[0].strip(" -|;:")
                    unit_value  = num_matches[0].group(0)
                    total_value = unit_value
                    qty_val     = "1"
            else:
                last_price_i  = price_indices[-1]
                unit_price_i  = price_indices[-2] if len(price_indices) >= 2 else price_indices[-1]
                total_value   = num_matches[last_price_i].group(0)
                unit_value    = num_matches[unit_price_i].group(0)
                qty_val       = "1"
                name_end      = num_matches[unit_price_i].start()
                for i in range(unit_price_i - 1, -1, -1):
                    tok = num_matches[i].group(0)
                    if "," not in tok and "." not in tok:
                        try:
                            v = int(tok)
                            if 1 <= v <= 9999:
                                qty_val  = tok
                                name_end = num_matches[i].start()
                                break
                        except ValueError:
                            pass
                raw_name = line[:name_end].strip(" -|;:")

        if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", raw_name)) < 3:
            return None

        return cls._normalize_row({
            "name": raw_name,
            "stock": qty_val,
            "purchase_price": unit_value,
            "line_total": total_value,
            "price": "",
            "currency": currency,
            "desc": raw,
            "_manual_sale_price": True,
            "_from_invoice": True,
        })

    # ── OCR satır parse (genel) ────────────────────────────────────────────
    @classmethod
    def _parse_invoice_ocr_line(cls, line):
        compact = re.sub(r"\s+", " ", str(line or "")).strip()
        if len(compact) < 6:
            return None
        normalized = cls._normalize_key(compact)
        if any(
            token in normalized
            for token in ("fatura", "senaryo", "vkn", "vergi dairesi", "iban", "web sitesi")
        ):
            return None
        if (
            not any(
                token in normalized
                for token in ("stok", "adet", "miktar", "tl", "eur", "usd", "try")
            )
            and "$" not in compact
            and "€" not in compact
            and "₺" not in compact
        ):
            money_pre = list(re.finditer(r"\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?", compact))
            if len(money_pre) < 2:
                return None

        compact_masked, masks = cls._mask_product_codes(compact)
        normalized_masked     = cls._normalize_key(compact_masked)

        money_matches = list(re.finditer(
            r"\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?", compact_masked
        ))
        if len(money_matches) < 2:
            return None

        qty_match = re.search(
            r"(\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?)\s*adet\b", normalized_masked
        )
        if qty_match:
            qty       = qty_match.group(1)
            cut_index = qty_match.start()
        else:
            qty       = "1"
            cut_index = money_matches[0].start()
            for m in money_matches:
                val = m.group(0).replace(" ", "")
                if "," in val:
                    continue
                try:
                    v = int(float(val))
                    if 0 < v <= 9999:
                        qty       = val
                        cut_index = m.start()
                        break
                except Exception:
                    continue

        unit_value  = (
            money_matches[-2].group(0) if len(money_matches) >= 2 else money_matches[-1].group(0)
        )
        total_value = money_matches[-1].group(0)
        currency    = cls._detect_currency(compact)

        name = compact_masked[:cut_index]
        row_no = re.match(r"^\s*(\d{1,2})\s*[|.]?\s+", name)
        if row_no:
            try:
                if int(row_no.group(1)) <= 20:
                    name = name[row_no.end():]
            except ValueError:
                pass
        name = name.strip()
        name = re.sub(r"[^A-Za-z0-9ÇĞİÖŞÜçğıöşü /._-]+", " ", name)
        name = re.sub(r"\s+", " ", name).strip(" -|")
        name = cls._unmask_product_codes(name, masks)
        compact = cls._unmask_product_codes(compact_masked, masks)

        if not name:
            return None
        normalized_name = cls._normalize_key(name)
        if "stok" in normalized_name and len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name)) < 6:
            name = "Stok Kalemi"
        name = re.sub(
            r"^(mal hizmet|aciklama|urun|hizmet)\s+", "", name, flags=re.IGNORECASE
        ).strip()
        if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name)) < 2:
            return None

        return {
            "name": name, "stock": qty, "purchase_price": unit_value,
            "line_total": total_value, "price": "", "currency": currency,
            "desc": compact, "_manual_sale_price": True, "_from_invoice": True,
        }

    # ── Tablo satırı parse (tablo header'li PDF/metin) ────────────────────
    @classmethod
    def _parse_invoice_line(cls, line):
        compact = re.sub(r"\s+", " ", str(line or "")).strip()
        if len(compact) < 6:
            return None
        raw     = compact
        compact = re.sub(r"^\d+[\.)\-\:\s]+\s*", "", compact)
        compact = compact.strip("|")
        normalized = cls._normalize_key(compact)
        if "fatura" in normalized or "senaryo" in normalized:
            return None
        if any(
            token in normalized
            for token in ("tel", "telefon", "fax", "vkn", "web sitesi",
                          "vergi dairesi", "iban", "banka", "mersis",
                          "istanbul", "antalya", "karabuk", "muratpasa")
        ):
            return None

        compact_masked, masks = cls._mask_product_codes(compact)
        normalized_masked     = cls._normalize_key(compact_masked)
        money_pattern   = r"\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?|\d+(?:,\d+)?"
        qty_match       = re.search(
            rf"(?P<qty>{money_pattern})\s*(adet|ad|pcs|miktar)\b", normalized_masked
        )
        amount_matches  = list(re.finditer(money_pattern, compact_masked))
        if not amount_matches:
            return None

        currency      = cls._detect_currency(compact)
        qty           = ""
        purchase_price = ""

        if qty_match:
            qty        = qty_match.group("qty")
            after_qty  = compact_masked[qty_match.end():]
            later_amounts = re.findall(money_pattern, after_qty)
            if later_amounts:
                purchase_price = later_amounts[0]
        else:
            for m in amount_matches:
                val = m.group(0).replace(" ", "")
                if "," in val:
                    continue
                try:
                    v = int(float(val))
                    if 0 < v <= 9999:
                        qty = val
                        for m2 in amount_matches[amount_matches.index(m) + 1:]:
                            if "," in m2.group(0):
                                purchase_price = m2.group(0)
                                break
                        if not purchase_price and amount_matches.index(m) + 1 < len(amount_matches):
                            purchase_price = amount_matches[amount_matches.index(m) + 1].group(0)
                        break
                except Exception:
                    continue
            if not qty:
                qty = amount_matches[0].group(0)
                purchase_price = amount_matches[1].group(0) if len(amount_matches) >= 2 else ""

        if not qty or not purchase_price:
            return None

        cut_index = compact_masked.find(qty.replace(" ", ""))
        if cut_index < 0:
            cut_index = amount_matches[0].start() if amount_matches else len(compact_masked)
        name = compact_masked[:cut_index].strip(" -|;:")
        if not name or len(name) < 2:
            name = compact_masked
        name = re.sub(r"\s{2,}", " ", name).strip()
        name = cls._unmask_product_codes(name, masks)
        compact = cls._unmask_product_codes(compact_masked, masks)
        if len(name) > 120:
            name = name[:120].strip()
        if len(name) < 2:
            return None
        if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name)) < 3:
            return None
        if " " not in name and len(amount_matches) < 2:
            return None

        return {
            "name": name, "stock": qty, "purchase_price": purchase_price,
            "currency": currency, "desc": raw,
        }
