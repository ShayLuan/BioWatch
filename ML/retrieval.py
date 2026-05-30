import pandas as pd

# 1. Fully instrumented reference station (Potomac Basin - Downstream Shenandoah)
site = "01646500"
p_codes = "00010,00060,63680,00076"
start_date = "2024-01-01"
end_date = "2025-12-31"

url = f"https://nwis.waterservices.usgs.gov/nwis/iv/?format=rdb&sites={site}&parameterCd={p_codes}&startDT={start_date}&endDT={end_date}&siteStatus=all"

print(f"Fetching integrated matrix from USGS Station {site}...")
try:
    # Read text data and drop the formatting row (index 0)
    df = pd.read_csv(url, sep='\t', comment='#').drop(0)
except Exception as e:
    print(f"Connection error: {e}")
    exit()

# Initialize columns mapping
df = df.rename(columns={'datetime': 'Timestamp'})
rename_dict = {}

# Dynamically track what actually came through the API pipeline
for col in df.columns:
    if '00010' in col and not col.endswith('_cd'):
        rename_dict[col] = 'Temperature_C'
    elif '00060' in col and not col.endswith('_cd'):
        rename_dict[col] = 'Flow_CFS'
    elif ('63680' in col or '00076' in col) and not col.endswith('_cd'):
        rename_dict[col] = 'Turbidity_FNU'

df = df.rename(columns=rename_dict)

# Explicitly verify column inclusion before processing splits
target_cols = ['Temperature_C', 'Flow_CFS', 'Turbidity_FNU']
missing = [c for c in target_cols if c not in df.columns]

if missing:
    print("\n[!] Mapping Failed.")
    print(f"Columns actually found in download: {list(df.columns)}")
    print(f"Could not resolve codes for: {missing}")
else:
    # Cast to types cleanly
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df[target_cols] = df[target_cols].apply(pd.to_numeric, errors='coerce')

    # Keep only rows where we have valid data to feed the feature matrix
    df_clean = df[['Timestamp'] + target_cols].dropna()

    print(f"\nSuccess! Generated continuous matrix with {len(df_clean)} synchronized rows.")
    print(df_clean.head())

    # Save directly to your workspace
    df_clean.to_csv("sensor_activity.csv", index=False)
    print("\nMatrix saved cleanly to 'sensor_activity.csv'")