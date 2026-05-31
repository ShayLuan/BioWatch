#!/usr/bin/env python3
"""
BioWatch — ILI9341 320×240 dashboard for Pi Zero W

Wiring (Pi Zero W → ILI9341)
─────────────────────────────
  GPIO 11 (SPI0_CLK)  → CLK / SCK
  GPIO 10 (SPI0_MOSI) → MOSI / SDA
  GPIO  8 (SPI0_CE0)  → CS
  GPIO 24             → DC
  GPIO 25             → RST
  3.3 V               → VCC + LED (backlight)
  GND                 → GND

Install (Pi Zero W)
───────────────────
  sudo apt install python3-pip python3-dev libopenjp2-7 libtiff5 -y
  pip3 install adafruit-circuitpython-rgb-display adafruit-blinka \
               pillow websockets

Enable SPI via raspi-config → Interface Options → SPI → Yes, reboot.

Run alongside the server
────────────────────────
  # terminal 1
  cd ~/BioWatch && python backend/server.py
  # terminal 2
  python pi/display.py
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime

import websockets
from PIL import Image, ImageDraw, ImageFont

import board
import busio
import digitalio
import adafruit_rgb_display.ili9341 as ili9341

# ── Display init ────────────────────────────────────────────────────────────
spi     = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
cs      = digitalio.DigitalInOut(board.CE0)
dc      = digitalio.DigitalInOut(board.D24)
rst     = digitalio.DigitalInOut(board.D25)
display = ili9341.ILI9341(spi, cs=cs, dc=dc, rst=rst,
                           width=320, height=240, baudrate=16_000_000)

W, H = 320, 240

# ── Layout ──────────────────────────────────────────────────────────────────
HDR_H   = 24          # header bar
STAT_W  = 140         # left stats column
GRAPH_X = STAT_W
GRAPH_W = W - STAT_W  # 180 px
GRAPH_H = H - HDR_H - 78
FLAG_Y  = HDR_H + GRAPH_H
FLAG_H  = H - FLAG_Y
MAX_FLAGS_VISIBLE = 3

# ── Colours (RGB) ───────────────────────────────────────────────────────────
BG      = (10,  10,  20)
PANEL   = (20,  20,  40)
WHITE   = (255, 255, 255)
GREY    = (120, 120, 140)
CYAN    = (0,   210, 255)
GREEN   = (50,  220, 110)
YELLOW  = (255, 210, 0)
ORANGE  = (255, 130, 0)
RED     = (255, 45,  45)
GRAPH_LINE = (0, 170, 230)

TIER_COL = {
    "normal":   GREEN,
    "watch":    YELLOW,
    "elevated": ORANGE,
    "critical": RED,
}

# ── Fonts ───────────────────────────────────────────────────────────────────
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"
def _font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_PATH.format("-Bold" if bold else ""), size)
    except Exception:
        return ImageFont.load_default()

fnt_big  = _font(34, bold=True)   # large numbers
fnt_med  = _font(19, bold=True)   # turbidity reading
fnt_sm   = _font(13)              # labels
fnt_tiny = _font(11)              # flags + sub-labels

# ── State shared between WS listener and renderer ───────────────────────────
GRAPH_SAMPLES = GRAPH_W          # one pixel column per sample
turb_buf      = deque([0.0] * GRAPH_SAMPLES, maxlen=GRAPH_SAMPLES)
TURB_GRAPH_MAX = 20.0            # NTU ceiling for Y-axis

state = {
    "temp":    None,
    "turb":    None,
    "tier":    "normal",
    "sensor":  "—",
    "flags":   deque(maxlen=20),  # full history; only last 3 shown
}

# ── Renderer ────────────────────────────────────────────────────────────────
def render():
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    tcol = TIER_COL.get(state["tier"], GREEN)

    # Header bar
    draw.rectangle([0, 0, W - 1, HDR_H - 1], fill=PANEL)
    draw.text((6, 5),       "BioWatch",              font=fnt_sm,  fill=CYAN)
    draw.text((90, 5),      f"[{state['tier'].upper()}]",
                                                      font=fnt_sm,  fill=tcol)
    draw.text((W - 62, 5),  datetime.now().strftime("%H:%M:%S"),
                                                      font=fnt_sm,  fill=GREY)

    # Left stats panel background
    draw.rectangle([0, HDR_H, STAT_W - 1, FLAG_Y - 1], fill=PANEL)
    draw.line([STAT_W - 1, HDR_H, STAT_W - 1, FLAG_Y - 1], fill=GREY)

    # Temperature
    draw.text((8, HDR_H + 6), "TEMP", font=fnt_tiny, fill=GREY)
    temp_str = f"{state['temp']:.1f}°C" if state["temp"] is not None else "—"
    draw.text((8, HDR_H + 18), temp_str, font=fnt_big, fill=WHITE)

    # Turbidity
    draw.text((8, HDR_H + 68), "TURBIDITY", font=fnt_tiny, fill=GREY)
    turb_str = f"{state['turb']:.1f}" if state["turb"] is not None else "—"
    draw.text((8, HDR_H + 80), turb_str, font=fnt_med, fill=tcol)
    draw.text((8, HDR_H + 102), "NTU",   font=fnt_tiny, fill=GREY)

    # Sensor ID bottom of stats
    draw.text((8, FLAG_Y - 16), state["sensor"], font=fnt_tiny, fill=GREY)

    # Graph area background
    draw.rectangle([GRAPH_X, HDR_H, W - 1, FLAG_Y - 1], fill=(5, 5, 15))

    # Grid lines at 25 / 50 / 75 %
    for pct in (0.25, 0.5, 0.75):
        gy = int(FLAG_Y - 1 - pct * GRAPH_H)
        draw.line([GRAPH_X, gy, W - 1, gy], fill=(28, 28, 48))

    # Threshold line at TURB_FLAG_NTU (4.5 NTU)
    TURB_FLAG_NTU = 4.5
    gy_flag = int(FLAG_Y - 1 - (TURB_FLAG_NTU / TURB_GRAPH_MAX) * (GRAPH_H - 2))
    draw.line([GRAPH_X, gy_flag, W - 1, gy_flag], fill=(180, 60, 60))

    # Plot turbidity history as a line
    pts = list(turb_buf)
    prev = None
    for i, v in enumerate(pts):
        x = GRAPH_X + i
        y = int(FLAG_Y - 1 - min(v / TURB_GRAPH_MAX, 1.0) * (GRAPH_H - 2))
        if prev:
            draw.line([prev, (x, y)], fill=GRAPH_LINE, width=1)
        prev = (x, y)

    # Graph axis label
    draw.text((GRAPH_X + 3, HDR_H + 2),
              f"Turbidity  0–{int(TURB_GRAPH_MAX)} NTU", font=fnt_tiny, fill=GREY)

    # Flags strip
    draw.rectangle([0, FLAG_Y, W - 1, H - 1], fill=(15, 7, 7))
    draw.line([0, FLAG_Y, W - 1, FLAG_Y], fill=RED)
    draw.text((6, FLAG_Y + 3), "FLAGS", font=fnt_tiny, fill=RED)

    recent = list(reversed(state["flags"]))[:MAX_FLAGS_VISIBLE]
    for i, f in enumerate(recent):
        y = FLAG_Y + 14 + i * 20
        line = f"{f['ts']}  T:{f['temp']:.1f}°C  NTU:{f['turb']:.1f}"
        draw.text((6, y), line, font=fnt_tiny, fill=ORANGE)

    if not recent:
        draw.text((6, FLAG_Y + 14), "No flags in window", font=fnt_tiny, fill=GREY)

    display.image(img)

# ── Boot screen ─────────────────────────────────────────────────────────────
def boot_screen(msg="Connecting…"):
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((10, H // 2 - 20), "BioWatch", font=fnt_big,  fill=CYAN)
    draw.text((10, H // 2 + 20), msg,         font=fnt_sm,   fill=GREY)
    display.image(img)

# ── WebSocket listener ───────────────────────────────────────────────────────
async def listen():
    boot_screen("Connecting to server…")
    url = "ws://127.0.0.1:8000/ws/dashboard"

    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                boot_screen("Connected — waiting for data")
                print(f"[display] Connected to {url}")

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    mtype = msg.get("type")

                    if mtype == "reading":
                        state["sensor"] = msg.get("sensorId", state["sensor"])
                        state["temp"]   = float(msg["temp"])
                        state["turb"]   = float(msg["turbidity"])
                        turb_buf.append(state["turb"])
                        render()

                    elif mtype == "flag":
                        ts = datetime.fromtimestamp(
                                msg["ts"] / 1000).strftime("%H:%M:%S")
                        state["flags"].append({
                            "ts":   ts,
                            "temp": float(msg["temp"]),
                            "turb": float(msg["turbidity"]),
                        })
                        render()

                    elif mtype == "status":
                        tier = msg.get("tier", "normal")
                        if tier != state["tier"]:
                            state["tier"] = tier
                            render()

        except Exception as e:
            print(f"[display] WS error: {e} — reconnecting in 3 s")
            boot_screen(f"Reconnecting… ({type(e).__name__})")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(listen())
