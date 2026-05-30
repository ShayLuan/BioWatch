import os
import pandas as pd
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))

# 1. Load the pristine time-series data
df = pd.read_csv(os.path.join(_HERE, "sensor_activity.csv"))
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df = df.sort_values('Timestamp').reset_index(drop=True)

print(f"Loaded {len(df)} rows of raw sensor data. Engineering features...")

# 2. Define standard rolling window parameters based on 15-min logging
# 24 hours = 96 rows | 48 hours = 192 rows
WINDOW_24H = 96
WINDOW_48H = 192

# --- Feature Engineering Pipeline ---

# A. Turbidity Delta / Spikes (Captures storm runoff flushing bacteria/ARGs into water)
df['Turbidity_Delta_24h'] = df['Turbidity_FNU'] - df['Turbidity_FNU'].shift(WINDOW_24H)
df['Turbidity_Max_48h'] = df['Turbidity_FNU'].rolling(window=WINDOW_48H).max()

# B. Thermal Accumulation (Sustained warmth accelerates plasmid-mediated HGT)
df['Temp_Rolling_Mean_48h'] = df['Temperature_C'].rolling(window=WINDOW_48H).mean()

# C. Flow Dynamics (High flow = rapid downstream transport / dilution effects)
df['Flow_Delta_24h'] = df['Flow_CFS'] - df['Flow_CFS'].shift(WINDOW_24H)

# D. Feature Interactions (High suspended solids + optimal incubation temperature)
df['Temp_Turbidity_Interaction'] = df['Temperature_C'] * df['Turbidity_FNU']

# Drop the initialization rows that don't have enough history for the rolling windows
df_features = df.dropna().reset_index(drop=True)

print(f"Features engineered successfully! Matrix shape: {df_features.shape}")
print(df_features[['Timestamp', 'Turbidity_Delta_24h', 'Temp_Rolling_Mean_48h', 'Temp_Turbidity_Interaction']].head())

# Save your complete feature matrix X
df_features.to_csv(os.path.join(_HERE, "engineered_features.csv"), index=False)
print("\nFeature matrix exported to 'engineered_features.csv'")