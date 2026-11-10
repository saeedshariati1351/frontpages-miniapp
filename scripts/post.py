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
groups as is. A second run for the same date edits the message (skipped when
nothing changed).

Target: the public channel «صفحه نخست جهان» where the bot is an admin
(TELEGRAM_CHANNEL_ID, else data/channel.json, else found from the bot's
updates: the channel where the bot was made admin). Until the channel is
found the post goes to the owner's chat (TELEGRAM_CHAT_ID / notify-state).
When the channel is first found, data/channel.json is written (id, title,
link; the Mini App shows the link) and the channel link is added to the
bot's description.

Usage: python3 scripts/post.py [DATE] [--preview] [--today-only]
  --today-only: do nothing unless DATE is the latest day (scheduled runs)
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, TELEGRAM_CHAT_ID
State: data/post-state.json {"date", "message_id", "chat_id", "hash"}
"""
import hashlib, html, json, os, sys, urllib.parse, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "post-state.json"
CHANNEL = ROOT / "data" / "channel.json"
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


def find_channel(token):
    """Channel where the bot is an admin, from data/channel.json, env or the bot's updates."""
    cid = os.environ.get("TELEGRAM_CHANNEL_ID", "").strip()
    if not cid and CHANNEL.exists():
        cid = str(json.loads(CHANNEL.read_text()).get("id") or "")
    if not cid:
        r = api(token, "getUpdates", {"allowed_updates": ["my_chat_member", "channel_post", "message"]})
        if not r.get("ok"):
            print("getUpdates:", r.get("description"))
        for u in reversed(r.get("result", [])):
            m = u.get("my_chat_member")
            if m and m["chat"].get("type") == "channel" and \
                    m["new_chat_member"].get("status") == "administrator":
                cid = str(m["chat"]["id"]); break
            p = u.get("channel_post")
            if p:
                cid = str(p["chat"]["id"]); break
    if not cid:
        return None
    me = api(token, "getMe", {}).get("result", {})
    mem = api(token, "getChatMember", {"chat_id": cid, "user_id": me.get("id")})
    status = mem.get("result", {}).get("status")
    if status not in ("administrator", "creator") or not mem["result"].get("can_post_messages", True):
        print("bot is not an admin with posting rights in", cid, status, mem.get("description", ""))
        return None
    chat = api(token, "getChat", {"chat_id": cid}).get("result", {})
    info = {"id": chat.get("id", cid), "title": chat.get("title", ""), "username": chat.get("username", "")}
    info["link"] = f"https://t.me/{info['username']}" if info["username"] else (chat.get("invite_link") or "")
    if not info["link"]:
        info["link"] = api(token, "exportChatInviteLink", {"chat_id": cid}).get("result", "")
    old = json.loads(CHANNEL.read_text()) if CHANNEL.exists() else {}
    if old != info:
        CHANNEL.write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n")
        print("channel:", info)
    if info["link"]:
        d = api(token, "getMyDescription", {}).get("result", {}).get("description", "")
        if info["link"] not in d:
            line = f"📢 کانال «{info['title']}»: {info['link']}"
            nd = (d + "\n\n" + line).strip() if len(d) + len(line) + 2 <= 512 else line
            print("description:", api(token, "setMyDescription", {"description": nd}).get("ok"))
    return str(info["id"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    days = json.loads((ROOT / "data" / "index.json").read_text())
    date = args[0] if args else days[0]["date"]
    if "--today-only" in sys.argv and date != days[0]["date"]:
        print("latest day has no post yet"); return
    if not (ROOT / "data" / "posts" / f"{date}.json").exists():
        print("no post for", date); return
    text, img = build(date)
    if "--preview" in sys.argv:
        print(text, "\n\nimage:", img, "\nlength:", len(text)); return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN not set; skipping"); return
    chat = find_channel(token)
    if not chat:
        print("no channel yet: sending to the owner's chat")
        chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        ns = ROOT / "data" / "notify-state.json"
        if not chat and ns.exists():
            chat = str(json.loads(ns.read_text()).get("chat_id") or "")
    if not chat:
        sys.exit("no chat id")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    share = "https://t.me/share/url?" + urllib.parse.urlencode(
        {"url": APP_LINK, "text": "صفحهٔ اول روزنامه‌های امروز جهان با تیترهای ترجمه‌شده به فارسی"})
    payload = {
        "chat_id": chat, "text": text, "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [
            [{"text": "📰 صفحهٔ اول روزنامه‌های جهان", "url": APP_LINK}],
            [{"text": "📤 ارسال برای دوستان", "url": share}]]},
        "link_preview_options": ({"url": img, "prefer_large_media": True, "show_above_text": True}
                                 if img else {"is_disabled": True}),
    }
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    same = state.get("date") == date and str(state.get("chat_id")) == str(chat) and state.get("message_id")
    if same and state.get("hash") == digest:
        print("already sent, unchanged"); return
    if same:
        r = api(token, "editMessageText", dict(payload, message_id=state["message_id"]))
        if r.get("ok") or "not modified" in r.get("description", ""):
            state["hash"] = digest
            STATE.write_text(json.dumps(state) + "\n")
            print("edited", state["message_id"]); return
        print("edit failed, sending new:", r.get("description"))
    r = api(token, "sendMessage", payload)
    if not r.get("ok"):
        print("send failed:", r); sys.exit(1)
    STATE.write_text(json.dumps({"date": date, "message_id": r["result"]["message_id"],
                                 "chat_id": chat, "hash": digest}) + "\n")
    print("sent", r["result"]["message_id"], "to", chat)


if __name__ == "__main__":
    main()
