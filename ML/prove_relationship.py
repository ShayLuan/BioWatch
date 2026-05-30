import numpy as np
import pandas as pd
import scipy.stats as stats

# 1. Load your compiled data matrix
df = pd.read_csv("final_training_set.csv")

print("=========================================================")
print("  MATHEMATICAL PROOF: ENVIRONMENTAL DRIVERS OF AMR RISK  ")
print("=========================================================\n")

# --- FIX 1: Explicitly map your text classes to numbers ---
risk_mapping = {"Low": 0, "Medium": 1, "High": 2}
df["AMR_Risk_Numeric"] = df["AMR_Risk_Class"].map(risk_mapping)

# If it's already numeric, fall back safely
if df["AMR_Risk_Numeric"].isna().all():
    df["AMR_Risk_Numeric"] = df["AMR_Risk_Class"].astype(float)

# --- PROOF 1: Spearman Rank Correlation against Target Abundance ---
turb_corr, turb_p = stats.spearmanr(
    df["Turbidity_Max_48h"], df["Target_Gene_Abundance"]
)
temp_corr, temp_p = stats.spearmanr(df["Temperature_C"], df["Target_Gene_Abundance"])

print("1. SPEARMAN RANK CORRELATION (Against Raw Target Abundance):")
print(
    f"  * 48h Max Turbidity: Correlation = {turb_corr:.3f} | p-value = {turb_p:.4e}"
)
print(
    f"  * Temperature (°C) : Correlation = {temp_corr:.3f} | p-value = {temp_p:.4e}"
)

# --- PROOF 2: Odds Ratio Matrix (The Risk Multiplier) ---
median_turb = df["Turbidity_Max_48h"].median()
median_temp = df["Temperature_C"].median()

# Identify instances where BOTH Turbidity and Temp are elevated
df["High_Turb_and_Temp"] = (
    (df["Turbidity_Max_48h"] > median_turb) & (df["Temperature_C"] > median_temp)
).astype(int)

# --- FIX 2: Correctly binarize the risk using the new numeric scale ---
# 0 = Low Risk baseline, 1 = Elevated Risk (Medium or High)
df["Elevated_AMR"] = (df["AMR_Risk_Numeric"] > 0).astype(int)

# Build Contingency Table
contingency_table = pd.crosstab(df["High_Turb_and_Temp"], df["Elevated_AMR"])

# Ensure it is a valid 2x2 table before passing to Fisher Test
if contingency_table.shape == (2, 2):
    odds_ratio, p_value = stats.fisher_exact(contingency_table)

    print("\n2. ODDS RATIO ANALYSIS (Co-occurring Environmental Spikes):")
    print(f"  * Median Turbidity Threshold Used: {median_turb:.2f} FNU")
    print(f"  * Median Temperature Threshold Used: {median_temp:.2f} °C")
    print(f"  * Calculated Odds Ratio: {odds_ratio:.2f}x")
    print(f"  * Fisher Exact Test p-value: {p_value:.4e}")

    if p_value < 0.05:
        print(
            f"\n  => VERDICT: SUCCESS! When Turbidity and Temperature are both high,"
        )
        print(
            f"     the odds of encountering an AMR spike are significantly multiplied by {odds_ratio:.2f}x (p < 0.05)."
        )
    else:
        print(
            f"\n  => VERDICT: The current median thresholds do not yield a significant odds split (p = {p_value:.3f})."
        )
else:
    print("\n[!] Error: Contingency table is not 2x2. Check your data split labels.")
    print(contingency_table)