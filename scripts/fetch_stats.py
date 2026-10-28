#!/usr/bin/env python3
"""Monthly users of the Mini App, as Telegram shows them on the bot's public
page (t.me/<bot>: "N monthly users"). Writes data/stats.json
{"monthly_users": N, "updated": "YYYY-MM-DD"}; leaves it unchanged if the
count can't be read. Runs in GitHub Actions (t.me isn't reachable from the
cloud sandbox).

Usage: python3 scripts/fetch_stats.py [bot_username]
"""
import datetime, html, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "stats.json"
BOT = sys.argv[1] if len(sys.argv) > 1 else "worldnewspaperminiappbot"

req = urllib.request.Request(f"https://t.me/{BOT}", headers={"User-Agent": "Mozilla/5.0"})
page = html.unescape(urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"))
extra = re.search(r'class="tgme_page_extra"[^>]*>(.*?)</div>', page, re.S)
print("tgme_page_extra:", extra.group(1).strip() if extra else None)
m = re.search(r"([\d][\d\s,.  ]*)\s*monthly users?", page, re.I)
if not m:
    print("monthly users not found; stats unchanged")
    sys.exit(0)
n = int(re.sub(r"\D", "", m.group(1)))
old = json.loads(OUT.read_text()) if OUT.exists() else {}
today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3, minutes=30))).date().isoformat()
new = {"monthly_users": n, "updated": today}
if old.get("monthly_users") != n:
    OUT.write_text(json.dumps(new) + "\n")
print("monthly users:", n)
