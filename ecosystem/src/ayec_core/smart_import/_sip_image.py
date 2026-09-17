# -*- coding: utf-8 -*-
# _sip_image.py
# Görsel parse mixin'i — tablo çizgisi tespiti, bölge kırpma,
# çizgisiz satır bulma, belge bölge tespiti.

import re


class _SipImage:
    """
    Görsel parse işlemleri.
    _SipOcr, _SipUtils, _SipConstants ile birlikte kullanılır.
    """

    # ── Ana görüntü parse ──────────────────────────────────────────────────
    @classmethod
    def _parse_image(cls, file_path, strict_table=False):
        from ._sip_lazy_imports import (
            get_Image, get_ImageOps,
            _get_easyocr_reader, get_pytesseract
        )
        Image = get_Image()
        ImageOps = get_ImageOps()
        pytesseract = get_pytesseract()
        if _get_easyocr_reader() is None and (
            not pytesseract or not cls._configure_tesseract()
        ):
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}

        try:
            base_image = Image.open(file_path)
            base_image = ImageOps.exif_transpose(base_image)
        except Exception:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}

        try:
            gray = ImageOps.autocontrast(ImageOps.grayscale(base_image), cutoff=2)
        except Exception:
            gray = base_image

        width, height = base_image.size
        candidates = []

        try:
            # 1) Telefon ekranı / WhatsApp ekran görüntüsü tespiti
            phone_crop = cls._crop_invoice_from_phone(base_image, gray)
            if phone_crop is not None:
                # Fatura belgesi bölgesini öncelikli aday olarak ekle
                candidates.append(cls._enhance_image_for_ocr(phone_crop))
                # Fatura içinde de tablo bölgesi kırp
                pw, ph = phone_crop.size
                # Üstteki logo/başlık bölgesini atla, tablo genellikle %25-85 arasında
                table_crop = phone_crop.crop((
                    int(pw * 0.00), int(ph * 0.25),
                    int(pw * 1.00), int(ph * 0.88),
                ))
                if table_crop.size[0] > 80 and table_crop.size[1] > 40:
                    candidates.append(cls._enhance_image_for_ocr(table_crop))

            # 2) Tam görsel (fallback)
            candidates.append(cls._enhance_image_for_ocr(base_image))

            # 3) Belge bölgesi tespiti
            detected_doc = cls._extract_document_region(gray)
            if detected_doc is not None:
                candidates.append(cls._enhance_image_for_ocr(detected_doc))

            # 4) Tablo bölgesi (alt yarı)
            tbl_crop = base_image.crop((
                int(width * 0.00), int(height * 0.35),
                int(width * 1.00), int(height * 0.88),
            ))
            if tbl_crop.size[0] > 50 and tbl_crop.size[1] > 30:
                candidates.append(cls._enhance_image_for_ocr(tbl_crop))

            # 5) Dikey görsel için orta kesit
            if height > width:
                crop_mid = base_image.crop((
                    int(width * 0.03), int(height * 0.15),
                    int(width * 0.97), int(height * 0.88),
                ))
                candidates.append(cls._enhance_image_for_ocr(crop_mid))
        except Exception:
            candidates = [cls._enhance_image_for_ocr(base_image)]

        best = {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}
        best_score = -1.0
        for img in candidates:
            ocr_text = cls._ocr_image_to_text(img)
            if not ocr_text.strip():
                continue
            parsed = cls._parse_text_content(ocr_text, strict_table=strict_table)
            score = cls._score_parse_result(parsed)
            if score > best_score:
                best = parsed
                best_score = score
            if best.get("raw_rows") and len(best["raw_rows"]) >= 2:
                return best

        if not best.get("raw_rows"):
            try:
                col_rows = cls._extract_rows_lineless(gray)
                if col_rows:
                    best = {
                        "raw_rows": col_rows,
                        "detected_columns": list({k for r in col_rows for k in r}),
                        "suggested_mapping": {f: f for f in cls.FIELD_ORDER},
                        "metadata": {},
                    }
            except Exception:
                pass
        return best

    # ── Telefon / WhatsApp ekran görüntüsü tespiti ────────────────────────
    @classmethod
    def _detect_phone_screenshot(cls, gray_image):
        """
        Görselin bir telefon ekran görüntüsü olup olmadığını tespit eder.
        Belirtiler:
        - Dikey oran (yükseklik / genişlik > 1.5)
        - Üstte koyu status bar bölgesi (karanlık piksel bandı)
        - Belirgin beyaz belge dikdörtgeni ortada
        Returns:
            True/False
        """
        try:
            width, height = gray_image.size
            aspect = height / max(width, 1)

            # Dikey oran kontrolü
            if aspect < 1.2:
                return False

            # Üst %8'lik bölgede koyu piksel oranı (status bar)
            top_band_h = int(height * 0.08)
            if top_band_h < 5:
                return False
            pix = gray_image.load()
            dark_count = 0
            sample_cols = max(1, width // 30)
            total = 0
            for y in range(top_band_h):
                for x in range(0, width, sample_cols):
                    total += 1
                    if pix[x, y] < 80:  # koyu piksel
                        dark_count += 1
            dark_ratio = dark_count / max(total, 1)

            # Orta bölgede beyaz alan kontrolü (fatura belgesi)
            mid_y = height // 2
            mid_band_h = int(height * 0.15)
            bright_count = 0
            total2 = 0
            for y in range(mid_y - mid_band_h // 2, mid_y + mid_band_h // 2):
                if y < 0 or y >= height:
                    continue
                for x in range(int(width * 0.05), int(width * 0.95), sample_cols):
                    total2 += 1
                    if pix[x, y] > 200:  # parlak piksel
                        bright_count += 1
            bright_ratio = bright_count / max(total2, 1)

            # Telefon ekranı: ya üstte koyu status bar ya da ortada büyük beyaz alan
            return dark_ratio > 0.15 or bright_ratio > 0.60
        except Exception:
            return False

    @classmethod
    def _crop_invoice_from_phone(
        cls, base_image, gray_image
    ):
        """
        Telefon ekranı görselinden fatura belgesini kırpar.
        1. Telefon çerçevesini atlar (kenar padding)
        2. En büyük beyaz dikdörtgen bölgeyi döndürür
        3. Başarısız olursa None döner (ana parser fallback kullanır)
        """
        try:
            if not cls._detect_phone_screenshot(gray_image):
                return None

            width, height = base_image.size

            # WhatsApp fatura fotoğrafı genellikle chat balonu içinde:
            # - Soldan %3-5, sağdan %3-5 padding
            # - Üstten %12-20 (status bar + chat başlığı + ballon üstü)
            # - Alttan %10-15 (alt menü + ballon altı)
            # Önce sabit kırpma ile başla
            left   = int(width  * 0.04)
            top    = int(height * 0.14)
            right  = int(width  * 0.96)
            bottom = int(height * 0.88)

            # Kırpılan bölgede en büyük beyaz dikdörtgeni bul
            crop = gray_image.crop((left, top, right, bottom))
            doc_region = cls._find_white_document_rect(crop)

            if doc_region is not None:
                # Koordinatları orijinal görsele geri çevir
                dx, dy, dw, dh = doc_region
                abs_left   = left  + dx
                abs_top    = top   + dy
                abs_right  = left  + dx + dw
                abs_bottom = top   + dy + dh
                # Minimum boyut kontrolü
                if (abs_right - abs_left) > width * 0.25 and (abs_bottom - abs_top) > height * 0.15:
                    return base_image.crop((abs_left, abs_top, abs_right, abs_bottom))

            # Belge tespiti başarısız — sabit kırpmayı döndür
            cropped = base_image.crop((left, top, right, bottom))
            if cropped.size[0] > 80 and cropped.size[1] > 80:
                return cropped
            return None
        except Exception:
            return None

    @classmethod
    def _find_white_document_rect(cls, gray_crop):
        """
        Kırpılmış gri görselde en büyük beyaz dikdörtgen bölgeyi bulur.
        Fatura belgesi tipik olarak beyaz arka plana sahiptir.
        Returns:
            (x, y, w, h) tuple veya None
        """
        try:
            width, height = gray_crop.size
            pix = gray_crop.load()

            # Her satırın ortalama parlaklığını hesapla
            row_brightness = []
            step = max(1, width // 50)
            for y in range(height):
                total = sum(pix[x, y] for x in range(0, width, step))
                avg = total / max(1, width // step)
                row_brightness.append(avg)

            # Beyaz bölge eşiği
            BRIGHT_THRESHOLD = 185

            # Ardışık parlak satır bantlarını bul
            in_bright = False
            bright_bands = []
            band_start = 0
            for y, brightness in enumerate(row_brightness):
                if brightness >= BRIGHT_THRESHOLD and not in_bright:
                    in_bright = True
                    band_start = y
                elif brightness < BRIGHT_THRESHOLD and in_bright:
                    in_bright = False
                    if y - band_start >= int(height * 0.05):  # min %5 yükseklik
                        bright_bands.append((band_start, y))
            if in_bright and height - band_start >= int(height * 0.05):
                bright_bands.append((band_start, height))

            if not bright_bands:
                return None

            # En büyük bandı seç
            best_band = max(bright_bands, key=lambda b: b[1] - b[0])
            band_y_start, band_y_end = best_band

            # Bu bandda sütun (x ekseni) sınırlarını bul
            col_bright = []
            step_y = max(1, (band_y_end - band_y_start) // 20)
            for x in range(width):
                total = sum(
                    pix[x, y]
                    for y in range(band_y_start, band_y_end, step_y)
                    if 0 <= y < height
                )
                count = len(range(band_y_start, band_y_end, step_y))
                col_bright.append(total / max(count, 1))

            # Sütun sınırları
            x_start = 0
            x_end = width
            for x in range(width):
                if col_bright[x] >= BRIGHT_THRESHOLD:
                    x_start = x
                    break
            for x in range(width - 1, -1, -1):
                if col_bright[x] >= BRIGHT_THRESHOLD:
                    x_end = x + 1
                    break

            w = x_end - x_start
            h = band_y_end - band_y_start
            if w < width * 0.2 or h < height * 0.1:
                return None
            return (x_start, band_y_start, w, h)
        except Exception:
            return None

    # ── Tablo ızgara tespiti ───────────────────────────────────────────────
    @classmethod
    def _parse_grid_rows_from_image(cls, file_path):
        from ._sip_lazy_imports import (
            get_Image, get_ImageOps, get_ImageFilter
        )
        Image = get_Image()
        ImageOps = get_ImageOps()
        ImageFilter = get_ImageFilter()
        if not cls._configure_tesseract():
            return []
        try:
            img = Image.open(file_path)
            img = ImageOps.exif_transpose(img)
            gray = ImageOps.grayscale(img)
            gray = ImageOps.autocontrast(gray, cutoff=2)
            w, h = gray.size
            if w < 1200:
                scale = max(2, 2400 // max(w, 1))
                gray = gray.resize((w * scale, h * scale), Image.LANCZOS)
                gray = gray.filter(ImageFilter.SHARPEN)
                gray = gray.filter(ImageFilter.SHARPEN)
            elif w < 2000:
                gray = gray.resize((w * 2, h * 2), Image.LANCZOS)
                gray = gray.filter(ImageFilter.SHARPEN)
        except Exception:
            return []

        all_rows = []
        for threshold in [0.25, 0.30, 0.40, 0.50]:
            rows = cls._extract_rows_with_threshold(gray, threshold)
            if len(rows) >= len(all_rows):
                all_rows = rows
            if len(all_rows) >= 2:
                break

        if not all_rows:
            all_rows = cls._extract_rows_lineless(gray)
        return cls._dedupe_rows(all_rows)

    @classmethod
    def _extract_rows_with_threshold(cls, gray, black_threshold):
        from ._sip_lazy_imports import get_ImageFilter
        ImageFilter = get_ImageFilter()
        best_rows = []
        for bw_thresh in [160, 180, 200, 128]:
            bw = gray.point(lambda p, t=bw_thresh: 255 if p > t else 0, mode="1")
            pix = bw.load()
            width, height = bw.size
            line_y = []
            for y in range(height):
                black = sum(1 for x in range(width) if pix[x, y] == 0)
                if width > 0 and (black / width) >= black_threshold:
                    line_y.append(y)
            if len(line_y) < 3:
                continue
            bands = []
            start = line_y[0]
            prev  = line_y[0]
            for y in line_y[1:]:
                if y == prev + 1:
                    prev = y
                    continue
                bands.append((start, prev))
                start = y
                prev  = y
            bands.append((start, prev))
            if len(bands) < 3:
                continue
            rows = cls._ocr_row_bands(gray, bands, width, height)
            if len(rows) > len(best_rows):
                best_rows = rows
            if len(best_rows) >= 2:
                break
        return best_rows

    @classmethod
    def _ocr_row_bands(cls, gray, bands, width, height):
        rows = []
        for i in range(len(bands) - 1):
            top    = bands[i][1] + 1
            bottom = bands[i + 1][0] - 1
            h = bottom - top + 1
            if h < 8 or h > 200:
                continue
            combined = cls._ocr_row_split(
                gray, 0, max(0, top), width, min(height, bottom + 1)
            )
            if not combined:
                continue
            parsed = cls._parse_single_invoice_row_text(combined)
            if parsed:
                rows.append(parsed)
        return rows

    @classmethod
    def _ocr_row_split(cls, gray, x0, y0, x1, y1):
        from ._sip_lazy_imports import get_Image, get_ImageOps, get_ImageFilter
        Image = get_Image()
        ImageOps = get_ImageOps()
        ImageFilter = get_ImageFilter()
        """Tek satırı sütun bölgelerine bölerek OCR et."""
        w = x1 - x0
        h = y1 - y0
        if h < 4 or w < 10:
            return None
        scale = 4 if h < 15 else (3 if h < 25 else 2)

        def _ocr_crop(left, right):
            crop = gray.crop((left, y0, right, y1))
            crop = crop.resize(
                (max(1, crop.width * scale), max(1, crop.height * scale)),
                Image.LANCZOS,
            )
            crop = ImageOps.autocontrast(crop, cutoff=2)
            crop = crop.filter(ImageFilter.SHARPEN)
            return cls._ocr_image_to_text(crop.convert("RGB")).strip()

        split_x   = x0 + int(w * 0.55)
        name_text = _ocr_crop(x0, split_x)
        nums_text = _ocr_crop(split_x, x1)
        combined  = f"1 {name_text} {nums_text}".strip()
        return combined if combined.strip() != "1" else None

    @classmethod
    def _extract_rows_lineless(cls, gray):
        from ._sip_lazy_imports import get_Image
        Image = get_Image()
        try:
            width, height = gray.size
            pix = gray.load()
            row_brightness = [
                sum(pix[x, y] for x in range(width)) / width
                for y in range(height)
            ]
            threshold_bright = 200
            rows = []
            in_text = False
            text_start = 0
            text_bands = []
            for y, brightness in enumerate(row_brightness):
                if brightness < threshold_bright and not in_text:
                    in_text = True
                    text_start = y
                elif brightness >= threshold_bright and in_text:
                    in_text = False
                    band_h = y - text_start
                    if 8 <= band_h <= 180:
                        text_bands.append((text_start, y))
            if in_text:
                band_h = height - text_start
                if 8 <= band_h <= 180:
                    text_bands.append((text_start, height))
            for top, bottom in text_bands:
                width2 = gray.size[0]
                combined = cls._ocr_row_split(gray, 0, top, width2, bottom)
                if not combined:
                    continue
                parsed = cls._parse_single_invoice_row_text(combined)
                if parsed:
                    rows.append(parsed)
            return rows
        except Exception:
            return []

    # ── Belge bölgesi tespiti ─────────────────────────────────────────────
    @classmethod
    def _extract_document_region(cls, gray_image):
        try:
            width, height = gray_image.size
            pixels = gray_image.load()
            bright_points = []
            for y in range(0, height, max(1, height // 250)):
                for x in range(0, width, max(1, width // 250)):
                    if pixels[x, y] >= 215:
                        bright_points.append((x, y))
            if len(bright_points) < 100:
                return None
            xs = [p[0] for p in bright_points]
            ys = [p[1] for p in bright_points]
            left   = max(0, min(xs) - 10)
            top    = max(0, min(ys) - 10)
            right  = min(width,  max(xs) + 10)
            bottom = min(height, max(ys) + 10)
            if right - left < width * 0.35 or bottom - top < height * 0.20:
                return None
            return gray_image.crop((left, top, right, bottom))
        except Exception:
            return None

    @classmethod
    def _build_document_focus_candidates(cls, document_image):
        from ._sip_lazy_imports import get_Image
        Image = get_Image()
        candidates = []
        try:
            width, height = document_image.size
            table_left = document_image.crop((
                int(width * 0.02), int(height * 0.34),
                int(width * 0.78), int(height * 0.63),
            ))
            candidates.append(table_left.resize(
                (max(1, table_left.width * 6), max(1, table_left.height * 6))
            ))
            table_full = document_image.crop((
                int(width * 0.02), int(height * 0.32),
                int(width * 0.98), int(height * 0.68),
            ))
            candidates.append(table_full.resize(
                (max(1, table_full.width * 5), max(1, table_full.height * 5))
            ))
            metadata_box = document_image.crop((
                int(width * 0.64), int(height * 0.12),
                int(width * 0.98), int(height * 0.38),
            ))
            candidates.append(metadata_box.resize(
                (max(1, metadata_box.width * 6), max(1, metadata_box.height * 6))
            ))
        except Exception:
            return []
        return candidates

    @classmethod
    def _parse_phone_screenshot_fast(cls, gray_image):
        from ._sip_lazy_imports import get_Image
        Image = get_Image()
        width, height = gray_image.size
        crops = []
        try:
            main_doc = gray_image.crop((
                int(width * 0.04), int(height * 0.20),
                int(width * 0.96), int(height * 0.86),
            ))
            crops.append(main_doc.resize(
                (max(1, main_doc.width * 3), max(1, main_doc.height * 3))
            ))
        except Exception:
            return {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}
        best       = {"raw_rows": [], "detected_columns": [], "suggested_mapping": {}, "metadata": {}}
        best_score = -1.0
        for crop in crops:
            ocr_text = cls._ocr_image_to_text(crop.convert("RGB"))
            if not ocr_text.strip():
                continue
            parsed = cls._parse_text_content(ocr_text, strict_table=True)
            score  = cls._score_parse_result(parsed)
            if score > best_score:
                best       = parsed
                best_score = score
        return best

    # ── Seçili alan wrapper ────────────────────────────────────────────────
    @classmethod
    def parse_selected_area(cls, path):
        """Seçili kırpma alanı için daha katı (satır odaklı) parser."""
        from pathlib import Path
        file_path = Path(path)
        ext = file_path.suffix.lower()
        if ext not in cls.IMAGE_EXTENSIONS:
            return cls.parse_file(path)

        candidates = []

        def _candidate_score(c):
            rows = c.get("rows") or []
            if not rows:
                return 0.0
            row_scores  = [cls._selected_area_row_quality(row) for row in rows]
            strong_rows = sum(1 for s in row_scores if s >= 7.0)
            return sum(row_scores) + min(strong_rows, 4) * 2.0

        def _is_strong_candidate(c):
            rows = c.get("rows") or []
            if not rows:
                return False
            row_scores  = [cls._selected_area_row_quality(row) for row in rows]
            strong_rows = sum(1 for s in row_scores if s >= 7.0)
            return strong_rows >= 2 or (len(rows) == 1 and row_scores[0] >= 11.0)

        def _result(c, warnings=None):
            return {
                "rows": c.get("rows") or [],
                "raw_rows": c.get("raw_rows") or [],
                "detected_columns": c.get("detected_columns") or [],
                "suggested_mapping": c.get("suggested_mapping") or {},
                "warnings": list(warnings if warnings is not None else c.get("warnings") or []),
                "metadata": c.get("metadata") or {},
                "source_path": str(file_path),
                "source_type": ext.lstrip("."),
            }

        paddle_rows = cls._parse_selected_area_with_paddle_boxes(file_path)
        if paddle_rows:
            candidate = {
                "rows": paddle_rows,
                "raw_rows": paddle_rows,
                "detected_columns": ["name", "stock", "purchase_price", "line_total", "currency"],
                "suggested_mapping": {
                    "name": "name",
                    "stock": "stock",
                    "purchase_price": "purchase_price",
                    "line_total": "line_total",
                    "currency": "currency",
                },
                "warnings": [],
                "metadata": {"parser": "paddleocr_boxes"},
            }
            candidates.append(candidate)
            if _is_strong_candidate(candidate):
                return _result(candidate)

        grid_rows = cls._parse_grid_rows_from_image(file_path)
        if grid_rows:
            detected_columns = cls._detect_columns_from_rows(grid_rows)
            mapping = cls._match_column_names(detected_columns)
            rows = cls._normalize_mapped_rows(grid_rows, mapping, invoice_mode=True)
            rows = cls._filter_core_rows(rows)
            rows = cls._filter_selected_area_rows(rows)
            candidate = {
                "rows": rows, "raw_rows": grid_rows,
                "detected_columns": detected_columns, "suggested_mapping": mapping,
                "warnings": [], "metadata": {"parser": "grid"},
            }
            candidates.append(candidate)
            if _is_strong_candidate(candidate):
                return _result(candidate)

        parsed = cls._parse_image(file_path, strict_table=True)
        raw_rows = parsed.get("raw_rows") or []
        mapping  = parsed.get("suggested_mapping") or {}
        rows = cls._normalize_mapped_rows(raw_rows, mapping, invoice_mode=True)
        rows = cls._filter_core_rows(rows)
        rows = cls._filter_selected_area_rows(rows)
        strict_candidate = {
            "rows": rows, "raw_rows": raw_rows,
            "detected_columns": parsed.get("detected_columns") or [],
            "suggested_mapping": mapping,
            "warnings": list(parsed.get("warnings") or []),
            "metadata": parsed.get("metadata") or {},
        }
        candidates.append(strict_candidate)
        if _is_strong_candidate(strict_candidate):
            return _result(strict_candidate)

        parsed = cls._parse_image(file_path, strict_table=False)
        raw_rows = parsed.get("raw_rows") or []
        mapping  = parsed.get("suggested_mapping") or {}
        rows = cls._normalize_mapped_rows(raw_rows, mapping, invoice_mode=True)
        rows = cls._filter_core_rows(rows)
        rows = cls._filter_selected_area_rows(rows)
        candidates.append({
            "rows": rows, "raw_rows": raw_rows,
            "detected_columns": parsed.get("detected_columns") or [],
            "suggested_mapping": mapping,
            "warnings": list(parsed.get("warnings") or []),
            "metadata": parsed.get("metadata") or {},
        })

        if not candidates:
            candidates.append({
                "rows": [], "raw_rows": [], "detected_columns": [],
                "suggested_mapping": {}, "warnings": [], "metadata": {},
            })

        best = sorted(candidates, key=_candidate_score, reverse=True)[0]
        rows = best.get("rows") or []
        warnings = list(best.get("warnings") or [])

        if not rows:
            try:
                fallback = cls.parse_file(str(file_path))
                fallback_rows = cls._filter_selected_area_rows(fallback.get("rows") or [])
                if fallback_rows:
                    warnings.insert(0, "Secili alan okunamadi; dosyanin tamami otomatik olarak tarandi.")
                    return _result({
                        "rows": fallback_rows,
                        "raw_rows": fallback.get("raw_rows") or [],
                        "detected_columns": fallback.get("detected_columns") or [],
                        "suggested_mapping": fallback.get("suggested_mapping") or {},
                        "metadata": fallback.get("metadata") or {},
                    }, warnings + list(fallback.get("warnings") or []))
            except Exception:
                pass
            warnings.append("Secili alanda satirlar net okunamadi. Alani biraz daha genis secin.")

        return _result(best, warnings)

    @classmethod
    def _parse_selected_area_with_paddle_boxes(cls, file_path):
        items = cls._paddleocr_box_items(file_path)
        if not items:
            return []
        rows = cls._group_paddle_items_by_row(items)
        header_index = cls._find_invoice_header_row(rows)
        if header_index is None:
            return []
        columns = cls._detect_invoice_columns_from_header(rows[header_index])
        if not columns:
            return []
        parsed_rows = []
        for row_items in rows[header_index + 1:]:
            row = cls._parse_paddle_invoice_row(row_items, columns)
            if row:
                parsed_rows.append(row)
        return cls._dedupe_rows(parsed_rows)

    @classmethod
    def _paddleocr_box_items(cls, file_path):
        try:
            from paddleocr import PaddleOCR
        except Exception:
            return []
        if not hasattr(cls, "_paddleocr_table_reader"):
            try:
                cls._paddleocr_table_reader = PaddleOCR(
                    use_angle_cls=True,
                    lang="tr",
                    show_log=False,
                )
            except Exception:
                return []
        try:
            result = cls._paddleocr_table_reader.ocr(str(file_path), cls=True)
        except Exception:
            return []
        items = []

        def _looks_like_bbox(value):
            if not isinstance(value, (list, tuple)) or len(value) < 4:
                return False
            try:
                for point in value[:4]:
                    if not isinstance(point, (list, tuple)) or len(point) < 2:
                        return False
                    float(point[0])
                    float(point[1])
                return True
            except Exception:
                return False

        def _add_line(bbox, payload):
            text = str(payload[0] if payload else "").strip()
            if not text:
                return
            try:
                confidence = float(payload[1])
            except Exception:
                confidence = 0.0
            try:
                xs = [float(pt[0]) for pt in bbox]
                ys = [float(pt[1]) for pt in bbox]
            except Exception:
                return
            items.append({
                "text": text,
                "confidence": confidence,
                "x0": min(xs),
                "x1": max(xs),
                "y0": min(ys),
                "y1": max(ys),
                "cx": sum(xs) / max(len(xs), 1),
                "cy": sum(ys) / max(len(ys), 1),
                "h": max(ys) - min(ys),
            })

        def _collect(node):
            if not node:
                return
            if isinstance(node, dict):
                texts = node.get("rec_texts") or node.get("texts") or []
                boxes = node.get("rec_polys") or node.get("rec_boxes") or node.get("dt_polys") or []
                scores = node.get("rec_scores") or node.get("scores") or []
                for idx, text in enumerate(texts):
                    bbox = boxes[idx] if idx < len(boxes) else None
                    if bbox is None:
                        continue
                    score = scores[idx] if idx < len(scores) else 0.0
                    _add_line(bbox, (text, score))
                return
            if isinstance(node, (list, tuple)):
                if len(node) >= 2 and _looks_like_bbox(node[0]) and isinstance(node[1], (list, tuple)):
                    _add_line(node[0], node[1])
                    return
                for child in node:
                    _collect(child)

        _collect(result)
        return items

    @classmethod
    def _group_paddle_items_by_row(cls, items):
        if not items:
            return []
        heights = sorted(max(1.0, item.get("h", 1.0)) for item in items)
        median_h = heights[len(heights) // 2] if heights else 12.0
        tolerance = max(8.0, min(22.0, median_h * 0.75))
        rows = []
        for item in sorted(items, key=lambda it: (it["cy"], it["x0"])):
            for row in rows:
                row_y = sum(it["cy"] for it in row) / max(len(row), 1)
                if abs(item["cy"] - row_y) <= tolerance:
                    row.append(item)
                    break
            else:
                rows.append([item])
        for row in rows:
            row.sort(key=lambda it: it["x0"])
        return rows

    @classmethod
    def _find_invoice_header_row(cls, rows):
        best_idx = None
        best_score = 0
        for idx, row in enumerate(rows):
            if len(row) < 3:
                continue
            text = cls._normalize_key(" ".join(item["text"] for item in row))
            item_keys = [cls._normalize_key(item["text"]) for item in row]
            score = 0
            if any("mal" in key and "hizmet" in key for key in item_keys):
                score += 3
            if any("miktar" in key for key in item_keys):
                score += 2
            if any("birim" in key and "fiyat" in key for key in item_keys):
                score += 2
            if any("tutar" in key for key in item_keys):
                score += 1
            if score > best_score:
                best_score = score
                best_idx = idx
        return best_idx if best_score >= 3 else None

    @classmethod
    def _detect_invoice_columns_from_header(cls, header_items):
        cols = {}
        for item in header_items:
            norm = cls._normalize_key(item["text"])
            cx = item["cx"]
            if "miktar" in norm:
                cols["stock"] = cx
            elif "birim" in norm and ("fiyat" in norm or "fyat" in norm):
                cols["purchase_price"] = cx
            elif "tutar" in norm and cx > cols.get("purchase_price", 0):
                cols["line_total"] = max(cx, cols.get("line_total", 0))
            elif "mal" in norm and "hizmet" in norm:
                if "name" not in cols:
                    cols["name"] = cx
                else:
                    cols["line_total"] = max(cx, cols.get("line_total", 0))
            elif (
                norm in ("pb", "para birimi", "para br", "para br.",
                         "doviz", "doviz birimi", "currency", "birim")
                or (norm.startswith("para") and "bir" in norm)
            ):
                # Para birimi / PB sutununu tespit et
                cols["currency"] = cx
        if "line_total" not in cols:
            xs = [item["cx"] for item in header_items]
            if xs:
                cols["line_total"] = max(xs)
        if "name" not in cols or not any(k in cols for k in ("stock", "purchase_price", "line_total")):
            return {}
        return cols

    @classmethod
    def _extract_money_candidates(cls, text):
        values = []
        for match in re.finditer(r"(?<!%)\b\d+(?:[.,]\d+)*(?:\s*(?:USD|EUR|TRY|TL))?\b", str(text or ""), flags=re.IGNORECASE):
            value = match.group(0).strip()
            if value:
                numeric = re.sub(r"\s*(USD|EUR|TRY|TL)\s*$", "", value, flags=re.IGNORECASE).strip()
                suffix = value[len(numeric):]
                if numeric.count(".") > 1 and "," not in numeric:
                    parts = numeric.split(".")
                    numeric = "".join(parts[:-1]) + "," + parts[-1]
                    value = numeric + suffix
                values.append(value)
        return values

    @classmethod
    def _parse_paddle_invoice_row(cls, row_items, columns):
        text_all = " ".join(item["text"] for item in row_items)
        norm_all = cls._normalize_key(text_all)
        if not row_items or any(key in norm_all for key in ("mal hizmet", "birim fiyat", "kdv orani")):
            return None
        ordered_cols = sorted(columns.items(), key=lambda pair: pair[1])
        boundaries = {}
        for idx, (field, center) in enumerate(ordered_cols):
            left = -10_000.0 if idx == 0 else (ordered_cols[idx - 1][1] + center) / 2
            right = 10_000.0 if idx == len(ordered_cols) - 1 else (center + ordered_cols[idx + 1][1]) / 2
            boundaries[field] = (left, right)
        buckets = {field: [] for field in columns}
        trailing_money = []
        for item in row_items:
            norm = cls._normalize_key(item["text"])
            if norm.isdigit() and item["cx"] < columns.get("name", 0):
                continue
            field = None
            for key, (left, right) in boundaries.items():
                if left <= item["cx"] < right:
                    field = key
                    break
            if field:
                buckets.setdefault(field, []).append(item["text"])
            if re.search(r"\d", item["text"]) and cls._detect_currency(item["text"]) in {"USD", "EUR", "TRY"}:
                trailing_money.append(item["text"])
        name = " ".join(buckets.get("name") or []).strip(" -|;:")
        stock = " ".join(buckets.get("stock") or []).strip()
        unit = " ".join(buckets.get("purchase_price") or []).strip()
        total = " ".join(buckets.get("line_total") or []).strip()
        if not total and trailing_money:
            total = trailing_money[-1]
        # Para birimi: once 'currency' bucket'inden oku (PB sutunu varsa)
        bucket_currency_text = " ".join(buckets.get("currency") or []).strip()
        currency = cls._detect_currency(" ".join([unit, total, text_all]))
        stock, _unit_label = cls._extract_qty_and_unit(stock)
        unit, unit_currency = cls._extract_price_and_currency(unit)
        total, total_currency = cls._extract_price_and_currency(total)
        unit_candidates = cls._extract_money_candidates(unit)
        total_candidates = cls._extract_money_candidates(total)
        if unit_candidates:
            unit = unit_candidates[0]
        if total_candidates:
            total = total_candidates[-1]
        # Para birimi oncelik sirasi: bucket (PB sutunu) > birim fiyat > tutar > text detect
        if bucket_currency_text:
            bucket_cur = str(bucket_currency_text).strip().upper()
            if bucket_cur in ("USD", "EUR", "TRY", "TL"):
                currency = "TRY" if bucket_cur == "TL" else bucket_cur
            else:
                currency = cls._detect_currency(bucket_currency_text) or unit_currency or total_currency or currency
        else:
            currency = unit_currency or total_currency or currency
        if not name or len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", name)) < 3:
            return None
        row = cls._normalize_row({
            "name": name,
            "stock": stock,
            "purchase_price": unit,
            "price": "",
            "line_total": total,
            "currency": currency,
            "desc": text_all,
            "_manual_sale_price": True,
            "_from_invoice": True,
            "_confidence": min((item.get("confidence", 1.0) for item in row_items), default=1.0),
        })
        expected_total = float(row.get("stock") or 0) * float(row.get("purchase_price") or 0.0)
        if expected_total > 0:
            current_total = float(row.get("line_total") or 0.0)
            if current_total <= 0 or current_total < expected_total * 0.35:
                row["line_total"] = round(expected_total, 4)
        if not row.get("stock") or not row.get("purchase_price"):
            return None
        return row
