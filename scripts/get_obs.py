import argparse, os, datetime as dt
from pathlib import Path
import pandas as pd
from meteostat import Point, Hourly, Daily

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=45.00)
    ap.add_argument("--lon", type=float, default=45.00)
    ap.add_argument("--elev", type=float, default=0.0)
    ap.add_argument("--start_time", type=str, required=True) # format: YYYY-MM-DD
    ap.add_argument("--end_time", type=str, required=True) # format: YYYY-MM-DD
    ap.add_argument("--location", type=str, default="45 lat, 45 lon")

    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    start = dt.datetime.fromisoformat(args.start_time)
    end = dt.datetime.fromisoformat(args.end_time)

    loc = Point(args.lat, args.lon, args.elev)

    df_hour = Hourly(loc, start, end, "UTC").fetch()
    df_day = Daily(loc, start, end).fetch()

    if df_hour.empty:
        print("df_hour is empty")
    df_hour.to_parquet(data_dir/f"{args.location}_hourly.parquet")
    if df_day.empty:
        print("df_day is empty")
    df_day.to_parquet(data_dir/f"{args.location}_daily.parquet")



if __name__ == "__main__":
    main()
