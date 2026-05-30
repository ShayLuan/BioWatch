import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, mutual_info_classif

# 1. Load Data
df = pd.read_csv("final_training_set.csv")
feature_cols = [
    'Temperature_C', 'Flow_CFS', 'Turbidity_FNU',
    'Turbidity_Delta_24h', 'Turbidity_Max_48h',
    'Temp_Rolling_Mean_48h', 'Flow_Delta_24h',
    'Temp_Turbidity_Interaction'
]
X = df[feature_cols]
y = df['AMR_Risk_Class']

# 2. Stratified Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

print(f"Initial Feature Matrix Shape: {X_train.shape}")

# 3. Mutual-information feature selection (SelectKBest — replaces mRMR,
#    same relevance criterion, available on all Python versions via scikit-learn)
print("\n--- Running Phase 1: Mutual Information Filter ---")
selector = SelectKBest(mutual_info_classif, k=4)
selector.fit(X_train, y_train)
selected_features = list(X_train.columns[selector.get_support()])
print(f"Top 4 selected features: {selected_features}")

# Filter datasets to chosen variables
X_train_mrmr = X_train[selected_features]
X_test_mrmr = X_test[selected_features]

# 4. Standard Scaling
scaler = StandardScaler()
X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train_mrmr), columns=selected_features)
X_test_scaled = pd.DataFrame(scaler.transform(X_test_mrmr), columns=selected_features)

# Reset indices to align cleanly for file caching
y_train = y_train.reset_index(drop=True)
y_test = y_test.reset_index(drop=True)

# 5. Export for downstream steps
X_train_scaled.assign(Target=y_train).to_csv("X_train_scaled.csv", index=False)
X_test_scaled.assign(Target=y_test).to_csv("X_test_scaled.csv", index=False)
print("\nScaled mRMR features cached to 'X_train_scaled.csv' and 'X_test_scaled.csv'")

# Persist scaler + feature list so ml_service.py can load them at inference time
import joblib, json, os
_here = os.path.dirname(os.path.abspath(__file__))
joblib.dump(scaler, os.path.join(_here, "scaler.pkl"))
with open(os.path.join(_here, "selected_features.json"), "w") as _f:
    json.dump(selected_features, _f)
print("Saved scaler.pkl and selected_features.json")
