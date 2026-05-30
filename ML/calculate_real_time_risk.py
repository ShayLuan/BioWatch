import numpy as np


class AMRRiskEngine:
    def __init__(self):
        # Layer B Calibration Coefficients (Derived from your Linear SVM + Tree Insights)
        # Calibrated using the Potomac/Little Falls 2024-2025 dataset
        self.temp_median = 16.5  # Baseline regional median temp (°C)
        self.turb_median = 8.2  # Baseline regional median turbidity (FNU)

        # Weights for our 0-100 Biofilm-Risk Multiplier
        self.w_temp = 0.40  # 40% weight on thermal metabolic incubation
        self.w_turb = 0.60  # 60% weight on physical suspended solids/runoff

    def calculate_realtime_risk(self, raw_temp, raw_turb, historical_buffer=None):
        """
        Exposes the unified endpoint for the Backend/IoT pipeline.
        Accepts current sensor readings and optional historical windows.
        """
        # 1. Fallback handling for missing historical windows during live telemetry
        if historical_buffer and len(historical_buffer) >= 4:
            # If backend maintains a running 48-hour list, capture the true max
            turb_max_48h = max([r['turbidity'] for r in historical_buffer])
        else:
            # Dynamic approximation if streaming single-frame packets
            turb_max_48h = max(raw_turb, self.turb_median * 1.5 if raw_turb > self.turb_median else raw_turb)

        # 2. Compute Layer B Linear Activation Scores (Min-Max Scaling Approximations)
        temp_score = min(max((raw_temp / 30.0) * 100, 0), 100)  # Caps at 30°C optimal growth
        turb_score = min(max((turb_max_48h / 50.0) * 100, 0), 100)  # Caps at 50 FNU heavy runoff

        # 3. Calculate Consolidated Risk Matrix Score
        risk_score = int((temp_score * self.w_temp) + (turb_score * self.w_turb))

        # 4. Map to Labeled Clinical Response Bands
        if risk_score < 35:
            band = "Low Risk"
            drivers = ["Baseline environmental conditions.", "Biofilm formation suppressed."]
        elif 35 <= risk_score < 70:
            band = "Medium Risk"
            drivers = []
            if raw_temp > self.temp_median: drivers.append("Elevated thermal incubation profile.")
            if raw_turb > self.turb_median: drivers.append("Minor turbidity suspension noted.")
        else:
            band = "High Risk"
            drivers = ["Severe runoff or flushing event detected.", "Immediate sanitation validation recommended."]

        return {
            "risk_score": risk_score,
            "band": band,
            "drivers": drivers
        }


# --- Quick Test Loop for Integration Verification ---
if __name__ == "__main__":
    engine = AMRRiskEngine()
    # Test a simulated severe storm runoff spike
    sample_reading = engine.calculate_realtime_risk(raw_temp=22.4, raw_turb=42.1)
    print("Integration Test Output:")
    print(sample_reading)