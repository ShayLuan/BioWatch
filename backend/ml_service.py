# ml_service.py — FastAPI ML inference service (port 8001)
#
# Loads the LASSO model trained by ML/feature_selection_lasso.py.
# Falls back to AMRRiskEngine if model artifacts are not yet present
# (i.e. the training pipeline hasn't been run yet).

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import logging
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List, Optional

from calculate_real_time_risk import AMRRiskEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ML_DIR = os.path.join(os.path.dirname(__file__), "..", "ML")

app = FastAPI(title="BioWatch ML Service")

# ── Load artifacts produced by the training pipeline ─────────────────────────
_model    = None
_scaler   = None
_features: List[str] = []

def _load_artifacts():
    global _model, _scaler, _features
    model_path    = os.path.join(ML_DIR, "lasso_model.pkl")
    scaler_path   = os.path.join(ML_DIR, "scaler.pkl")
    features_path = os.path.join(ML_DIR, "selected_features.json")

    if all(os.path.exists(p) for p in [model_path, scaler_path, features_path]):
        _model  = joblib.load(model_path)
        _scaler = joblib.load(scaler_path)
        with open(features_path) as f:
            _features = json.load(f)
        logger.info(f"ML artifacts loaded. Active features: {_features}")
    else:
        logger.warning(
            "ML artifacts not found — run ML/feature_selection_scaling_mRMR.py "
            "then ML/feature_selection_lasso.py to generate them. "
            "Falling back to AMRRiskEngine."
        )

_load_artifacts()
_fallback = AMRRiskEngine()

# Midpoints of each risk band (used to build a continuous score from class probs)
_BAND_MIDPOINTS = {"Low Risk": 17, "Medium Risk": 52, "High Risk": 85}


# ── Request schema ────────────────────────────────────────────────────────────
class SensorFeatures(BaseModel):
    # Raw sensor values — always present
    Temperature_C:           float
    Turbidity_FNU:           float
    # Derived from rolling buffer — optional; server computes these when possible
    Turbidity_Delta_24h:     float = 0.0
    Turbidity_Max_48h:       Optional[float] = None
    Temp_Rolling_Mean_48h:   Optional[float] = None
    Flow_Delta_24h:          float = 0.0
    Flow_CFS:                float = 0.0
    Temp_Turbidity_Interaction: Optional[float] = None


# ── Inference endpoint ────────────────────────────────────────────────────────
@app.post("/predict")
def predict(payload: SensorFeatures) -> dict:
    # Fill derived fields that the caller left as None
    temp = payload.Temperature_C
    turb = payload.Turbidity_FNU
    feat = payload.model_dump()
    feat.setdefault("Turbidity_Max_48h",       turb)
    feat.setdefault("Temp_Rolling_Mean_48h",   temp)
    feat.setdefault("Temp_Turbidity_Interaction", temp * turb)
    if feat["Turbidity_Max_48h"] is None:
        feat["Turbidity_Max_48h"] = turb
    if feat["Temp_Rolling_Mean_48h"] is None:
        feat["Temp_Rolling_Mean_48h"] = temp
    if feat["Temp_Turbidity_Interaction"] is None:
        feat["Temp_Turbidity_Interaction"] = temp * turb

    # ── Fallback path: model not trained yet ─────────────────────────────────
    if _model is None:
        result = _fallback.calculate_realtime_risk(temp, turb)
        result["source"] = "AMRRiskEngine (model not trained)"
        return result

    # ── LASSO inference path ──────────────────────────────────────────────────
    # Select and order only the features the model was trained on
    X = pd.DataFrame([{f: feat.get(f, 0.0) for f in _features}])
    X_scaled = pd.DataFrame(_scaler.transform(X), columns=_features)

    pred_class = _model.predict(X_scaled)[0]
    proba      = _model.predict_proba(X_scaled)[0]
    classes    = list(_model.classes_)

    # Continuous 0-100 risk score via probability-weighted band midpoints
    risk_score = int(sum(
        p * _BAND_MIDPOINTS.get(c, 50)
        for c, p in zip(classes, proba)
    ))

    # Driver messages consistent with AMRRiskEngine vocabulary
    if pred_class == "High Risk":
        drivers = [
            "Severe runoff or flushing event detected.",
            "Immediate sanitation validation recommended.",
        ]
    elif pred_class == "Medium Risk":
        drivers = []
        if temp > _fallback.temp_median:
            drivers.append("Elevated thermal incubation profile.")
        if turb > _fallback.turb_median:
            drivers.append("Minor turbidity suspension noted.")
    else:
        drivers = [
            "Baseline environmental conditions.",
            "Biofilm formation suppressed.",
        ]

    return {
        "risk_score":    risk_score,
        "band":          pred_class,
        "drivers":       drivers,
        "probabilities": {c: round(p, 3) for c, p in zip(classes, proba)},
        "source":        "LASSO",
    }


@app.get("/health")
def health():
    return {
        "status":        "ok",
        "model_loaded":  _model is not None,
        "features":      _features,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
