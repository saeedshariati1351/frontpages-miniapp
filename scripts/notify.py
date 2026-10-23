#!/usr/bin/env python3
"""Daily bot message for the Mini App chat.

Sends one message per day to the bot's chat with a button that opens the
Mini App, so the chat preview always shows today's edition instead of
Telegram's "You allowed this bot to message you…" line. Later runs on the
same day edit that message (updated counts) instead of sending a new one.

Env: TELEGRAM_BOT_TOKEN; TELEGRAM_CHAT_ID and APP_URL optional (chat id is
found from the last private chat that sent /start to the bot)
State: data/notify-state.json  {"date": ..., "message_id": ...}
"""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "notify-state.json"
APP_URL = os.environ.get("APP_URL") or "https://saeedshariati1351.github.io/frontpages-miniapp/"
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def api(token, method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN not set; skipping"); return
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    chat = chat or str(state.get("chat_id") or "")
    if not chat:
        # No chat id given: use the private chat that last wrote to the bot
        # (the owner sends /start once).
        r = api(token, "getUpdates", {})
        ids = [u["message"]["chat"]["id"] for u in r.get("result", [])
               if u.get("message", {}).get("chat", {}).get("type") == "private"]
        if not ids:
            print("No chat id: send /start to the bot, then rerun.", r.get("description", ""))
            sys.exit(1)
        chat = str(ids[-1])

    days = json.loads((ROOT / "data" / "index.json").read_text())
    d = days[0]
    text = (
        f"📰 صفحهٔ اول روزنامه‌های امروز — {d['date_fa']}\n\n"
        f"{str(d['papers']).translate(FA)} روزنامه · "
        f"{str(d['headlines']).translate(FA)} تیتر ترجمه‌شده به فارسی"
    )
    markup = {"inline_keyboard": [[{"text": "📖 باز کردن صفحه‌های اول", "web_app": {"url": APP_URL}}]]}

    if state.get("date") == d["date"] and state.get("message_id"):
        r = api(token, "editMessageText", {
            "chat_id": chat, "message_id": state["message_id"],
            "text": text, "reply_markup": markup})
        if r.get("ok") or "not modified" in r.get("description", ""):
            print("edited", state["message_id"]); return
        print("edit failed, sending new:", r.get("description"))

    r = api(token, "sendMessage", {"chat_id": chat, "text": text, "reply_markup": markup})
    if not r.get("ok"):
        print("send failed:", r); sys.exit(1)
    STATE.write_text(json.dumps({"date": d["date"], "message_id": r["result"]["message_id"],
                                 "chat_id": chat}) + "\n")
    print("sent", r["result"]["message_id"])


if __name__ == "__main__":
    main()
