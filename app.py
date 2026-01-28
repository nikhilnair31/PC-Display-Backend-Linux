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
WEBHOOK_SECRET = os.environ.get("OCTO_WEBHOOK_SECRET", "SOME_LONG_RANDOM_STRING")
RPI_ENDPOINT = os.environ.get("RPI_URL")

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
        x = int(cell["x"])
        y = int(cell["y"])
        w = int(cell["w"])
        h = int(cell["h"])

        name = str(cell.get("name", ""))
        fn_name_raw = str(cell.get("fnName", "") or "")
        invert = bool(cell.get("invert", False))
        static_text = str(cell.get("staticText", "") or "")
        static_image_path = cell.get("staticImage") or ""
    
        padding = int(canvas_cfg.get("padding", 4))
        indent = int(cell.get("indent", 0))
        padding = padding + indent
        
        font_size = int(cell.get("fontSize", 12))
        is_bold = bool(cell.get("fontBold", False))
        is_italic = bool(cell.get("fontItalic", False))
        if is_bold and is_italic and os.path.exists(BOLD_ITALIC_FONT_PATH):
            font = get_font(font_size, BOLD_ITALIC_FONT_PATH)
        elif is_bold and os.path.exists(BOLD_FONT_PATH):
            font = get_font(font_size, BOLD_FONT_PATH)
        elif is_italic and os.path.exists(ITALIC_FONT_PATH):
            font = get_font(font_size, ITALIC_FONT_PATH)
        else:
            font = get_font(font_size, REGULAR_FONT_PATH)

        # Set color based on invert
        bg = 0 if invert else 255
        fg = 255 if invert else 0

        # cell background
        outline_flag = bool(cell.get("outline", False))
        draw.rectangle(
            [x, y, x + w, y + h],
            fill=bg,
            outline=fg if outline_flag else bg
        )

        # run function if provided
        result = run_cell_function(fn_name_raw, w, h, indent) if fn_name_raw else None

        # image branch: fn image or static image
        content_img = None
        if isinstance(result, Image.Image):
            content_img = result.convert("L")
        elif static_image_path:
            try:
                if static_image_path.startswith("http://") or static_image_path.startswith("https://"):
                    resp_img = requests.get(static_image_path, timeout=5)
                    resp_img.raise_for_status()
                    content_img = Image.open(BytesIO(resp_img.content)).convert("L")
                else:
                    path = static_image_path
                    if not os.path.isabs(path):
                        path = os.path.join(BASE_DIR, path)
                    content_img = Image.open(path).convert("L")
            except Exception as e:
                print("static image load error:", static_image_path, e)
                content_img = None
        if content_img is not None:
            # If function says "don't scale", paste raw and skip all scaling steps
            if hasattr(content_img, "skip_scale") and content_img.skip_scale:
                paste_x = x + (w - content_img.width) // 2
                paste_y = y + (h - content_img.height) // 2
                if invert:
                    content_img = ImageOps.invert(content_img)
                img.paste(content_img, (paste_x, paste_y))
                continue
            
            # Cell-level override; fall back to "fit"
            scale_mode = str(cell.get("scaleMode", "") or "").lower()
            if scale_mode not in ("fit", "fill", "none"):
                scale_mode = "fit"

            max_w = max(1, w - 2 * padding)
            max_h = max(1, h - 2 * padding)

            if scale_mode == "fill":
                inner_x = x + 1
                inner_y = y + 1
                inner_w = max(1, w - 2)
                inner_h = max(1, h - 2)

                content_img = ImageOps.fit(content_img, (inner_w, inner_h))
                paste_x, paste_y = inner_x, inner_y

            elif scale_mode == "none":
                content_img = content_img.crop(
                    (0, 0, min(content_img.width, max_w), min(content_img.height, max_h))
                )
                paste_x = x + padding
                paste_y = y + padding

            else:  # "fit"
                content_img.thumbnail((max_w, max_h))
                paste_x = x + padding + (max_w - content_img.width) // 2
                paste_y = y + padding + (max_h - content_img.height) // 2

            if invert:
                content_img = ImageOps.invert(content_img)

            img.paste(content_img, (paste_x, paste_y))
            continue  # done with this cell

        # text branch: function text OR static text
        if result is None or isinstance(result, Image.Image):
            content_text = static_text
        else:
            content_text = str(result) if str(result) else static_text
        if not content_text:
            # no fn text, no static text -> nothing to draw
            continue

        # Alignment options from layout, with defaults
        h_align = str(cell.get("hAlign", "left")).lower()
        v_align = str(cell.get("vAlign", "top")).lower()
        if h_align not in ("left", "center", "right"):
            h_align = "left"
        if v_align not in ("top", "middle", "bottom"):
            v_align = "top"

        lines = content_text.splitlines()
        line_height = font_size + 2
        num_lines = len(lines)
        total_height = line_height * num_lines

        # Vertical alignment: compute first line's y
        if v_align == "top":
            y_start = y + padding
        elif v_align == "middle":
            y_start = y + (h - total_height) // 2
        else:  # "bottom"
            y_start = y + h - padding - total_height

        y_text = y_start

        for line in lines:
            if y_text > y + h - padding:
                break

            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]

            if h_align == "left":
                x_text = x + padding
            elif h_align == "center":
                x_text = x + (w - text_w) // 2
            else:  # "right"
                x_text = x + w - padding - text_w

            # Simulate bold if needed and no bold font file exists
            if is_bold and not os.path.exists(BOLD_FONT_PATH):
                draw.text((x_text + 1, y_text), line, fill=fg, font=font)

            draw.text((x_text, y_text), line, fill=fg, font=font)
            y_text += line_height

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
