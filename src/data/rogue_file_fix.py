import xarray as xr
import glob
import os
from pathlib import Path

# Update this path to where your data is
era5_path = Path("./data/raw/era5/")

def find_rogue_files():
    print(f"Scanning files in {era5_path}...")
    files = sorted(glob.glob(os.path.join(era5_path, "*extracted/*.nc")))
    
    sizes = {}
    bad_files = []
    
    for f in files:
        try:
            # We open slightly deeper to check dimensions without loading data
            with xr.open_dataset(f) as ds:
                lat_size = ds.sizes.get('latitude', 0)
                
                # Track statistics
                if lat_size not in sizes:
                    sizes[lat_size] = 0
                sizes[lat_size] += 1
                
                # Identify the "Small" files (assuming 481 is the correct size)
                if lat_size == 7: 
                    bad_files.append(f)
                    print(f"⚠️ FOUND ROGUE FILE (Size 7): {os.path.basename(f)}")
        except Exception as e:
            print(f"❌ Corrupt file: {os.path.basename(f)}")

    print("\n--- SUMMARY ---")
    print(f"Distribution of Latitude Sizes: {sizes}")
    
    if bad_files:
        print(f"\nFound {len(bad_files)} rogue files.")
        user_input = input("Do you want to delete these files now? (y/n): ")
        if user_input.lower() == 'y':
            for f in bad_files:
                os.remove(f)
            print("Deleted.")
        else:
            print("Files kept. Please move them manually before running your main script.")
    else:
        print("No rogue files found with size 7.")

if __name__ == "__main__":
    find_rogue_files()