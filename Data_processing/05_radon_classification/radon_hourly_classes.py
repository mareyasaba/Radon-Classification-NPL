"""
TITLE: radon_hourly_classes.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Hourly radon classification and its seasonal diurnal summaries:
           1. classify_two_class() / classify_three_class():
              hourly dRn_rel = (Rn_mod - Rn_meas) / Rn_meas, classified per
              site and season by percentiles.
                2 classes: 'low' (retained) / 'high' (excluded) mismatch
                3 classes: 1 small (40-60th), 2 medium (20-40th, 60-80th),
                           3 large (<=20th, >80th)  (Table 3)
              -> {site}_2class_NS_rel.csv  (Fig 4a)
              -> {site}_3class_NS_rel.csv  (Fig 4b)
           2. class_averaging(): seasonal diurnal composites of radon, signed
              CH4 inlet difference, PBLH and wind speed per class.
              -> {site}_seasonal_3class_rel.csv (Fig 9)
              -> {site}_seasonal_2class_rel.csv (not used by a paper figure)
           3. class_counts(): fraction of hours in each class by hour of day.
              -> {site}_seasonal_3class_counts_rel.csv (Fig 10)
              -> {site}_seasonal_2class_counts_rel.csv (not used by a paper figure)

SOURCE FILES (Radon_Method/Exclusion_Windows_New/RELATIVE_DIFFERENCES/{SITE}_exclusion_windows/):
  - classification.py                                         -> 1
  - everything_averaging.py (HFD, RGL), everything_averaging_NEW.py (TAC, WAO) -> 2
  - counts.py                                                 -> 3
CHANGES:
  - Four per-site copies of each script merged into functions with a `site`
    argument; per-site settings (2-class percentiles, TAC/WAO CH4 handling)
    kept as explicit dictionaries/branches.
  - Paths from config.py (the originals used '../{SITE} exclusion windows/...').
  - The monthly branch of counts.py (groupby('class','Month'), which would raise
    an error) is not carried over; only seasonal counts are used.
  - classification_additional.py (absolute difference, HFD only) is not
    carried over.
NOTES:
  - ISSUE: in the original two_class() for RGL, TAC and WAO the column called
    'relative difference' was the ABSOLUTE difference Rn_mod - Rn_meas (only
    HFD divided by Rn_meas). Fig 4 (HFD) is unaffected; the Supplement
    cumulative plots for RGL, TAC and WAO are. Corrected here; set
    config.REPRODUCE_ORIGINAL_OUTPUTS = True to reproduce the original files.
  - ISSUE (not changed): two_class() keeps only Mar 2021 - Feb 2022, but
    three_class() has no date filter, so the 3-class percentiles and the
    Fig 4b / 9 / 10 composites use all model-measurement overlap in 2020-2022,
    while the Fig 9 caption says JJA 2021. Pass restrict_to_paper_year=True
    if Mar 2021 - Feb 2022 is intended.
  - ISSUE (not changed): DIC_PERCS are hard-coded and are NOT NaN-adjusted
    ("NOTE: NOT NAN-ADJUSTED PERCENTILES" in the original Fig 4 script),
    whereas the 4 h InTEM selection files (radon_selection_files.py) rescale
    the acceptance rate for missing radon. The Fig 4a threshold lines
    therefore may not equal the thresholds applied in the InTEM selection.
  - ISSUE (not changed): TAC uses ch4_diff_low-mid (54 m - 100 m); the Fig 9
    caption says 54 and 185 m.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from common import load_rn_meas_hourly, load_rn_mod_hourly  # noqa: E402

# Lower/upper percentiles of dRn_rel for the hourly two-class split
# (chosen to match the current InTEM seasonal retention; not NaN-adjusted).
DIC_PERCS = {'hfd': {'DJF': [18.5, 81.5], 'MAM': [19.5, 80.5], 'JJA': [21, 79], 'SON': [25, 75]},
             'tac': {'DJF': [18.5, 81.5], 'MAM': [19, 81], 'JJA': [18.5, 81.5], 'SON': [23.5, 76.5]},
             'rgl': {'DJF': [20, 80], 'MAM': [21, 79], 'JJA': [23, 77], 'SON': [25, 75]},
             'wao': {'DJF': [24.5, 75.5], 'MAM': [18, 82], 'JJA': [26, 74], 'SON': [28, 72]}}


# =============================================================================
#   1. Hourly classification
# =============================================================================
def _rn_hourly(site, absolute=False):
    """Hourly measured radon merged (inner) with modelled radon, plus dRn_rel."""
    mod = config.rn_mod_col(site)
    df_rn_meas_avg = load_rn_meas_hourly(site)   # average Rn measurements over an hour
    df_rn_mod = load_rn_mod_hourly()             # add both category 0 and 1

    merge = df_rn_meas_avg.merge(df_rn_mod, how='inner', on='time')
    if absolute:
        merge['relative difference'] = merge[mod] - merge['radon']
    else:
        merge['relative difference'] = (merge[mod] - merge['radon']) / (merge['radon'])
    merge = merge[['time', 'radon', mod, 'relative difference']]
    return merge


def _add_season(merge):
    merge = merge.copy()
    merge.insert(loc=merge.columns.get_loc('time') + 1, column='Season', value=config.season_of(merge['time']))
    return merge


def _seasonal_values(merge, s):
    return merge.loc[(merge['Season'] == s) & np.isfinite(merge['relative difference']), 'relative difference']


def classify_three_class(site, restrict_to_paper_year=False, save=True):
    merge = _rn_hourly(site)

    # ISSUE: no date filter in the original (see header).
    if restrict_to_paper_year:
        merge = merge[config.in_paper_year(merge['time'])]

    merge = _add_season(merge)
    rd = merge['relative difference']

    for s in config.SEASONS:
        v = _seasonal_values(merge, s).values
        p20, p40, p60, p80 = (np.percentile(v, q) for q in (20, 40, 60, 80))
        print(f'{site.upper()}, {s}: 20th {p20}, 40th {p40}, 60th {p60}, 80th {p80}')

        in_s = merge['Season'] == s
        merge.loc[in_s & (rd > p40) & (rd <= p60), 'class'] = 1   # small
        merge.loc[in_s & (rd > p20) & (rd <= p40), 'class'] = 2   # medium
        merge.loc[in_s & (rd > p60) & (rd <= p80), 'class'] = 2   # medium
        merge.loc[in_s & (rd > p80), 'class'] = 3                 # large
        merge.loc[in_s & (rd <= p20), 'class'] = 3                # large

    if save:
        merge.to_csv(config.hourly_class(site, '3'), index=False)
    return merge


def classify_two_class(site, save=True):
    # ISSUE: RGL, TAC and WAO originally used the absolute difference (see header).
    absolute = config.REPRODUCE_ORIGINAL_OUTPUTS and site in ('rgl', 'tac', 'wao')
    merge = _rn_hourly(site, absolute=absolute)

    # We are only taking data from Mar-2021 to Feb-2022 (i.e. 1 year of data)
    merge = merge[config.in_paper_year(merge['time'])]
    merge = _add_season(merge)
    rd = merge['relative difference']

    for s in config.SEASONS:
        v = _seasonal_values(merge, s).values
        lo, hi = DIC_PERCS[site][s]
        p_lo, p_hi = np.percentile(v, lo), np.percentile(v, hi)
        print(f'{site.upper()}, {s}: {lo} percentile {p_lo}, {hi} percentile {p_hi}')

        in_s = merge['Season'] == s
        merge.loc[in_s & ((rd > p_lo) & (rd <= p_hi)), 'class'] = 'low'
        merge.loc[in_s & ((rd > p_hi) | (rd <= p_lo)), 'class'] = 'high'

    if save:
        merge.to_csv(config.hourly_class(site, '2'), index=False)
    return merge


# =============================================================================
#   2. Seasonal / monthly diurnal averages per class
# =============================================================================
def class_averaging(site, classes='2', average='seasonal', save=True):
    mod = config.rn_mod_col(site)

    # Time series of Rn mod, meas, difference with column for classification
    rn_mod_meas = pd.read_csv(config.hourly_class(site, classes), parse_dates=[0])
    rn_mod_meas.set_index('time', inplace=True)

    # Time series of modelled PBLH and wind speed
    df_fp = pd.read_csv(config.pblh_ws(site), parse_dates=[0])
    df_fp.set_index('time', inplace=True)

    # MERGE ALL DATAFRAMES TOGETHER
    if site in ('hfd', 'rgl'):
        df_vdiff_interp = pd.read_csv(config.vdiff_interp(site), parse_dates=[0]).set_index('time')
        full_df = rn_mod_meas.join(df_vdiff_interp, how='left').join(df_fp, how='left')
        full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error')]  # remove error columns
    elif site == 'tac':
        df_vdiff_interp = pd.read_csv(config.vdiff_interp(site), parse_dates=[0]).set_index('time')
        # ISSUE: 54 m - 100 m; caption says 54 and 185 m (ch4_diff_low-high).
        df_vdiff_interp.rename(columns={'ch4_diff_low-mid': 'ch4_diff'}, inplace=True)
        full_df = rn_mod_meas.join(df_vdiff_interp, how='left').join(df_fp, how='left')
        full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error|ch4_C')]  # remove error columns
    elif site == 'wao':
        full_df = rn_mod_meas.join(df_fp, how='left')
        full_df = full_df.loc[:, ~full_df.columns.str.contains('stdev|error')]
        full_df['ch4_diff'] = np.nan  # single CH4 inlet

    # Spread columns (std of the same quantity)
    full_df['radon_spread'] = full_df['radon']
    full_df[f'{mod}_spread'] = full_df[mod]
    full_df['wind_speed_spread'] = full_df['wind_speed']
    full_df['PBLH_spread'] = full_df['PBLH']

    agg = {'radon': 'mean', 'radon_spread': 'std', mod: 'mean', f'{mod}_spread': 'std',
           'relative difference': 'mean'}
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

    full_df.reset_index(inplace=True)

    if average == 'monthly':
        full_df.insert(loc=0, column='Month', value=full_df['time'].dt.month)
        full_df.insert(loc=full_df.columns.get_loc('Month') + 1, column='Hour', value=full_df['time'].dt.hour)
        full_avg = full_df.groupby(['class', 'Month', 'Hour']).agg(agg).reset_index()
    elif average == 'seasonal':
        full_df.insert(loc=full_df.columns.get_loc('Season') + 1, column='Hour', value=full_df['time'].dt.hour)
        full_avg = full_df.groupby(['class', 'Season', 'Hour']).agg(agg).reset_index()

    if save:
        full_avg.to_csv(config.hourly_class_avg(site, classes, average))
    return full_avg


# =============================================================================
#   3. Class fractions by hour of day
# =============================================================================
def class_counts(site, classes='2', save=True):
    rn_mod_meas = pd.read_csv(config.hourly_class(site, classes), parse_dates=[0])
    rn_mod_meas.insert(loc=rn_mod_meas.columns.get_loc('Season') + 1, column='Hour', value=rn_mod_meas['time'].dt.hour)

    counts = rn_mod_meas.groupby(['class', 'Season', 'Hour']).count()
    counts.reset_index(inplace=True)
    counts['fraction'] = (counts['time'] / counts.groupby(['Season', 'Hour'])['time'].transform('sum'))

    if save:
        counts.to_csv(config.hourly_class_counts(site, classes), index=False)
    return counts


# %%
if __name__ == '__main__':
    for site in config.SITE_LIST:
        classify_two_class(site)
        classify_three_class(site)
        for c in ['2', '3']:
            class_averaging(site, classes=c, average='seasonal')
            class_counts(site, classes=c)
