import cdsapi
import os
import pandas as pd
import requests
from calendar import monthrange

YEARS = range(2000, 2025)
HOURS = [f"{i:02d}:00" for i in range(24)]
# Lat and lon bounding box for central PA
AREA = [41.50, -78.50, 40.0, -76.50]

GHCN_STATION_METADATA_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
GHCN_BASE_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/"
GHCN_DIR = "data/raw/ghcn"

c = cdsapi.Client()

def download_era5_only():
    # download_era5_data(dataset="reanalysis-era5-single-levels", variables = [
    #    "2m_temperature", "surface_pressure", "10m_u_component_of_wind", "10m_v_component_of_wind",
    #    "total_precipitation", "2m_dewpoint_temperature", "total_column_water_vapour",
    #    "precipitation_type", "cape",
    #    "convective_inhibition", "boundary_layer_height", "surface_solar_radiation_downwards"]) 
    

    download_era5_data(dataset="reanalysis-era5-pressure-levels", variables = [
        "geopotential", "temperature", "u_component_of_wind", "v_component_of_wind",
        "vertical_velocity", "specific_humidity"], pressure_levels=["850", "700", "500", "300"]) 

def download_everything():
    # no explicit retrieve function for ghcn data
    os.makedirs(GHCN_DIR, exist_ok=True)

    stations = get_ghcn_stations(AREA)
    print(f"found {len(stations)} stations in this bounding box")
    for station in stations["id"].values:
        download_ghcn_data(station)

    download_era5_data(dataset="reanalysis-era5-single-levels", variables = [
        "2m_temperature", "surface_pressure", "10m_u_component_of_wind", "10m_v_component_of_wind",
        "total_precipitation", "2m_dewpoint_temperature", "total_column_water_vapour",
        "precipitation_type", "cape",
        "convective_inhibition", "boundary_layer_height", "surface_solar_radiation_downwards"]) 
    

    download_era5_data(dataset="reanalysis-era5-pressure-levels", variables = [
        "geopotential", "temperature", "u_component_of_wind", "v_component_of_wind",
        "vertical_velocity", "specific_humidity"], pressure_levels=["850", "700", "500", "300"]) 
   

def download_era5_data(dataset, variables, pressure_levels=None):
    """loops through years and months, collecting era5 data"""
    for var in variables:
        for year in YEARS:
            for month in range (1, 13):
                # handles number of days for different months, monthrange also handles leap years
                _, numdays = monthrange(year, month)
                days = [f"{i:02d}" for i in range(1, numdays + 1)]

                # naming convention for raw data files for this project
                var_clean = var.replace("/", "_")
                target_name = f"data/raw/{dataset.split('_')[-1]}_{year}-{month:02d}_{var_clean}.nc"
                
                # check existence (downloads can take multiple days)
                if os.path.exists(target_name):
                    continue

                # define the request dictionary
                request = {
                    "product_type": ["reanalysis"],
                    "data_format": "netcdf",
                    # "download_format": "unarchived",
                    "variable": [var],
                    "year": str(year),
                    "month": f"{month:02d}",
                    "day": days,
                    "time": HOURS,
                    "area": AREA,
                }

                if pressure_levels:
                    request["pressure_level"] = pressure_levels
                
                print(f"Requesting: {var} for {target_name}...")

                try:
                    c.retrieve(dataset, request, target_name)
                except Exception as e:
                    print(f"Failed {target_name}: {e}")

def get_ghcn_stations(area):
    """parses GHCN metadata to find stations within bounds"""
    df = pd.read_fwf(GHCN_STATION_METADATA_URL, header=None,
                     widths=[11, 9, 10, 7, 3, 31],
                     names=["id", "lat", "lon", "elev", "state", "name"])
    north, west, south, east = area
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    print(f"lat: {df['lat']}")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    print(f"lon: {df['lon']}")
    mask = (df["lat"] <= north) & (df["lat"] >= south) & (df["lon"] <= east) & (df["lon"] >= west)
    return df[mask]

def download_ghcn_data(station_id):
    url = f"{GHCN_BASE_URL}{station_id}.csv.gz"
    dest_path = os.path.join(GHCN_DIR, f"{station_id}.csv.gz")

    if (os.path.exists(dest_path)):
        return
    
    print(f"Downloading {station_id} ...")
    try:
        # mitigate memory issues
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size = 8192):
                f.write(chunk)
    except Exception as e:
        print(f"Failed to download {station_id}: {e}")


if __name__ == "__main__":
    if os.listdir("data/raw/ghcn/"):
        download_era5_only()
    else: download_everything()