#!/usr/bin/env python3
"""Mint LQIP blurDataURL constants for the first-load hero + home tiles.

next/image `placeholder="blur"` needs an explicit `blurDataURL` for images
referenced by string path (not static import). This regenerates the real
low-quality image placeholders straight from the source artwork, so the blur
always matches the actual image.

Run from anywhere (paths are repo-relative to this file):

    python apps/web/scripts/mint-image-lqip.py

Then paste the printed data URLs into:
  - app/page.tsx                  -> HERO_BLUR
  - app/app/(tabs)/today/page.tsx -> TILE_BLUR map

Requires Pillow with WebP support (PIL.features.check("webp")).
"""
import base64
import io
import os

PERSONAS = os.path.join(
    os.path.dirname(__file__), "..", "public", "personas"
)

# Every image painted on first load (the logged-out hero + the four logged-in
# home tiles). Keyed by the public path used in the components.
TARGETS = {
    "/personas/wise-room-hero.webp": "wise-room-hero.webp",
    "/personas/discuss.webp": "discuss.webp",
    "/personas/insights.webp": "insights.webp",
    "/personas/revisit.webp": "revisit.webp",
    "/personas/rituals.webp": "rituals.webp",
}

LQIP_WIDTH = 16  # px wide; height follows the source aspect ratio


def mint(path: str) -> str:
    from PIL import Image

    img = Image.open(path).convert("RGB")
    w, h = img.size
    new_h = max(1, round(LQIP_WIDTH * h / w))
    small = img.resize((LQIP_WIDTH, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, format="WEBP", quality=40, method=6)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    assert len(b64) % 4 == 0, "base64 padding invalid"
    return f"data:image/webp;base64,{b64}"


if __name__ == "__main__":
    for public_path, fname in TARGETS.items():
        data_url = mint(os.path.join(PERSONAS, fname))
        print(f"{public_path}\n  {data_url}\n")
