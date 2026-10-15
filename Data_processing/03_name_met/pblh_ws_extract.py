"""
TITLE: pblh_ws_extract.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Extract the NAME-modelled boundary-layer height (PBLH) and wind speed
         at each site from the monthly NAME CH4 footprint files, and save one
         time series per site:
           {site}_pblh_ws.csv  (time, PBLH, wind_speed, ...)  -> used in Figs 5-7, 9, 11
           {SITE}-{h}magl_allyears.nc

SOURCE FILE: Regional_modelling/Data/METHANE/Footprints/HFD100/pblh_plotting.ipynb
CHANGES:
  - The notebook was hard-coded to HFD and run inside each footprint folder;
    here it loops over the four sites using config.py paths.
  - The exploratory PBLH time-series plot cells are not carried over.
NOTES:
  - The NAME CH4 footprints (*_UKV_EUROPE_YYYYMM.nc) are not in the original
    Modelling/ directory, so this step can only be re-run once they are added
    under data/raw/name_footprints/methane/. The four {site}_pblh_ws.csv files
    already exist in Regional_modelling/Data/METHANE/Footprints/{SITE}/ and can
    be copied to outputs/03_name_met/ instead.
"""

import sys
from pathlib import Path

import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

DROP_VARS = ('fp', 'temperature', 'pressure', 'wind_direction', 'release_lat', 'release_lon',
             'particle_locations_n', 'particle_locations_e', 'particle_locations_s', 'particle_locations_w',
             'mean_age_particles_n', 'mean_age_particles_e', 'mean_age_particles_s', 'mean_age_particles_w')


def extract_pblh_ws(site, save=True):
    ds = xr.open_mfdataset(config.name_met_footprint_glob(site))
    ds = ds.drop_vars(DROP_VARS)
    ds = ds.drop_dims(['lon', 'lat', 'lev', 'height'])  # drop useless dimensions
    df = ds.to_dataframe()

    if save:
        ds.to_netcdf(path=config.pblh_ws_allyears_nc(site), mode='w', format='NETCDF4')  # all years
        df.to_csv(config.pblh_ws(site), sep=',')
    return df


# %%
if __name__ == '__main__':
    for site in config.SITE_LIST:
        extract_pblh_ws(site)
