from flask import render_template
import requests
import base64
import json
from typing import Optional
from PIL import ImageFont
import tools.colorutils as colorutils

try:
    import cairosvg
except Exception:
    print(
        "cairo import error! this doesnt happen on dev lmao im just testing on windows"
    )

FONT_FAMILY = "'Century Gothic', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
FONT_PATH = "/usr/local/share/fonts/centurygothic.ttf"
PRESENCE_COLORS = {"active": "#43B581", "away": "#747F8D"}
THEME_COLORS = {
    "dark": {
        "bg": "1a1c1f",
        "text_primary": "#ffffff",
        "text_secondary": "#aaaaaa",
        "text_tertiary": "#666666",
        "divider": "#313336",
        "idle_text": "#aaaaaa",
        "spotify_color": "#1CB853",
        "activity_title": "#ffffff",
        "activity_sub": "#cccccc",
        "activity_time": "#cccccc",
        "username_color": "#cccccc",
    },
    "light": {
        "bg": "ededed",
        "text_primary": "#111111",
        "text_secondary": "#555555",
        "text_tertiary": "#999999",
        "divider": "#D5D5D5",
        "idle_text": "#444444",
        "spotify_color": "#0d943d",
        "activity_title": "#000000",
        "activity_sub": "#777777",
        "activity_time": "#777777",
        "username_color": "#666666",
    },
}


def fetch_b64(url):
    if not url:
        return
    try:
        r = requests.get(url, timeout=5)
        return base64.b64encode(r.content).decode()
    except Exception:
        return


def measure_text_width(text, font_path, font_size):
    try:
        font = ImageFont.truetype(font_path, font_size)
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except Exception:
        return len(text) * font_size * 0.6


def fetch_emoji(emoji_name, _is_twmoji=False):
    emoji_name = emoji_name.strip(":")
    try:
        with open("emoji_list.json", "r", encoding="utf-8") as fh:
            emoji_list = json.load(fh)["emojies"]
        url = emoji_list.get(emoji_name)
        if not url:
            if _is_twmoji:
                return
            else:
                return fetch_emoji("tw_" + emoji_name.strip(":"), _is_twmoji=True)
        return fetch_b64(url)
    except Exception:
        return


def _e(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _css(**props):
    return "; ".join(f"{k.replace("_","-")}: {v}" for (k, v) in props.items())


def _maxlength(s, length):
    return s if len(s) <= length else s[: length - 3] + "..."


def img(b64, mime="png", **style_kw):
    if not b64:
        return ""
    return f'<img src="data:image/{mime};base64,{b64}" style="{_css(**style_kw)}" />'


def render_card_sync(
    data,
    theme="light",
    bg=None,
    border_radius="10px",
    idle_message="Nothing much to say...",
    hide_status=False,
):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            with open(data, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    t = THEME_COLORS.get(theme, THEME_COLORS["light"])
    raw_bg = bg if bg else t["bg"]
    import re, secrets

    def _is_safe_token(s):
        if not s or len(s) > 200:
            return False
        if any(c in s for c in "<>\"'`;/\\"):
            return False
        if s.count("(") != s.count(")"):
            return False
        return True

    def _parse_linear_gradient(s):
        m = re.match("^\\s*linear-gradient\\s*\\((.*)\\)\\s*$", s, re.I)
        if not m:
            return
        inner = m.group(1)
        parts = [p.strip() for p in re.split(",(?![^()]*\\))", inner) if p.strip()]
        if not parts:
            return
        if re.match("^[0-9.+-]+deg$", parts[0], re.I):
            parts = parts[1:]
        if len(parts) < 2:
            return
        for token in parts:
            if not _is_safe_token(token):
                return
        gid = f"g{secrets.token_hex(6)}"
        stops = []
        n = len(parts)
        for i, token in enumerate(parts):
            tkn = token
            offset = None
            m2 = re.match("^(.*)\\s+([0-9.]+%?)$", token)
            if m2:
                tkn = m2.group(1).strip()
                offset = m2.group(2)
            # if token is a bare hex like '000' or 'ffffff', add leading '#'
            if re.fullmatch(r"[0-9A-Fa-f]{3,8}", tkn):
                tkn = f"#{tkn}"
            if not offset:
                offset = f"{int(i*100/(n-1))}%"
            stops.append(f'<stop offset="{offset}" stop-color="{tkn}" />')
        defs = f'<defs><linearGradient id="{gid}" x1="0%" y1="0%" x2="100%" y2="0%">{"".join(stops)}</linearGradient></defs>'
        return defs, f"url(#{gid})"

    bg_defs = ""
    bg_fill = None
    if raw_bg and isinstance(raw_bg, str):
        raw_bg = raw_bg.strip()
        if raw_bg.lower().startswith("linear-gradient"):
            parsed = _parse_linear_gradient(raw_bg)
            if parsed:
                bg_defs, bg_fill = parsed
        if not bg_fill and _is_safe_token(raw_bg):
            if raw_bg.startswith("#"):
                bg_fill = raw_bg
            elif re.fullmatch("[0-9A-Fa-f]{3,8}", raw_bg):
                bg_fill = f"#{raw_bg}"
            else:
                bg_fill = raw_bg
    if not bg_fill:
        bg_fill = f"#{t["bg"]}"
    user = data.get("slack_user", {})
    display_name = _e(user.get("display_name") or user.get("real_name") or "")
    real_name = _e(user.get("real_name", ""))
    title = _e(user.get("title", ""))
    pronouns = _e(_maxlength(user.get("pronouns", ""), 40))
    avatar_url = user.get("avatar_url", "")
    presence = data.get("slack_status", "")
    status_emoji = data.get("status_emoji", "")
    status_text = _e(_maxlength(data.get("status_text", ""), 55))
    avatar_b64 = fetch_b64(avatar_url)
    presence_color = PRESENCE_COLORS.get(presence, PRESENCE_COLORS["away"])
    avatar_border_color = colorutils.get_avatar_main_color_b64(
        avatar_b64, presence_color
    )
    try:
        border_radius_px = int("".join(filter(str.isdigit, border_radius)))
    except Exception:
        border_radius_px = 10
    divider_color = t["divider"]
    status_emoji_b64 = None
    has_status_text = bool(status_text and status_text.strip())
    if status_emoji and status_emoji.strip():
        status_emoji_b64 = fetch_emoji(status_emoji.strip(":"))
    banner_height = 150 if not hide_status else 100
    EMOJI_SIZE = 16
    EMOJI_TEXT_GAP = 8
    CARD_WIDTH = 410
    if status_emoji_b64 and has_status_text:
        text_w = measure_text_width(status_text, FONT_PATH, 13)
        group_w = EMOJI_SIZE + EMOJI_TEXT_GAP + text_w
        emoji_x = (CARD_WIDTH - group_w) / 2
        status_text_x = emoji_x + EMOJI_SIZE + EMOJI_TEXT_GAP
    else:
        emoji_x = 0
        status_text_x = CARD_WIDTH / 2
    return render_template(
        "card.html",
        banner_height=banner_height,
        bg_color=raw_bg,
        bg_fill=bg_fill,
        bg_defs=bg_defs,
        border_radius_px=border_radius_px,
        text_primary=t["text_primary"],
        text_secondary=t["text_secondary"],
        text_tertiary=t["text_tertiary"],
        divider_color=divider_color,
        font_family=FONT_FAMILY,
        avatar_b64=avatar_b64,
        avatar_border_color=avatar_border_color,
        presence_color=presence_color,
        real_name=real_name,
        display_name=display_name,
        title=title,
        pronouns=pronouns,
        idle_message=_e(idle_message),
        status_emoji_b64=status_emoji_b64,
        status_text=status_text,
        has_status_text=has_status_text,
        hide_status=hide_status,
        emoji_x=emoji_x,
        status_text_x=status_text_x,
    )


def render_card_sync_png(
    data,
    theme="light",
    bg=None,
    border_radius="10px",
    idle_message="Nothing much to say...",
    hide_status=False,
    scale=4.0,
):
    svg_str = render_card_sync(
        data=data,
        theme=theme,
        bg=bg,
        border_radius=border_radius,
        idle_message=idle_message,
        hide_status=hide_status,
    )
    return cairosvg.svg2png(bytestring=svg_str.encode(), scale=max(min(scale, 10), 0.2))
