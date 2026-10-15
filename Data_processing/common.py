"""
TITLE: common.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Loaders for measured and modelled radon that were copied into almost
         every original script (classification.py, everything_averaging.py,
         alistair_averaging.py, selection_file_creation_1yr*.py,
         file_processing_*.py). The operations are unchanged; they now live in
         one place.
"""

import pandas as pd
import xarray as xr

import config


def load_rn_meas_hourly(site):
    """Measured radon averaged to hourly values (30-minute obs -> hourly mean).

    Columns: time, radon, radon_uncertainty (plus any other numeric variables
    in the CEDA file).
    """
    ds = xr.open_dataset(config.radon_obs(site), decode_times=True)
    df = ds.to_dataframe().reset_index()
    df['time'] = df['time'].dt.floor('h')
    df = df.groupby(['time']).mean(numeric_only=True).reset_index()
    return df


def load_rn_mod_hourly(radon_map=config.RADON_MAP):
    """Modelled radon from the merged NAME output, summed over 'cat'.

    The model output has two categories (0 and 1, one per flux map: Zhang
    global and traceRadon Europe); summing them gives the total modelled
    activity concentration.
    """
    path = config.OUTPUT_DIR / '01_name_radon_model' / f'output_traceRadon_{radon_map}' \
        / f'for_all_months_{radon_map}.nc'
    ds = xr.open_dataset(path, decode_times=True)
    df = ds.to_dataframe().reset_index()
    df = df.groupby(['time']).sum(numeric_only=True).reset_index()
    return df


def to_4h(df):
    """Average an hourly table onto the InTEM 4 h windows (02, 06, 10, 14, 18, 22 UTC)."""
    df = df.copy()
    df['time'] = (df['time'] - pd.Timedelta(hours=2)).dt.floor('4h')
    df = df.groupby(['time']).mean(numeric_only=True).reset_index()
    df['time'] += pd.Timedelta(hours=2)
    return df
