import pandas as pd
import statistics as st
import re

def main():
    data = pd.read_parquet("LA_hourly.parquet")
    print(data)
    low_temps = collect_low_temps(data.temp)
    print(low_temps)
    low_temp_mean = st.mean(low_temps)
    print(low_temp_mean)
    print("\n\n")


def collect_low_temps(temps):
    low_temps = []
    for temp in temps:
        if temp <= 18.0:
            low_temps.append(temp)

    return low_temps


if __name__ == "__main__":
    main()
