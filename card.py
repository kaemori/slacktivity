from flask import render_template
import requests
import base64
import json
from typing import Optional
from PIL import ImageFont


import tools.colorutils as colorutils

import cairosvg

FONT_FAMILY = (
    "'Century Gothic', -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)

FONT_PATH = "/usr/local/share/fonts/centurygothic.ttf"

PRESENCE_COLORS = {
    "active": "#43B581",
    "away": "#747F8D",
}

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


def fetch_b64(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=5)
        return base64.b64encode(r.content).decode()
    except Exception:
        return None


def measure_text_width(text: str, font_path: str, font_size: int) -> float:
    try:
        font = ImageFont.truetype(font_path, font_size)
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]
    except Exception:
        return len(text) * font_size * 0.6  # rough fallback


def fetch_emoji(emoji_name: str, _is_twmoji=False) -> Optional[str]:
    emoji_name = emoji_name.strip(":")
    try:
        with open("emoji_list.json", "r", encoding="utf-8") as fh:
            emoji_list = json.load(fh)["emojies"]
        url = emoji_list.get(emoji_name)
        if not url:
            if _is_twmoji:
                return None
            else:
                return fetch_emoji("tw_" + emoji_name.strip(":"), _is_twmoji=True)
        return fetch_b64(url)
    except Exception:
        return None


def _e(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _css(**props) -> str:
    return "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in props.items())


def _maxlength(s: str, length: int) -> str:
    return s if len(s) <= length else s[: length - 3] + "..."


def img(b64, mime="png", **style_kw):
    if not b64:
        return ""
    return f'<img src="data:image/{mime};base64,{b64}" style="{_css(**style_kw)}" />'


def render_card_sync(
    data: dict,
    theme: str = "light",
    bg: Optional[str] = None,
    border_radius: str = "10px",
    idle_message: str = "Nothing much to say...",
    hide_status: bool = False,
) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            with open(data, "r", encoding="utf-8") as fh:
                data = json.load(fh)

    t = THEME_COLORS.get(theme, THEME_COLORS["light"])
    bg_color = bg if bg else t["bg"]

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

    # parse border_radius to just the number for SVG rx=
    try:
        border_radius_px = int("".join(filter(str.isdigit, border_radius)))
    except Exception:
        border_radius_px = 10

    # divider color — strip the hsl() for SVG since SVG supports it fine actually
    divider_color = t["divider"]

    # status emoji
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
        bg_color=bg_color,
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
    data: dict,
    theme: str = "light",
    bg: Optional[str] = None,
    border_radius: str = "10px",
    idle_message: str = "Nothing much to say...",
    hide_status: bool = False,
    scale: float = 4.0,
) -> bytes:
    svg_str = render_card_sync(
        data=data,
        theme=theme,
        bg=bg,
        border_radius=border_radius,
        idle_message=idle_message,
        hide_status=hide_status,
    )
    return cairosvg.svg2png(bytestring=svg_str.encode(), scale=max(min(scale, 10), 0.2))
