#!/usr/bin/env python3
"""Keep the permanent archive small enough for GitHub Pages (1 GB site limit).

Covers newer than KEEP_DAYS stay at full size (600x800). Older covers are
shrunk once to 330x440 at lower quality (~25 KB each instead of ~130 KB).
Nothing is deleted: every day stays in the archive.

Usage: python3 scripts/archive_shrink.py [TODAY YYYY-MM-DD]
"""
import os, sys, datetime
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP_DAYS = 30
SMALL = (330, 440)


def main():
    today = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    cdir = os.path.join(ROOT, "covers")
    shrunk = 0
    for day in sorted(os.listdir(cdir)):
        try:
            d = datetime.date.fromisoformat(day)
        except ValueError:
            continue
        if (today - d).days <= KEEP_DAYS:
            continue
        for f in os.listdir(os.path.join(cdir, day)):
            if not f.endswith(".jpg"):
                continue
            path = os.path.join(cdir, day, f)
            im = Image.open(path)
            if im.width <= SMALL[0]:
                continue
            im = im.convert("RGB")
            im.thumbnail(SMALL)
            im.save(path, quality=70, optimize=True)
            shrunk += 1
    print(f"shrunk {shrunk} archived covers")


if __name__ == "__main__":
    main()
