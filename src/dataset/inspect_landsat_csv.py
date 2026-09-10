import pandas as pd
from pathlib import Path

csv_path = Path("data/raw/landsat/monthly_features/sierra_nevada_landsat_features_2020_2026.csv")

df = pd.read_csv(csv_path)

print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print(df.head())
print(df.isna().sum())
print(df.describe())

print("\nRows per month:")
print(df.groupby(["year", "month"]).size())