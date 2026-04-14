# functions.py

import os, json, requests
from statistics import mean
from io import BytesIO
from dotenv import load_dotenv
from typing import Dict
from PIL import Image, ImageFont

load_dotenv()

FONT_PATH = "Helmet-Regular.ttf"

_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}

# --- UTILITIES ---

def get_font(size: int) -> ImageFont.ImageFont:
    size = max(6, min(48, int(size)))
    if size in _font_cache:
        return _font_cache[size]
    try:
        font = ImageFont.truetype(FONT_PATH, size)
    except Exception:
        font = ImageFont.load_default()
    _font_cache[size] = font
    return font

# --- CONTENT ---

WEATHER_ICON_MAP = {
    "clear-night": "https://img.icons8.com/forma-bold/100/moon.png",
    "cloudy": "https://img.icons8.com/forma-bold/100/cloud.png",
    "fog": "https://img.icons8.com/forma-bold/100/fog-day.png",
    "hail": "https://img.icons8.com/forma-bold/100/hail.png",
    "lightning": "https://img.icons8.com/forma-bold/100/lightning-bolt.png",
    "lightning-rainy": "https://img.icons8.com/forma-bold/100/storm.png",
    "partlycloudy": "https://img.icons8.com/forma-bold/100/partly-cloudy-day.png",
    "pouring": "https://img.icons8.com/forma-bold/100/rain.png",
    "rainy": "https://img.icons8.com/forma-bold/100/light-rain.png",
    "snowy": "https://img.icons8.com/forma-bold/100/snow.png",
    "snowy-rainy": "https://img.icons8.com/forma-bold/100/sleet.png",
    "sunny": "https://img.icons8.com/forma-bold/100/sun.png",
    "windy": "https://img.icons8.com/forma-bold/100/wind.png",
    "windy-variant": "https://img.icons8.com/forma-bold/100/wind.png",
    "exceptional": "https://img.icons8.com/forma-bold/100/error.png",
}

def get_ha_weather_icon(entity_id):
    """Internal helper to resolve icon URL from weather state"""
    ha_url = os.environ.get("HA_URL")
    ha_token = os.environ.get("HA_TOKEN")
    url = f"{ha_url.rstrip('/')}/api/states/{entity_id}"
    headers = {"Authorization": f"Bearer {ha_token}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        state = resp.json().get("state", "").lower().replace("_", "").replace(" ", "")
        return WEATHER_ICON_MAP.get(state, WEATHER_ICON_MAP["exceptional"])
    except:
        return WEATHER_ICON_MAP["exceptional"]

def get_ha_state(cell_w: int, cell_h: int, cell_i: int, cell: dict = None) -> str:
    ha_url = os.getenv("HA_URL")
    ha_token = os.getenv("HA_TOKEN")

    if not ha_url or not ha_token:
        return "HA: Config Missing"

    # Grab the Entity ID from the layout configuration
    entity_id = None
    if cell:
        entity_id = cell.get("haEntityId")

    if not entity_id:
        return "HA: No Entity ID"

    # API Request to Home Assistant
    url = f"{ha_url.rstrip('/')}/api/states/{entity_id}"
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # Return the state (e.g., 'on', 'off', '22.5')
            return str(data.get("state", "Unknown"))
        else:
            return f"HA Err: {resp.status_code}"
    except Exception as e:
        return f"HA Error: {type(e).__name__}"


def get_ha_image(cell_w: int, cell_h: int, cell_i: int, cell: dict = None) -> Image.Image:
    ha_url = os.getenv("HA_URL")
    ha_token = os.getenv("HA_TOKEN")

    if not ha_url or not ha_token:
        print("HA Config Missing for Image")
        return None

    entity_id = None
    if cell:
        entity_id = cell.get("haEntityId")

    if not entity_id:
        return None

    headers = {
        "Authorization": f"Bearer {ha_token}",
    }

    # Home Assistant uses different API endpoints for cameras vs images
    if entity_id.startswith("camera."):
        url = f"{ha_url.rstrip('/')}/api/camera_proxy/{entity_id}"
    else:
        url = f"{ha_url.rstrip('/')}/api/image_proxy/{entity_id}"

    try:
        # Fetch the actual image from Home Assistant
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 200:
            # Open the image using PIL so the dashboard can render it
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            return img
        else:
            print(f"HA Image Proxy returned {resp.status_code}")
            return None

    except Exception as e:
        print(f"HA Image Fetch Error: {e}")
        return None