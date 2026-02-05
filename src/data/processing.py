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

def main():
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

        # move ghcn element, value data into column format
        pivoted_data = pivot_ghcn(merged_data)

        # Build features for this training set
        # final_data = build_features(merged_data)
        
        # Save this specific station's training file
        pivoted_data.to_csv(f"data/processed/{station.station_id}_merged.csv", index=False)
    # merged_data = merge_with_era5(cleaned, xr_era5)
    final = concatenate_cols()
    final.to_csv("data/processed/full_dataset_1.csv", index=False)

def rank_stations(start_year, end_year):
    """ranks ghcn station based on (mainly) quantity of data"""
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
    """optional cleaning function if workflow changes from for-loop-centric flow"""
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
    """builds more useful dataframe columns -- using era5 hourly data -- to merge with ghcn daily data"""
    levels = point_ds.pressure_level.values.astype(int)

    # need to convert to hPa
    era5["era5_surface_pressure_mean"] = (point_ds["sp"].resample(time="1D").mean()) / 100
    high_pressure = (point_ds["sp"] / 100) > 1020
    low_pressure = (point_ds["sp"] / 100) < 980
    era5["high_pressure_hours"] = high_pressure.resample(time="1D").sum()
    era5["low_pressure_hours"] = low_pressure.resample(time="1D").sum()

    # need to convert to Celsius
    era5["era5_temp_mean"] = point_ds["t2m"].resample(time="1D").mean() - 273.15
    era5["era5_high_temp"] = point_ds["t2m"].resample(time="1D").max() - 273.15
    era5["era5_low_temp"] = point_ds["t2m"].resample(time="1D").min() - 273.15
    era5["era5_dewpoint_mean"] = point_ds["d2m"].resample(time="1D").mean() - 273.15

    # and need to convert from m to mm for readability
    era5["era5_precip_sum"] = point_ds["tp"].resample(time="1D").sum() * 1000
    is_precipitating = point_ds["tp"] > 0
    era5["era5_precip_hours"] = is_precipitating.resample(time="1D").sum()
    era5["era5_wind_x_surface_mean"] = point_ds["u10"].resample(time="1D").mean()
    era5["era5_wind_y_surface_mean"] = point_ds["v10"].resample(time="1D").mean()
    era5["era5_cape_mean"] = point_ds["cape"].resample(time="1D").mean()
    era5["era5_cin_mean"] = point_ds["cin"].resample(time="1D").mean()
    high_cape = point_ds["cape"] > 2500
    era5["era5_significant_cape"] = high_cape.resample(time="1D").sum()
    era5["column_water_vapor_mean"] = point_ds["tcwv"].resample(time="1D").mean()

    # pressure level columns
    for level in levels:
        suffix=f"_{level}hPa"

        # need to reduce to level dimension
        level_slice = point_ds.sel(pressure_level=level)

        era5[f"era5_temp_mean{suffix}"] = level_slice["t"].resample(time="1D").mean() - 273.15
        era5[f"era5_wind_x_mean{suffix}"] = level_slice["u"].resample(time="1D").mean() 
        era5[f"era5_wind_y_mean{suffix}"] = level_slice["v"].resample(time="1D").mean()

        # z is given in m^2 / s^2 in the era5 raw data
        era5[f"era5_geopotential_mean{suffix}"] = (level_slice["z"].resample(time="1D").mean()) / 9.81

        # convert to g/kg (from kg/kg)
        era5[f"era5_specific_humidity_mean{suffix}"] = (level_slice["q"].resample(time="1D").mean()) * 1000

    ## had issues downloading ptype data, so will use proxies
    # using 850hPa level to check for potential freezing rain / ice
    level_850 = point_ds.sel(pressure_level=850)
    # snow often falls above freezing, so will consider up to 2ºC
    potential_snow = (point_ds["t2m"] < 275.15) & (point_ds["tp"] > 0) & (level_850["t"] < 273.15)
    # for ice or freezing rain, need a section of warm air for precip to fall through, often occurs around 850 level
    potential_ice = (point_ds["t2m"] < 273.15) & (point_ds["tp"] > 0) & (level_850["t"] > 273.15)
    era5["era5_potential_snow_hours"] = potential_snow.resample(time="1D").sum()
    era5["era5_potential_ice_hours"] = potential_ice.resample(time="1D").sum()


    return era5

def pivot_ghcn(df):
    # ghcn_cols = ["id", "date", "element", "value"]
    df = df[df["qflag"].isna()]
    era5_cols = [c for c in df.columns if c not in ["element", "value", "mflag", "qflag", "sflag", "obs_time", "Unnamed: 0"]]

    df_era5 = df[era5_cols].drop_duplicates(subset=["id", "date"])

    df_ghcn_wide = df.pivot_table(
        index=["id", "date"],
        columns="element",
        values="value"
    ).reset_index()

    final_df = pd.merge(df_ghcn_wide, df_era5, on=["id", "date"], how="inner")

    return final_df

def concatenate_cols():
    file_path = Path("./data/processed/")
    df_all = pd.DataFrame()
    files = list(file_path.iterdir())

    for file in files:
        print(file)
        # gitkeep file obviously can't be included in the dataframe
        if (".gitkeep" in file.name or "full_dataset.csv" in file.name):
            continue
        df_curr = pd.read_csv(file)
        df_all = pd.concat([df_all, df_curr])
    ghcn = get_ghcn_stations(AREA)
    cols_to_keep = df_all.columns.tolist() + ["elev"]
    df_with_elev = pd.merge(df_all, ghcn, on="id", how="inner")
    df_with_elev = df_with_elev[cols_to_keep]

    return df_with_elev

def build_features(df):
    ...


if __name__ == "__main__":
    main()


