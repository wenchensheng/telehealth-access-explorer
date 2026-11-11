"""Draw the app icons (PNG) with Pillow: a phone-screen glyph with a pulse line on teal."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "docs" / "icons"
BG_TOP, BG_BOTTOM = (11, 60, 73), (18, 128, 116)


def draw(size: int, maskable: bool = False, rounded: bool = True) -> Image.Image:
    s = 4 * size  # supersample, then downscale for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.new("RGB", (1, s))
    for y in range(s):
        f = y / (s - 1)
        grad.putpixel((0, y), tuple(int(a + (b - a) * f) for a, b in zip(BG_TOP, BG_BOTTOM)))
    grad = grad.resize((s, s))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22) if rounded else 0, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    pad = 0.27 if maskable else 0.2  # maskable icons keep content inside the 80% safe zone
    x0, y0, x1, y1 = s * (pad + 0.12), s * pad, s * (1 - pad - 0.12), s * (1 - pad)
    w = int(s * 0.035)
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(s * 0.07), outline="white", width=w)
    d.line([((x0 + x1) / 2 - s * 0.05, y1 - s * 0.06), ((x0 + x1) / 2 + s * 0.05, y1 - s * 0.06)],
           fill="white", width=int(w * 0.8))
    cy = (y0 + y1) / 2 - s * 0.03
    pts = [(x0 - s * 0.06, cy), (x0 + s * 0.08, cy), (x0 + s * 0.13, cy - s * 0.12), (x0 + s * 0.2, cy + s * 0.12),
           (x0 + s * 0.26, cy - s * 0.05), (x0 + s * 0.3, cy), (x1 + s * 0.06, cy)]
    d.line(pts, fill=(255, 214, 102), width=int(w * 1.1), joint="curve")
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192).save(OUT / "icon-192.png")
    draw(512).save(OUT / "icon-512.png")
    draw(512, maskable=True, rounded=False).save(OUT / "icon-maskable-512.png")
    draw(180, rounded=False).convert("RGB").save(OUT / "apple-touch-icon.png")  # iOS rounds corners itself
    draw(32).save(OUT / "favicon-32.png")
    print(f"[icons] wrote 5 icons to {OUT}")


if __name__ == "__main__":
    main()
