import pandas as pd
import xarray as xr
import os
import glob
import zipfile
import shutil
from pathlib import Path
from collect import get_ghcn_stations, AREA

directory_path = Path("./data/raw/ghcn/")
era5_path = Path("./data/raw/era5/")
START_YEAR = 2000
END_YEAR = 2025

def rank_stations(start_year, end_year):
    results = []

    for file in directory_path.iterdir():
        df = pd.read_csv(file, header=None, names=["id", "date", "element", "value", "mflag", "qflag", "sflag", "obs_time"])
        # print(f"successful read on file {file}")
        # print(df)

        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")

        mask = (df["date"].dt.year >= start_year) & (df["date"].dt.year <= end_year)
        subset = df[mask]

        if subset.empty:
            continue

        tmax_count = len(subset[subset["element"] == "TMAX"])
        tmin_count = len(subset[subset["element"] == "TMIN"])
        precip_count = len(subset[subset["element"] == "PRCP"])
        wind_count = len(subset[subset["element"] == "AWND"])

        # create dictionary of counts
        results.append({
            "station_id": os.path.basename(file).replace(".csv.gz", ""),
            "tmax_days": tmax_count,
            "tmin_days": tmin_count,
            "precip_days": precip_count,
            "wind_days": wind_count,
            # need enough data to accurately verify predictions
            "good_coverage": bool((tmax_count > 9000) & (tmin_count > 9000) & (wind_count > 9000))
        })

    print(results)
    ranking = pd.DataFrame(results).sort_values(by="good_coverage", ascending = False)
    return ranking

def clean_selected_data(stations):
    cleaned = []
    for s in stations.itertuples():
        name = s.station_id
        df = pd.read_csv(f"{directory_path}/{name}.csv.gz", header=None, names=["id", "date", "element", "value", "mflag", "qflag", "sflag", "obs_time"])
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")

        mask = (df["date"].dt.year >= START_YEAR) & (df["date"].dt.year <= END_YEAR)
        subset = df[mask]

        # raw data is not in decimal point form
        subset["value"] = subset["value"] / 10
        subset = subset[subset["value"] != "NaN"]

        # print(subset)

        cleaned.append(subset)

    return cleaned

def unzip_era5():
    """era5 files were downloaded as zips and need to be unpacked"""
    zips = glob.glob(os.path.join(era5_path, "*.nc"))
    for f in zips:
        if zipfile.is_zipfile(f):
            with zipfile.ZipFile(f, 'r') as zip_ref:
                extract_to = f.replace(".nc", "_extracted")
                zip_ref.extractall(extract_to)

def collect_era5():
    surface_file_pattern = os.path.join(era5_path, "*extracted/*.nc")
    # pressure level data was downloaded one variable at a time
    ds = xr.open_mfdataset(
        surface_file_pattern,
        combine="by_coords",
        coords="minimal",
        compat="override",
        engine="netcdf4",
        chunks="auto"
    )
        
    
    return ds

def collect_era5_pressure():
    # pressure level data was downloaded one variable at a time
    plvl_file_pattern = os.path.join("./data/raw/*pressure-levels*.nc")
    ds = xr.open_mfdataset(
        plvl_file_pattern,
        combine="by_coords",
        coords="minimal",
        compat="override",
        engine="netcdf4",
        chunks="auto"
    )

    return ds





def merge_with_era5(ghcn, era5_s, era5_p, lat, lon):
    """merge ghcn station df with era5 dfs"""
    merged = pd.DataFrame
    era5 = xr.merge([era5_s, era5_p], compat="minimal", join="inner")
    # use nearest datapoints to station's lat and lon to reduce era5 extent
    point_ds = era5.sel(latitude=lat, longitude=lon, method="nearest").compute()
    print(point_ds.head(5))

    if "valid_time" in point_ds.coords:
        point_ds = point_ds.rename({"valid_time": "time"})

    daily_era5 = xr.Dataset()
    # build dataset columns
    daily_era5 = build_columns(daily_era5, point_ds)

    era5_df = daily_era5.to_dataframe().reset_index()
    era5_df = era5_df.rename(columns={"time": "date"})

    ghcn["date"] = pd.to_datetime(ghcn["date"])
    era5_df["date"] = pd.to_datetime(era5_df["date"])

    merged = pd.merge(ghcn, era5_df, on="date", how="inner")

    return merged

def build_columns(era5, point_ds):
    era5["era5_temp_mean"] = point_ds["t2m"].resample(time="1D").mean() - 273.15
    era5["era5_precip_sum"] = point_ds["tp"].resample(time="1D").sum() * 1000
    # era5["era5_precip_type"] = point_ds["ptype"].resample(time="1D").
    era5["era5_wind_x"] = point_ds["u10"].resample(time="1D").mean()
    era5["era5_wind_y"] = point_ds["v10"].resample(time="1D").mean()

    return era5

def build_features(df):
    ...


ranking = rank_stations(START_YEAR, END_YEAR)
selected = ranking.head(6)
print(selected)
unzip_era5()
xr_era5_surface = collect_era5()
xr_era5_pressure = collect_era5_pressure()
print("save complete")

metadata_df = get_ghcn_stations(AREA)
selected_with_coords = pd.merge(selected, metadata_df[["id", "lat", "lon"]],
                               left_on="station_id", right_on="id")

for station in selected_with_coords.itertuples():
    # Load and clean ONLY this station
    df_ghcn = pd.read_csv(f"{directory_path}/{station.station_id}.csv.gz", 
                          header=None, 
                          names=["id", "date", "element", "value", "mflag", "qflag", "sflag", "obs_time"])
    
    # Clean ghcn data (i.e. datetime and unit conversion)
    df_ghcn["date"] = pd.to_datetime(df_ghcn["date"], format="%Y%m%d")
    df_ghcn = df_ghcn[(df_ghcn["date"].dt.year >= START_YEAR) & (df_ghcn["date"].dt.year <= END_YEAR)]
    df_ghcn["value"] = df_ghcn["value"] / 10

    # Merge with ERA5 using the coordinates from 'selected_with_coords'
    merged_data = merge_with_era5(df_ghcn, xr_era5_surface, xr_era5_pressure, station.lat, station.lon)

    # Build features for this training set
    final_data = build_features(merged_data)
    
    # Save this specific station's training file
    # merged_data.to_csv(f"data/processed/{station.station_id}_merged.csv", index=False)
    print(final_data)
    final_data.to_csv("~/Downloads/check_data_3.csv")
    break
# merged_data = merge_with_era5(cleaned, xr_era5)


