from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "site-media"
LOGO = ROOT / "assets" / "ayec_logo.png"
SIZE = (960, 540)
BG = (5, 17, 31)
ACCENT = (45, 109, 246)
MINT = (42, 211, 194)


def cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    ratio = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize(
        (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def compose(path: Path, title: str, index: int, total: int) -> Image.Image:
    source = cover(Image.open(path), (900, 480))
    canvas = Image.new("RGB", SIZE, BG)
    canvas.paste(source, (30, 42))

    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((22, 34, 938, 530), radius=22, outline=ACCENT + (150,), width=2)
    draw.rounded_rectangle((36, 48, 270, 92), radius=14, fill=(5, 20, 36, 225))

    logo = Image.open(LOGO).convert("RGBA").resize((34, 34), Image.Resampling.LANCZOS)
    overlay.alpha_composite(logo, (43, 53))
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=13)
    draw.text((86, 55), "AYEC PRO", fill=(255, 255, 255, 255), font=font)
    draw.text((86, 75), title, fill=(163, 188, 218, 255), font=small)

    start_x = 830 - total * 18
    for dot in range(total):
        color = MINT + (255,) if dot == index else (104, 129, 158, 210)
        draw.ellipse((start_x + dot * 22, 61, start_x + dot * 22 + 9, 70), fill=color)
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    return canvas


def build_gif(name: str, slides: list[tuple[Path, str]]) -> None:
    cards = [compose(path, title, index, len(slides)) for index, (path, title) in enumerate(slides)]
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index, current in enumerate(cards):
        frames.extend([current] * 2)
        durations.extend([900, 900])
        following = cards[(index + 1) % len(cards)]
        for step in range(1, 7):
            frames.append(Image.blend(current, following, step / 7))
            durations.append(70)
    palette_frames = [frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for frame in frames]
    palette_frames[0].save(
        OUT / name,
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    capture_root = ROOT / "artifacts" / "live-program-screens"
    live = max(path for path in capture_root.iterdir() if path.is_dir())
    build_gif(
        "ayecpro_secure_access.gif",
        [
            (live / "ayec_live_dashboard.png", "SERVIS YONETIMI"),
            (live / "ayec_live_customers.png", "MUSTERI YONETIMI"),
        ],
    )
    build_gif(
        "ayecpro_license_center.gif",
        [
            (live / "ayec_live_stock.png", "STOK YONETIMI"),
            (live / "ayec_live_finance.png", "FINANS YONETIMI"),
        ],
    )
    build_gif(
        "ayecpro_smart_workflow.gif",
        [
            (live / "ayec_live_appointments.png", "RANDEVU PLANLAMA"),
            (live / "ayec_live_service_board.png", "SERVIS PANOSU"),
            (live / "ayec_live_dashboard.png", "CANLI OPERASYON"),
        ],
    )


if __name__ == "__main__":
    main()
