# functions.py

import os, re, json, time, random, psutil, subprocess, requests, tempfile, datetime
from statistics import (
    mean
)
from dotenv import (
    load_dotenv
)
from datetime import (
    date
)
from math import (
    ceil
)
from io import (
    BytesIO
)
from statistics import (
    mean
)
from dotenv import (
    load_dotenv
)
from PIL import (
    Image,
    ImageFont,
    ImageDraw
)
from typing import (
    Any, Dict, Callable
)

load_dotenv()

IMMICH_UPLOAD_PATH = "/mnt/storage/immich-app/photos"
IMMICH_API = os.getenv("IMMICH_API", "http://localhost:2283/api")
IMMICH_KEY = os.getenv("IMMICH_API_KEY")
HEADERS = {"x-api-key": IMMICH_KEY}
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION")
FONT_PATH = "Helmet-Regular.ttf"
_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
PRINTER_STATE_PATH = os.path.join(os.path.dirname(__file__), "printer_state.json")

# --- UTLITIES ---
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
def get_time_date(cell_w: int, cell_h: int, cell_i: int) -> str:
    now = datetime.datetime.now()
    header = now.strftime("%a %d %b")
    return header

def get_weather_data(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        cur = resp["current"]
        fc = resp["forecast"]["forecastday"][0]["day"]
        ast = resp["forecast"]["forecastday"][0]["astro"]
        hours = resp["forecast"]["forecastday"][0]["hour"]

        # Basic conditions
        cond = cur["condition"]["text"]
        temp_c = int(cur["temp_c"])
        feelslike_c = int(cur["feelslike_c"])
        high_c = int(fc["maxtemp_c"])
        low_c  = int(fc["mintemp_c"])
        sunset_time = ast.get("sunset")

        # Hour range
        start_hour = 8
        end_hour = 23

        # Helper to extract hour from "2025-11-26 03:00"
        def extract_hour(h):
            return int(h["time"].split(" ")[1].split(":")[0])

        # Get average rain chance
        rain_vals = [h["chance_of_rain"] for h in hours
                     if start_hour <= extract_hour(h) <= end_hour]
        avg_rain_chance = mean(rain_vals) if rain_vals else 0

        # Get average snow chance
        snow_vals = [h["chance_of_snow"] for h in hours
                     if start_hour <= extract_hour(h) <= end_hour]
        avg_snow_chance = mean(snow_vals) if snow_vals else 0

        # Build summary
        pieces = [
            f"Now: {cond}",
            f"{temp_c}°C (~{feelslike_c}°C)",
            f"H: {high_c}°C",
            f"L: {low_c}°C",
            f"Rain ~{int(avg_rain_chance)}%",
            f"Snow ~{int(avg_snow_chance)}%",
            f"Sunset: {sunset_time}",
        ]

        return "\n".join(pieces)
    except Exception as e:
        return f"Weather error: {e}"

def get_temp_high_low(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        fc = resp["forecast"]["forecastday"][0]["day"]
        
        high_c = int(fc["maxtemp_c"])
        low_c  = int(fc["mintemp_c"])

        return f"{high_c} to {low_c} °C"
    except Exception as e:
        return f"Weather error: {e}"

def get_sunset(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        ast = resp["forecast"]["forecastday"][0]["astro"]
        
        sunset_time = ast.get("sunset")

        return f"{sunset_time}"
    except Exception as e:
        return f"Weather error: {e}"

def get_curr_condition_icon(cell_w: int, cell_h: int, cell_i: int) -> Image.Image:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        icon_path = resp["current"]["condition"]["icon"]  # e.g. //cdn.weatherapi.com/...
        if icon_path.startswith("//"):
            icon_url = "https:" + icon_path
        else:
            icon_url = icon_path

        img_bytes = requests.get(icon_url, timeout=5).content
        img = Image.open(BytesIO(img_bytes)).convert("RGBA")

        # Resize cleanly to fit cell
        img = img.resize((cell_w, cell_h), Image.LANCZOS)

        # Scale by 1.2×
        scale = 2
        new_w = int(cell_w * scale)
        new_h = int(cell_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        img.skip_scale = True

        return img

    except Exception as e:
        # Return a small blank error image instead of a string
        err_img = Image.new("RGBA", (cell_w, cell_h), (255, 0, 0, 255))
        return err_img

def get_curr_condition(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        cur = resp["current"]
        
        cond = cur["condition"]["text"]
        
        return f"{cond}"
    except Exception as e:
        return f"Weather error: {e}"

def get_temperature(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        cur = resp["current"]
        
        temp_c = int(cur["temp_c"])
        feelslike_c = int(cur["feelslike_c"])
        
        return f"{temp_c}(~{feelslike_c})°C)"
    except Exception as e:
        return f"Weather error: {e}"

def get_rain_perc(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        hours = resp["forecast"]["forecastday"][0]["hour"]

        # Hour range
        start_hour = 8
        end_hour = 23

        # Helper to extract hour from "2025-11-26 03:00"
        def extract_hour(h):
            return int(h["time"].split(" ")[1].split(":")[0])

        # Get average rain chance
        rain_vals = [h["chance_of_rain"] for h in hours
                     if start_hour <= extract_hour(h) <= end_hour]
        avg_rain_chance = mean(rain_vals) if rain_vals else 0
        
        return f"~{int(avg_rain_chance)}%"
    except Exception as e:
        return f"Weather error: {e}"

def get_snow_perc(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        url = (
            "https://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}"
            f"&q={WEATHER_LOCATION}"
            f"&days=1&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=5).json()

        hours = resp["forecast"]["forecastday"][0]["hour"]

        # Hour range
        start_hour = 8
        end_hour = 23

        # Helper to extract hour from "2025-11-26 03:00"
        def extract_hour(h):
            return int(h["time"].split(" ")[1].split(":")[0])

        snow_vals = [h["chance_of_snow"] for h in hours
                     if start_hour <= extract_hour(h) <= end_hour]
        avg_snow_chance = mean(snow_vals) if snow_vals else 0
        
        return f"~{int(avg_snow_chance)}%"
    except Exception as e:
        return f"Weather error: {e}"

def get_emoji(cell_w: int, cell_h: int, cell_i: int) -> str:
    emoji = random.choice(["(·‿·)", "(￣ー￣)", "(ಠ_ಠ)", "(。_。)", "(•_•)"])
    return emoji

def get_pc_status(cell_w: int, cell_h: int, cell_i: int) -> str:
    # CPU TEMPERATURE
    cpu_temp = None
    try:
        temps = psutil.sensors_temperatures()
        if "coretemp" in temps:
            # pick the first temperature sensor
            cpu_temp = int(temps["coretemp"][0].current)
    except:
        pass
    if cpu_temp is None:
        try:
            out = subprocess.check_output(["sensors"]).decode()
            m = re.search(r"(?i)Package.*?\+(\d+)", out)
            if m:
                cpu_temp = int(m.group(1))
        except:
            cpu_temp = 0
    if cpu_temp is None:
        cpu_temp = 0

    # GPU TEMPERATURE
    gpu_temp = None
    try:
        # NVIDIA (nvidia-smi)
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if out:
            gpu_temp = int(out)
    except:
        pass
    if gpu_temp is None:
        gpu_temp = 0

    # MEMORY (GB)
    mem = psutil.virtual_memory().used / (1024**3)
    mem_gb = int(mem)

    # FINAL FORMAT
    return f"CPU {cpu_temp}°C\nGPU {gpu_temp}°C\nMEM {mem_gb}G"

def get_cpu_temp(cell_w: int, cell_h: int, cell_i: int) -> str:
    # CPU TEMPERATURE
    cpu_temp = None
    try:
        temps = psutil.sensors_temperatures()
        if "coretemp" in temps:
            # pick the first temperature sensor
            cpu_temp = int(temps["coretemp"][0].current)
    except:
        pass
    if cpu_temp is None:
        try:
            out = subprocess.check_output(["sensors"]).decode()
            m = re.search(r"(?i)Package.*?\+(\d+)", out)
            if m:
                cpu_temp = int(m.group(1))
        except:
            cpu_temp = 0
    if cpu_temp is None:
        cpu_temp = 0
    
    return f"{cpu_temp}°C"

def get_gpu_temp(cell_w: int, cell_h: int, cell_i: int) -> str:
    # GPU TEMPERATURE
    gpu_temp = None
    try:
        # NVIDIA (nvidia-smi)
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if out:
            gpu_temp = int(out)
    except:
        pass
    if gpu_temp is None:
        gpu_temp = 0

    # MEMORY (GB)
    mem = psutil.virtual_memory().used / (1024**3)
    mem_gb = int(mem)

    # FINAL FORMAT
    return f"{gpu_temp}°C"

def get_mem_amount(cell_w: int, cell_h: int, cell_i: int) -> str:
    # MEMORY (GB)
    mem = psutil.virtual_memory().used / (1024**3)
    mem_gb = int(mem)

    # FINAL FORMAT
    return f"{mem_gb}G"

def get_pc_ip_address(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        out = subprocess.check_output(["hostname", "-I"]).decode().strip()
        return out.split()[0]  # first IP, same behavior people usually want
    except:
        return "0.0.0.0"

def get_random_labeled_face(cell_w: int, cell_h: int, cell_i: int) -> Image.Image:
    # 1) Get all people
    people_resp = requests.get(f"{IMMICH_API}/people", headers=HEADERS, timeout=5)
    if people_resp.status_code != 200:
        return "Failed to fetch people", 500

    people_data = people_resp.json()
    people = people_data.get("people", [])

    # 2) Filter allowed names
    ALLOWED_NAMES = {"B", "Me", "Nik", "Nikhil", "Shivani"}
    selected_people = [p for p in people if p.get("name") in ALLOWED_NAMES]

    if not selected_people:
        return "No allowed labeled faces found", 404

    person_ids = [p["id"] for p in selected_people]

    # 3) Ask Immich for random assets for these people
    search_body = {
        "personIds": person_ids,
        "size": 50,          # up to you; 1–1000 allowed
        "type": "IMAGE",
        "withPeople": True,
        "withDeleted": False,
        "withArchived": False,
    }

    random_resp = requests.post(
        f"{IMMICH_API}/search/random",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=search_body,
        timeout=10,
    )

    if random_resp.status_code != 200:
        return "Failed to search random assets", 500

    data = random_resp.json()

    # searchRandom returns a plain list of asset objects
    if not isinstance(data, list) or not data:
        return "No face assets found for allowed people", 404

    asset = random.choice(data)
    asset_id = asset["id"]

    # 4) Fetch thumbnail
    thumb_url = f"{IMMICH_API}/assets/{asset_id}/thumbnail"
    img_resp = requests.get(thumb_url, headers=HEADERS, timeout=10)

    if img_resp.status_code != 200:
        return "Failed to fetch thumbnail", 404

    img = Image.open(BytesIO(img_resp.content)).convert("L")
    return img

def render_life_progress(cell_w: int, cell_h: int, cell_i: int) -> Image.Image:
    try:
        birthdate = date(1998, 8, 31)
        deathdate = date(birthdate.year + 80, birthdate.month, birthdate.day)
        today = max(min(date.today(), deathdate), birthdate)

        total_days = (deathdate - birthdate).days
        days_elapsed = (today - birthdate).days
        perc = days_elapsed / total_days
        perc_str = f"{perc * 100:.2f}% of life over"

        # match cell size exactly
        img = Image.new("L", (cell_w, cell_h), 255)
        draw = ImageDraw.Draw(img)

        # protect borders by at least 1 pixel
        inset = 1

        # adaptive font
        font = get_font(max(10, int(cell_h * 0.22)))

        # text
        draw.text((8 + inset, 5 + inset), perc_str, font=font, fill=0)

        # bar
        margin = inset + int(cell_h * 0.1)
        bar_top = int(cell_h * 0.5)
        bar_height = int(cell_h * 0.15)
        bar_left = margin
        bar_right = cell_w - margin - inset
        bar_bottom = bar_top + bar_height

        draw.rectangle([bar_left, bar_top, bar_right, bar_bottom],
                       outline=0, fill=255)

        filled = bar_left + int((bar_right - bar_left) * perc)
        draw.rectangle([bar_left, bar_top, filled, bar_bottom],
                       outline=0, fill=0)

        img = img.convert("1")
        return img

    except Exception as e:
        print("e:", e)
        return None

def get_year_left_text(cell_w: int, cell_h: int, cell_i: int) -> Image.Image:
    try:
        today = date.today()
        curr_year = today.year

        # Start and end of the current year
        start = date(curr_year, 1, 1)
        end = date(curr_year + 1, 1, 1)  # Jan 1 of next year

        total_days = (end - start).days
        days_elapsed = (today - start).days + 1  # inclusive of today

        perc_done = days_elapsed / total_days
        perc_left = 1.0 - perc_done

        perc_str = f"{perc_done * 100:.2f}% of {curr_year} done"
        
        return perc_str

    except Exception as e:
        print("get_year_left error:", e)
        return None

def get_year_left_bar(cell_w: int, cell_h: int, cell_i: int) -> Image.Image:
    try:
        today = date.today()
        curr_year = today.year

        # Start and end of the current year
        start = date(curr_year, 1, 1)
        end = date(curr_year + 1, 1, 1)  # Jan 1 of next year

        total_days = (end - start).days
        days_elapsed = (today - start).days + 1  # inclusive of today

        perc_done = days_elapsed / total_days
        perc_left = 1.0 - perc_done

        perc_str = f"{perc_done * 100:.2f}% of {curr_year} done"

        img = Image.new("L", (cell_w, cell_h), 255)
        draw = ImageDraw.Draw(img)

        # Progress bar (showing DONE portion)
        margin = cell_i + int(cell_h * 0.1)
        bar_top = int(cell_h * 0.5)
        bar_height = int(cell_h * 0.15)
        bar_left = margin
        bar_right = cell_w - margin - cell_i
        bar_bottom = bar_top + bar_height

        # Bar outline
        draw.rectangle([bar_left, bar_top, bar_right, bar_bottom],
                       outline=0, fill=255)

        # Filled portion for elapsed (done)
        filled = bar_left + int((bar_right - bar_left) * perc_done)
        draw.rectangle([bar_left, bar_top, filled, bar_bottom],
                       outline=0, fill=0)

        img = img.convert("1")
        img.info["scale_mode"] = "fill"  # so it fills the cell if you want
        return img

    except Exception as e:
        print("get_year_left error:", e)
        return None

def get_printer_status(cell_w: int, cell_h: int, cell_i: int) -> str:
    try:
        with open(PRINTER_STATE_PATH, "r") as f:
            s = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "OFFLINE"

    state = str(s.get("state", "UNKNOWN")).upper()
    progress = s.get("progress")
    time_remaining = s.get("time_remaining")
    updated_at = s.get("updated_at", 0)

    # OctoPrint uses these states while a job is active
    active_states = ["STARTED", "RESUMED", "UPDATE", "PRINTING"]

    if state in active_states:
        # Build the status parts
        parts = ["PRINTING"] # We can normalize the display text to "PRINTING"
        
        if progress is not None:
            parts.append(f"{int(progress)}%")
            
        if time_remaining is not None and time_remaining > 0:
            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            parts.append(f"{minutes}m {seconds:02d}s")
            
        return " • ".join(parts)

    if state == "COMPLETED":
        now = time.time()
        # If finished more than 5 minutes ago, show IDLE
        if now - updated_at > 300:
            return "IDLE"
        return "FINISHED"

    if state in ["FAILED", "CANCELED", "ERROR"]:
        return f"ERR: {state}"

    return state if state != "UNKNOWN" else "IDLE"
