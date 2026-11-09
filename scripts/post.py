#!/usr/bin/env python3
"""Nightly shareable Telegram post: today's top front-page headlines.

Reads data/posts/DATE.json:
  {"date": "YYYY-MM-DD", "lead": "short Persian lead",
   "items": [{"slug": "<paper slug>", "fa": "<Persian headline>"}, ...],
   "covers": [slug, ...]  # optional, for posts/DATE.jpg (scripts/post_image.py)}
and sends it to the bot's chat as one message: the cover collage as a large
preview above the text, the lead, one line per headline (flag + paper), a
text link and a URL button that opens the Mini App. URL buttons and text
links survive forwarding, so the message can be forwarded to channels and
groups as is. A second run for the same date edits the message.

Usage: python3 scripts/post.py [DATE] [--preview]
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (else chat_id from data/notify-state.json)
State: data/post-state.json {"date", "message_id", "chat_id"}
"""
import html, json, os, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "post-state.json"
APP_LINK = "https://t.me/worldnewspaperminiappbot/frontpages"
BOT = "@worldnewspaperminiappbot"
RAW = "https://raw.githubusercontent.com/saeedshariati1351/frontpages-miniapp/main/"
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def api(token, method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def build(date):
    post = json.loads((ROOT / "data" / "posts" / f"{date}.json").read_text())
    day = json.loads((ROOT / "data" / f"{date}.json").read_text())
    papers = {p["slug"]: (c["flag"], p["fa"]) for c in day["countries"] for p in c["papers"]}
    n_p = sum(len(c["papers"]) for c in day["countries"])
    n_h = sum(len(p.get("headlines") or []) for c in day["countries"] for p in c["papers"])
    e = html.escape
    lines = [f"🗞 <b>صفحهٔ اول روزنامه‌های جهان</b>",
             f"📅 {e(day['date_fa'])}", "", f"<i>{e(post['lead'])}</i>", ""]
    for it in post["items"]:
        flag, name = papers[it["slug"]]
        lines.append(f"{flag} <b>{e(name)}:</b> {e(it['fa'])}")
    lines += ["",
              f"🔗 <a href=\"{APP_LINK}\">صفحهٔ اول {str(n_p).translate(FA)} روزنامه و "
              f"{str(n_h).translate(FA)} تیتر ترجمه‌شده به فارسی</a>",
              f"🤖 {BOT}"]
    text = "\n".join(lines)
    img = ROOT / "posts" / f"{date}.jpg"
    return text, (RAW + f"posts/{date}.jpg" if img.exists() else None)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    days = json.loads((ROOT / "data" / "index.json").read_text())
    date = args[0] if args else days[0]["date"]
    if not (ROOT / "data" / "posts" / f"{date}.json").exists():
        print("no post for", date); return
    text, img = build(date)
    if "--preview" in sys.argv:
        print(text, "\n\nimage:", img, "\nlength:", len(text)); return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN not set; skipping"); return
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    ns = ROOT / "data" / "notify-state.json"
    if not chat and ns.exists():
        chat = str(json.loads(ns.read_text()).get("chat_id") or "")
    if not chat:
        sys.exit("no chat id")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    payload = {
        "chat_id": chat, "text": text, "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": "📰 صفحهٔ اول روزنامه‌های جهان", "url": APP_LINK}]]},
        "link_preview_options": ({"url": img, "prefer_large_media": True, "show_above_text": True}
                                 if img else {"is_disabled": True}),
    }
    if state.get("date") == date and state.get("message_id"):
        r = api(token, "editMessageText", dict(payload, message_id=state["message_id"]))
        if r.get("ok") or "not modified" in r.get("description", ""):
            print("edited", state["message_id"]); return
        print("edit failed, sending new:", r.get("description"))
    r = api(token, "sendMessage", payload)
    if not r.get("ok"):
        print("send failed:", r); sys.exit(1)
    STATE.write_text(json.dumps({"date": date, "message_id": r["result"]["message_id"],
                                 "chat_id": chat}) + "\n")
    print("sent", r["result"]["message_id"])


if __name__ == "__main__":
    main()
