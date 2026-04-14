# app.py

import re, os, sys, json, time, random, psutil, subprocess, requests, tempfile, importlib, inspect, traceback, threading
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from flask import Flask, send_file, request, jsonify
from typing import Any, Dict, Callable
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

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
RPI_ENDPOINT = os.environ.get("RPI_URL")

functions_module = importlib.import_module("functions")
FUNCTION_MAP = {
    name: fn
    for name, fn in inspect.getmembers(functions_module, inspect.isfunction)
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

        push_event.set() 
        return jsonify({"status": "ok"})

    if not os.path.exists(LAYOUT_JSON_PATH):
        return jsonify({"canvas": None, "cells": []})

    try:
        with open(LAYOUT_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Failed to read layout:", e, flush=True)
        return jsonify({"canvas": None, "cells": []})

    return jsonify(data)

# --- HOME ASSISTANT INTEGRATION ---
@app.route("/api/ha_entities", methods=["GET"])
def get_ha_entities():
    ha_url = os.environ.get("HA_URL")
    ha_token = os.environ.get("HA_TOKEN")
    
    if not ha_url or not ha_token:
        return jsonify({"error": "HA config missing"}), 400

    url = f"{ha_url.rstrip('/')}/api/states"
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            entities = [
                {
                    "id": e["entity_id"],
                    "name": e.get("attributes", {}).get("friendly_name", ""),
                    "state": e.get("state", "") # ADD THIS LINE
                }
                for e in data
            ]
            entities.sort(key=lambda x: x["id"])
            return jsonify(entities)
        else:
            return jsonify({"error": f"HA returned {resp.status_code}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    filename = f"{name}_{int(time.time())}{ext}"
    save_path = os.path.join(STATIC_IMG_DIR, filename)
    file.save(save_path)

    rel_path = os.path.relpath(save_path, BASE_DIR)
    return jsonify({"path": rel_path})

def get_font(size: int, fontpath: str) -> ImageFont.ImageFont:
    size = max(6, min(200, int(size)))
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

def run_cell_function(fn_name_raw: str, w: int, h: int, i: int, cell_dict: dict) -> Any:
    fn_name = strip_fn_name(fn_name_raw)
    if not fn_name:
        return None

    fn = FUNCTION_MAP.get(fn_name)
    if fn is None:
        return f"ERR {fn_name}: NOT_FOUND"

    try:
        sig = inspect.signature(fn)
        if 'cell' in sig.parameters:
            return fn(w, h, i, cell=cell_dict)
        else:
            return fn(w, h, i)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"ERROR in function '{fn_name}': {e!r}\n{tb}", flush=True)
        return f"ERR: {e.__class__.__name__}"

def break_word_py(word: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_w: int, lines: list) -> str:
    current_str = ""
    for char in word:
        test_str = current_str + char
        if draw.textbbox((0, 0), test_str, font=font)[2] > max_w and current_str != "":
            lines.append(current_str)
            current_str = char
        else:
            current_str = test_str
    return current_str

def get_wrapped_text(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_w: int) -> list:
    lines = []
    for para in str(text).splitlines():
        if not para:
            lines.append("")
            continue
        words = para.split(' ')
        line = ""
        for word in words:
            test_line = line + ("" if not line else " ") + word
            if draw.textbbox((0, 0), test_line, font=font)[2] <= max_w:
                line = test_line
            else:
                if line:
                    lines.append(line)
                    line = word
                    # Check if the individual word also exceeds the max width
                    if draw.textbbox((0, 0), word, font=font)[2] > max_w:
                        line = break_word_py(word, font, draw, max_w, lines)
                else:
                    line = break_word_py(word, font, draw, max_w, lines)
        if line:
            lines.append(line)
    return lines

def render_layout_to_image(layout: dict) -> Image.Image:
    canvas_cfg = layout.get("canvas", {})
    width = int(canvas_cfg.get("width", 480))
    height = int(canvas_cfg.get("height", 800))

    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)

    cells = layout.get("cells", [])
    for cell in cells:
        round_digits = cell.get("round")
        prefix = str(cell.get("prefix", ""))
        suffix = str(cell.get("suffix", ""))

        x, y, w, h = int(cell["x"]), int(cell["y"]), int(cell["w"]), int(cell["h"])
        invert = bool(cell.get("invert", False))
        indent = int(cell.get("indent", 0))
        padding = int(canvas_cfg.get("padding", 4)) + indent
        font_size = int(cell.get("fontSize", 12))
        
        bg, fg = (0, 255) if invert else (255, 0)

        if bool(cell.get("outline", False)):
            draw.rectangle([x, y, x + w, y + h], fill=bg, outline=fg)
        else:
            draw.rectangle([x, y, x + w, y + h], fill=bg)

        fn_name_raw = str(cell.get("fnName", "") or "").strip()

        # HA Fallback
        if not fn_name_raw and cell.get("haEntityId"):
            ent = str(cell.get("haEntityId"))
            if ent.startswith("camera.") or ent.startswith("image."):
                fn_name_raw = "get_ha_image"
            else:
                fn_name_raw = "get_ha_state"

        result = run_cell_function(fn_name_raw, w, h, indent, cell) if fn_name_raw else None
        
        # --- IMAGE BRANCH ---
        content_img = None
        if not result and cell.get("haEntityId"):
            ent = str(cell.get("haEntityId"))
            if ent.startswith("weather."):
                # 1. Get the actual icon URL using the helper in functions.py
                icon_url = functions_module.get_ha_weather_icon(ent)
                try:
                    resp = requests.get(icon_url, timeout=5)
                    content_img = Image.open(BytesIO(resp.content)).convert("L")
                except Exception as e:
                    print(f"Weather icon download failed: {e}")
        elif isinstance(result, Image.Image):
            content_img = result.convert("L")
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
        # Apply rounding if specified and content is numeric
        if round_digits is not None:
            try:
                # Remove any existing % or spaces before trying to float
                clean_text = content_text.replace('%', '').strip()
                num = float(clean_text)
                content_text = f"{num:.{round_digits}f}"
            except (ValueError, TypeError):
                pass # Not a number, skip rounding

        # Then apply prefix/suffix
        content_text = prefix + content_text + suffix
        # content_text = str(result) if result is not None else str(cell.get("staticText", "") or "")
        # if not content_text: continue

        # Text Transformations
        text_transform = str(cell.get("textTransform", "none")).lower()
        if text_transform == "uppercase":
            content_text = content_text.upper()
        elif text_transform == "lowercase":
            content_text = content_text.lower()
        elif text_transform == "capitalize":
            content_text = content_text.capitalize()
        elif text_transform == "titlecase":
            content_text = content_text.title()

        # Load correct font path
        is_bold = bool(cell.get("fontBold", False))
        is_italic = bool(cell.get("fontItalic", False))
        if is_bold and is_italic: f_path = BOLD_ITALIC_FONT_PATH
        elif is_bold: f_path = BOLD_FONT_PATH
        elif is_italic: f_path = ITALIC_FONT_PATH
        else: f_path = REGULAR_FONT_PATH
        
        if not os.path.exists(f_path):
            f_path = REGULAR_FONT_PATH

        # Wrapping and Auto Sizing
        auto_size = bool(cell.get("autoTextSize", False))
        should_wrap = bool(cell.get("wrapText", True))
        max_txt_w = max(10, w - (2 * padding))
        max_txt_h = max(10, h - (2 * padding))
        wrapped_lines = []
        font = None

        if auto_size:
            best_size = min(max_txt_h, 200)
            min_size = 6
            while best_size >= min_size:
                font = get_font(best_size, f_path)
                if should_wrap:
                    wrapped_lines = get_wrapped_text(content_text, font, draw, max_txt_w)
                else:
                    wrapped_lines = content_text.splitlines()

                line_h = best_size + 2
                total_h = line_h * len(wrapped_lines)
                max_line_w = max([draw.textbbox((0, 0), l, font=font)[2] for l in wrapped_lines] + [0])

                if total_h <= max_txt_h and max_line_w <= max_txt_w:
                    break
                best_size -= 1
            font_size = best_size
        else:
            font = get_font(font_size, f_path)
            if should_wrap:
                wrapped_lines = get_wrapped_text(content_text, font, draw, max_txt_w)
            else:
                wrapped_lines = content_text.splitlines()

        # Aligns
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
        return "No layout JSON found", 404

    with open(LAYOUT_JSON_PATH, "r", encoding="utf-8") as f:
        layout = json.load(f)

    img = render_layout_to_image(layout)
    img = img.rotate(180)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp, format="PNG")
    tmp.flush()
    tmp.close()

    return send_file(tmp.name, mimetype="image/png")

@app.route("/force_push", methods=["POST"])
def force_push():
    push_event.set()
    return jsonify({"status": "pushed"})

def push_worker():
    while True:
        try:
            if os.path.exists(LAYOUT_JSON_PATH):
                with open(LAYOUT_JSON_PATH, "r") as f:
                    layout = json.load(f)
                
                interval = int(layout.get("canvas", {}).get("refreshInterval", 1200))
                
                img = render_layout_to_image(layout)
                img = img.rotate(180)
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                if RPI_ENDPOINT:
                    requests.post(RPI_ENDPOINT, files={'image': ('dash.png', img_byte_arr, 'image/png')}, timeout=10)
                    print(f"Pushed to Pi. Next scheduled refresh in {interval}s", flush=True)
                
                woken_up = push_event.wait(timeout=interval)
                if woken_up:
                    print("Worker woken up early (Layout updated or Printer event)!", flush=True)
                    push_event.clear()
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Push worker error: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    thread = threading.Thread(target=push_worker, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5001)