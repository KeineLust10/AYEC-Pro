import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
NATIVE_IMAGE = ROOT / "artifacts/desktop_shell_reference/20261018_221646_306206/koyu_mavi_route_30_1280x1024.png"
WEB_IMAGE = ROOT / "output/playwright/appointment-calendar-matched-20261021-followup/appointments-week-matched-1040x1024.png"
RESULT_PATH = ROOT / "output/playwright/appointment-calendar-matched-20261021-followup/paired-visual-metrics.json"
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-image", type=Path, default=NATIVE_IMAGE)
    parser.add_argument("--web-image", type=Path, default=WEB_IMAGE)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    native_path = args.native_image if args.native_image.is_absolute() else ROOT / args.native_image
    web_path = args.web_image if args.web_image.is_absolute() else ROOT / args.web_image
    result_path = args.output if args.output.is_absolute() else ROOT / args.output
    native_image = Image.open(native_path).convert("RGB")
    web_image = Image.open(web_path).convert("RGB")
    native = np.asarray(native_image.crop(NATIVE_CROP))
    web = np.asarray(web_image.crop(WEB_CROP))
    if native.shape != web.shape or native.shape != (764, 1020, 3):
        raise ValueError(f"Unexpected paired crop dimensions: native={native.shape}, web={web.shape}")
    result = {
        "native_image": str(native_path.relative_to(ROOT)),
        "web_image": str(web_path.relative_to(ROOT)),
        "native_crop": list(NATIVE_CROP),
        "web_crop": list(WEB_CROP),
        "paired": measure(native, web),
        "bands": {
            name: measure(native[y0:y1], web[y0:y1])
            for name, y0, y1 in BANDS
        },
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
