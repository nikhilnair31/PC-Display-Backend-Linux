# E-Ink Dashboard

Server-side backend for a Waveshare 7.5" e-paper dashboard. Renders a layout of cells (text, HA entities, images) into a grayscale PNG and pushes it to a Raspberry Pi over HTTP.

**Frontend (RPI):** [PC-Display-Frontend-Linux](https://github.com/nikhilnair31/PC-Display-Frontend-Linux)

## Architecture

```
[Home Assistant] --> [app.py :5001] --POST image--> [RPI receiver :5002] --> [e-Paper display]
                         ^
                         |
                   canvas_layout.json ( edited via /canvas UI )
```

- **app.py** — Flask server. Renders layout to image, pushes to Pi on a timer or layout change.
- **functions.py** — Content helpers (`get_ha_state`, `get_ha_image`, `get_ha_weather_icon`). Skips render if HA is unreachable.
- **canvas_layout.json** — The layout definition. Edit via the `/canvas` web UI.
- **canvas.html** — Drag-and-drop layout editor served at `/canvas`.

## Server Setup

### 1. Install dependencies

```bash
cd /home/nikhil/Projects/PC_Display
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env` in the project root:

```
HA_URL=https://your-ha-instance.duckdns.org/
HA_TOKEN=your_long_lived_access_token
RPI_URL=http://<pi_ip>:5002/receive_image
```

### 3. Firewall

```bash
sudo ufw allow 5001/tcp
```

### 4. Systemd service

```bash
sudo cp dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dashboard.service
```

### 5. Create layout

Visit `http://<server_ip>:5001/canvas` and build your layout.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/canvas` | GET | Layout editor UI |
| `/canvas_layout` | GET/POST | Read or save layout JSON |
| `/get_dashboard_image` | GET | Render and return the current dashboard as PNG |
| `/api/ha_entities` | GET | List all HA entities (for the canvas editor) |
| `/upload_static_image` | POST | Upload an image for use in cells |
| `/force_push` | POST | Immediately push the current layout to the Pi |

## RPI Setup

See the [frontend repo](https://github.com/nikhilnair31/PC-Display-Frontend-Linux) for Pi-side setup. The Pi runs a polling script that fetches `/get_dashboard_image` from this server and writes it to the e-paper display.

## Notes

- Icons: [icons8.com/icons](https://icons8.com/icons/)
- Font: Helmet-Regular.ttf (included in repo)
- If HA is unreachable, the server skips rendering entirely — the Pi keeps showing the last good image.
