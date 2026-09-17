# -*- coding: utf-8 -*-
# _sip_invoice_parsers.py
# Fatura yüksek-seviye parse mixin'i.
# Metin içeriğinden satır çıkaran tüm parser stratejileri burada.

import re


class _SipInvoiceParsers:
    """
    Fatura metin parse stratejileri.
    _SipInvoiceLine, _SipUtils, _SipConstants, _SipNormalize ile birlikte kullanılır.
    """

    # ── Fatura başlık / footer tespiti ─────────────────────────────────────
    @classmethod
    def _is_invoice_header_line(cls, normalized_line):
        return any(
            a in normalized_line and b in normalized_line
            for a, b in cls._INVOICE_HEADER_KEYS
        )

    @classmethod
    def _is_invoice_footer_line(cls, normalized_line):
        return any(key in normalized_line for key in cls._INVOICE_FOOTER_KEYS)

    @classmethod
    def _matches_invoice_skip_label(cls, normalized_text):
        text = str(normalized_text or "")
        if not text:
            return False
        for skip in cls.INVOICE_SKIP_LABELS:
            label = cls._normalize_key(skip)
            if not label:
                continue
            if len(label) <= 3:
                if re.search(rf"(?<![a-z0-9]){re.escape(label)}(?![a-z0-9])", text):
                    return True
                continue
            if label in text:
                return True
        return False

    # ── Belge meta veri çıkarma ────────────────────────────────────────────
    @classmethod
    def _extract_document_metadata(cls, text):
        metadata = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = re.match(r"^\s*([^:=\-]{2,50})\s*[:=\-]\s*(.+?)\s*$", line)
            if not match:
                continue
            label    = cls._normalize_key(match.group(1))
            meta_key = cls.DOCUMENT_LABEL_ALIASES.get(label)
            if meta_key:
                metadata[meta_key] = match.group(2).strip()
        supplier_company = cls._extract_supplier_company(text)
        if supplier_company:
            metadata["supplier_company"] = supplier_company
        return metadata

    @classmethod
    def _extract_supplier_company(cls, text):
        candidates = []
        for raw_line in str(text or "").splitlines()[:20]:
            line = " ".join(str(raw_line or "").split())
            normalized = cls._normalize_key(line)
            if not normalized:
                continue
            if normalized == "sayin":
                break
            if any(
                marker in normalized
                for marker in (
                    "anonim sirket", "limited sirket", " ltd", " a s",
                    "bilisim", "ticaret", "sanayi",
                )
            ):
                candidates.append(line)
        if not candidates:
            return ""
        company = candidates[0]
        suffix_pattern = (
            r"^(.+?(?:A\.?\s*(?:S|\u015e)\.?|"
            r"LTD\.?\s*(?:STI|\u015eT\u0130)\.?|LIMITED(?:\s+SIRKETI)?))"
            r"(?=\s|$)"
        )
        match = re.search(suffix_pattern, company, flags=re.IGNORECASE)
        if match:
            company = match.group(1)
        return company.strip(" -:;,.")

    # ── Ana metin içerik parse ─────────────────────────────────────────────
    @classmethod
    def _parse_text_content(cls, text, strict_table=False):
        text = str(text or "").strip()
        if not text:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}

        metadata        = cls._extract_document_metadata(text)
        normalized_text = cls._normalize_key(text)

        if strict_table:
            parsers = [
                cls._parse_invoice_numbered_rows,
                cls._parse_invoice_table_text,
                cls._parse_invoice_columnar_rows,
                cls._parse_invoice_ocr_rows,
                cls._parse_invoice_multiline_blocks,
            ]
        else:
            parsers = [
                cls._parse_invoice_numbered_rows,
                cls._parse_invoice_columnar_rows,
                cls._parse_invoice_table_text,
                cls._parse_invoice_ocr_rows,
                cls._parse_invoice_multiline_blocks,
            ]
        if "fatura" not in normalized_text:
            parsers.extend([cls._parse_key_value_blocks, cls._parse_freeform_lines])

        best_rows  = []
        best_score = None
        for parser in parsers:
            raw_rows = parser(text)
            if not raw_rows:
                continue
            candidate_rows = cls._filter_selected_area_rows(raw_rows) if strict_table else raw_rows
            if not candidate_rows:
                continue
            score  = sum(cls._selected_area_row_quality(row) for row in candidate_rows)
            score += len(candidate_rows) * 3.0
            if best_score is None or score > best_score:
                best_score = score
                best_rows  = candidate_rows

        if best_rows:
            detected_columns = cls._detect_columns_from_rows(best_rows)
            return {
                "raw_rows": best_rows,
                "detected_columns": detected_columns,
                "suggested_mapping": cls._match_column_names(detected_columns),
                "metadata": metadata,
            }
        return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": metadata}

    # ── Numaralı satır parser ─────────────────────────────────────────────
    @classmethod
    def _parse_invoice_numbered_rows(cls, text):
        all_lines = [cls._cleanup_ocr_line(line) for line in str(text or "").splitlines()]

        header_line_idx = -1
        for idx, line in enumerate(all_lines):
            if not line:
                continue
            if cls._is_invoice_header_line(cls._normalize_key(line)):
                header_line_idx = idx
                break

        active_lines = all_lines[header_line_idx + 1:] if header_line_idx >= 0 else all_lines

        blocks  = []
        current = ""
        for line in active_lines:
            if not line:
                continue
            normalized = cls._normalize_key(line)
            if cls._is_invoice_footer_line(normalized):
                break

            has_invoice_values = bool(
                re.search(
                    r"\d+(?:[.,]\d+)?\s*(?:adet|adot|adee|ades|aded|acetl?|acel|ad\s*et|adt|adeti)\b",
                    normalized, re.IGNORECASE,
                )
                or re.search(r"\d\s*(?:usd|eur|try|tl)\b", normalized, re.IGNORECASE)
            )
            if not has_invoice_values and cls._is_firm_name_line(line):
                continue

            is_new_block = bool(
                re.match(r"^\s*\d{1,3}(?:[\.)\-\:\s])\s*\S", line)
                and not re.match(r"^\s*\d+\.\d", line)
            )
            if is_new_block:
                if current:
                    blocks.append(current.strip())
                current = line
            else:
                if current:
                    current = f"{current} {line}".strip()

        if current:
            blocks.append(current.strip())

        rows = []
        seen = set()
        for block in blocks:
            normalized = cls._normalize_key(block)
            if cls._matches_invoice_skip_label(normalized):
                continue
            block_has_invoice_values = bool(
                re.search(
                    r"\d+(?:[.,]\d+)?\s*(?:adet|adot|adee|ades|aded|acetl?|acel|ad\s*et|adt|adeti)\b",
                    normalized, re.IGNORECASE,
                )
                or re.search(r"\d\s*(?:usd|eur|try|tl)\b", normalized, re.IGNORECASE)
            )
            if not block_has_invoice_values and cls._is_firm_name_line(block):
                continue
            row = cls._parse_numbered_invoice_block(block)
            if not row:
                continue
            key = (row.get("name", ""), row.get("stock", 0),
                   row.get("purchase_price", 0.0), row.get("currency", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    # ── Kolumnar (tek satır) parser ────────────────────────────────────────
    @classmethod
    def _parse_invoice_columnar_rows(cls, text):
        lines = [cls._cleanup_ocr_line(ln) for ln in str(text or "").splitlines()]

        header_idx = -1
        for idx, line in enumerate(lines):
            if cls._is_invoice_header_line(cls._normalize_key(line)):
                header_idx = idx
                break
        if header_idx < 0:
            return []

        rows = []
        seen = set()
        for line in lines[header_idx + 1:]:
            if not line:
                continue
            nrm = cls._normalize_key(line)
            if cls._is_invoice_footer_line(nrm):
                break
            if cls._matches_invoice_skip_label(nrm):
                continue

            fixed = re.sub(
                r"(\d+)\s*(acetl|acet|acel|adot|adt|adeti)\b",
                r"\1 Adet", line, flags=re.IGNORECASE
            )
            fixed = re.sub(
                r"(?<!\d\s)(?<!\d)\b(acetl|acet|acel|adot|adt|adeti)\b",
                "1 Adet", fixed, flags=re.IGNORECASE
            )
            fixed = re.sub(r"\bUsDI\b|\bUsDl\b|\bUsD\b|\bUSDI\b", "USD", fixed)
            fixed = re.sub(r"\bU50\b|\bU5D\b|\bU[sS][0o]\b", "USD", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"(\d)([Uu][sS][dDI0oO]+)\b", r"\1 USD", fixed)
            fixed = re.sub(r"(\d+)U5[0oO]\b", r"\1 USD", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"(\d+)ous[Dd]\b", r"\1 USD", fixed, flags=re.IGNORECASE)

            def _fix_missing_comma(m):
                num = m.group(1)
                if len(num) >= 3 and "," not in num and "." not in num:
                    return f"{num[:-2]},{num[-2:]} USD"
                return m.group(0)
            fixed = re.sub(r"(\d{3,})\s+USD\b", _fix_missing_comma, fixed)

            has_qty   = bool(re.search(r"\b(\d+(?:[.,]\d+)?)\s*adet\b", fixed, re.IGNORECASE))
            has_price = bool(re.search(
                r"\d{1,3}(?:[.,]\d{1,3})*(?:[.,]\d{1,2})?\s*(USD|EUR|TRY|TL)",
                fixed, re.IGNORECASE
            ))
            letters = len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", fixed))
            if not has_qty and not has_price:
                continue
            if letters < 4:
                continue

            has_adet        = bool(re.search(r"\d\s*adet\b|\badet\s*\d", fixed, re.IGNORECASE))
            has_price_token = bool(re.search(r"\d\s*USD|\d\s*EUR|\d\s*TL", fixed, re.IGNORECASE))
            if not (has_adet or has_price_token):
                if cls._is_firm_name_line(line):
                    continue

            parsed = cls._parse_numbered_invoice_block(fixed)
            if not parsed:
                parsed = cls._parse_invoice_ocr_line(fixed)
            if not parsed:
                continue
            row = cls._normalize_row(parsed)
            if not row.get("name"):
                continue
            if row.get("stock", 0) <= 0 and row.get("purchase_price", 0.0) <= 0:
                continue
            key = (row["name"], row["stock"], row["purchase_price"], row["currency"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    # ── Tablo metin parser ─────────────────────────────────────────────────
    @classmethod
    def _parse_invoice_table_text(cls, text):
        rows   = []
        seen   = set()
        lines  = [cls._cleanup_ocr_line(line) for line in text.splitlines()]
        header_index = -1

        for idx, line in enumerate(lines):
            lowered = cls._normalize_key(line)
            has_name_col = ("mal hizmet" in lowered or "aciklama" in lowered
                            or "açıklama" in lowered or "urun" in lowered)
            has_num_col  = ("miktar" in lowered or "birim fiyat" in lowered
                            or "tutar" in lowered or "adet" in lowered)
            if has_name_col and has_num_col:
                header_index = idx
                break
            if has_name_col and idx + 1 < len(lines):
                next_lowered = cls._normalize_key(lines[idx + 1])
                if ("miktar" in next_lowered or "birim fiyat" in next_lowered
                        or "tutar" in next_lowered):
                    header_index = idx + 1
                    break

        active_lines = lines[header_index + 1:] if header_index >= 0 else lines
        for raw_line in active_lines:
            line    = cls._cleanup_ocr_line(raw_line)
            if not line:
                continue
            lowered = cls._normalize_key(line)
            if header_index >= 0 and cls._is_invoice_footer_line(lowered):
                break
            if header_index < 0 and "adet" not in lowered and "[" not in line:
                continue
            if cls._matches_invoice_skip_label(lowered):
                if header_index >= 0:
                    break
                continue
            if cls._is_firm_name_line(line):
                continue
            parsed = cls._parse_invoice_line(line)
            if not parsed:
                continue
            row = cls._normalize_row(parsed)
            if not row.get("name"):
                continue
            if row.get("stock", 0) <= 0 and row.get("purchase_price", 0.0) <= 0:
                continue
            key = (row.get("name", ""), row.get("stock", 0),
                   row.get("purchase_price", 0.0), row.get("currency", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    # ── OCR satır parser ──────────────────────────────────────────────────
    @classmethod
    def _parse_invoice_ocr_rows(cls, text):
        rows   = []
        seen   = set()
        lines  = [cls._cleanup_ocr_line(line) for line in text.splitlines()]
        header_index = -1
        for idx, line in enumerate(lines):
            lowered = cls._normalize_key(line)
            if ("mal hizmet" in lowered or "aciklama" in lowered) and (
                "miktar" in lowered or "birim fiyat" in lowered or "tutar" in lowered
            ):
                header_index = idx
                break

        active_lines = lines[header_index + 1:] if header_index >= 0 else lines
        for raw_line in active_lines:
            line = cls._cleanup_ocr_invoice_line(raw_line)
            if not line:
                continue
            lowered = cls._normalize_key(line)
            if cls._is_invoice_footer_line(lowered):
                break
            if cls._matches_invoice_skip_label(lowered):
                break
            if cls._is_firm_name_line(line):
                continue
            parsed = cls._parse_invoice_ocr_line(line)
            if not parsed:
                continue
            row = cls._normalize_row(parsed)
            if not row.get("name"):
                continue
            key = (row.get("name", ""), row.get("stock", 0),
                   row.get("purchase_price", 0.0), row.get("currency", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    # ── Çok satırlı blok parser ────────────────────────────────────────────
    @classmethod
    def _parse_invoice_multiline_blocks(cls, text):
        rows  = []
        lines = [cls._cleanup_ocr_invoice_line(line) for line in text.splitlines()]
        seen  = set()
        for idx, line in enumerate(lines[:-1]):
            next_line = lines[idx + 1]
            if not line or not next_line:
                continue
            if cls._matches_invoice_skip_label(cls._normalize_key(line)):
                continue
            if cls._matches_invoice_skip_label(cls._normalize_key(next_line)):
                continue
            if not cls._looks_like_product_name(line):
                continue
            if not cls._looks_like_numeric_invoice_line(next_line):
                continue
            parsed = cls._parse_invoice_ocr_line(f"{line} {next_line}")
            if not parsed:
                continue
            row = cls._normalize_row(parsed)
            key = (row.get("name", ""), row.get("stock", 0),
                   row.get("purchase_price", 0.0), row.get("currency", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    # ── Serbest form parser'lar ────────────────────────────────────────────
    @classmethod
    def _parse_key_value_blocks(cls, text):
        rows    = []
        current = {}
        for raw_line in text.splitlines() + [""]:
            line = raw_line.strip()
            if not line:
                if current.get("name") or current.get("brand"):
                    rows.append(current.copy())
                current = {}
                continue
            match = re.match(r"^\s*([^:=\-]{2,40})\s*[:=\-]\s*(.+?)\s*$", line)
            if match:
                label = cls._normalize_key(match.group(1))
                field = cls.LABEL_ALIASES.get(label)
                if field:
                    current[field] = match.group(2).strip()
                    continue
            if not current.get("name"):
                current["name"] = line
            elif not current.get("desc"):
                current["desc"] = line
        return [cls._normalize_row(row) for row in rows if row.get("name")]

    @classmethod
    def _parse_freeform_lines(cls, text):
        rows = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            name = cls._extract_text_after(line, ["urun", "urun adi", "parca", "parca adi", "ad"])
            if not name:
                continue
            rows.append(cls._normalize_row({
                "name":             name,
                "brand":            cls._extract_text_after(line, ["marka", "brand", "marka model"]),
                "compatible_models":cls._extract_text_after(line, ["model", "uyumlu arac"]),
                "stock":            cls._extract_number_after(line, ["adet", "miktar", "qty", "stock"]),
                "purchase_price":   cls._extract_number_after(
                    line, ["alis", "alis fiyati", "maliyet", "cost", "birim fiyat"]
                ),
                "price":            cls._extract_number_after(line, ["satis", "satis fiyati", "price"]),
                "vehicle_brand":    cls._extract_text_after(line, ["arac marka"]),
                "vehicle_model":    cls._extract_text_after(line, ["arac model"]),
                "supplier":         cls._extract_text_after(line, ["tedarikci", "supplier"]),
                "position":         cls._extract_text_after(line, ["parca konumu", "pozisyon"]),
            }))
        return rows
