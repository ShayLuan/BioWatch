# MPCHACKS - BioWatch
A bacteria growth monitoring tool to help hospitals reduce the risk of drain-related outbreaks
# 🔬 Coupled Two-Tier AMR Risk Engine

This engine acts as the predictive intelligence layer of our IoT framework. It bridges high-fidelity offline biological datasets with low-latency, real-time edge telemetry.

## 🏗️ The Two-Tier Architecture

### Tier A: The Evidence Model (Offline Baseline)
* **Dataset:** 103,526 synchronized rows of continuous environmental sensor tracking (Flow, Temperature, Turbidity) sourced from the USGS National Water Information System (Station 01646500).
* **Validation:** Used to compute Spearman Rank Correlation matrices to verify the statistical significance ($p < 0.05$) of turbidity spikes and thermal accumulation against historical biological target indicators. 
* **Insight:** Proved that co-occurring environmental spikes create a high-probability incubator zone, creating an explicit mathematical justification for our risk boundaries.

### Tier B: The Inference Engine (Real-Time Runtime)
* **Deployment:** A lightweight, production-ready class (`AMRRiskEngine`) integrated directly into the backend server pipeline.
* **Input:** Real-time stream data from the physical ESP32-S3 microcontroller sensors (Water Temperature + Analog Turbidity).
* **Output:** A deterministic 0–100 consolidated risk score, categorized into clinical priority risk bands with actionable, dynamic driver descriptions.

## 📈 Parameter Logic & Mapping Matrix
Our Tier B scoring function uses a min-max scaling approach calibrated against regional baseline medians ($T_{median} = 16.5^\circ\text{C}$, $Turb_{median} = 8.2\text{ FNU}$):

| Risk Band | Score Range | Clinical Interpretation | Triggered Drivers |
| :--- | :--- | :--- | :--- |
| **Low Risk** | 0 – 34 | Stable baseline baseline conditions. Suppression of microbial biofilms. | "Baseline environmental conditions." |
| **Medium Risk** | 35 – 69 | Elevated parameter footprint. Accelerated baseline metabolic incubation. | "Elevated thermal incubation profile." / "Minor turbidity suspension." |
| **High Risk** | 70 – 100 | Critical runoff or flushing event. Optimal conditions for rapid biofilm amplification. | "Severe runoff event detected." / "Immediate sanitation validation recommended." |
