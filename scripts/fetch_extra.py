#!/usr/bin/env python3
"""Front pages that frontpages.com does not carry (papers with "via" in papers.json).

Runs in GitHub Actions (.github/workflows/extra-covers.yml), because the
newspapers' own sites are not reachable from every environment.

Usage: python3 scripts/fetch_extra.py YYYY-MM-DD [YYYY-MM-DD ...]
Adds covers/<date>/<slug>.jpg and merges the entry into data/<date>.covers.json.
Existing covers are never replaced or removed.
"""
import datetime, io, json, os, re, shutil, subprocess, sys, tempfile, urllib.request
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


def inline_svg(svg_url):
    """SVG text with every url(...) (web fonts, images) embedded as data: URIs."""
    import base64, urllib.parse
    svg = get(svg_url).decode("utf-8", "ignore")
    def emb(m):
        ref = m.group(2)
        if ref.startswith(("data:", "#")):
            return m.group(0)
        u = urllib.parse.urljoin(svg_url, ref)
        try:
            data = get(u)
        except Exception as e:
            print("   font/img miss", u, str(e)[:50]); return m.group(0)
        ext = u.split("?")[0].rsplit(".", 1)[-1].lower()
        mime = {"woff": "font/woff", "woff2": "font/woff2", "ttf": "font/ttf", "otf": "font/otf",
                "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        return f"url({m.group(1)}data:{mime};base64,{base64.b64encode(data).decode()}{m.group(1)})"
    svg = re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", emb, svg)
    svg = re.sub(r'(xlink:href|href)="(?!data:|#|https?:)([^"]+)"',
                 lambda m: f'{m.group(1)}="{urllib.parse.urljoin(svg_url, m.group(2))}"', svg)
    return re.sub(r"<\?xml[^>]*\?>", "", svg)


def chrome_render(sub_url, svg_url, w, h):
    """Draw the page background with its SVG text layer in headless Chrome (web fonts included)."""
    exe = next((shutil.which(x) for x in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if shutil.which(x)), None)
    if not exe:
        raise RuntimeError("no chrome")
    svg = inline_svg(svg_url).lstrip("\ufeff")
    print("   svg bytes", len(svg), "fonts", svg.count("font/"))
    if os.environ.get("DEBUG_SVG"):
        print("   SVG HEAD:", re.sub(r"base64,[A-Za-z0-9+/=]{200,}", "base64,...", svg)[:600])
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "layer.svg"), "w", encoding="utf-8").write(svg)
        page = os.path.join(d, "p.html")
        open(page, "w").write(f'''<!doctype html><html><body style="margin:0">
<div style="position:relative;width:{w}px;height:{h}px;overflow:hidden">
<img src="{sub_url}" style="position:absolute;left:0;top:0;width:{w}px;height:{h}px">
<img src="layer.svg" style="position:absolute;left:0;top:0;width:{w}px;height:{h}px">
</div></body></html>''')
        out = os.path.join(d, "o.png")
        r = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            "--virtual-time-budget=20000", f"--window-size={w},{h}", f"--screenshot={out}",
                            "file://" + page], timeout=180, capture_output=True, text=True)
        if not os.path.exists(out):
            raise RuntimeError("chrome: " + r.stderr[-300:])
        return Image.open(out).convert("RGB").copy()


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
    root = f"https://aawsat.com/files/pdf/issue{issue}"
    src = f"{root}/index.html"
    base = f"{root}/files/assets"
    # 1) the full PDF of the issue (page 1 with its text)
    for u in (f"{base}/common/downloads/publication.pdf", f"{base}/common/downloads/Asharq.pdf",
              f"{root}/files/assets/common/downloads/publication.pdf?uni=1"):
        try:
            im = pdf_first_page(get(u, 120))
            print("  ok pdf", u, im.size)
            return im, src
        except Exception as e:
            print("  miss", u, str(e)[:80])
    # 2) FlippingBook page = background image + vector text layer (SVG)
    sub = None
    for k in (5, 4, 3):
        try:
            sub = Image.open(io.BytesIO(get(f"{base}/common/page-html5-substrates/page0001_{k}.jpg"))).convert("RGB")
            print("  substrate", k, sub.size); break
        except Exception as e:
            print("  miss substrate", k, str(e)[:60])
    if sub is not None:
        sub_url = f"{base}/common/page-html5-substrates/page0001_{k}.jpg"
        for u in (f"{base}/common/page-vectorlayers/0001.svg", f"{base}/common/page-vectorlayers/page0001.svg"):
            try:
                get(u)
            except Exception as e:
                print("  miss", u, str(e)[:60]); continue
            try:
                out = chrome_render(sub_url, u, sub.width, sub.height)
                print("  ok chrome render", u, out.size)
                return out, src
            except Exception as e:
                print("  chrome failed", str(e)[:200])
    # 3) cover image on the home page (rendered page, only for the latest issue)
    try:
        html = get("https://aawsat.com/").decode("utf-8", "ignore")
        m = re.search(r'<img[^>]+alt="صورة الغلاف"[^>]*>', html)
        if m and f"issue{issue}/" in html:
            tag = m.group(0)
            print("  home tag", tag[:300])
            urls = re.findall(r'(?:src|data-src|srcset)="([^" ]+)', tag)
            for u in urls:
                u = u if u.startswith("http") else "https://aawsat.com" + u
                for v in (re.sub(r"/styles/[^/]+/public/", "/", u).replace(".webp", ""), u):
                    try:
                        im = Image.open(io.BytesIO(get(v)))
                        print("  home cover", v, im.size)
                        if im.width >= 300:
                            return im, src
                    except Exception as e:
                        print("  miss", v, str(e)[:60])
    except Exception as e:
        print("  home:", e)
    try:  # debug: what the issue page references
        html = get(src).decode("utf-8", "ignore")
        print("  refs:", sorted(set(re.findall(r'files/assets/[A-Za-z0-9_./-]+', html)))[:40])
    except Exception:
        pass
    return None


# ---------- direct file URLs found beforehand (e.g. Al-Akhbar's daily PDF on media.al-akhbar.com) ----------
GIVEN = {}  # (slug, date) -> url, from --url slug=DATE=URL


def given_url(slug):
    def fetch(d):
        u = GIVEN.get((slug, d.isoformat()))
        if not u:
            print("  no url given"); return None
        data = get(u, 120)
        im = pdf_first_page(data) if data[:4] == b"%PDF" else Image.open(io.BytesIO(data))
        print("  ok", u, im.size)
        return im, u
    return fetch


SOURCES = {"aawsat": aawsat}


def probe(urls):
    """Debug helper: print links/images that look like print editions on the given pages."""
    for u in urls:
        try:
            html = get(u).decode("utf-8", "ignore")
        except Exception as e:
            print("PROBE", u, "->", e); continue
        print("PROBE", u, len(html), "bytes; title:", re.findall(r"<title>(.*?)</title>", html, re.S)[:1])
        refs = re.findall(r'(?:href|src|data-src|content)="([^"]+)"', html)
        hits = [r for r in refs if re.search(r"pdf|issue|edition|newspaper|archive|cover|front|\.jpe?g|page", r, re.I)]
        seen = []
        for r in hits:
            if r not in seen:
                seen.append(r)
        for r in seen[:80]:
            print("   ", r[:200])


def main():
    if sys.argv[1] == "--probe":
        return probe(sys.argv[2:])
    args = sys.argv[1:]
    while "--url" in args:
        i = args.index("--url")
        slug, date, u = args[i + 1].split("=", 2)
        GIVEN[(slug, date)] = u
        del args[i:i + 2]
    papers = [p for g in json.load(open(os.path.join(ROOT, "scripts", "papers.json"), encoding="utf-8"))
              for p in g["papers"] if p.get("via")]
    dates = args or sorted({d for _, d in GIVEN})
    for date in dates:
        d = datetime.date.fromisoformat(date)
        cpath = os.path.join(ROOT, "data", f"{date}.covers.json")
        found = json.load(open(cpath)) if os.path.exists(cpath) else {}
        outdir = os.path.join(ROOT, "covers", date)
        os.makedirs(outdir, exist_ok=True)
        for p in papers:
            slug = p["slug"]
            if slug in found:
                print(date, "have:", slug); continue
            fetcher = given_url(slug) if p["via"] == "url" else SOURCES[p["via"]]
            if p["via"] == "url" and (slug, date) not in GIVEN:
                continue
            print(date, "trying:", slug)
            try:
                r = fetcher(d)
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
