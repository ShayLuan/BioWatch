#!/usr/bin/env python3
"""
BioWatch — ILI9341 320×240 dashboard for Pi Zero W

Layout (320×240)
─────────────────────────────────────────────────────
  Y=  0  Header bar  28px  — title + clock
  Y= 28  Dots strip  22px  — 4 flag-level dots
  Y= 50  ├──stats──┬──────graph──────┤
         │ 130px   │    190px        │  130px tall
  Y=180  └─────────┴─────────────────┘
  Y=180  Action strip  60px  — tier message / cleaning steps

Wiring (Pi Zero W SPI0)
────────────────────────
  GPIO 11  CLK/SCK → ILI9341 CLK
  GPIO 10  MOSI    → ILI9341 MOSI/SDA
  GPIO  8  CE0     → ILI9341 CS
  GPIO 24  D24     → ILI9341 DC
  GPIO 25  D25     → ILI9341 RST
  3.3 V            → VCC + LED
  GND              → GND

Install
───────
  sudo raspi-config → Interface Options → SPI → enable → reboot
  pip3 install adafruit-circuitpython-rgb-display adafruit-blinka \
               pillow websockets

Run alongside server
─────────────────────
  # Server is on the Legion: change SERVER_WS below to its IP.
  # If Pi IS the server, keep localhost.
"""

import asyncio, json, time
from collections import deque
from datetime import datetime

import websockets
from PIL import Image, ImageDraw, ImageFont

import board, busio, digitalio
import adafruit_rgb_display.ili9341 as ili9341

# ── Config ──────────────────────────────────────────────────────────────────
SERVER_WS = "ws://192.168.43.119:8000/ws/dashboard"  # Legion IP — change if Pi is server

W, H = 320, 240

# Layout
HDR_H    = 28      # header bar
DOTS_H   = 22      # flag dots strip
MAIN_Y   = HDR_H + DOTS_H          # 50
MAIN_H   = 130
STAT_W   = 130
GRAPH_X  = STAT_W
GRAPH_W  = W - STAT_W              # 190
ACTION_Y = MAIN_Y + MAIN_H         # 180
ACTION_H = H - ACTION_Y            # 60

TURB_GRAPH_MAX  = 20.0
TURB_FLAG_NTU   = 4.5
GRAPH_SAMPLES   = GRAPH_W

# ── Colours ─────────────────────────────────────────────────────────────────
BG      = (10,  10,  20)
PANEL   = (20,  20,  40)
WHITE   = (255, 255, 255)
GREY    = (110, 110, 130)
CYAN    = (0,   210, 255)
GREEN   = (50,  220, 110)
YELLOW  = (255, 210, 0)
ORANGE  = (255, 130, 0)
RED     = (255, 45,  45)
GRAPH_LINE = (0, 170, 230)
EMPTY_DOT  = (40,  40,  60)

TIER_COL = {
    "passed": GREEN,
    "warn":   YELLOW,
    "warn2":  ORANGE,
    "panic":  RED,
}
TIER_LABEL = {
    "passed": "PASSED",
    "warn":   "WARN",
    "warn2":  "WARN LVL 2",
    "panic":  "PANIC",
}

def flag_dot_color(flag_num: int):
    if flag_num >= 5: return RED
    if flag_num == 4: return ORANGE
    if flag_num == 3: return YELLOW
    return WHITE

def get_dots(count: int):
    """Return list of 4 (color, lit) tuples."""
    if count == 0:
        return [(EMPTY_DOT, False)] * 4
    start = max(1, count - 3)
    nums  = list(range(start, count + 1))
    dots  = [(EMPTY_DOT, False)] * (4 - len(nums))
    dots += [(flag_dot_color(n), True) for n in nums]
    return dots

# ── Display init ─────────────────────────────────────────────────────────────
spi     = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
cs      = digitalio.DigitalInOut(board.CE0)
dc      = digitalio.DigitalInOut(board.D24)
rst     = digitalio.DigitalInOut(board.D25)
display = ili9341.ILI9341(spi, cs=cs, dc=dc, rst=rst,
                           width=W, height=H, baudrate=16_000_000)

# ── Fonts ────────────────────────────────────────────────────────────────────
_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"
def _f(size, bold=False):
    try:    return ImageFont.truetype(_FONT.format("-Bold" if bold else ""), size)
    except: return ImageFont.load_default()

fnt_big  = _f(32, bold=True)
fnt_med  = _f(18, bold=True)
fnt_sm   = _f(13)
fnt_tiny = _f(11)

# ── State ────────────────────────────────────────────────────────────────────
turb_buf = deque([0.0] * GRAPH_SAMPLES, maxlen=GRAPH_SAMPLES)

state = {
    "temp":   None,
    "turb":   None,
    "tier":   "passed",
    "count":  0,
    "action": None,
    "steps":  None,
}

# ── Renderer ─────────────────────────────────────────────────────────────────
def render():
    img  = Image.new("RGB", (W, H), BG)
    d    = ImageDraw.Draw(img)
    tcol = TIER_COL.get(state["tier"], GREEN)
    now  = datetime.now().strftime("%H:%M:%S")

    # ── Header bar ───────────────────────────────────────────────────────────
    d.rectangle([0, 0, W - 1, HDR_H - 1], fill=PANEL)
    d.text((8, 7), "BioWatch", font=fnt_sm, fill=CYAN)
    d.text((W - 62, 7), now, font=fnt_sm, fill=GREY)

    # ── Flag dots strip ───────────────────────────────────────────────────────
    d.rectangle([0, HDR_H, W - 1, MAIN_Y - 1], fill=(14, 14, 28))
    dots = get_dots(state["count"])
    dot_r = 7
    total_w = 4 * (dot_r * 2) + 3 * 8
    x0 = (W - total_w) // 2
    for i, (col, lit) in enumerate(dots):
        cx = x0 + i * (dot_r * 2 + 8) + dot_r
        cy = HDR_H + DOTS_H // 2
        if lit:
            d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=col)
        else:
            d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                      outline=EMPTY_DOT, width=1)

    # ── Left stats panel ──────────────────────────────────────────────────────
    d.rectangle([0, MAIN_Y, STAT_W - 1, ACTION_Y - 1], fill=PANEL)
    d.line([STAT_W - 1, MAIN_Y, STAT_W - 1, ACTION_Y - 1], fill=GREY)

    d.text((8, MAIN_Y + 5),  "TEMP",  font=fnt_tiny, fill=GREY)
    t_str = f"{state['temp']:.1f}°C" if state["temp"] is not None else "—"
    d.text((8, MAIN_Y + 18), t_str,   font=fnt_big,  fill=WHITE)

    d.text((8, MAIN_Y + 65), "TURBIDITY", font=fnt_tiny, fill=GREY)
    turb_str = f"{state['turb']:.1f}" if state["turb"] is not None else "—"
    d.text((8, MAIN_Y + 78), turb_str, font=fnt_med,  fill=tcol)
    d.text((8, MAIN_Y + 100), "NTU",   font=fnt_tiny, fill=GREY)

    # ── Graph area ────────────────────────────────────────────────────────────
    d.rectangle([GRAPH_X, MAIN_Y, W - 1, ACTION_Y - 1], fill=(5, 5, 15))
    for pct in (0.25, 0.5, 0.75):
        gy = int(ACTION_Y - 1 - pct * MAIN_H)
        d.line([GRAPH_X, gy, W - 1, gy], fill=(28, 28, 48))
    # Flag threshold line
    gy_flag = int(ACTION_Y - 1 - (TURB_FLAG_NTU / TURB_GRAPH_MAX) * (MAIN_H - 2))
    d.line([GRAPH_X, gy_flag, W - 1, gy_flag], fill=(160, 50, 50))

    pts = list(turb_buf)
    prev = None
    for i, v in enumerate(pts):
        x = GRAPH_X + i
        y = int(ACTION_Y - 1 - min(v / TURB_GRAPH_MAX, 1.0) * (MAIN_H - 2))
        if prev:
            d.line([prev, (x, y)], fill=GRAPH_LINE, width=1)
        prev = (x, y)
    d.text((GRAPH_X + 3, MAIN_Y + 2), f"0–{int(TURB_GRAPH_MAX)} NTU",
           font=fnt_tiny, fill=GREY)

    # ── Action strip ─────────────────────────────────────────────────────────
    action_bg = {
        "passed": (12, 30, 20),
        "warn":   (40, 35, 5),
        "warn2":  (45, 25, 5),
        "panic":  (50, 8,  8),
    }.get(state["tier"], BG)
    d.rectangle([0, ACTION_Y, W - 1, H - 1], fill=action_bg)
    d.line([0, ACTION_Y, W - 1, ACTION_Y], fill=tcol)

    tier_label = TIER_LABEL.get(state["tier"], "")
    d.text((8, ACTION_Y + 4), f"[{tier_label}]", font=fnt_tiny, fill=tcol)

    if state["action"]:
        d.text((8, ACTION_Y + 18), state["action"], font=fnt_tiny, fill=WHITE)
    if state["tier"] == "panic" and state["steps"]:
        step = state["steps"][0] if state["steps"] else ""
        d.text((8, ACTION_Y + 34), f"1. {step}", font=fnt_tiny, fill=ORANGE)
        d.text((8, ACTION_Y + 48), "   See dashboard for full protocol", font=fnt_tiny, fill=GREY)
    elif state["tier"] == "passed":
        d.text((8, ACTION_Y + 18), "Conditions nominal.", font=fnt_tiny, fill=GREEN)

    display.image(img)

# ── Boot screen ───────────────────────────────────────────────────────────────
def boot_screen(msg: str = "Connecting…"):
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    d.text((12, H // 2 - 24), "BioWatch", font=fnt_big, fill=CYAN)
    d.text((12, H // 2 + 18), msg,         font=fnt_sm,  fill=GREY)
    display.image(img)

# ── WebSocket listener ────────────────────────────────────────────────────────
async def listen():
    boot_screen("Connecting to server…")
    while True:
        try:
            async with websockets.connect(SERVER_WS, ping_interval=20) as ws:
                print(f"[display] Connected to {SERVER_WS}")
                boot_screen("Connected — waiting for data")
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    t = msg.get("type")
                    if t == "reading":
                        state["temp"] = float(msg["temp"])
                        state["turb"] = float(msg["turbidity"])
                        turb_buf.append(state["turb"])
                        render()
                    elif t == "status":
                        state["tier"]   = msg.get("tier", "passed")
                        state["count"]  = msg.get("flagsInWindow", 0)
                        state["action"] = msg.get("action")
                        if msg.get("steps"):
                            state["steps"] = msg["steps"]
                        render()

        except Exception as e:
            print(f"[display] {type(e).__name__}: {e} — reconnecting in 3s")
            boot_screen(f"Reconnecting…")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(listen())
