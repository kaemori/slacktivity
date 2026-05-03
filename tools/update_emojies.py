import os
from dotenv import load_dotenv

import requests
import json
import time

load_dotenv("secrets.env")

base_url = "https://slack.com/api/emoji.list"
header = {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}


def _get_emoji_list():
    try:
        r = requests.get(base_url, headers=header, timeout=5)
        data = r.json()
        if not data.get("ok"):
            print("Error fetching emoji list:", data.get("error"))
            return {}
        return data.get("emoji", {})
    except Exception as e:
        print("Exception fetching emoji list:", e)
        return {}


def _write_emojies():
    with open("emoji_list.json", "w", encoding="utf-8") as fh:
        emoji_list = _get_emoji_list()
        json.dump({"last_update": time.time(), "emojies": emoji_list}, fh, indent=4)


def try_update_emojies():
    try:
        with open("emoji_list.json", "r", encoding="utf-8") as fh:
            last_update = json.load(fh)["last_update"]

            if time.time() - last_update > 60 * 60 * 60:  # every hour
                _write_emojies()

    except FileNotFoundError:
        _write_emojies()
