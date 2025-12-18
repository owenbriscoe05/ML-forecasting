# ML-forecasting
Forecast conditions using ERA5 + station observations
Limited to single location (central PA) due to local storage bottleneck
Conditions predicted:
- tmax & tmin
- t_dewpoint
- RH (average)
- precip (quant & type)
- p_surface
- p_500
- wind surface velocity
- CIN & CAPE
- severe weather risk score
## Quick start
conda env create -f environment.yml
conda activate ML-forecasting
python scripts/train.py --target tmax --lead 24
