# scripts/preprocess.py
import pandas as pd

def load_and_clean(path="data/multi_modal_routes_100cities.csv"):
    """
    Load CSV, clean and normalize basic fields.
    Returns: cleaned pandas DataFrame
    """
    df = pd.read_csv(path)
    # Basic cleaning
    df = df.dropna(subset=["source","destination","cost"])
    df['source'] = df['source'].astype(str).str.strip().str.title()
    df['destination'] = df['destination'].astype(str).str.strip().str.title()
    df['mode'] = df['mode'].astype(str).str.strip().str.lower()
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce')
    df = df.dropna(subset=['cost'])
    df = df[df['cost'] > 0]
    df['duration_hours'] = pd.to_numeric(df['duration_hours'], errors='coerce').fillna(0.0)
    df['distance_km'] = pd.to_numeric(df['distance_km'], errors='coerce').fillna(0)
    df.reset_index(drop=True, inplace=True)
    return df

if __name__ == "__main__":
    df = load_and_clean()
    print(df.head(8).to_string(index=False))
    print("Total rows:", len(df))
