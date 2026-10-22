#!/usr/bin/env python3
"""Combine papers.json + covers + headlines into data/<date>.json and data/latest.json.

Usage: python3 scripts/build_data.py YYYY-MM-DD

headlines/<date>.json maps slug -> list of [original, persian] or
[original, persian, url]. When no url is given, the headline links to the
first result for that headline on the newspaper's own site.
"""
import json, os, sys, datetime, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


def to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def fa_date(date):
    d = datetime.date.fromisoformat(date)
    jy, jm, jd = to_jalali(d.year, d.month, d.day)
    return f"{WEEKDAYS[d.weekday()]} {jd} {MONTHS[jm - 1]} {jy}".translate(FA_DIGITS)


def article_link(site, headline):
    domain = urllib.parse.urlparse(site).netloc.replace("www.", "")
    # DuckDuckGo's "\" prefix jumps straight to the first result
    return "https://duckduckgo.com/?q=" + urllib.parse.quote(f"\\{headline} site:{domain}")


def main():
    date = sys.argv[1]
    groups = json.load(open(os.path.join(ROOT, "scripts", "papers.json"), encoding="utf-8"))
    covers = json.load(open(os.path.join(ROOT, "data", f"{date}.covers.json"), encoding="utf-8"))
    hpath = os.path.join(ROOT, "headlines", f"{date}.json")
    heads = json.load(open(hpath, encoding="utf-8")) if os.path.exists(hpath) else {}
    out = {"date": date, "date_fa": fa_date(date), "countries": []}
    for g in groups:
        papers = []
        for p in g["papers"]:
            c = covers.get(p["slug"])
            if not c:
                continue
            items = []
            for h in heads.get(p["slug"], []):
                url = h[2] if len(h) > 2 and h[2] else article_link(p["site"], h[0])
                items.append({"o": h[0], "fa": h[1], "url": url, "direct": len(h) > 2 and bool(h[2])})
            papers.append({"slug": p["slug"], "name": p["name"], "fa": p["fa"], "site": p["site"],
                           "img": f"covers/{date}/{p['slug']}.jpg", "w": c["w"], "h": c["h"],
                           "source": c.get("source"), "headlines": items})
        if papers:
            out["countries"].append({"name": g["country"], "flag": g["flag"], "papers": papers})
    for name in (f"{date}.json", "latest.json"):
        json.dump(out, open(os.path.join(ROOT, "data", name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # archive index
    ipath = os.path.join(ROOT, "data", "index.json")
    idx = json.load(open(ipath, encoding="utf-8")) if os.path.exists(ipath) else []
    idx = [e for e in idx if e["date"] != date] + [{"date": date, "date_fa": out["date_fa"]}]
    idx.sort(key=lambda e: e["date"], reverse=True)
    json.dump(idx, open(ipath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(len(c["papers"]) for c in out["countries"])
    nh = sum(len(p["headlines"]) for c in out["countries"] for p in c["papers"])
    print(f"{out['date_fa']}: {n} papers, {nh} headlines")


if __name__ == "__main__":
    main()
