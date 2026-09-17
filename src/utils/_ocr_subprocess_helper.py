# -*- coding: utf-8 -*-
"""
OCR Subprocess Helper
Kullanım: python _ocr_subprocess_helper.py <image_path>
Çıktı: stdout'a OCR metni (UTF-8)
"""
import sys
import os

# Windows'ta stdout UTF-8 olarak zorla
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        sys.exit(1)

    try:
        import easyocr
        from PIL import Image, ImageOps, ImageFilter, ImageEnhance
        import numpy as np

        reader = easyocr.Reader(["tr", "en"], gpu=False, verbose=False)
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        # Görüntü ön işleme: büyüt + kontrast + keskinleştir
        w, h = img.size
        if w < 2400:
            scale = max(2, min(4, 2400 // max(w, 1)))
            img = img.resize((w * scale, h * scale), Image.LANCZOS)
        img_rgb = img.convert("RGB")
        # Keskinleştir
        img_rgb = img_rgb.filter(ImageFilter.SHARPEN)
        img_rgb = img_rgb.filter(ImageFilter.SHARPEN)
        # Kontrast artır
        img_rgb = ImageEnhance.Contrast(img_rgb).enhance(2.0)

        img_array = np.array(img_rgb)

        results = reader.readtext(
            img_array,
            detail=1,
            paragraph=False,
            text_threshold=0.5,
            low_text=0.3,
            width_ths=0.9,
            mag_ratio=1.5,
        )
        if not results:
            sys.exit(2)

        items = []
        for (bbox, text, _conf) in results:
            ys = [pt[1] for pt in bbox]
            y_mid = sum(ys) / len(ys)
            x_left = min(pt[0] for pt in bbox)
            items.append((y_mid, x_left, str(text)))

        heights = [max(pt[1] for pt in bbox) - min(pt[1] for pt in bbox)
                   for (bbox, _t, _c) in results]
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

        print("\n".join(lines))
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
