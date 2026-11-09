#!/usr/bin/env python3
"""Collage of a few covers for the nightly Telegram post.

Usage: python3 scripts/post_image.py DATE
Reads data/posts/DATE.json ("covers": [slug, ...], else the slugs of "items")
and writes posts/DATE.jpg (1200 px wide, up to 6 covers in rows of 3 on a dark band).
"""
import json, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def main(date):
    post = json.loads((ROOT / "data" / "posts" / f"{date}.json").read_text())
    slugs = post.get("covers") or []
    if not slugs:
        seen = []
        for it in post["items"]:
            if it["slug"] not in seen:
                seen.append(it["slug"])
        slugs = seen
    files = [ROOT / "covers" / date / f"{s}.jpg" for s in slugs]
    files = [f for f in files if f.exists()][:6]
    if not files:
        sys.exit("no covers found")
    W, pad = 1200, 14
    n = len(files)
    cols = 3 if n >= 5 else n
    rows = (n + cols - 1) // cols
    cw = (W - pad * (cols + 1)) // cols
    ch = int(cw * 4 / 3)
    img = Image.new("RGB", (W, ch + (ch // 2 + pad) * (rows - 1) + 2 * pad), (24, 28, 36))
    for i, f in enumerate(files):
        c = Image.open(f).convert("RGB")
        # crop to 3:4 from the top (masthead + lead story stay visible)
        r = c.width / c.height
        if r > 0.75:
            nw = int(c.height * 0.75)
            c = c.crop(((c.width - nw) // 2, 0, (c.width - nw) // 2 + nw, c.height))
        else:
            c = c.crop((0, 0, c.width, int(c.width / 0.75)))
        c = c.resize((cw, ch), Image.LANCZOS)
        r_, k = divmod(i, cols)
        if r_ > 0:
            c = c.crop((0, 0, cw, ch // 2))
        y = pad if r_ == 0 else pad + ch + pad + (r_ - 1) * (ch // 2 + pad)
        img.paste(c, (pad + k * (cw + pad), y))
    out = ROOT / "posts" / f"{date}.jpg"
    out.parent.mkdir(exist_ok=True)
    img.save(out, quality=85, optimize=True)
    print("wrote", out.relative_to(ROOT), img.size)


if __name__ == "__main__":
    main(sys.argv[1])
