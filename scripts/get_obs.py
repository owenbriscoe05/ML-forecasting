import argparse, os, datetime as dt
from pathlib import Path
import pandas as pd
from meteostat import Point, Hourly, Daily

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default="45.00")
    ap.add_argument("--lon", type=float, default="45.00")
    ap.add_argument("--elev", type=float, default=0.0)
    ap.add_argument("--start_time", type=str, required=True) # format: YYYY-MM-DD
    ap.add_argument("--end_time", type=str, required=True) # format: YYYY-MM-DD
    ap.add_argument("--location", type=str, default="45 lat, 45 lon")

    ap.parse_args()

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
