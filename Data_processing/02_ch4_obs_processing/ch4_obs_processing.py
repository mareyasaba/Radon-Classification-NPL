"""
TITLE: ch4_obs_processing.py
AUTHOR: Mareya Saba
DATE CREATED: 07/08/2023
DATE LAST EDITED:
PURPOSE: Turn the hourly CH4 exports for each inlet into a gap-limited,
         interpolated hourly series and compute the signed CH4 inlet
         difference (lower inlet minus upper inlet) used in Figs 5, 7 and 9:
           {site}{h}_60min.csv  -> {site}{h}_60min_processed.csv   (pre_processing)
                                -> {site}{h}_hour.csv                (even_hours*)
                                -> {site}_vdiff_interp.csv           (even_hours*)
         Sites: HFD (50, 100 m), RGL (45, 90 m), TAC (54, 100, 185 m).
         WAO has a single inlet and is not processed here.

SOURCE FILES:
  - Regional_modelling/Data/Hourly_averaging/hourly_average.py  -> pre_processing()
  - Radon_Method/Seasonal_average/all_funcs_hourly.py            -> even_hours(), even_hours_tac()
CHANGES:
  - Paths from config.py. The original even_hours* wrote to
    Processed_raw_data/, and the vdiff files were then moved by hand to
    Vertical_difference/; here they are written straight to outputs/02_ch4_obs_processing/.
  - hourly_average(), hourly_counting() and seasonal_average() from the
    source files were exploratory and are not used by any figure, so they are
    not carried over.
NOTES:
  - ISSUE (not changed): even_hours_tac() writes three differences. Every
    downstream TAC script uses ch4_diff_low-mid = 54 m minus 100 m, but the
    Fig 7 and Fig 9 captions describe 54 m and 185 m (ch4_diff_low-high).
    Decide which is intended; see the renames in 04 and 05.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


# =============================================================================
#   1. Clean the raw hourly export (from hourly_average.py)
# =============================================================================
def pre_processing(site, height, save=True):
    """Read one inlet's 60-min CH4 export, convert 'NAN' strings to NaN.

    Returns:
        df: dataframe with time, ch4_C, ch4_stdev (NaNs as np.nan)
    """
    df = pd.read_csv(config.ch4_raw_60min(site, height), dayfirst=True, skipinitialspace=True)

    df["time"] = pd.to_datetime(df["time"], dayfirst=True)  # convert times to datetime

    # REPLACE "NAN" STRINGS
    for col in df.columns:
        if col != 'time':
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if save:
        df.to_csv(config.ch4_60min_processed(site, height), sep=',', index=False)
        print('Saved', config.ch4_60min_processed(site, height))

    return df


# =============================================================================
#   2. Even hourly series with short-gap interpolation (from all_funcs_hourly.py)
# =============================================================================
def _even_hourly(df_c, df_new):
    """Interpolate gaps shorter than 10 hours; longer gaps stay NaN."""
    mask = df_c.copy()
    for col in df_c.columns:
        df = pd.DataFrame(df_c[col])
        df['new'] = ((df.notnull() != df.shift().notnull()).cumsum())
        df['ones'] = 1
        mask[col] = (df.groupby('new')['ones'].transform('count') < 10) | df_c[col].notnull()

    return df_c.interpolate(method='index')[mask].reindex(df_new.index)


def _prepare(df, df_new):
    """Concatenate with an empty hourly frame, sort, and drop NaN-only duplicates."""
    df_c = pd.concat([df, df_new]).sort_index()
    df_c = df_c[~df_c.index.duplicated(keep=False) | df_c[['ch4_C', 'ch4_stdev']].notnull().any(axis=1)]
    return df_c


def _empty_hourly():
    df_new = pd.DataFrame({'time': pd.date_range('2014-01-01', '2023-01-30', freq='1h', inclusive='both'),
                           'ch4_C': np.nan, 'ch4_stdev': np.nan})
    return df_new.set_index('time')


def even_hours(site, vertical_diffs=True):
    """HFD and RGL: two inlets -> {site}{h}_hour.csv and {site}_vdiff_interp.csv."""
    low_h = config.SITES[site]['ch4']['low']
    high_h = config.SITES[site]['ch4']['high']

    df_low = pd.read_csv(config.ch4_60min_processed(site, low_h))
    df_low["time"] = pd.to_datetime(df_low["time"])  # processed files are ISO (yyyy-mm-dd)
    df_low = df_low.set_index('time')

    df_high = pd.read_csv(config.ch4_60min_processed(site, high_h))
    df_high["time"] = pd.to_datetime(df_high["time"])  # processed files are ISO (yyyy-mm-dd)
    df_high = df_high.set_index('time')

    # Create new dataframe with hourly data
    df_new = _empty_hourly()

    df_low_c_interp = _even_hourly(_prepare(df_low, df_new), df_new)
    df_low_c_interp.to_csv(config.ch4_hour_interp(site, low_h), sep=',', index=True)

    df_high_c_interp = _even_hourly(_prepare(df_high, df_new), df_new)
    df_high_c_interp.to_csv(config.ch4_hour_interp(site, high_h), sep=',', index=True)

    if vertical_diffs:
        # Rename columns so that they can be concatenated into 1 dataframe with same time series
        df_low_c_interp = df_low_c_interp.rename(columns={"ch4_C": "ch4_C_low", "ch4_stdev": "ch4_stdev_low"})
        df_high_c_interp = df_high_c_interp.rename(columns={"ch4_C": "ch4_C_high", "ch4_stdev": "ch4_stdev_high"})

        df_all = df_low_c_interp.join(df_high_c_interp, how='outer')

        # Add columns for vertical difference and error in vertical difference
        df_all['ch4_diff'] = df_all['ch4_C_low'] - df_all['ch4_C_high']
        df_all['ch4_diff_err'] = np.sqrt(df_all['ch4_stdev_low']**2 + df_all['ch4_stdev_high']**2)
        df_all.to_csv(config.vdiff_interp(site), sep=',', index=True)
        return df_all


def even_hours_tac(vertical_diffs=True):
    """TAC: three inlets (54, 100, 185 m) -> tac{h}_hour.csv and tac_vdiff_interp.csv."""
    site = 'tac'
    low_h = config.SITES[site]['ch4']['low']
    mid_h = config.SITES[site]['ch4']['mid']
    high_h = config.SITES[site]['ch4']['high']

    df_low = pd.read_csv(config.ch4_60min_processed(site, low_h), parse_dates=[0]).set_index('time')
    df_mid = pd.read_csv(config.ch4_60min_processed(site, mid_h), parse_dates=[0]).set_index('time')
    df_high = pd.read_csv(config.ch4_60min_processed(site, high_h), parse_dates=[0]).set_index('time')

    # Create new dataframe with hourly data
    df_new = _empty_hourly()

    df_low_c_interp = _even_hourly(_prepare(df_low, df_new), df_new)
    df_low_c_interp.to_csv(config.ch4_hour_interp(site, low_h), sep=',', index=True)

    df_mid_c_interp = _even_hourly(_prepare(df_mid, df_new), df_new)
    df_mid_c_interp.to_csv(config.ch4_hour_interp(site, mid_h), sep=',', index=True)

    df_high_c_interp = _even_hourly(_prepare(df_high, df_new), df_new)
    df_high_c_interp.to_csv(config.ch4_hour_interp(site, high_h), sep=',', index=True)

    if vertical_diffs:
        # Rename columns so that they can be concatenated into 1 dataframe with same time series
        df_low_c_interp = df_low_c_interp.rename(columns={"ch4_C": "ch4_C_low", "ch4_stdev": "ch4_stdev_low"})
        df_mid_c_interp = df_mid_c_interp.rename(columns={"ch4_C": "ch4_C_mid", "ch4_stdev": "ch4_stdev_mid"})
        df_high_c_interp = df_high_c_interp.rename(columns={"ch4_C": "ch4_C_high", "ch4_stdev": "ch4_stdev_high"})

        df_all = df_low_c_interp.join(df_mid_c_interp, how='outer').join(df_high_c_interp, how='outer')

        # Add columns for vertical difference and error in vertical difference
        df_all['ch4_diff_low-mid'] = df_all['ch4_C_low'] - df_all['ch4_C_mid']
        df_all['ch4_diff_low-mid_error'] = np.sqrt((df_all['ch4_stdev_low'])**2 + df_all['ch4_stdev_mid']**2)

        df_all['ch4_diff_mid-high'] = df_all['ch4_C_mid'] - df_all['ch4_C_high']
        df_all['ch4_diff_mid-high_error'] = np.sqrt((df_all['ch4_stdev_mid'])**2 + df_all['ch4_stdev_high']**2)

        df_all['ch4_diff_low-high'] = df_all['ch4_C_low'] - df_all['ch4_C_high']
        df_all['ch4_diff_low-high_error'] = np.sqrt((df_all['ch4_stdev_low'])**2 + df_all['ch4_stdev_high']**2)
        df_all.to_csv(config.vdiff_interp(site), sep=',', index=True)
        return df_all


# %%
if __name__ == '__main__':
    for site in ['hfd', 'rgl', 'tac']:
        for h in config.SITES[site]['ch4'].values():
            pre_processing(site, h)

    even_hours('hfd')
    even_hours('rgl')
    even_hours_tac()
