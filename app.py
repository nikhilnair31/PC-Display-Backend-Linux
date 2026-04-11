# app.py

import re, os, sys, json, time, random, psutil, subprocess, requests, tempfile, importlib, inspect, traceback, threading
from io import (
    BytesIO
)
from PIL import (
    Image, ImageDraw, ImageFont, ImageOps
)
from flask import (
    Flask, send_file, request, jsonify
)
from typing import (
    Any, Dict, Callable
)
from dotenv import (
    load_dotenv
)
from werkzeug.utils import (
    secure_filename
)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CANVAS_HTML_PATH = os.path.join(BASE_DIR, "canvas.html")
LAYOUT_JSON_PATH = os.path.join(BASE_DIR, "canvas_layout.json")
REGULAR_FONT_PATH = "Helmet-Regular.ttf"
BOLD_FONT_PATH = "Helmet-Regular.ttf"
ITALIC_FONT_PATH = "Helmet-Regular.ttf"
BOLD_ITALIC_FONT_PATH = "Helmet-Regular.ttf"
_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
STATIC_IMG_DIR = os.path.join(BASE_DIR, "static_images")
os.makedirs(STATIC_IMG_DIR, exist_ok=True)
PRINTER_STATE_PATH = os.path.join(os.path.dirname(__file__), "printer_state.json")
WEBHOOK_SECRET=os.environ.get("WEBHOOK_SECRET", "SOME_LONG_RANDOM_STRING")
RPI_ENDPOINT = os.environ.get("RPI_URL")

# --- HOME ASSISTANT ---
HA_URL = os.environ.get("HA_URL")
HA_TOKEN = os.environ.get("HA_TOKEN")

# Ensure HA_URL and HA_TOKEN are set
if not HA_URL or not HA_TOKEN:
    print("WARNING: Home Assistant URL or Token not set. HA features will be disabled.", flush=True)
    HA_HEADERS: Dict[str, str] = {}
else:
    HA_HEADERS = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

def get_ha_entity_state(entity_id: str) -> dict | None:
    if not HA_HEADERS: # HA is disabled
        return None
    try:
        response = requests.get(f"{HA_URL}/api/states/{entity_id}", headers=HA_HEADERS, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching HA entity {entity_id}: {e}", flush=True)
        return None

def get_ha_entities() -> list[dict]:
    if not HA_HEADERS: # HA is disabled
        return []
    try:
        response = requests.get(f"{HA_URL}/api/states", headers=HA_HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching all HA entities: {e}", flush=True)
        return []

@app.route("/api/ha/entities")
def list_ha_entities():
    entities = get_ha_entities()
    simplified_entities = []
    for entity in entities:
        simplified_entities.append({
            "entity_id": entity["entity_id"],
            "friendly_name": entity["attributes"].get("friendly_name", entity["entity_id"]),
            "state": entity["state"],
            "unit_of_measurement": entity["attributes"].get("unit_of_measurement"),
            "device_class": entity["attributes"].get("device_class"),
            "icon": entity["attributes"].get("icon"),
            "domain": entity["entity_id"].split('.')[0]
        })
    return jsonify(simplified_entities)

functions_module = importlib.import_module("functions")
FUNCTION_MAP = {
    name: fn
    for name, fn in inspect.getmembers(functions_module, inspect.isfunction)
}

EVENT_MAP = {
    1: "STARTED",
    2: "COMPLETED",
    3: "FAILED",
    4: "PAUSED",
    5: "RESUMED",
    6: "UPDATE",
    7: "ATTENTION",
    8: "CANCELED",
    9: "ERROR",
    10: "COOLDOWN",
}

push_event = threading.Event()

app = Flask(__name__)

# --- CANVAS ---
@app.route("/canvas")
def layout_canvas():
    return send_file(CANVAS_HTML_PATH, mimetype="text/html")

@app.route("/canvas_layout", methods=["GET", "POST"])
def canvas_layout():
    if request.method == "POST":
        # Save layout
        try:
            data = request.get_json(force=True)
        except Exception:
            return "Invalid JSON", 400

        try:
            with open(LAYOUT_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Failed to save layout:", e, flush=True)
            return "Failed to save layout", 500

        push_event.set() # Wake up the worker to push the new layout immediately
        return jsonify({"status": "ok"})

    # GET -> load layout
    if not os.path.exists(LAYOUT_JSON_PATH):
        return jsonify({"canvas": None, "cells": []})

    try:
        with open(LAYOUT_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Failed to read layout:", e, flush=True)
        return jsonify({"canvas": None, "cells": []})

    return jsonify(data)

# --- PRINTER ---
def load_printer_state():
    try:
        with open(PRINTER_STATE_PATH, "r") as f:
            dat = json.load(f)
            # print(f'Loaded', flush=True)
            return dat
    except FileNotFoundError:
        # print(f'FileNotFoundError', flush=True)
        return {"state": "UNKNOWN", "progress": None}

def save_printer_state(state):
    with open(PRINTER_STATE_PATH, "w") as f:
        json.dump(state, f)
        # print(f'Saved', flush=True)

@app.route("/octo_webhook", methods=["POST"])
def octo_webhook():
    data = request.get_json(silent=True) or {}
    print(f'data: {data}', flush=True)

    # --- Validate Secret ---
    incoming_secret = data.get("SecretKey")
    if incoming_secret != WEBHOOK_SECRET:
        return "forbidden", 403

    event = data.get("EventType")
    progress = data.get("Progress")
    filename = data.get("FileName")
    error_msg = data.get("Error")
    time_left = data.get("TimeRemainingSec")

    state = load_printer_state()

    # ---- APPLY EVENT TYPE STATE ----
    if event in EVENT_MAP:
        state["prev_state"] = EVENT_MAP[event]
        state["state"] = EVENT_MAP[event]

    # ---- Update progress ----
    if progress is not None:
        state["progress"] = progress

    # ---- Update file ----
    if filename:
        state["file"] = filename

    # ---- Update time remaining ----
    if time_left is not None:
        state["time_remaining"] = time_left
    
    state["updated_at"] = time.time()

    save_printer_state(state)
    push_event.set() # Wake up worker to show new print progress immediately
    return "ok", 200

# --- OUTPUT ---
@app.route("/upload_static_image", methods=["POST"])
def upload_static_image():
    if "file" not in request.files:
        return "No file part", 400

    file = request.files["file"]
    if file.filename == "":
        return "Empty filename", 400

    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    # make it unique-ish
    filename = f"{name}_{int(time.time())}{ext}"
    save_path = os.path.join(STATIC_IMG_DIR, filename)
    file.save(save_path)

    # store relative path in layout
    rel_path = os.path.relpath(save_path, BASE_DIR)

    return jsonify({"path": rel_path})

def get_font(size: int, fontpath: str) -> ImageFont.ImageFont:
    size = max(6, min(48, int(size)))
    if size in _font_cache:
        return _font_cache[size]
    try:
        font = ImageFont.truetype(fontpath, size)
    except Exception:
        font = ImageFont.load_default()
    _font_cache[size] = font
    return font

def strip_fn_name(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw.endswith("()"):
        raw = raw[:-2].strip()
    return raw

def run_cell_function(fn_name_raw: str, w: int, h: int, i: int) -> Any:
    fn_name = strip_fn_name(fn_name_raw)
    if not fn_name:
        return None

    fn = FUNCTION_MAP.get(fn_name)
    if fn is None:
        msg = f"ERR {fn_name}: NOT_FOUND"
        print(msg, flush=True)
        return msg

    try:
        return fn(w, h, i)
    except Exception as e:
        tb = traceback.format_exc()
        # print full traceback to systemd/journal so you can read it
        print(f"ERROR in function '{fn_name}': {e!r}\n{tb}", flush=True)
        # return a short error string that includes the exception message (so it shows up on the image)
        return f"ERR {fn_name}: {e.__class__.__name__}: {str(e)}"

def render_layout_to_image(layout: dict) -> Image.Image:
    canvas_cfg = layout.get("canvas", {})
    width = int(canvas_cfg.get("width", 480))
    height = int(canvas_cfg.get("height", 800))

    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)

    cells = layout.get("cells", [])
    for cell in cells:
        x, y, w, h = int(cell["x"]), int(cell["y"]), int(cell["w"]), int(cell["h"])
        invert = bool(cell.get("invert", False))
        indent = int(cell.get("indent", 0))
        padding = int(canvas_cfg.get("padding", 4)) + indent
        font_size = int(cell.get("fontSize", 12))
        
        # Color mapping
        bg, fg = (0, 255) if invert else (255, 0)

        # Draw cell background/outline
        if bool(cell.get("outline", False)):
            draw.rectangle([x, y, x + w, y + h], fill=bg, outline=fg)
        else:
            draw.rectangle([x, y, x + w, y + h], fill=bg)

        # Run function or fetch HA entity
        content_text = ""
        content_img = None

        entity_id = cell.get("entityId", "")
        if entity_id:
            entity_state = get_ha_entity_state(entity_id)
            if entity_state:
                # Basic text formatting for HA entity
                state = entity_state.get("state", "UNKNOWN")
                unit = entity_state["attributes"].get("unit_of_measurement", "")
                if unit:
                    content_text = f"{state}{unit}"
                else:
                    content_text = str(state)
            else:
                content_text = f"ERR:{entity_id[:10]}..."
        elif fn_name_raw:
            result = run_cell_function(fn_name_raw, w, h, indent)
            if isinstance(result, Image.Image):
                content_img = result.convert("L")
            else:
                content_text = str(result) if result is not None else ""

        # --- IMAGE BRANCH (Restored for Immich/Static) ---
        elif cell.get("staticImage"):
            try:
                path = cell.get("staticImage")
                if path.startswith("http"):
                    resp = requests.get(path, timeout=5)
                    content_img = Image.open(BytesIO(resp.content)).convert("L")
                else:
                    full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
                    content_img = Image.open(full_path).convert("L")
            except Exception as e:
                print(f"Image load error: {e}")

        if content_img is not None:
            if hasattr(content_img, "skip_scale") and content_img.skip_scale:
                px = x + (w - content_img.width) // 2
                py = y + (h - content_img.height) // 2
                if invert: content_img = ImageOps.invert(content_img)
                img.paste(content_img, (px, py))
                continue

            mode = str(cell.get("scaleMode", "fit")).lower()
            max_w, max_h = max(1, w - 2 * padding), max(1, h - 2 * padding)
            
            if mode == "fill":
                content_img = ImageOps.fit(content_img, (w - 2, h - 2))
                px, py = x + 1, y + 1
            elif mode == "none":
                content_img = content_img.crop((0, 0, min(content_img.width, max_w), min(content_img.height, max_h)))
                px, py = x + padding, y + padding
            else: # fit
                content_img.thumbnail((max_w, max_h))
                px = x + padding + (max_w - content_img.width) // 2
                py = y + padding + (max_h - content_img.height) // 2

            if invert: content_img = ImageOps.invert(content_img)
            img.paste(content_img, (px, py))
            continue

        # --- TEXT BRANCH ---
        content_text = str(result) if result is not None else str(cell.get("staticText", "") or "")
        if not content_text: continue

        # Load correct font
        is_bold = bool(cell.get("fontBold", False))
        f_path = BOLD_FONT_PATH if is_bold and os.path.exists(BOLD_FONT_PATH) else REGULAR_FONT_PATH
        font = get_font(font_size, f_path)

        # Wrap text logic
        should_wrap = bool(cell.get("wrapText", True))
        max_txt_w = max(10, w - (2 * padding))
        wrapped_lines = []
        if should_wrap:
            for para in content_text.splitlines():
                words = para.split(' ')
                line = []
                for word in words:
                    test = ' '.join(line + [word])
                    if draw.textbbox((0, 0), test, font=font)[2] <= max_txt_w or not line:
                        line.append(word)
                    else:
                        wrapped_lines.append(' '.join(line))
                        line = [word]
                wrapped_lines.append(' '.join(line))
        else:
            wrapped_lines = content_text.splitlines()

        # Vertical Alignment
        h_align = str(cell.get("hAlign", "left")).lower()
        v_align = str(cell.get("vAlign", "top")).lower()
        line_h = font_size + 2
        total_h = line_h * len(wrapped_lines)

        if v_align == "middle": ty = y + (h - total_h) // 2
        elif v_align == "bottom": ty = y + h - padding - total_h
        else: ty = y + padding

        for line in wrapped_lines:
            if ty + font_size > y + h: break
            tw = draw.textbbox((0, 0), line, font=font)[2]
            if h_align == "center": tx = x + (w - tw) // 2
            elif h_align == "right": tx = x + w - padding - tw
            else: tx = x + padding

            draw.text((tx, ty), line, fill=fg, font=font)
            ty += line_h

    return img

@app.route("/get_dashboard_image")
def get_dashboard_image():
    if not os.path.exists(LAYOUT_JSON_PATH):
        # Nothing saved yet – return 404 instead of raising
        return "No layout JSON found", 404

    with open(LAYOUT_JSON_PATH, "r", encoding="utf-8") as f:
        layout = json.load(f)

    img = render_layout_to_image(layout)
    img = img.rotate(180)

    # Save to a temporary file and send it
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp, format="PNG")
    tmp.flush()
    tmp.close()

    return send_file(tmp.name, mimetype="image/png")

# -- PUSHING ---
@app.route("/force_push", methods=["POST"])
def force_push():
    """Manually trigger the background worker to push an update."""
    push_event.set()
    return jsonify({"status": "pushed"})

def push_worker():
    while True:
        try:
            if os.path.exists(LAYOUT_JSON_PATH):
                with open(LAYOUT_JSON_PATH, "r") as f:
                    layout = json.load(f)
                
                interval = int(layout.get("canvas", {}).get("refreshInterval", 1200))
                
                # Render and Push
                img = render_layout_to_image(layout)
                img = img.rotate(180)
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                if RPI_ENDPOINT:
                    requests.post(RPI_ENDPOINT, files={'image': ('dash.png', img_byte_arr, 'image/png')}, timeout=10)
                    print(f"Pushed to Pi. Next scheduled refresh in {interval}s", flush=True)
                
                # This is the magic part: wait for 'interval' seconds OR until push_event.set() is called
                woken_up = push_event.wait(timeout=interval)
                if woken_up:
                    print("Worker woken up early (Layout updated or Printer event)!", flush=True)
                    push_event.clear()
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Push worker error: {e}", flush=True)
            time.sleep(10)

# --- MAIN ---
if __name__ == "__main__":
    thread = threading.Thread(target=push_worker, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5001)
