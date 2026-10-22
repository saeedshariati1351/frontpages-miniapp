#!/usr/bin/env python3
"""Download today's front-page images from frontpages.com.

Usage: python3 scripts/fetch_covers.py [YYYY-MM-DD]
Writes covers/<date>/<slug>.jpg (full) and <slug>-t.jpg (thumbnail),
and data/<date>.covers.json listing which papers have a cover for that date.
"""
import io, json, os, re, sys, datetime, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (FrontPagesMiniApp)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    ymd = date.replace("-", "/")
    groups = json.load(open(os.path.join(ROOT, "scripts", "papers.json"), encoding="utf-8"))
    outdir = os.path.join(ROOT, "covers", date)
    os.makedirs(outdir, exist_ok=True)
    found = {}
    for g in groups:
        for p in g["papers"]:
            slug = p["slug"]
            try:
                html = get(f"https://www.frontpages.com/{slug}/").decode("utf-8", "ignore")
                m = re.search(r'og:image" content="https://www\.frontpages\.com/g/(\d{4}/\d{2}/\d{2})/([^"/]+)\.webp\.jpg"', html)
                if not m:
                    print("no image:", slug); continue
                imgdate, name = m.group(1), m.group(2)
                if imgdate != ymd:
                    print(f"stale ({imgdate}):", slug); continue
                # the public preview image (top of the front page), as used on frontpages.com listings
                url = f"https://www.frontpages.com/t/{imgdate}/{name}@2x.webp"
                im = Image.open(io.BytesIO(get(url))).convert("RGB")
                im.save(os.path.join(outdir, f"{slug}.jpg"), quality=82, optimize=True)
                found[slug] = {"w": im.width, "h": im.height,
                               "source": f"https://www.frontpages.com/{slug}/"}
                print("ok:", slug, im.size)
            except Exception as e:
                print("error:", slug, e)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump(found, open(os.path.join(ROOT, "data", f"{date}.covers.json"), "w"), indent=1)
    print(f"{len(found)} covers for {date}")


if __name__ == "__main__":
    main()
