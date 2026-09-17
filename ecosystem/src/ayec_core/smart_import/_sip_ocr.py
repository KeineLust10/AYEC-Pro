# -*- coding: utf-8 -*-
# _sip_ocr.py
# OCR işleme mixin'i — Tesseract yapılandırma, görüntü iyileştirme,
# EasyOCR/Tesseract/subprocess metin çıkarma.

import os
from pathlib import Path


class _SipOcr:
    """OCR yardımcıları. _SipUtils ve _SipConstants ile birlikte kullanılır."""

    # ── Tesseract yapılandırma ─────────────────────────────────────────────
    @classmethod
    def _configure_tesseract(cls):
        from ._sip_lazy_imports import get_pytesseract
        pytesseract = get_pytesseract()
        if not pytesseract:
            return False
        current_cmd = str(
            getattr(pytesseract.pytesseract, "tesseract_cmd", "") or ""
        ).strip()
        if current_cmd and Path(current_cmd).exists():
            return True
        for candidate in cls.TESSERACT_CANDIDATES:
            if Path(candidate).exists():
                pytesseract.pytesseract.tesseract_cmd = candidate
                return True
        return False

    # ── Görüntü iyileştirme ────────────────────────────────────────────────
    @classmethod
    def _enhance_image_for_ocr(cls, pil_image):
        from ._sip_lazy_imports import get_Image, get_ImageFilter, get_ImageOps
        Image = get_Image()
        ImageFilter = get_ImageFilter()
        ImageOps = get_ImageOps()
        """
        OCR doğruluğunu artırmak için gelişmiş görüntü ön işleme.
        WhatsApp JPEG gibi düşük kaliteli görüntüler için kritik.
        """
        try:
            from PIL import ImageEnhance

            img = pil_image.convert("RGB")
            w, h = img.size

            # 1) Minimum 2400px genişliğine kadar LANCZOS ile büyüt
            if w < 2400:
                scale = max(2, min(4, 2400 // max(w, 1)))
                img = img.resize((w * scale, h * scale), Image.LANCZOS)
                w, h = img.size

            # 2) Grayscale'e çevir
            gray = img.convert("L")

            # 3) Kontrast artır
            gray = ImageEnhance.Contrast(gray).enhance(2.5)

            # 4) Keskinleştir (2 tur — bulanık JPEG için)
            gray = gray.filter(ImageFilter.SHARPEN)
            gray = gray.filter(ImageFilter.SHARPEN)

            # 5) Hafif medyan blur ile JPEG gürültüsünü gider
            gray = gray.filter(ImageFilter.MedianFilter(size=3))

            # 6) Autocontrast — arka plan ile metin arası zıtlık maksimize et
            gray = ImageOps.autocontrast(gray, cutoff=3)

            # 7) Adaptif eşikleme (Sauvola benzeri basit yaklaşım):
            #    Ortalama parlaklığın altında kalan pikselleri siyah yap
            #    Bu JPEG sıkıştırma artefaktlarını azaltır
            try:
                import statistics
                pix_vals = list(gray.getdata())
                median_bright = statistics.median(pix_vals[:min(5000, len(pix_vals))])
                # Eşik: medyan - 20 (metin genellikle çok daha koyu)
                threshold = max(100, int(median_bright) - 20)
                gray = gray.point(lambda p: 255 if p > threshold else p)
            except Exception:
                pass

            return gray.convert("RGB")
        except Exception:
            return pil_image.convert("RGB")

    # ── Ana OCR metni çıkarma ──────────────────────────────────────────────
    @classmethod
    def _ocr_image_to_text(cls, pil_image):
        from ._sip_lazy_imports import get_ImageOps, get_pytesseract, _get_easyocr_reader
        ImageOps = get_ImageOps()
        pytesseract = get_pytesseract()
        """
        Görseli metne çevirir.
        Öncelik: EasyOCR → subprocess (.venv_active) → Tesseract → boş string
        """
        enhanced = cls._enhance_image_for_ocr(pil_image)

        # --- PaddleOCR (optional) ---
        try:
            from paddleocr import PaddleOCR
            import numpy as np

            if not hasattr(cls, "_paddleocr_reader"):
                try:
                    cls._paddleocr_reader = PaddleOCR(
                        use_angle_cls=True,
                        lang="tr",
                        show_log=False,
                    )
                except TypeError:
                    cls._paddleocr_reader = PaddleOCR(
                        lang="tr",
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False,
                    )
            try:
                result = cls._paddleocr_reader.ocr(np.array(enhanced), cls=True)
            except TypeError:
                result = cls._paddleocr_reader.ocr(np.array(enhanced))
            items = []

            def _add_boxed_text(text, bbox=None):
                if not text:
                    return
                try:
                    pts = bbox.tolist() if hasattr(bbox, "tolist") else bbox
                    ys = [float(pt[1]) for pt in pts]
                    xs = [float(pt[0]) for pt in pts]
                    items.append((sum(ys) / max(len(ys), 1), min(xs), str(text)))
                except Exception:
                    items.append((len(items) * 20.0, 0.0, str(text)))

            def _collect(node):
                if not node:
                    return
                if isinstance(node, dict):
                    texts = node.get("rec_texts") or node.get("texts") or []
                    boxes = (
                        node.get("rec_polys")
                        or node.get("rec_boxes")
                        or node.get("dt_polys")
                        or []
                    )
                    for idx, text in enumerate(texts):
                        bbox = boxes[idx] if idx < len(boxes) else None
                        _add_boxed_text(text, bbox)
                    return
                if isinstance(node, (list, tuple)):
                    if len(node) >= 2 and isinstance(node[1], (list, tuple)):
                        bbox, payload = node[0], node[1]
                        text = payload[0] if payload else ""
                        _add_boxed_text(text, bbox)
                        return
                    for child in node:
                        _collect(child)

            _collect(result)
            if items:
                items.sort(key=lambda x: (x[0], x[1]))
                lines = []
                cur_y = None
                cur_items = []
                for y_mid, x_left, text in items:
                    if cur_y is None or abs(y_mid - cur_y) <= 12:
                        cur_items.append((x_left, text))
                        cur_y = y_mid if cur_y is None else (cur_y + y_mid) / 2
                    else:
                        lines.append(" ".join(t for _, t in sorted(cur_items)))
                        cur_items = [(x_left, text)]
                        cur_y = y_mid
                if cur_items:
                    lines.append(" ".join(t for _, t in sorted(cur_items)))
                return "\n".join(lines)
        except Exception:
            pass

        # --- EasyOCR (tercihli) ---
        reader = _get_easyocr_reader()
        if reader is not None:
            try:
                import numpy as np
                img_array = np.array(enhanced)
                results = reader.readtext(
                    img_array,
                    detail=1,
                    paragraph=False,
                    text_threshold=0.4,    # 0.5'ten düşürüldü: daha fazla metin yakala
                    low_text=0.25,         # 0.3'ten düşürüldü
                    width_ths=0.9,
                    mag_ratio=2.0,         # 1.5'ten artırıldı: küçük yazı için
                )
                if results:
                    items = []
                    for (bbox, text, _conf) in results:
                        ys = [pt[1] for pt in bbox]
                        y_mid = sum(ys) / len(ys)
                        x_left = min(pt[0] for pt in bbox)
                        items.append((y_mid, x_left, str(text)))
                    if not items:
                        return ""
                    heights = [
                        max(pt[1] for pt in bbox) - min(pt[1] for pt in bbox)
                        for (bbox, _t, _c) in results
                    ]
                    med_h = sorted(heights)[len(heights) // 2] if heights else 20
                    tol = max(med_h * 0.55, 8)
                    items.sort(key=lambda x: (x[0], x[1]))
                    lines = []
                    cur_y = None
                    cur_items = []
                    for (y_mid, x_left, text) in items:
                        if cur_y is None or abs(y_mid - cur_y) <= tol:
                            cur_items.append((x_left, text))
                            cur_y = (cur_y + y_mid) / 2 if cur_y is not None else y_mid
                        else:
                            cur_items.sort(key=lambda t: t[0])
                            lines.append(" ".join(t for _, t in cur_items))
                            cur_items = [(x_left, text)]
                            cur_y = y_mid
                    if cur_items:
                        cur_items.sort(key=lambda t: t[0])
                        lines.append(" ".join(t for _, t in cur_items))
                    return "\n".join(lines)
            except Exception:
                pass
            # Fallback: paragraph=True
            try:
                import numpy as np
                img_array = np.array(enhanced)
                results = reader.readtext(img_array, detail=0, paragraph=True)
                return "\n".join(str(r) for r in results)
            except Exception:
                pass

        # --- EasyOCR subprocess fallback (.venv_active) ---
        try:
            import subprocess
            import tempfile
            configured_python = os.environ.get("AYEC_OCR_PYTHON", "")
            candidates = [Path(configured_python)] if configured_python else []
            helper = Path(__file__).parent / "_ocr_subprocess_helper.py"
            venv_py = next((p for p in candidates if p.exists()), None)
            if venv_py and helper.exists():
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                    tmp_path = tf.name
                enhanced.save(tmp_path, format="PNG")
                try:
                    result = subprocess.run(
                        [str(venv_py), str(helper), tmp_path],
                        capture_output=True,
                        timeout=120,
                    )
                    if result.returncode == 0 and result.stdout:
                        ocr_text = result.stdout.decode("utf-8", errors="replace").strip()
                        if ocr_text:
                            return ocr_text
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
        except Exception:
            pass

        # --- Tesseract fallback ---
        if pytesseract and cls._configure_tesseract():
            try:
                gray_t = ImageOps.grayscale(enhanced)
                best_text = ""
                for psm in (6, 4, 3):
                    try:
                        txt = pytesseract.image_to_string(
                            gray_t,
                            lang="tur+eng",
                            config=f"--psm {psm} -c preserve_interword_spaces=1",
                        )
                        if len(txt) > len(best_text):
                            best_text = txt
                    except Exception:
                        pass
                if best_text:
                    return best_text
            except Exception:
                pass

        return ""

    # ── Tesseract veri satırları ───────────────────────────────────────────
    @classmethod
    def _extract_tesseract_data_lines(cls, image, lang="tur+eng", config="--psm 6"):
        from ._sip_lazy_imports import get_pytesseract
        pytesseract = get_pytesseract()
        if not pytesseract:
            return ""
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=f"{config} -c preserve_interword_spaces=1",
            output_type=pytesseract.Output.DICT,
        )
        buckets = {}
        count = len(data.get("text") or [])
        for i in range(count):
            text = str((data.get("text") or [""])[i] or "").strip()
            if not text:
                continue
            conf_raw = str((data.get("conf") or [""])[i] or "").strip()
            try:
                conf = float(conf_raw)
            except Exception:
                conf = -1.0
            if conf >= 0 and conf < 20:
                continue
            key = (
                (data.get("block_num") or [0])[i],
                (data.get("par_num") or [0])[i],
                (data.get("line_num") or [0])[i],
            )
            left = int((data.get("left") or [0])[i] or 0)
            buckets.setdefault(key, []).append((left, text))
        lines = []
        for _, words in sorted(buckets.items()):
            ordered = [word for _, word in sorted(words, key=lambda item: item[0])]
            line = cls._cleanup_ocr_line(" ".join(ordered))
            if line:
                lines.append(line)
        return "\n".join(lines)
