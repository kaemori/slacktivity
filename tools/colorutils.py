# gets main color from avatar and uses it as the presence circle color, with a border that matches the card background to create a "cutout" effect
import base64
from io import BytesIO

from PIL import Image


def get_avatar_main_color_b64(avatar_b64: str, fallback_color: str) -> str:
    try:
        img = Image.open(BytesIO(base64.b64decode(avatar_b64)))
        img = img.resize((1, 1))
        main_color = img.getpixel((0, 0))
        return "#%02x%02x%02x" % main_color
    except Exception as e:
        print("Error fetching avatar color:", e)
        return fallback_color
