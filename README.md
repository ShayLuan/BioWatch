# 🦠 BioWatch

**Real-time bacterial risk monitoring for hospital sink traps**

Built at MPCHacks 2026 — a low-cost IoT + ML system that continuously monitors hospital drain water to flag pathogen outbreak conditions *before* patients are exposed.

---

## The Problem

Hospital water infrastructure — sinks, drains, utility rooms — is a primary reservoir for opportunistic pathogens and Antibiotic Resistance Genes (ARGs) in clinical settings like NICUs. A [2026 study by Bourdin et al.](https://journals.asm.org/doi/10.1128/msystems.01546-25) found *S. maltophilia* in 67% of NICU drain samples.

The only way to confirm what's growing — qPCR and metagenomic sequencing — is slow, manual, and far too expensive to run continuously. Outbreaks get detected *after* patient exposure, leaving clinical staff entirely reactive.

In the US alone, antibiotic-resistant infections cause **2.8 million infections** and **35,000 deaths** yearly, costing over **$4.6 billion annually** for just the six most aggressive pathogens ([CDC](https://www.cdc.gov/antimicrobial-resistance/stories/partner-estimates.html)).

## The Solution

BioWatch is a physical sensor node that sits in a sink's P-trap and continuously monitors **turbidity** and **temperature** — the environmental conditions that precede pathogen proliferation. When conditions cross risk thresholds, alerts escalate through a tiered system (Passed → Warn → Warn Lvl 2 → PANIC) so staff know exactly *which* sinks need attention and *how urgently*.

---

## Architecture

```
ESP32-S3 Node                Raspberry Pi Backend              Dashboard
┌──────────────┐           ┌──────────────────────┐         ┌──────────────┐
│ DS18B20 temp │──┐        │  FastAPI server      │         │ React + Vite │
│ Turbidity    │──┤ WiFi   │  ┌─────────────────┐ │  WS     │ Live gauges  │
│ sensor       │──┼──────► │  │ ML Risk Engine  │ │ ◄─────► │ Sparklines   │
│              │  │  WS    │  │ (Decision Tree) │ │         │ Flag log     │
└──────────────┘  │        │  └─────────────────┘ │         │ Tier alerts  │
                  │        └──────────────────────┘         └──────────────┘
                  │                    │
                  │                    │
                  │        ┌───────────▼──────────┐
                  └──────► │ ILI9341 240×320      │
                           │ on-device display    │
                           └──────────────────────┘
```

**Data flow:** `ESP32 (temp + turbidity) → WebSocket → Backend (risk scoring + SQLite) → WebSocket push → Dashboard (display only) + Pi display`

---

## Project Structure

```
BioWatch/
├── deployment/               # ESP32-S3 Arduino firmware
│   └── deployment.ino        #   Sensor reads → WiFi → WebSocket JSON
├── server.py                 # FastAPI backend (port 8001) — ML inference service
├── calculate_real_time_risk.py  # AMRRiskEngine — deterministic risk scorer
├── data_gen.py               # Pi Zero ILI9341 display client
├── simulation/
│   └── esp32_sensor_data.py  # Simulated sensor data generator (CSV + JSON)
├── ML/                       # Training pipeline (offline)
│   ├── retrieval.py          #   USGS data retrieval
│   ├── water_quality_portal.py  # WQP data fetch
│   ├── build_features.py     #   24h/48h feature engineering
│   ├── compiling_training_data.py  # Match env data ↔ biological data
│   └── visualize_tree.py     #   Decision tree visualization
├── src/
│   ├── App.jsx               # Main dashboard component
│   ├── main.jsx              # React entry point
│   ├── config.js             # Thresholds, tier definitions, constants
│   ├── seed.js               # Demo sensor seed data
│   ├── mockBackend.js        # Client-side mock for offline dev
│   ├── styles.js             # Dashboard CSS-in-JS
│   └── components/
│       ├── StatTile.jsx      # Temp/turbidity card with sparkline
│       ├── Sparkline.jsx     # Recharts mini line graph
│       ├── FlagMeter.jsx     # Escalation progress bar
│       ├── TierBadge.jsx     # Risk tier indicator
│       └── WaterPipe.jsx     # Animated pipe visualization
├── package.json
├── vite.config.js
└── requirements.txt
```

---

## Hardware

| Component | Role | ~Cost |
|-----------|------|-------|
| ESP32-S3 | Sensor node MCU, WiFi streaming | ~$12 |
| SEN0189 turbidity sensor | Analog turbidity (ADC → NTU) | ~$21 |
| DS18B20 (waterproof) | Temperature probe | ~$18 |
| Raspberry Pi Zero W | Backend server + on-device display | ~$15 |
| ILI9341 320×240 TFT | Local sink-side status screen | ~$4 |

**Total per sink node: ~$25**

### Wiring (ESP32)

| Pin | Connection |
|-----|------------|
| GPIO 4 | DS18B20 DATA (breakout has pull-up) |
| GPIO 34 | Turbidity sensor AOUT (ADC1_CH6) |
| 3.3V | Sensor VCC |
| GND | Sensor GND |

### Wiring (Pi Zero W → ILI9341, SPI0)

| Pi GPIO | Display Pin |
|---------|-------------|
| GPIO 11 (SCK) | CLK |
| GPIO 10 (MOSI) | MOSI/SDA |
| GPIO 8 (CE0) | CS |
| GPIO 24 | DC |
| GPIO 25 | RST |
| 3.3V | VCC + LED |

---

## ML Pipeline

### Data Sources
- **USGS NWIS** — 103,526 instantaneous water quality records (Station 01646500, Potomac River near Washington, DC)
- **Zenodo** — [Shenandoah Valley Water Transect Data](https://doi.org/10.5281/zenodo.15865614) (Graber Neufeld, 2025) — biological validation targets

### Pipeline Steps

1. **Data Collection** — Retrieve raw 15-min interval flow, temperature, and turbidity data from USGS via `retrieval.py` and `water_quality_portal.py`
2. **Feature Engineering** — Convert raw readings into 24h/48h trend deltas using `build_features.py` (how do conditions *change* over time?)
3. **Training Set** — Match 103 days of environmental data against biological targets using `compiling_training_data.py`
4. **Feature Selection** — mRMR (Maximum Relevance, Minimum Redundancy) to identify the 4 most informative, non-redundant indicators
5. **Classification** — Decision tree for interpretable risk thresholds that run directly on edge hardware
6. **Deployment** — `calculate_real_time_risk.py` produces a deterministic 0–100 risk score from live sensor input

### Risk Scoring (AMRRiskEngine)

Calibrated against regional environmental medians (T_median = 16.5°C, Turb_median = 8.2 FNU):

| Risk Band | Score | Clinical Interpretation |
|-----------|-------|------------------------|
| **Low** | 0–34 | Stable baseline. Biofilm formation suppressed. |
| **Medium** | 35–69 | Elevated thermal/turbidity footprint. Accelerated metabolic incubation. |
| **High** | 70–100 | Critical runoff/flushing event. Immediate sanitation validation recommended. |

### Why a Decision Tree?

We initially explored LASSO for feature selection, but it consistently eliminated turbidity — our single most important signal — because the relationships between environmental parameters and biological outcomes are nonlinear. A decision tree handles this naturally and, critically, produces *interpretable thresholds* — exactly what you need when the model triggers a real alert on real hardware.

---

## Escalation Tiers

The dashboard uses a flag-based escalation system. A flag fires when **turbidity ≥ 4.5 NTU** AND **temperature ≥ 26°C** simultaneously, with a 30-second debounce. Flags accumulate in a sliding 6-hour window:

| Flags in Window | Tier | Response |
|-----------------|------|----------|
| 0–4 | **Passed** ✅ | Conditions nominal |
| 5–9 | **Warn** ⚠️ | Human action required — investigate drain |
| 10–17 | **Warn Lvl 2** 🚨 | Urgent action — targeted disinfection |
| 18+ | **PANIC** 🆘 | Immediate sanitisation protocol with step-by-step guidance |

---

## Getting Started

### Prerequisites

- Node.js ≥ 18
- Python ≥ 3.10
- Arduino IDE (for ESP32 firmware)

### Dashboard (frontend)

```bash
npm install
npm run dev        # Vite dev server on :5173
```

The dashboard works offline with the built-in mock backend for demo purposes.

### Backend

```bash
pip install -r requirements.txt
python server.py   # FastAPI ML service on :8001
```

### ESP32 Firmware

1. Install Arduino libraries: `WebSockets`, `ArduinoJson`, `OneWire`, `DallasTemperature`
2. Update WiFi credentials and Pi IP in `deployment/deployment.ino`
3. Flash to ESP32-S3

### Pi Display

```bash
# Enable SPI: sudo raspi-config → Interface Options → SPI → enable → reboot
pip3 install adafruit-circuitpython-rgb-display adafruit-blinka pillow websockets
python data_gen.py
```

---

## Sensor Calibration

We ran a dilution series experiment to characterize the turbidity sensor's response curve, fitting it with R², establishing the limit of detection, and measuring repeatability across trials. This calibration maps raw ADC values to meaningful NTU readings using the relationship:

```
NTU = max(0, (3.0V - V_measured) / 3.0V × 100)
```

---

## Datasets

- U.S. Geological Survey. *National Water Information System (NWIS) Instantaneous Values Data.* Station 01646500, Potomac River near Washington, DC. Retrieved May 30, 2026.
- Graber Neufeld, D. (2025). *Shenandoah Valley Water Transect Data* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.15865614

## References

- [CDC — Antibiotic Resistance Threats and Partner Estimates](https://www.cdc.gov/antimicrobial-resistance/stories/partner-estimates.html)
- Bourdin, T. et al. (2026). Abundance of opportunistic pathogens in NICU drain microbiomes. *mSystems*. https://journals.asm.org/doi/10.1128/msystems.01546-25

---

## Tech Stack

**Hardware:** ESP32-S3 · DS18B20 · SEN0189 Turbidity Sensor · Raspberry Pi Zero W · ILI9341 TFT

**Backend:** Python · FastAPI · scikit-learn · joblib · SQLite · WebSockets

**Frontend:** React 18 · Vite · Recharts · Lucide React

**ML:** mRMR feature selection · Decision tree classification · Spearman rank correlation (validation)

---
## License

Built at MPCHacks 2026
