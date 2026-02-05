import pandas as pd
import numpy as np
import os
from pathlib import Path

# --- CONFIGURATION ---
INPUT_FILE_PATH = Path("./data/processed/")
TARGET_VARS = ["TMAX", "TMIN", "PRCP", "AWND", "era5_surface_pressure_mean", "era5_dewpoint_mean"]     # What we want to predict
WINDOW_SIZE = 5         # How many days back to look (Lag 1, 2, 3)
TEST_START_DATE = "2020-01-01"

def load_and_pivot(file_path):
    df_all = pd.DataFrame
    files = list(file_path.iterdir())
    for file in files:
        if (file.contains(".csv")):
            df_all = pd.concat([df_all, file])
    
        



def create_lags(df, target, window=3):
    df = df.sort_values(by=["id", "date"])
    
    # We want to lag EVERYTHING except the ID and Date
    # Note: We do NOT lag the Target at T=0 (that's the answer key)
    # We DO lag the Target from T-1 (Yesterday's max temp helps predict today's)
    feature_cols = [c for c in df.columns if c not in ["id", "date"]]
    
    for lag in range(1, window + 1):
        # We group by ID so we don't accidentally lag data from Station A into Station B
        shifted = df.groupby("id")[feature_cols].shift(lag)
        shifted.columns = [f"{c}_lag{lag}" for c in shifted.columns]
        df = pd.concat([df, shifted], axis=1)
        
    # Remove rows with NaNs created by lagging (the first 3 days of data)
    df = df.dropna()
    return df

def main():
    # 1. Prepare Data
    df = load_and_pivot(INPUT_FILE_PATH)
    
    # 2. Feature Engineering
    df_lagged = create_lags(df, TARGET_VAR, WINDOW_SIZE)
    
    # 3. Time Split
    print(f"Splitting data at {TEST_START_DATE}...")
    train = df_lagged[df_lagged["date"] < TEST_START_DATE]
    test = df_lagged[df_lagged["date"] >= TEST_START_DATE]
    
    # 4. Define Features (X) and Target (y)
    # INPUTS: All the "_lag" columns + static Era5 features (if you want 'today's' forecast)
    # NOTE: Standard MOS uses ERA5(Today) + Observations(Yesterday)
    
    # Features = ERA5 columns (Current Day) + All Lagged Columns (History)
    # We exclude the 'Current Day' GHCN columns (TMAX, TMIN, PRCP) because that's cheating!
    
    ghcn_current_day_cols = ["TMAX", "TMIN", "PRCP", "AWND", "SNOW", "SNWD"] 
    exclude_cols = ["id", "date"] + [c for c in ghcn_current_day_cols if c in df_lagged.columns]
    
    X_cols = [c for c in df_lagged.columns if c not in exclude_cols]
    
    X_train = train[X_cols]
    y_train = train[TARGET_VAR]
    
    X_test = test[X_cols]
    y_test = test[TARGET_VAR]
    
    print("-" * 30)
    print(f"Training Data: {X_train.shape}")
    print(f"Testing Data:  {X_test.shape}")
    print("-" * 30)
    print("Ready for ML Model!")

    # Example: Simple Check
    # from sklearn.linear_model import LinearRegression
    # model = LinearRegression()
    # model.fit(X_train, y_train)
    # print(f"Test Score: {model.score(X_test, y_test)}")

if __name__ == "__main__":
    main()