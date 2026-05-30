"""
BioWatch ML Training Pipeline
==============================
Runs the full training sequence in order:
  1. build_features.py          — engineer rolling-window features from raw sensor data
  2. compiling_training_data.py — join features with biological targets; label Low/Medium/High Risk
  3. feature_selection_scaling_mRMR.py — mutual-info feature selection + StandardScaler
  4. feature_selection_lasso.py — LASSO regularization; saves lasso_model.pkl

Outputs written to the ML/ directory:
  engineered_features.csv, final_training_set.csv,
  X_train_scaled.csv, X_test_scaled.csv,
  scaler.pkl, selected_features.json, lasso_model.pkl

Run from any directory:
  python ML/train_pipeline.py
"""

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("build_features",                  "Step 1: Feature engineering"),
    ("compiling_training_data",         "Step 2: Compile training set"),
    ("feature_selection_scaling_mRMR",  "Step 3: Mutual-info selection + scaling"),
    ("feature_selection_lasso",         "Step 4: LASSO regularization + model save"),
]

def run_step(module_name: str, label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    path = os.path.join(_HERE, f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

if __name__ == "__main__":
    for module_name, label in STEPS:
        run_step(module_name, label)

    print("\n" + "="*60)
    print("  Pipeline complete.")
    print(f"  Model artifacts saved to: {_HERE}")
    print("  Start ml_service.py (port 8001) to serve predictions.")
    print("="*60)
