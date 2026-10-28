#!/usr/bin/env python3
"""Monthly users of the Mini App, as Telegram counts them (the "N monthly users"
shown on the bot's profile; MTProto field User.bot_active_users).

Logs in to Telegram's MTProto API as the bot (Telethon, bot token) and reads
the bot's own user object. Writes data/stats.json
{"monthly_users": N, "updated": "YYYY-MM-DD"}; leaves it unchanged if the
count can't be read. Runs in GitHub Actions.

Env: TELEGRAM_BOT_TOKEN, TG_API_ID, TG_API_HASH (from my.telegram.org)
"""
import asyncio, datetime, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "stats.json"


async def active_users():
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.users import GetUsersRequest
    from telethon.tl.types import InputUserSelf
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    client = TelegramClient(StringSession(), int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"])
    await client.start(bot_token=token)
    try:
        me = await client.get_me()
        n = getattr(me, "bot_active_users", None)
        print("get_me: username=%s bot_active_users=%s" % (me.username, n))
        if n is None:
            users = await client(GetUsersRequest([InputUserSelf()]))
            n = getattr(users[0], "bot_active_users", None)
            print("users.getUsers(self): bot_active_users=%s" % n)
        return n
    finally:
        await client.disconnect()


def main():
    for k in ("TELEGRAM_BOT_TOKEN", "TG_API_ID", "TG_API_HASH"):
        if not os.environ.get(k):
            print(f"{k} not set; stats unchanged"); return
    n = asyncio.run(active_users())
    if n is None:
        print("monthly users not available; stats unchanged"); return
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    if old.get("monthly_users") == n:
        print("monthly users unchanged:", n); return
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3, minutes=30))).date().isoformat()
    OUT.write_text(json.dumps({"monthly_users": n, "updated": today}) + "\n")
    print("monthly users:", n)


if __name__ == "__main__":
    main()
