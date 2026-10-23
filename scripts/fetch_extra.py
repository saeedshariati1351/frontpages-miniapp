#!/usr/bin/env python3
"""Front pages that frontpages.com does not carry (papers with "via" in papers.json).

Runs in GitHub Actions (.github/workflows/extra-covers.yml), because the
newspapers' own sites are not reachable from every environment.

Usage: python3 scripts/fetch_extra.py YYYY-MM-DD [YYYY-MM-DD ...]
Adds covers/<date>/<slug>.jpg and merges the entry into data/<date>.covers.json.
Existing covers are never replaced or removed.
"""
import datetime, io, json, os, re, sys, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
W, H = 900, 1200  # top of the page, 3:4 like the other covers (but sharper for Arabic text)


def get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def top_crop(im):
    im = im.convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    return im.crop((0, 0, W, min(H, im.height)))


def pdf_first_page(data):
    import fitz  # pymupdf
    doc = fitz.open(stream=data, filetype="pdf")
    pix = doc[0].get_pixmap(dpi=110)
    return Image.open(io.BytesIO(pix.tobytes("png"))).copy()


# ---------- Asharq Al-Awsat (aawsat.com FlippingBook issues) ----------
AAWSAT_BASE = (datetime.date(2026, 10, 22), 17495)  # issue 17495 = Thursday 22 Oct 2026


def aawsat_issue_ok(n, d):
    try:
        html = get(f"https://aawsat.com/files/pdf/issue{n}/index.html").decode("utf-8", "ignore")
    except Exception as e:
        print("  issue", n, "->", e)
        return False
    marks = [d.strftime("%Y/%m/%d"), f"{d.day} {d.strftime('%B')} {d.year}", d.strftime("%Y-%m-%d")]
    ok = any(m in html for m in marks)
    print("  issue", n, "date match" if ok else "no date match")
    return ok


def aawsat(d):
    n0 = AAWSAT_BASE[1] + (d - AAWSAT_BASE[0]).days
    issue = next((n for n in (n0, n0 - 1, n0 + 1, n0 - 2, n0 + 2) if aawsat_issue_ok(n, d)), None)
    if issue is None:
        return None
    base = f"https://aawsat.com/files/pdf/issue{issue}/files/assets"
    cands = [f"{base}/common/page-html5-substrates/page0001_{k}.jpg" for k in (5, 4, 3, 2, 1)]
    cands += [f"{base}/common/page-html5-substrates/page0001_{k}.webp" for k in (5, 4, 3, 2, 1)]
    cands += [f"{base}/common/page-substrates/page0001.jpg", f"{base}/flash/pages/page0001_l.jpg",
              f"{base}/flash/pages/page0001.jpg", f"{base}/mobile/pages/page0001_l.jpg"]
    for u in cands:
        try:
            im = Image.open(io.BytesIO(get(u)))
            print("  ok", u, im.size)
            if im.width >= 500:
                return im, f"https://aawsat.com/files/pdf/issue{issue}/index.html"
        except Exception as e:
            print("  miss", u, str(e)[:60])
    for u in (f"{base}/common/downloads/publication.pdf", f"{base}/common/downloads/Asharq.pdf"):
        try:
            im = pdf_first_page(get(u, 90))
            print("  ok pdf", u, im.size)
            return im, f"https://aawsat.com/files/pdf/issue{issue}/index.html"
        except Exception as e:
            print("  miss", u, str(e)[:60])
    # last resort: cover thumbnail on the home page (only valid for the latest issue)
    try:
        html = get("https://aawsat.com/").decode("utf-8", "ignore")
        m = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="صورة الغلاف"', html) or \
            re.search(r'<img[^>]+alt="صورة الغلاف"[^>]*src="([^"]+)"', html)
        if m and f"issue{issue}" in html:
            u = m.group(1)
            u = u if u.startswith("http") else "https://aawsat.com" + u
            for v in (re.sub(r"/styles/[^/]+/public/", "/", u).replace(".webp", ""), u):
                try:
                    im = Image.open(io.BytesIO(get(v)))
                    print("  ok home cover", v, im.size)
                    return im, f"https://aawsat.com/files/pdf/issue{issue}/index.html"
                except Exception as e:
                    print("  miss", v, str(e)[:60])
    except Exception as e:
        print("  home:", e)
    return None


SOURCES = {"aawsat": aawsat}


def main():
    papers = [p for g in json.load(open(os.path.join(ROOT, "scripts", "papers.json"), encoding="utf-8"))
              for p in g["papers"] if p.get("via")]
    for date in sys.argv[1:]:
        d = datetime.date.fromisoformat(date)
        cpath = os.path.join(ROOT, "data", f"{date}.covers.json")
        found = json.load(open(cpath)) if os.path.exists(cpath) else {}
        outdir = os.path.join(ROOT, "covers", date)
        os.makedirs(outdir, exist_ok=True)
        for p in papers:
            slug = p["slug"]
            if slug in found:
                print(date, "have:", slug); continue
            print(date, "trying:", slug)
            try:
                r = SOURCES[p["via"]](d)
            except Exception as e:
                print("  error:", e); r = None
            if not r:
                print(date, "not found:", slug); continue
            im, source = r
            im = top_crop(im)
            im.save(os.path.join(outdir, f"{slug}.jpg"), quality=82, optimize=True)
            found[slug] = {"w": im.width, "h": im.height, "source": source}
            print(date, "ok:", slug, im.size)
        json.dump(found, open(cpath, "w"), indent=1)


if __name__ == "__main__":
    main()
