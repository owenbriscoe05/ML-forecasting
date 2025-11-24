# ML-forecasting
Forecast targets using ERA5 + station observations
## Quick start
conda env create -f environment.yml
conda activate ML-forecasting
python scripts/train.py --target tmax --lead 24
