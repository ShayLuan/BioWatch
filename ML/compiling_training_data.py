import os
import pandas as pd
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))

# 1. Load your engineered predictor features (X)
df_features = pd.read_csv(os.path.join(_HERE, "engineered_features.csv"))
df_features['Timestamp'] = pd.to_datetime(df_features['Timestamp'])

# 2. Extract a 'Date' string for straightforward daily grouping if needed
df_features['Date'] = df_features['Timestamp'].dt.date

print(f"Aggregating {len(df_features)} sensor records into daily statistical profiles...")

# Group by date to extract daily snapshots of our engineered features
df_daily_features = df_features.groupby('Date').agg({
    'Temperature_C': 'mean',
    'Flow_CFS': 'mean',
    'Turbidity_FNU': 'mean',
    'Turbidity_Delta_24h': 'max',       # Capture the peak spike of the day
    'Turbidity_Max_48h': 'max',         # Capture the maximum 48h envelope
    'Temp_Rolling_Mean_48h': 'mean',
    'Flow_Delta_24h': 'max',
    'Temp_Turbidity_Interaction': 'mean'
}).reset_index()

# 3. Simulate or Load your AMR Targets (Y)
# REPLACE THIS BLOCK with your actual pandas read command for the Zenodo data, e.g.:
# df_targets = pd.read_excel("2-alldata_multi_regression.xlsx")
# Ensure it has a column cast to datetime matching your dates!
print("Loading AMR biological target indicators...")
# (Using placeholder dates matching your 2024 sensor activity timeline for demonstration)
mock_dates = pd.date_range(start="2024-01-05", end="2025-12-25", freq='W').date
np.random.seed(42)
df_targets = pd.DataFrame({
    'Date': mock_dates,
    'Target_Gene_Abundance': np.random.exponential(scale=100, size=len(mock_dates)) # Mock biological signal
})

# 4. Set Thresholds for Multi-Class AMR Risk Target (0: Low, 1: Medium, 2: High)
print("Calculating multi-class percentile thresholds...")

# Calculate the 50th and 85th percentiles from your biological target column
lower_threshold = df_targets['Target_Gene_Abundance'].quantile(0.50)
upper_threshold = df_targets['Target_Gene_Abundance'].quantile(0.85)

# Define a function to map the abundance values into three distinct classes
def assign_risk_class(abundance):
    if abundance < lower_threshold:
        return "Low Risk"
    elif lower_threshold <= abundance < upper_threshold:
        return "Medium Risk"
    else:
        return "High Risk"

# Apply the mapping function to create your new target column
df_targets['AMR_Risk_Class'] = df_targets['Target_Gene_Abundance'].apply(assign_risk_class)

print(f"Thresholds: Low Risk < {lower_threshold:.2f} | Medium Risk up to {upper_threshold:.2f} | High Risk >= {upper_threshold:.2f}")
# 5. Execute the Final Matrix Join
df_daily_features['Date'] = pd.to_datetime(df_daily_features['Date']).dt.date
df_targets['Date'] = pd.to_datetime(df_targets['Date']).dt.date

df_train = pd.merge(df_targets, df_daily_features, on='Date', how='inner')

print(f"\nFinal Training Matrix compiled successfully!")
print(f"Total labeled samples available for training: {len(df_train)}")
print(f"Class Balance: {df_train['AMR_Risk_Class'].value_counts().to_dict()} (0: Low Risk, 1: High Risk)")

# Save the final training file
df_train.to_csv(os.path.join(_HERE, "final_training_set.csv"), index=False)
print("\nExported training-ready matrix to 'final_training_set.csv'")