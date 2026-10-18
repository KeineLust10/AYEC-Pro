import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
NATIVE_IMAGE = ROOT / "output/field_map_visual_check/20261013_094637/koyu_mavi_appointments.png"
WEB_IMAGE = ROOT / "output/playwright/appointment-calendar-matched-20261017/appointments-week-matched-1040x1024.png"
RESULT_PATH = ROOT / "output/playwright/appointment-calendar-matched-20261017/paired-visual-metrics.json"
NATIVE_CROP = (260, 70, 1280, 834)
WEB_CROP = (0, 0, 1020, 764)
BANDS = (("toolbar", 0, 91), ("metrics", 91, 154), ("calendar", 154, 724), ("bottom", 724, 764))


def measure(native, web):
    delta = np.abs(native.astype(np.int16) - web.astype(np.int16))
    return {
        "mae": round(float(delta.mean()), 3),
        "exact_pixel_share": round(float((delta.max(axis=2) == 0).mean()), 4),
        "p95_channel_delta": int(np.percentile(delta, 95)),
    }


def main():
    native_image = Image.open(NATIVE_IMAGE).convert("RGB")
    web_image = Image.open(WEB_IMAGE).convert("RGB")
    native = np.asarray(native_image.crop(NATIVE_CROP))
    web = np.asarray(web_image.crop(WEB_CROP))
    if native.shape != web.shape or native.shape != (764, 1020, 3):
        raise ValueError(f"Unexpected paired crop dimensions: native={native.shape}, web={web.shape}")
    result = {
        "native_image": str(NATIVE_IMAGE.relative_to(ROOT)),
        "web_image": str(WEB_IMAGE.relative_to(ROOT)),
        "native_crop": list(NATIVE_CROP),
        "web_crop": list(WEB_CROP),
        "paired": measure(native, web),
        "bands": {
            name: measure(native[y0:y1], web[y0:y1])
            for name, y0, y1 in BANDS
        },
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
