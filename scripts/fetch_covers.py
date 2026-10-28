#!/usr/bin/env python3
"""Download today's front-page images from frontpages.com.

Usage: python3 scripts/fetch_covers.py [YYYY-MM-DD]
Writes covers/<date>/<slug>.jpg (full) and <slug>-t.jpg (thumbnail),
and data/<date>.covers.json listing which papers have a cover for that date.

Safe to run several times a day: covers already in data/<date>.covers.json
are kept (never re-downloaded or removed); only missing papers are tried.
Papers with a "via" field in papers.json come from another source
(scripts/fetch_extra.py) and are skipped here.
"""
import io, json, os, re, sys, datetime, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (FrontPagesMiniApp)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _d(date):
    return datetime.date.fromisoformat(date)


def is_saturday(date):
    return _d(date).weekday() == 5


def is_sunday(date):
    return _d(date).weekday() == 6


def next_day(date):
    return (_d(date) + datetime.timedelta(days=1)).isoformat()


def prev_day_covers(date):
    prev = (_d(date) - datetime.timedelta(days=1)).isoformat()
    path = os.path.join(ROOT, "data", f"{prev}.covers.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def fetch_yesterday(slug, date, outdir, found):
    """Save the previous edition of a paper (frontpages.com's "yesterday's edition"
    button) when it carries `date`. Returns True if a cover was saved."""
    import base64
    req = urllib.request.Request(f"https://www.frontpages.com/{slug}/", data=b"y=1", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "ignore")
    ed = re.search(r'class="span-date[^"]*" datetime="(\d{4}-\d{2}-\d{2})"', html)
    m = re.search(r"getElementById\([^)]*\);var u=atob\('([A-Za-z0-9+/=]+)'\)", html)
    if not ed or ed.group(1) != date or not m:
        print(f"yesterday's edition not {date}:", slug)
        return False
    path = base64.b64decode(m.group(1)).decode()
    if not re.fullmatch(r"/g/\d{4}/\d{2}/\d{2}/[\w.-]+\.webp", path):
        print("unexpected yesterday image path:", slug, path)
        return False
    im = Image.open(io.BytesIO(get("https://www.frontpages.com" + path))).convert("RGB")
    if im.width > 900:
        im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
    im.save(os.path.join(outdir, f"{slug}.jpg"), quality=82, optimize=True)
    found[slug] = {"w": im.width, "h": im.height, "source": f"https://www.frontpages.com/{slug}/"}
    print("ok (yesterday's edition):", slug, im.size)
    return True


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    ymd = date.replace("-", "/")
    groups = json.load(open(os.path.join(ROOT, "scripts", "papers.json"), encoding="utf-8"))
    outdir = os.path.join(ROOT, "covers", date)
    os.makedirs(outdir, exist_ok=True)
    cpath = os.path.join(ROOT, "data", f"{date}.covers.json")
    found = json.load(open(cpath)) if os.path.exists(cpath) else {}
    added = 0
    for g in groups:
        for p in g["papers"]:
            slug = p["slug"]
            if p.get("via"):
                continue
            if slug in found and os.path.exists(os.path.join(outdir, f"{slug}.jpg")):
                print("have:", slug); continue
            try:
                html = get(f"https://www.frontpages.com/{slug}/").decode("utf-8", "ignore")
                m = re.search(r'og:image" content="https://www\.frontpages\.com/g/(\d{4}/\d{2}/\d{2})/([^"/]+)\.webp\.jpg"', html)
                if not m:
                    print("no image:", slug); continue
                imgdate, name = m.group(1), m.group(2)
                # the edition date shown on the page; evening uploads (e.g. Le Monde,
                # Arab News) carry the next day's date while the image path keeps the upload day
                ed = re.search(r'class="span-date[^"]*" datetime="(\d{4}-\d{2}-\d{2})"', html)
                edition = ed.group(1) if ed else imgdate.replace("/", "-")
                # Papers flagged "weekend" in papers.json print one combined Saturday/Sunday
                # edition, which frontpages.com lists under the Sunday date. File it under
                # Saturday, and don't file the same edition again under Sunday.
                if p.get("weekend") and is_saturday(date) and edition == next_day(date):
                    print(f"weekend edition ({edition}) filed under Saturday:", slug)
                elif edition != date:
                    # Papers flagged "yesterday" in papers.json: if today's page already shows
                    # the next edition, take the wanted date from frontpages.com's
                    # "yesterday's edition" view (one day back only).
                    if p.get("yesterday") and edition == next_day(date) and fetch_yesterday(slug, date, outdir, found):
                        added += 1
                    else:
                        print(f"stale ({edition}):", slug)
                    continue
                elif p.get("weekend") and is_sunday(date) and imgdate.replace("/", "-") < date \
                        and slug in prev_day_covers(date):
                    print("weekend edition already filed under Saturday:", slug); continue
                # the public preview image (top of the front page), as used on frontpages.com listings
                url = f"https://www.frontpages.com/t/{imgdate}/{name}@2x.webp"
                im = Image.open(io.BytesIO(get(url))).convert("RGB")
                im.save(os.path.join(outdir, f"{slug}.jpg"), quality=82, optimize=True)
                found[slug] = {"w": im.width, "h": im.height,
                               "source": f"https://www.frontpages.com/{slug}/"}
                added += 1
                print("ok:", slug, im.size)
            except Exception as e:
                print("error:", slug, e)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump(found, open(cpath, "w"), indent=1)
    print(f"{len(found)} covers for {date} ({added} new)")


if __name__ == "__main__":
    main()
