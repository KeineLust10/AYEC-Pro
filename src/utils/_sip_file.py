# -*- coding: utf-8 -*-
# _sip_file.py
# Dosya parse mixin'i — CSV, Excel, PDF, XML, DOCX.

import csv
import io
import re
import zipfile
from pathlib import Path

from defusedxml import ElementTree as ET

from ._sip_lazy_imports import pd, pdfplumber, QPdfDocument


class _SipFile:
    """
    Dosya ayrıştırma işlemleri.
    _SipUtils, _SipNormalize, _SipInvoiceParsers ile birlikte kullanılır.
    """

    # ── Companion XML tespiti ──────────────────────────────────────────────
    @classmethod
    def _find_companion_xml(cls, file_path):
        try:
            parent    = Path(file_path).parent
            xml_files = sorted(parent.glob("*.xml"))
            if not xml_files:
                return None
            if len(xml_files) == 1:
                return xml_files[0]
            stem      = cls._normalize_key(Path(file_path).stem)
            stem_base = stem.replace("ubl", "").strip()
            candidates = [stem, stem_base]
            for xml_path in xml_files:
                xml_stem = cls._normalize_key(xml_path.stem)
                if any(
                    token and (token in xml_stem or xml_stem in token)
                    for token in candidates
                ):
                    return xml_path
            for xml_path in xml_files:
                xml_stem = cls._normalize_key(xml_path.stem)
                if "ubl" in xml_stem or "fatura" in xml_stem or "invoice" in xml_stem:
                    return xml_path
            return None
        except Exception:
            return None

    # ── CSV ────────────────────────────────────────────────────────────────
    @classmethod
    def _parse_csv(cls, file_path):
        from ._sip_lazy_imports import get_pd
        pd = get_pd()
        rows   = []
        columns = []
        metadata = {}

        read_attempts = [
            {"encoding": "utf-8-sig", "sep": None},
            {"encoding": "cp1254",    "sep": None},
            {"encoding": "latin1",    "sep": None},
        ]
        for attempt in read_attempts:
            try:
                df = pd.read_csv(
                    file_path,
                    dtype=str,
                    keep_default_na=False,
                    sep=attempt["sep"],
                    engine="python",
                    encoding=attempt["encoding"],
                )
                if df is not None and not df.empty:
                    df = df.fillna("")
                    columns = [str(col) for col in df.columns]
                    for _, row in df.iterrows():
                        item = {
                            str(col): str(row.get(col, "") or "").strip()
                            for col in df.columns
                        }
                        if any(str(v).strip() for v in item.values()):
                            rows.append(item)
                    metadata["csv_encoding"] = attempt["encoding"]
                    break
            except Exception:
                continue

        if not rows:
            try:
                with open(file_path, "r", encoding="utf-8-sig", newline="") as fh:
                    sample  = fh.read(2048)
                    fh.seek(0)
                    dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
                    reader  = csv.DictReader(fh, dialect=dialect)
                    columns = list(reader.fieldnames or [])
                    for item in reader:
                        cleaned = {
                            str(k): str(v or "").strip()
                            for k, v in (item or {}).items()
                        }
                        if any(str(v).strip() for v in cleaned.values()):
                            rows.append(cleaned)
                    metadata["csv_engine"] = "csv_fallback"
            except Exception:
                rows = []

        if not rows:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": metadata}

        detected = columns or cls._detect_columns_from_rows(rows)
        return {
            "raw_rows": rows,
            "detected_columns": detected,
            "suggested_mapping": cls._match_column_names(detected),
            "metadata": metadata,
        }

    # ── Excel ──────────────────────────────────────────────────────────────
    @classmethod
    def _parse_spreadsheet(cls, file_path):
        from ._sip_lazy_imports import get_pd
        pd = get_pd()
        try:
            df_raw = pd.read_excel(file_path, header=None, dtype=str, keep_default_na=False)
        except Exception:
            df_raw = None

        if df_raw is None or df_raw.empty:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}

        df_raw = df_raw.fillna("")

        best_header_row = None
        best_hits       = 0
        for scan_row in range(min(15, len(df_raw))):
            candidate_vals = [str(v or "").strip() for v in df_raw.iloc[scan_row].tolist()]
            hits = sum(
                1 for v in candidate_vals
                if cls._normalize_key(v) in cls.COLUMN_ALIASES
            )
            if hits > best_hits and hits >= 2:
                best_hits       = hits
                best_header_row = scan_row

        header_idx = best_header_row if best_header_row is not None else 0
        try:
            df = pd.read_excel(file_path, header=header_idx, dtype=str, keep_default_na=False)
            if df is None or df.empty:
                raise ValueError("empty")
            df = df.fillna("")
        except Exception:
            try:
                df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
                df = df.fillna("")
                best_header_row = None
            except Exception:
                return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}

        detected_columns  = [str(col) for col in df.columns]
        suggested_mapping = cls._match_column_names(detected_columns)

        raw_rows = []
        for _, row in df.iterrows():
            item = {str(col): str(row.get(col, "") or "").strip() for col in df.columns}
            if not any(v for v in item.values()):
                continue
            vals = [item[k] for k in df.columns if str(k) in item]
            keys = [str(k) for k in df.columns]
            if vals == keys:
                continue
            raw_rows.append(item)

        return {
            "raw_rows": raw_rows,
            "detected_columns": detected_columns,
            "suggested_mapping": suggested_mapping,
            "metadata": {"header_row": best_header_row},
        }

    # ── DOCX ──────────────────────────────────────────────────────────────
    @classmethod
    def _read_docx_text(cls, file_path):
        namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        with zipfile.ZipFile(file_path) as zf:
            xml_bytes = zf.read("word/document.xml")
        root  = ET.fromstring(xml_bytes)
        lines = []
        for paragraph in root.findall(".//w:p", namespaces):
            parts = [
                node.text.strip()
                for node in paragraph.findall(".//w:t", namespaces)
                if node.text and node.text.strip()
            ]
            if parts:
                lines.append(" ".join(parts))
        return "\n".join(lines)

    # ── PDF ────────────────────────────────────────────────────────────────
    @classmethod
    def _read_pdf_text(cls, file_path):
        try:
            from ._sip_lazy_imports import get_QPdfDocument
            QPdfDocument = get_QPdfDocument()
            if not QPdfDocument:
                return ""
            document = QPdfDocument(None)  # parent olarak None ver
            if document.load(str(file_path)) != QPdfDocument.Status.Ready:
                return ""
            pages = []
            for page in range(document.pageCount()):
                try:
                    pages.append(document.getAllText(page).text())
                except Exception:
                    pass
            return "\n".join(pages)
        except Exception:
            return ""

    @classmethod
    def _parse_pdf_document(cls, file_path):
        from ._sip_lazy_imports import get_pdfplumber
        pdfplumber = get_pdfplumber()
        pdf_text = ""
        rows = []
        metadata = {}
        invoice_header = None
        if pdfplumber and pdfplumber is not False:
            try:
                with pdfplumber.open(str(file_path)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        if page_text:
                            pdf_text += page_text + "\n"
                            page_metadata = cls._extract_document_metadata(page_text)
                            for key, value in page_metadata.items():
                                metadata.setdefault(key, value)
                        tables = page.extract_tables() or []
                        for table in tables:
                            if not table:
                                continue
                            first_row_text = cls._normalize_key(
                                " ".join(str(cell or "") for cell in table[0])
                            )
                            if cls._is_invoice_header_line(first_row_text):
                                invoice_header = list(table[0])
                                parse_table = table
                            elif invoice_header:
                                parse_table = [invoice_header] + list(table)
                            else:
                                parse_table = table
                            normalized = cls._parse_table_rows(parse_table)
                            rows.extend(normalized)
                    if rows:
                        supplier_company = str(
                            metadata.get("supplier_company") or ""
                        ).strip()
                        if supplier_company:
                            for row in rows:
                                if not str(row.get("supplier") or "").strip():
                                    row["supplier"] = supplier_company
                        rows = cls._dedupe_rows(rows)
                        detected_columns = cls._detect_columns_from_rows(rows)
                        return {
                            "raw_rows": rows,
                            "detected_columns": detected_columns,
                            "suggested_mapping": cls._match_column_names(detected_columns),
                            "metadata": metadata,
                        }
            except Exception:
                pass

        # If no tables were extracted, fall back to parsing the plain text extracted via pdfplumber or QPdfDocument
        raw_text = pdf_text if pdf_text.strip() else cls._read_pdf_text(file_path)
        text_parsed = cls._parse_text_content(raw_text)
        if text_parsed.get("raw_rows"):
            return text_parsed

        ocr_parsed = cls._parse_pdf_via_ocr(file_path)
        if ocr_parsed.get("raw_rows"):
            metadata = ocr_parsed.get("metadata") or {}
            metadata["pdf_mode"] = "ocr_fallback"
            ocr_parsed["metadata"] = metadata
            return ocr_parsed
        return text_parsed


    @classmethod
    def _parse_pdf_via_ocr(cls, file_path):
        from ._sip_lazy_imports import get_pdfplumber
        pdfplumber = get_pdfplumber()
        if not pdfplumber:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}
        best   = {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}
        best_score = -1.0
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for page in (pdf.pages or [])[:4]:
                    try:
                        page_img = page.to_image(resolution=300)
                        pil_img  = page_img.original.convert("RGB")
                        ocr_text = cls._ocr_image_to_text(pil_img)
                        if not ocr_text.strip():
                            continue
                        parsed = cls._parse_text_content(ocr_text, strict_table=True)
                        score  = cls._score_parse_result(parsed)
                        if score > best_score:
                            best   = parsed
                            best_score = score
                    except Exception:
                        continue
        except Exception:
            return best
        return best

    # ── PDF tablo satırları ────────────────────────────────────────────────
    @classmethod
    def _parse_table_rows(cls, table):
        if not table or len(table) < 2:
            return []
        header = [cls._normalize_key(cell or "") for cell in table[0]]

        NAME_KEYS  = {"mal hizmet", "mal hizmet adi", "mal  hizmet", "aciklama",
                      "aciklama ad", "urun adi", "urun", "hizmet", "ticari mal",
                      "kalem", "cins", "tanim", "mal  hizmet adi", "urun hizmet",
                      "goods service", "item", "description"}
        STOCK_KEYS = {"miktar", "adet", "quantity", "qty", "miktar adet",
                      "siparis miktari", "pcs"}
        PRICE_KEYS = {"birim fiyat", "birim fiyati", "birim bedel", "unit price",
                      "fiyat", "alis fiyati", "kdvsiz birim fiyat",
                      "mal hizmet birim fiyati", "birim tutar", "birim tutari"}
        TOTAL_KEYS = {"mal hizmet tutari", "mal hizmet toplam", "tutar", "toplam",
                      "toplam tutar", "line total", "amount", "mal  hizmet tutari"}
        CODE_KEYS  = {"urun kod", "urun kodu", "stok no", "stok numarasi",
                      "stok kodu", "barkod", "barcode", "product code", "code"}

        name_idx = stock_idx = price_idx = total_idx = code_idx = None
        for idx, h in enumerate(header):
            if name_idx  is None and h in NAME_KEYS:  name_idx  = idx
            elif stock_idx is None and h in STOCK_KEYS: stock_idx = idx
            elif price_idx is None and h in PRICE_KEYS: price_idx = idx
            elif total_idx is None and h in TOTAL_KEYS: total_idx = idx
            if code_idx is None and h in CODE_KEYS:
                code_idx = idx

        if name_idx is None:
            for idx, h in enumerate(header):
                if "mal" in h and ("hizmet" in h or "hizm" in h):
                    name_idx = idx
                    break
            if name_idx is None:
                for idx, h in enumerate(header):
                    if any(k in h for k in ("aciklama", "urun", "hizmet", "tanim", "kalem", "cins")):
                        name_idx = idx
                        break

        if price_idx is None:
            for idx, h in enumerate(header):
                if "birim" in h and ("fiyat" in h or "bedel" in h or "tutar" in h):
                    price_idx = idx
                    break
            if price_idx is None:
                for idx, h in enumerate(header):
                    if "fiyat" in h or "bedel" in h:
                        price_idx = idx
                        break

        if stock_idx is None:
            for idx, h in enumerate(header):
                if "miktar" in h or "adet" in h or "qty" in h:
                    stock_idx = idx
                    break

        if total_idx is None:
            for idx, h in enumerate(header):
                if "tutar" in h and idx != price_idx:
                    total_idx = idx
                    break

        raw_rows = []
        for values in table[1:]:
            if not values:
                continue

            def _cell(idx):
                if idx is None or idx >= len(values):
                    return ""
                return str(values[idx] or "").strip()

            name_val  = _cell(name_idx)
            code_val  = _cell(code_idx).replace("\n", "").strip()
            stock_raw = _cell(stock_idx)
            price_raw = _cell(price_idx)
            total_raw = _cell(total_idx)

            normalized_values = cls._normalize_key(
                " ".join(str(cell or "") for cell in values)
            )
            sequence_value = _cell(0)
            if (
                cls._is_invoice_footer_line(normalized_values)
                or (
                    not re.search(r"\d", sequence_value)
                    and cls._matches_invoice_skip_label(normalized_values)
                )
            ):
                continue

            if not name_val:
                row_dict = {}
                for idx, cell in enumerate(values):
                    if idx < len(header) and header[idx]:
                        row_dict[header[idx]] = str(cell or "").strip()
                name_val = (row_dict.get("mal hizmet") or row_dict.get("mal  hizmet")
                            or row_dict.get("aciklama") or row_dict.get("urun adi")
                            or row_dict.get("urun") or "")
                if not stock_raw:
                    stock_raw = row_dict.get("miktar") or row_dict.get("adet") or ""
                if not price_raw:
                    price_raw = row_dict.get("birim fiyat") or row_dict.get("fiyat") or ""
                if not total_raw:
                    total_raw = row_dict.get("mal hizmet tutari") or row_dict.get("tutar") or ""
                if not code_val:
                    code_val = (row_dict.get("urun kod") or row_dict.get("urun kodu")
                                or row_dict.get("stok no") or row_dict.get("stok kodu")
                                or row_dict.get("barkod") or "")

            if not name_val:
                continue

            price_str, currency_from_price = cls._extract_price_and_currency(price_raw)
            total_str, currency_from_total = cls._extract_price_and_currency(total_raw)
            detected_currency = (
                currency_from_price or currency_from_total
                or cls._detect_currency(f"{price_raw} {total_raw} {name_val}")
            )
            qty_str, unit_value = cls._extract_qty_and_unit(stock_raw)

            normalized = cls._normalize_row({
                "name": name_val,
                "code": code_val,
                "unit": unit_value,
                "stock": qty_str,
                "purchase_price": price_str,
                "line_total": total_str,
                "price": "",
                "currency": detected_currency,
                "_manual_sale_price": True,
            })
            if normalized.get("name"):
                raw_rows.append(normalized)
        return raw_rows

    # ── XML ────────────────────────────────────────────────────────────────
    @classmethod
    def _parse_xml_invoice(cls, file_path):
        try:
            root = ET.parse(str(file_path)).getroot()
        except Exception:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}

        metadata = {
            "invoice_no":       cls._find_xml_text(root, "ID"),
            "invoice_date":     cls._find_xml_text(root, "IssueDate"),
            "invoice_type":     cls._find_xml_text(root, "InvoiceTypeCode"),
            "invoice_scenario": cls._find_xml_text(root, "ProfileID"),
        }

        rows = []
        for line in cls._find_xml_nodes(root, "InvoiceLine"):
            quantity_node = cls._find_xml_node(line, "InvoicedQuantity")
            price_node    = cls._find_xml_node(line, "PriceAmount")
            total_node    = cls._find_xml_node(line, "LineExtensionAmount")
            name          = cls._find_xml_text(line, "Name")
            if not name:
                item_node = cls._find_xml_node(line, "Item")
                if item_node is not None:
                    name = cls._find_xml_text(item_node, "Name")
            currency = ""
            if total_node is not None:
                currency = str(total_node.attrib.get("currencyID") or "").upper()
            if not currency and price_node is not None:
                currency = str(price_node.attrib.get("currencyID") or "").upper()
            row = cls._normalize_row({
                "name":           name or "",
                "stock":          cls._xml_text(quantity_node),
                "purchase_price": cls._xml_text(price_node),
                "price":          cls._xml_text(total_node),
                "currency":       currency,
            })
            if row.get("name"):
                rows.append(row)

        rows = cls._dedupe_rows(rows)
        detected_columns = cls._detect_columns_from_rows(rows)
        return {
            "raw_rows": rows,
            "detected_columns": detected_columns,
            "suggested_mapping": cls._match_column_names(detected_columns),
            "metadata": {k: v for k, v in metadata.items() if v},
        }
