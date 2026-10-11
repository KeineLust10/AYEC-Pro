# -*- coding: utf-8 -*-
"""Download and verify the EasyOCR models used by the web smart importer."""

import argparse
import os
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--module-path", default=str(root / "ocr-models" / "EasyOCR"))
    args = parser.parse_args()
    module_path = Path(args.module_path).expanduser().resolve()
    module_path.mkdir(parents=True, exist_ok=True)
    os.environ["EASYOCR_MODULE_PATH"] = str(module_path)

    from easyocr import Reader
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    reader = Reader(["tr", "en"], gpu=False, verbose=False)
    image = Image.new("RGB", (900, 150), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 35), "AYEC OCR READY", fill="black", font=ImageFont.load_default(size=48))
    recognized = " ".join(reader.readtext(np.asarray(image), detail=0))
    if "AYEC" not in recognized.upper() or "OCR" not in recognized.upper():
        raise RuntimeError("EasyOCR models initialized but failed the sample recognition check.")
    print("EasyOCR models are ready at {}".format(module_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
