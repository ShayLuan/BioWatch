import requests
import pandas as pd
import zipfile, io, os

BASE = "https://www.waterqualitydata.us/data/Result/search"

params = {
    "statecode": "US:51",          # Virginia FIPS
    "huc": "02070005;02070006",    # Shenandoah S/N Fork HUCs
    "characteristicName": "Temperature, water;Turbidity;Stream flow, instantaneous",
    "mimeType": "csv",
    "zip": "yes",
    "dataProfile": "narrowResult",
}

print("Downloading from WQP (this may take a minute)...")
r = requests.get(BASE, params=params, timeout=300)
r.raise_for_status()

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    csv_name = [f for f in z.namelist() if f.endswith(".csv")][0]
    df_raw = pd.read_csv(z.open(csv_name))

print(f"Downloaded {len(df_raw)} rows")
print("Columns:", list(df_raw.columns[:15]), "...")
