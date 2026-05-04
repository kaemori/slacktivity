import os
import threading
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    jsonify,
    render_template,
    Response,
    abort,
)
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.models.blocks import SectionBlock, ImageBlock
from slack_sdk.models.blocks.basic_components import MarkdownTextObject
from urllib.parse import urlencode, quote_plus, unquote_plus
from dotenv import load_dotenv
import sqlite3
import requests
from pathlib import Path
from cryptography.fernet import Fernet
import secrets
import string
import time
from tools.slack_fetch import get_user_data
from card import render_card_sync, render_card_sync_png
from tools.update_emojies import try_update_emojies

load_dotenv("secrets.env")
BASE_LINK = "https://slacktivity.hackclub.app"
REDIRECT_URI = "https://slacktivity.hackclub.app/oauth/callback"
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)
flask_app = Flask(__name__)
_fernet = Fernet(os.environ["TOKEN_ENCRYPTION_KEY"].encode())


def encrypt_token(token):
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(token):
    return _fernet.decrypt(token.encode()).decode()


def alphanum8():
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(8))


DB_PATH = Path.cwd() / "database" / "user_tokens.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_sql():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_tokens (
            user_id   TEXT PRIMARY KEY,
            token     TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("[slacktivity] db ready!!")


def db_set_token(user_id, token):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO user_tokens (user_id, token, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            token = excluded.token,
            updated_at = CURRENT_TIMESTAMP
    """,
        (user_id, encrypt_token(token)),
    )
    conn.commit()
    conn.close()


def db_get_token(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT token FROM user_tokens WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return
    return decrypt_token(row["token"])


def db_delete_token(user_id):
    conn = get_db()
    cur = conn.execute("DELETE FROM user_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


_pending_states = set()


def get_auth_url():
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return (
        f"https://slack.com/oauth/v2/authorize?client_id={os.environ["MY_CLIENT_ID"]}&user_scope=users:read,users.profile:read&redirect_uri={REDIRECT_URI}&state={state}",
        state,
    )


def post_ephemeral_or_dm(client, *, channel_id, user_id, **kwargs):
    try:
        client.chat_postEphemeral(channel=channel_id, user=user_id, **kwargs)
    except Exception as e:
        if "channel_not_found" not in str(e):
            raise
        sorry = "sorry! i couldn't reach where you ran the command, so thought i'd drop it off here instead."
        if "blocks" in kwargs:
            kwargs["blocks"] = [
                {"type": "section", "text": {"type": "mrkdwn", "text": sorry}}
            ] + list(kwargs["blocks"])
        elif "text" in kwargs:
            kwargs["text"] = f"""{sorry}

{kwargs['text']}"""
        kwargs.pop("user", None)
        client.chat_postMessage(channel=user_id, **kwargs)


@app.command("/slacktivity-help")
def help(ack, command, client):
    ack()
    user_id = command["user_id"]
    post_ephemeral_or_dm(
        client,
        channel_id=command["channel_id"],
        user_id=user_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": """*welcome to slacktivity!!*
to get started, first run `/slacktivity-register` to link your slack account~""",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": """*commands*
>`/slacktivity-register` — links your account so slacktivity can read your presence & status
>`/slacktivity-unregister` — removes your account & deletes your token
>`/slacktivity-preview` — shows your activity card with links to the svg & png versions
>`/slacktivity-create` — customise your card (theme, background, border radius, idle message, etc.)
>`/slacktivity-help` — shows this message :3""",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "`/slacktivity-preview` and `/slacktivity-create` have an option to send your profile card directly into chat for you!",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "also, if we can't reach you where you ran the command, we'll send the result directly to your direct messages!!",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "made w/ <3 by <@U098A2QC2LF> & the Icarus Alliance (+ Kai)",
                    }
                ],
            },
        ],
    )


@app.command("/slacktivity-register")
def register(ack, command, client):
    ack()
    user_id = command["user_id"]
    auth_url, state = get_auth_url()
    post_ephemeral_or_dm(
        client,
        channel_id=command["channel_id"],
        user_id=user_id,
        text="click the button below to register!!",
        attachments=[
            {
                "text": "",
                "fallback": "You are unable to register",
                "callback_id": "register_button",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "register",
                        "text": "Register",
                        "type": "button",
                        "url": auth_url,
                    }
                ],
            }
        ],
    )


@app.action("register_button")
def handle_register_button(ack, body):
    ack()


@app.command("/slacktivity-unregister")
def unregister(ack, command, client):
    ack()
    user_id = command["user_id"]
    if db_delete_token(user_id):
        post_ephemeral_or_dm(
            client,
            channel_id=command["channel_id"],
            user_id=user_id,
            text="ur unregistered!! ur token has been yeeted :3",
        )
    else:
        post_ephemeral_or_dm(
            client,
            channel_id=command["channel_id"],
            user_id=user_id,
            text="u weren't registered in the first place silly!!",
        )


@app.command("/slacktivity-preview")
def preview(ack, command, client):
    ack()
    user_id = command["user_id"]
    token = db_get_token(user_id)
    if token:
        svg_link = BASE_LINK + f"/user/{user_id}"
        png_link = BASE_LINK + f"/user/{user_id}?format=png"
        message_pretext = SectionBlock(
            text=MarkdownTextObject(
                text=f"""hi! your svg card can be found <{svg_link}|here>, and your png card can be found <{png_link}|here>!
the png is also below for you to use~"""
            ),
            block_id="pretext-md",
        )
        png_block = ImageBlock(
            title="slacktivity card, png",
            image_url=png_link + f"&v={alphanum8()}",
            alt_text=f"slacktivity card for user id {user_id}",
            block_id="png-img",
        )
        message_posttext = SectionBlock(
            text=MarkdownTextObject(
                text="if you want extra customization, you can always run `/slacktivity-create`~"
            ),
            block_id="posttext-md",
        )
        post_ephemeral_or_dm(
            client,
            channel_id=command["channel_id"],
            user_id=user_id,
            blocks=[
                message_pretext,
                png_block,
                message_posttext,
                {
                    "type": "actions",
                    "block_id": "preview_actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "📤 share to channel",
                            },
                            "style": "primary",
                            "action_id": "share_card_to_channel",
                            "value": f"{user_id}|{command["channel_id"]}",
                        }
                    ],
                },
            ],
        )
    else:
        post_ephemeral_or_dm(
            client,
            channel_id=command["channel_id"],
            user_id=user_id,
            text="u need to be registered to use this command! run `/slacktivity-register` first",
        )


@app.action("share_card_to_channel")
def share_card_to_channel(ack, body, client):
    ack()
    user_id, channel_id = body["actions"][0]["value"].split("|", 1)
    png_link = BASE_LINK + f"/user/{user_id}?format=png"
    user_token = db_get_token(user_id)
    if not user_token:
        post_ephemeral_or_dm(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text="couldn't find ur token!! try `/slacktivity-register` again :(",
        )
        return
    user_client = WebClient(token=user_token)
    user_client.chat_postMessage(
        channel=channel_id,
        as_user=True,
        text="my slacktivity card",
        blocks=[
            {
                "type": "image",
                "image_url": png_link + f"&v={alphanum8()}",
                "alt_text": "my slacktivity card",
            }
        ],
    )


@app.command("/slacktivity-create")
def create(ack, command, client):
    ack()
    user_id = command["user_id"]
    token = db_get_token(user_id)
    if not token:
        post_ephemeral_or_dm(
            client,
            channel_id=command["channel_id"],
            user_id=user_id,
            text="u need to be registered to use this command! run `/slacktivity-register` first",
        )
        return
    client.views_open(
        trigger_id=command["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "slacktivity_create_modal",
            "private_metadata": f"{user_id}|{command["channel_id"]}",
            "title": {"type": "plain_text", "text": "customise ur card"},
            "submit": {"type": "plain_text", "text": "preview"},
            "close": {"type": "plain_text", "text": "cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "theme_block",
                    "label": {"type": "plain_text", "text": "theme"},
                    "element": {
                        "type": "static_select",
                        "action_id": "theme",
                        "placeholder": {"type": "plain_text", "text": "pick a theme"},
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "dark"},
                            "value": "dark",
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "dark"},
                                "value": "dark",
                            },
                            {
                                "text": {"type": "plain_text", "text": "light"},
                                "value": "light",
                            },
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "bg_block",
                    "optional": True,
                    "label": {"type": "plain_text", "text": "custom background colour"},
                    "hint": {
                        "type": "plain_text",
                        "text": "any css colour: hex (include the leading #, e.g. #1a1a2e), rgb(30,30,46) (no #), or a gradient (include # in hex stops, e.g. linear-gradient(135deg,#1a1a2e,#16213e)). leave blank to use the theme default",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "bg",
                        "placeholder": {"type": "plain_text", "text": "#1a1a2e"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "border_radius_block",
                    "optional": True,
                    "label": {"type": "plain_text", "text": "border radius"},
                    "hint": {
                        "type": "plain_text",
                        "text": "any css border-radius value, e.g. 12px, 24px, 0px. default is 12px",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "border_radius",
                        "placeholder": {"type": "plain_text", "text": "12px"},
                        "initial_value": "12px",
                    },
                },
                {
                    "type": "input",
                    "block_id": "idle_message_block",
                    "optional": True,
                    "label": {"type": "plain_text", "text": "idle message"},
                    "hint": {
                        "type": "plain_text",
                        "text": 'shown when you\'re not doing anything. default: "not doing anything rn"',
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "idle_message",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "not doing anything rn",
                        },
                        "initial_value": "not doing anything rn",
                    },
                },
                {
                    "type": "input",
                    "block_id": "text_primary_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "primary text colour (text_primary)",
                    },
                    "hint": {
                        "type": "plain_text",
                        "text": "any css colour: hex (include leading #) or rgb(...). leave blank for theme default",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "text_primary",
                        "placeholder": {"type": "plain_text", "text": "#ffffff"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "text_secondary_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "secondary text colour (text_secondary)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "text_secondary",
                        "placeholder": {"type": "plain_text", "text": "#aaaaaa"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "text_tertiary_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "tertiary text colour (text_tertiary)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "text_tertiary",
                        "placeholder": {"type": "plain_text", "text": "#666666"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "divider_block",
                    "optional": True,
                    "label": {"type": "plain_text", "text": "divider colour (divider)"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "divider",
                        "placeholder": {"type": "plain_text", "text": "#313336"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "idle_text_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "idle text colour (idle_text)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "idle_text",
                        "placeholder": {"type": "plain_text", "text": "#aaaaaa"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "spotify_color_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "spotify colour (spotify_color)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "spotify_color",
                        "placeholder": {"type": "plain_text", "text": "#1CB853"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "activity_title_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "activity title colour (activity_title)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "activity_title",
                        "placeholder": {"type": "plain_text", "text": "#ffffff"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "activity_sub_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "activity subtitle colour (activity_sub)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "activity_sub",
                        "placeholder": {"type": "plain_text", "text": "#cccccc"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "activity_time_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "activity time colour (activity_time)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "activity_time",
                        "placeholder": {"type": "plain_text", "text": "#cccccc"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "username_color_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "username colour (username_color)",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "username_color",
                        "placeholder": {"type": "plain_text", "text": "#cccccc"},
                    },
                },
                {
                    "type": "input",
                    "block_id": "hide_status_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "hide status emoji & text?",
                    },
                    "element": {
                        "type": "checkboxes",
                        "action_id": "hide_status",
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "hide my slack status from the card",
                                },
                                "value": "true",
                            }
                        ],
                    },
                },
            ],
        },
    )


@app.view("slacktivity_create_modal")
def handle_create_modal(ack, body, client):
    ack()
    user_id, channel_id = body["view"]["private_metadata"].split("|", 1)
    values = body["view"]["state"]["values"]
    theme = values["theme_block"]["theme"]["selected_option"]["value"]
    bg = (values["bg_block"]["bg"].get("value") or "").strip() or None
    border_radius = (
        values["border_radius_block"]["border_radius"].get("value") or "12px"
    ).strip()
    idle_message = (
        values["idle_message_block"]["idle_message"].get("value")
        or "not doing anything rn"
    ).strip()
    hide_status = bool(
        values["hide_status_block"]["hide_status"].get("selected_options")
    )
    params = {"format": "png", "theme": theme}
    if bg:
        params["bg"] = bg
    params["borderRadius"] = border_radius
    params["idleMessage"] = idle_message
    if hide_status:
        params["hideStatus"] = "true"
    # include any optional colour overrides from the modal inputs
    color_keys = [
        "text_primary",
        "text_secondary",
        "text_tertiary",
        "divider",
        "idle_text",
        "spotify_color",
        "activity_title",
        "activity_sub",
        "activity_time",
        "username_color",
        "bg",
    ]
    for ck in color_keys:
        block = f"{ck}_block"
        try:
            val = (values[block][ck].get("value") or "").strip()
        except Exception:
            val = ""
        if val:
            params[ck] = val
    svg_params = {k: v for (k, v) in params.items() if k != "format"}
    svg_link = BASE_LINK + f"/user/{user_id}?" + urlencode(svg_params)
    png_link = BASE_LINK + f"/user/{user_id}?" + urlencode(params)
    # encode the png_link when embedding into the action `value` to avoid
    # accidental truncation or interpretation of characters like `#` by clients
    share_value = f"{user_id}|{channel_id}|{quote_plus(png_link)}"
    post_ephemeral_or_dm(
        client,
        channel_id=channel_id,
        user_id=user_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"""hi! your svg card can be found <{svg_link}|here>, and your png card can be found <{png_link}|here>!
the png is also below for you to use~""",
                },
            },
            {
                "type": "image",
                "title": {"type": "plain_text", "text": "slacktivity card, png"},
                "image_url": png_link + f"&v={alphanum8()}",
                "alt_text": f"slacktivity card for user id {user_id}",
            },
            {
                "type": "actions",
                "block_id": "create_preview_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📤 share to channel"},
                        "style": "primary",
                        "action_id": "share_custom_card_to_channel",
                        "value": share_value,
                    }
                ],
            },
        ],
    )


@app.action("share_custom_card_to_channel")
def share_custom_card_to_channel(ack, body, client):
    ack()
    user_id, channel_id, png_link_enc = body["actions"][0]["value"].split("|", 2)
    png_link = unquote_plus(png_link_enc)
    user_token = db_get_token(user_id)
    if not user_token:
        post_ephemeral_or_dm(
            client,
            channel_id=channel_id,
            user_id=user_id,
            text="couldn't find ur token!! try `/slacktivity-register` again :(",
        )
        return
    user_client = WebClient(token=user_token)
    user_client.chat_postMessage(
        channel=channel_id,
        as_user=True,
        text="my slacktivity card",
        blocks=[
            {
                "type": "image",
                "image_url": png_link + f"&v={alphanum8()}",
                "alt_text": "my slacktivity card",
            }
        ],
    )


@flask_app.route("/signup")
def signup():
    auth_url, state = get_auth_url()
    return redirect(auth_url, 301)


@flask_app.route("/oauth/callback")
def oauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if state not in _pending_states:
        return "invalid or expired state >:(", 400
    _pending_states.discard(state)
    if not code:
        return "no code received :(", 400
    resp = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": os.environ["MY_CLIENT_ID"],
            "client_secret": os.environ["MY_CLIENT_SECRET"],
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    data = resp.json()
    if not data.get("ok"):
        return f"auth failed: {data.get("error")}", 400
    authed_user = data.get("authed_user", {})
    user_token = authed_user.get("access_token")
    user_id = authed_user.get("id")
    if not user_token or not user_id:
        return "auth failed: missing token or user id", 400
    db_set_token(user_id, user_token)
    return render_template("registered.html")


@flask_app.errorhandler(404)
def page_not_found(e):
    return (
        jsonify(
            {"success": False, "error": f"nothing here! you sure you belong here?"}
        ),
        404,
    )


@flask_app.route("/")
def home():
    return render_template("index.html", BASE_LINK=BASE_LINK)


@flask_app.route("/<path:text>", methods=["GET", "POST"])
def all_routes(text):
    if text.startswith("api/users"):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"/api/users has now been replaced with /api/user. automatic redirects have been deprecated since initial prod",
                }
            ),
            404,
        )
    else:
        abort(404)


@flask_app.route("/api/delete/<slack_id>", methods=["POST"])
def api_delete(slack_id):
    if db_delete_token(slack_id):
        return jsonify({"success": True, "message": f"deleted token for {slack_id}"})
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"no token for {slack_id}. are you signed up?",
                }
            ),
            404,
        )


@flask_app.route("/api/user/<slack_id>")
def api_user(slack_id):
    token = db_get_token(slack_id)
    if not token:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"no token for {slack_id}, they need to /slacktivity-register first",
                }
            ),
            404,
        )
    try:
        data = get_user_data(slack_id, token)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 502
    return jsonify({"success": True, "data": data})


@flask_app.route("/user/<slack_id>")
def card_user(slack_id):
    token = db_get_token(slack_id)
    if not token:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"no token for {slack_id}, they need to /slacktivity-register first",
                }
            ),
            404,
        )
    try:
        data = get_user_data(slack_id, token)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 502
    theme = request.args.get("theme", "dark")
    bg = request.args.get("bg", None)
    border_radius = request.args.get("borderRadius", "12px")
    idle_message = request.args.get("idleMessage", "not doing anything rn")
    hide_status = request.args.get("hideStatus", "false").lower() == "true"
    # collect theme overrides
    color_keys = [
        "text_primary",
        "text_secondary",
        "text_tertiary",
        "divider",
        "idle_text",
        "spotify_color",
        "activity_title",
        "activity_sub",
        "activity_time",
        "username_color",
        "bg",
    ]
    theme_overrides = {}
    for ck in color_keys:
        v = request.args.get(ck)
        if v:
            theme_overrides[ck] = v

    svg = render_card_sync(
        data=data,
        theme=theme,
        bg=bg,
        border_radius=border_radius,
        idle_message=idle_message,
        hide_status=hide_status,
        theme_overrides=theme_overrides if theme_overrides else None,
    )
    out_format = request.args.get("format", None)
    try:
        scale = max(1, int(request.args.get("scale", "4")))
    except Exception:
        scale = 4.0
    if not out_format or out_format not in ("png",):
        return Response(svg, mimetype="image/svg+xml")
    png = render_card_sync_png(
        data=data,
        theme=theme,
        bg=bg,
        border_radius=border_radius,
        idle_message=idle_message,
        hide_status=hide_status,
        scale=scale,
        theme_overrides=theme_overrides if theme_overrides else None,
    )
    return Response(png, mimetype="image/png")


def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)


def update_emojies_periodically():
    while True:
        time.sleep(120)
        try_update_emojies()


if __name__ == "__main__":
    load_sql()
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=update_emojies_periodically, daemon=True).start()
    print("[slacktivity] bot is alive!!")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
