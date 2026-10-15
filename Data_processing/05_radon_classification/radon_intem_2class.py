"""
TITLE: radon_intem_2class.py
AUTHOR: Mareya Saba
DATE CREATED: 14/08/2023
DATE LAST EDITED:
PURPOSE: Summaries of the 4 h two-class radon selection that was sent to InTEM
         (Mar 2021 - Feb 2022), on an hourly basis:
           1. intem_2class_averaging(): seasonal diurnal composites of radon,
              signed CH4 inlet difference, PBLH and wind speed for retained
              (class 1) vs excluded (class 0) hours.
              -> {site}_intem_seasonal_rel.csv          (Fig 7, 'Rn' panels)
           2. intem_2class_counts(): fraction of retained/excluded hours by hour
              of day and season.
              -> {site}_intem_seasonal_counts_rel.csv   (Fig 8, 'Rn' panels)
              -> {site}_intem_seasonal_4h_counts_rel.csv (same on 4 h windows; not used by a figure)

SOURCE FILES (Radon_Method/Exclusion_Windows_FINAL_UPDATES_NEW_RELATIVE_DIFF/2cl_InTem_File_Processing/):
  - file_processing_hfd_rgl_tac.py, file_processing_wao.py -> 1
  - counts.py (class_avg, class_avg_4h)                    -> 2
CHANGES:
  - HFD/RGL/TAC and WAO versions merged; WAO keeps its no-CH4 branch.
  - Paths from config.py.
  - Monthly branches of counts.py (groupby('class','Month'), which would raise
    an error) are not carried over.
NOTES:
  - ISSUE (not changed): TAC uses ch4_diff_low-mid (54 m - 100 m); the Fig 7
    caption says 54 and 185 m.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from common import load_rn_meas_hourly, load_rn_mod_hourly  # noqa: E402


def _hourly_classes(site):
    """4 h InTEM classification forward-filled to every hour."""
    cl = pd.read_csv(config.sel_4h_2class(site), parse_dates=[0])
    cl.set_index('time', inplace=True)
    cl2 = cl.resample('1h').ffill().reset_index()
    return cl2[['time', 'Season', 'class']]


# =============================================================================
#   1. Seasonal / monthly diurnal averages (Fig 7)
# =============================================================================
def intem_2class_averaging(site, average='seasonal', save=True):
    rn_mod = config.rn_mod_col(site)

    # PART 1: 4 h InTEM classification file -> hourly
    cl2 = _hourly_classes(site)

    # PART 2: measured / modelled radon and relative difference
    df_rn_meas = load_rn_meas_hourly(site)
    df_rn_mod = load_rn_mod_hourly()
    rn_mod_meas = df_rn_meas.merge(df_rn_mod, how='outer', on='time')
    rn_mod_meas['relative difference'] = (rn_mod_meas[rn_mod] - rn_mod_meas['radon']) / (rn_mod_meas['radon'])
    rn_mod_meas = rn_mod_meas[['time', 'radon', rn_mod, 'relative difference']]

    # PART 3: CH4_DIFF, PBLH AND WS, MERGE EVERYTHING TOGETHER
    df_fp = pd.read_csv(config.pblh_ws(site), parse_dates=[0])

    if site == 'wao':
        full_df = cl2.merge(rn_mod_meas, how='outer', on='time').merge(df_fp, how='outer', on='time')
    else:
        df_vdiff_interp = pd.read_csv(config.vdiff_interp(site), parse_dates=[0])
        if site == 'tac':
            # ISSUE: 54 m - 100 m; caption says 54 and 185 m (ch4_diff_low-high).
            df_vdiff_interp.rename(columns={'ch4_diff_low-mid': 'ch4_diff'}, inplace=True)
        full_df = cl2.merge(rn_mod_meas, how='outer', on='time') \
            .merge(df_vdiff_interp, how='outer', on='time').merge(df_fp, how='outer', on='time')
    full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error|ch4_C')]  # remove error columns

    # 1 YEAR DATA MAR 2021 - FEB 2022
    full_df = full_df[config.in_paper_year(full_df['time'])].sort_values(by='time', ignore_index=True)

    # PART 4: monthly / seasonal diurnal averages
    full_df['radon_spread'] = full_df['radon']
    full_df[f'{rn_mod}_spread'] = full_df[rn_mod]
    full_df['wind_speed_spread'] = full_df['wind_speed']
    full_df['PBLH_spread'] = full_df['PBLH']

    agg = {'radon': 'mean', 'radon_spread': 'std', rn_mod: 'mean', f'{rn_mod}_spread': 'std',
           'relative difference': 'mean'}
    if site == 'wao':
        full_df['ch4_diff'] = np.nan  # single CH4 inlet
        agg.update({'wind_speed': 'mean', 'wind_speed_spread': 'std', 'PBLH': 'mean', 'PBLH_spread': 'std',
                    'ch4_diff': 'mean'})
    else:
        full_df['ch4_diff_spread'] = full_df['ch4_diff']
        agg.update({'ch4_diff': 'mean', 'ch4_diff_spread': 'std',
                    'wind_speed': 'mean', 'wind_speed_spread': 'std', 'PBLH': 'mean', 'PBLH_spread': 'std'})

    if average == 'monthly':
        full_df.insert(loc=0, column='Month', value=full_df['time'].dt.month)
        full_df.insert(loc=full_df.columns.get_loc('Month') + 1, column='Hour', value=full_df['time'].dt.hour)
        full_avg = full_df.groupby(['class', 'Month', 'Hour']).agg(agg).reset_index()
    elif average == 'seasonal':
        full_df.insert(loc=full_df.columns.get_loc('Season') + 1, column='Hour', value=full_df['time'].dt.hour)
        full_avg = full_df.groupby(['class', 'Season', 'Hour']).agg(agg).reset_index()

    if save:
        full_avg.to_csv(config.intem_2class_avg(site, average))
    return full_avg


# =============================================================================
#   2. Class fractions by hour of day (Fig 8)
# =============================================================================
def _fractions(df):
    df = df.copy()
    df.insert(loc=df.columns.get_loc('Season') + 1, column='Hour', value=df['time'].dt.hour)
    counts = df.groupby(['class', 'Season', 'Hour']).count()
    counts.reset_index(inplace=True)
    counts['fraction'] = (counts['time'] / counts.groupby(['Season', 'Hour'])['time'].transform('sum'))
    return counts


def intem_2class_counts(site, save=True):
    """Hourly (4 h class forward-filled to each hour) -> used by Fig 8."""
    counts = _fractions(_hourly_classes(site))
    if save:
        counts.to_csv(config.intem_2class_counts(site), index=False)
    return counts


def intem_2class_counts_4h(site, save=True):
    """Same, on the 4 h windows themselves (not used by a paper figure)."""
    cl = pd.read_csv(config.sel_4h_2class(site), parse_dates=[0])[['time', 'Season', 'class']]
    counts = _fractions(cl)
    if save:
        counts.to_csv(config.intem_2class_counts_4h(site), index=False)
    return counts


# %%
if __name__ == '__main__':
    for site in config.SITE_LIST:
        intem_2class_averaging(site, average='seasonal')
        intem_2class_counts(site)
        intem_2class_counts_4h(site)
