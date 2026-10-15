"""
TITLE: current_intem.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Everything about the CURRENT InTEM observation selection (the
         comparator method):
           1. intem_file_processing(): read the monthly InTEM CH4 time-series
              files for a site, find the 4 h windows InTEM did not retain, and
              expand them to an hourly 'low' (retained) / 'high' (excluded)
              classification. Also prints the seasonal retention percentages
              (Table 2).
              -> {SITE}_missing_windows.csv           (Figs 5, 6 hatching)
              -> {SITE}_alistair_classes_allhours.csv (input to 2 and 3)
           2. current_intem_averaging(): seasonal diurnal composites of
              measured/modelled radon, signed CH4 inlet difference, PBLH and
              wind speed for retained vs excluded hours.
              -> {site}_alistair_seasonal_2021.csv    (Fig 7, 'Current' panels)
           3. current_intem_counts(): fraction of retained/excluded hours per
              hour of day and season.
              -> {SITE}_alistair_classes_allhours_counts.csv (Fig 8, 'Current' panels)

SOURCE FILES:
  - InTEM_Testing/{HFD,RGL,TAC,WAO}/intem_file_processing.ipynb   -> 1
  - Radon_Method/Exclusion_Windows_New/{SITE}_exclusion_windows/Alistair/
        alistair_averaging.py (HFD, RGL), alistair_averaging_NEW.py (TAC, WAO) -> 2
        counts.py (all four sites)                                            -> 3
CHANGES:
  - The four per-site copies of each script are merged into one function with
    a `site` argument; the site differences (TAC column rename, WAO with no
    CH4 difference) are kept as explicit branches.
  - Paths from config.py.
  - Fig 8 reads the counts file. In the original folders it was saved as
    Alistair/2021_only/{SITE}_alistair_classes_allhours.csv, i.e. the same name
    as the hourly classes file from step 1. It is now
    {SITE}_alistair_classes_allhours_counts.csv; update the Fig 8 script to match.
  - TAC and WAO: alistair_averaging_NEW.py saved 'NEW_{site}_...' and its last
    call used average='monthly'; the files Fig 7 reads are the seasonal ones,
    so the default here is average='seasonal' and no 'NEW_' prefix.
  - The monthly branch of counts.py (groupby('class','Month'), which would raise
    an error) is not carried over; only the seasonal counts are used.
  - season_counting.ipynb duplicated the seasonal-percentage cell of
    intem_file_processing.ipynb and is not carried over.
NOTES:
  - ISSUE (see current_intem_averaging): the original RGL alistair_averaging.py
    read InTEM Testing/HFD/HFD_alistair_classes_allhours.csv, i.e. HFD's
    classes for RGL. The existing rgl_alistair_seasonal_2021.csv and the RGL
    'Current' panels of Fig 7 were made that way. This file reads each site's
    own classes, so re-running it WILL change the RGL panels of Fig 7.
    Set config.REPRODUCE_ORIGINAL_OUTPUTS = True to reproduce the original file.
  - ISSUE: TAC uses ch4_diff_low-mid (54 m - 100 m) as ch4_diff; the Fig 7
    caption says 54 and 185 m. Kept as in the original.
"""

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from common import load_rn_meas_hourly, load_rn_mod_hourly  # noqa: E402


# =============================================================================
#   1. InTEM files -> missing 4 h windows -> hourly classes (+ Table 2)
# =============================================================================
def intem_file_processing(site, save=True):
    path = config.intem_current_dir(site)  # folder with all InTEM files for this site
    all_files = glob.glob(os.path.join(path, '*'))

    concatenated_df = pd.concat((pd.read_csv(f, sep=r'\s+', skiprows=4) for f in all_files),
                                ignore_index=True)
    concatenated_df.drop([0], inplace=True)
    concatenated_df = concatenated_df[pd.to_numeric(concatenated_df['YYYY'], errors='coerce').notnull()]
    concatenated_df = concatenated_df.apply(pd.to_numeric)
    concatenated_df.reset_index(drop=True, inplace=True)
    concatenated_df.insert(0, 'DATETIME', pd.to_datetime(dict(year=concatenated_df.YYYY, month=concatenated_df.MM,
                                                              day=concatenated_df.DD, hour=concatenated_df.HH)))

    # Find out the 4H time windows that are missing from the above
    missing_windows = pd.date_range('2020-01-01 02:00:00', '2022-12-31 22:00:00', freq='4h',
                                    inclusive='both').difference(concatenated_df['DATETIME'])
    df1 = pd.DataFrame({'Missing dates': missing_windows})

    # Expand each missing 4 h window to its four hours
    df2 = pd.DataFrame(np.concatenate([[i + pd.to_timedelta(f'{n} h') for n in range(4)]
                                       for i in df1['Missing dates']]), columns=['Missing dates'])

    all_times = pd.DataFrame({'time': pd.date_range('2020-01-01 02:00:00', '2022-12-31 23:00:00', freq='1h',
                                                    inclusive='both'), 'class': ''})
    all_times.loc[all_times['time'].isin(df2['Missing dates']), 'class'] = 'high'   # excluded by InTEM
    all_times.loc[~all_times['time'].isin(df2['Missing dates']), 'class'] = 'low'   # retained by InTEM

    if save:
        df1.to_csv(config.intem_missing_windows(site), sep=',', index=False)
        all_times.to_csv(config.intem_classes_allhours(site), index=False)

    # ---- Table 2: seasonal retention percentages, Mar 2021 - Feb 2022 ----
    yr = all_times[config.in_paper_year(all_times['time'])].copy()

    yr_counts = yr.groupby(['class']).count().reset_index()
    yr_counts['percentage'] = (yr_counts['time'] / yr_counts['time'].sum() * 100).round(1).map('{}%'.format)
    print(f'{site.upper()} annual:\n{yr_counts}')

    yr.insert(loc=yr.columns.get_loc('time') + 1, column='season', value=config.season_of(yr['time']))
    seas_counts = yr.groupby(['season', 'class']).count().reset_index()
    seas_counts['season total'] = seas_counts.groupby('season')['time'].transform('sum')
    seas_counts['percentage'] = (seas_counts['time'] / seas_counts['season total'] * 100).round(1).map('{}%'.format)
    print(f'{site.upper()} seasonal:\n{seas_counts}')

    return all_times


# =============================================================================
#   2. Seasonal diurnal composites for the current InTEM classes (Fig 7)
# =============================================================================
def current_intem_averaging(site, average='seasonal', year='2021', save=True):
    mod = config.rn_mod_col(site)

    # Time series 2020-2022 of classification for the current InTEM method
    # ISSUE: the original RGL script read HFD's file here (see header).
    # config.REPRODUCE_ORIGINAL_OUTPUTS = True reproduces that behaviour.
    class_site = 'hfd' if (config.REPRODUCE_ORIGINAL_OUTPUTS and site == 'rgl') else site
    classes = pd.read_csv(config.intem_classes_allhours(class_site), parse_dates=[0])
    classes.set_index('time', inplace=True)

    # Measured (hourly mean) and modelled (cat 0 + cat 1) radon
    df_rn_meas_avg = load_rn_meas_hourly(site).set_index('time')
    df_rn_mod = load_rn_mod_hourly().set_index('time')

    # Time series of modelled PBLH and wind speed
    df_fp = pd.read_csv(config.pblh_ws(site), parse_dates=[0])
    df_fp.set_index('time', inplace=True)

    # MERGE ALL DATAFRAMES TOGETHER
    if site in ('hfd', 'rgl'):
        df_vdiff_interp = pd.read_csv(config.vdiff_interp(site), parse_dates=[0]).set_index('time')
        full_df = classes.join(df_rn_meas_avg, how='outer').join(df_rn_mod, how='outer') \
            .join(df_vdiff_interp, how='outer').join(df_fp, how='outer')
        full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error')]  # remove error columns

    elif site == 'tac':
        df_vdiff_interp = pd.read_csv(config.vdiff_interp(site), parse_dates=[0]).set_index('time')
        # ISSUE: 54 m - 100 m; captions say 54 and 185 m (ch4_diff_low-high).
        df_vdiff_interp.rename(columns={'ch4_diff_low-mid': 'ch4_diff'}, inplace=True)
        full_df = classes.join(df_rn_meas_avg, how='outer').join(df_rn_mod, how='outer') \
            .join(df_vdiff_interp, how='outer').join(df_fp, how='outer')
        full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error|ch4_C')]  # remove error columns

    elif site == 'wao':
        # Single CH4 inlet: no signed inlet difference
        full_df = classes.join(df_rn_meas_avg, how='outer').join(df_rn_mod, how='outer').join(df_fp, how='outer')
        full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error')]  # remove error columns
        full_df['ch4_diff'] = np.nan

    full_df.reset_index(inplace=True)

    if year == '2021':
        # Mar 2021 - Feb 2022 (1 year of data)
        full_df = full_df[config.in_paper_year(full_df['time'])].copy()
    elif year == '2020/2021':
        full_df = full_df[(full_df['time'] < '2022-01-01') & (full_df['time'] > '2019-12-31 23:00')].copy()

    full_df.insert(loc=full_df.columns.get_loc('time') + 1, column='Season', value=config.season_of(full_df['time']))

    # Spread columns (std of the same quantity)
    full_df['radon_spread'] = full_df['radon']
    full_df[f'{mod}_spread'] = full_df[mod]
    full_df['wind_speed_spread'] = full_df['wind_speed']
    full_df['PBLH_spread'] = full_df['PBLH']

    agg = {'radon': 'mean', 'radon_spread': 'std', mod: 'mean', f'{mod}_spread': 'std'}
    if site in ('hfd', 'rgl'):
        full_df['ch4_spread_low'] = full_df['ch4_C_low']
        full_df['ch4_spread_high'] = full_df['ch4_C_high']
        full_df['ch4_diff_spread'] = full_df['ch4_diff']
        agg.update({'ch4_C_low': 'mean', 'ch4_spread_low': 'std',
                    'ch4_C_high': 'mean', 'ch4_spread_high': 'std',
                    'ch4_diff': 'mean', 'ch4_diff_spread': 'std'})
    elif site == 'tac':
        full_df['ch4_diff_spread'] = full_df['ch4_diff']
        agg.update({'ch4_diff': 'mean', 'ch4_diff_spread': 'std'})
    agg.update({'wind_speed': 'mean', 'wind_speed_spread': 'std', 'PBLH': 'mean', 'PBLH_spread': 'std'})
    if site == 'wao':
        agg.update({'ch4_diff': 'mean'})

    if average == 'monthly':
        full_df.insert(loc=0, column='Month', value=full_df['time'].dt.month)
        full_df.insert(loc=full_df.columns.get_loc('Month') + 1, column='Hour', value=full_df['time'].dt.hour)
        full_avg = full_df.groupby(['class', 'Month', 'Hour']).agg(agg).reset_index()

    elif average == 'seasonal':
        full_df.insert(loc=full_df.columns.get_loc('Season') + 1, column='Hour', value=full_df['time'].dt.hour)
        full_avg = full_df.groupby(['class', 'Season', 'Hour']).agg(agg).reset_index()

    if save:
        full_avg.to_csv(config.intem_seasonal_avg(site, average, year))

    return full_avg


# =============================================================================
#   3. Fraction of retained / excluded hours by hour of day (Fig 8)
# =============================================================================
def current_intem_counts(site, year='2021', save=True):
    # Time series of current InTEM classes
    ali_cl = pd.read_csv(config.intem_classes_allhours(site), parse_dates=[0])

    if year == '2021':
        # Mar 2021 - Feb 2022 (1 year of data)
        ali_cl = ali_cl[config.in_paper_year(ali_cl['time'])]
    elif year == '2020/2021':
        ali_cl = ali_cl[(ali_cl['time'] < '2022-01-01') & (ali_cl['time'] > '2019-12-31 23:00')]
    elif year == 'all':
        pass

    ali_cl = ali_cl.copy()
    ali_cl.insert(loc=ali_cl.columns.get_loc('time') + 1, column='Season', value=config.season_of(ali_cl['time']))
    ali_cl.insert(loc=ali_cl.columns.get_loc('Season') + 1, column='Hour', value=ali_cl['time'].dt.hour)

    counts = ali_cl.groupby(['class', 'Season', 'Hour']).count()
    counts.reset_index(inplace=True)
    counts['fraction'] = (counts['time'] / counts.groupby(['Season', 'Hour'])['time'].transform('sum'))

    if save:
        counts.to_csv(config.intem_seasonal_counts(site), index=False)

    return counts


# %%
if __name__ == '__main__':
    for site in config.SITE_LIST:
        intem_file_processing(site)
        current_intem_averaging(site, average='seasonal', year='2021')
        current_intem_counts(site, year='2021')
