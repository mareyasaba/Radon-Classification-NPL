"""
TITLE: radon_selection_files.py
AUTHOR: Mareya Saba
DATE CREATED: 27/07/2023
DATE LAST EDITED:
PURPOSE: Build the 4 h radon observation-selection files for Mar 2021 - Feb 2022
         that were sent to InTEM, using the relative radon model-measurement
         difference  dRn_rel = (Rn_mod - Rn_meas) / Rn_meas.
           two_class_file():   retain the central part of each site/season
                               distribution so the retained fraction matches
                               the current InTEM method (Table 2).
           three_class_file(): retain the small + medium mismatch classes
                               (central 60 %, i.e. 20th-80th percentile).
         Outputs (per site):
           {site}_4h_2class_rel.csv, {SITE}_Rn_Rel_2cl_selection_1yr.txt
             -> Figs 5, 6 (grey shading), 7, 8 (via radon_intem_2class.py), 11
           {site}_4h_3class_rel.csv, {SITE}_Rn_Rel_3cl_selection_1yr.txt
             -> Fig 11, InTEM 3-class inversion
         class = 1 retained, class = 0 excluded (including windows with no
         measured radon).

SOURCE FILES:
  - Radon_Method/Exclusion_Windows_InTEM_Prep/Relative_difference_new/2cl/selection_file_creation_1yr.py
  - Radon_Method/Exclusion_Windows_InTEM_Prep/Relative_difference_new/3cl/selection_file_creation_1yr_scaled.py
CHANGES:
  - The two scripts shared Parts 1, 3 and 4 line for line; these are now
    shared helpers. The threshold logic of each (Part 2) is unchanged.
  - Paths from config.py.
NOTES:
  - The '3-class' InTEM file is binary: it marks small + medium (retained)
    vs large (excluded). The full small/medium/large classes used in Figs 4, 9
    and 10 come from radon_hourly_classes.py instead.
  - Acceptance rates are divided by the fraction of windows with measured
    radon ('scale') so that the retained share of ALL windows matches the
    target; when that exceeds 100 % every window with valid radon is retained.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from common import load_rn_meas_hourly, load_rn_mod_hourly, to_4h  # noqa: E402

# Percentage of 4 h windows retained by the current InTEM method,
# calculated from the InTEM files for Mar 21 - Feb 22 (Table 2).
DIC_ACCEPT = {'HFD': {'DJF': 63, 'MAM': 61, 'JJA': 58, 'SON': 50},
              'TAC': {'DJF': 63, 'MAM': 62, 'JJA': 63, 'SON': 53},
              'RGL': {'DJF': 60, 'MAM': 58, 'JJA': 54, 'SON': 50},
              'WAO': {'DJF': 51, 'MAM': 64, 'JJA': 48, 'SON': 44}}

# Percentages calculated from ALL of the InTEM files (2020 - 2022); not used.
# DIC_ACCEPT_ALL = {'HFD': {'DJF':62, 'MAM':59, 'JJA':49, 'SON':53},
#                   'TAC': {'DJF':58, 'MAM':60, 'JJA':62, 'SON':56},
#                   'RGL': {'DJF':60, 'MAM':58, 'JJA':58, 'SON':55},
#                   'WAO': {'DJF':56, 'MAM':57, 'JJA':52, 'SON':53}}


# =============================================================================
#   PART 1: load meas/mod radon, average over 4 h, relative difference
# =============================================================================
def _rn_4h_relative_difference(site):
    mod = config.rn_mod_col(site)

    df_rn_meas = to_4h(load_rn_meas_hourly(site))   # 30-min -> hourly -> 4 h mean
    df_rn_mod = to_4h(load_rn_mod_hourly())         # cat 0 + cat 1 -> 4 h mean

    # Merge dataframes and calculate difference
    merge = df_rn_meas.merge(df_rn_mod, how='outer', on='time')
    merge['relative difference'] = (merge[mod] - merge['radon']) / (merge['radon'])
    merge = merge[['time', 'radon', mod, 'relative difference']]

    # 1 YEAR DATA MAR 2021 - FEB 2022
    merge = merge[config.in_paper_year(merge['time'])].sort_values(by='time', ignore_index=True)

    merge.insert(loc=merge.columns.get_loc('time') + 1, column='Season', value=config.season_of(merge['time']))
    return merge


def _seasonal_values(merge, s):
    """Finite relative differences for one season (the distribution percentiles come from)."""
    return merge.loc[(merge['Season'] == s) & np.isfinite(merge['relative difference']), 'relative difference']


def _classify_central(merge, s, values, lp, hp, site):
    """class 1 if lp-th < dRn_rel <= hp-th percentile, else class 0."""
    p_lo = np.percentile(values.values, lp)
    p_hi = np.percentile(values.values, hp)
    print(f'{site}, {s}, {lp} percentile: {p_lo}')
    print(f'{site}, {s}, {hp} percentile: {p_hi}')

    rd = merge['relative difference']
    merge.loc[(merge['Season'] == s) & ((rd > p_lo) & (rd <= p_hi)), 'class'] = int(1)
    merge.loc[(merge['Season'] == s) & ((rd > p_hi) | (rd <= p_lo)), 'class'] = int(0)


# =============================================================================
#   PARTS 3-4: InTEM fixed-width format
# =============================================================================
def _write_intem_file(merge, site, path):
    merge = merge.copy()
    mod = config.rn_mod_col(site)

    merge.insert(loc=0, column='Index', value=merge.index)
    merge.insert(loc=0, column='Se', value=merge['time'].dt.second)
    merge.insert(loc=0, column='Mi', value=merge['time'].dt.minute)
    merge.insert(loc=0, column='Hr', value=merge['time'].dt.hour)
    merge.insert(loc=0, column='D', value=merge['time'].dt.day)
    merge.insert(loc=0, column='M', value=merge['time'].dt.month)
    merge.insert(loc=0, column='Yr', value=merge['time'].dt.year)
    merge.drop(columns=['time', 'Season'], inplace=True)

    merge.rename(columns={'radon': 'RnMeas', mod: 'RnMod', 'relative difference': 'RnDiff', 'class': 'S'},
                 inplace=True)

    c_move = merge.pop("S")
    merge.insert(loc=merge.columns.get_loc('Se') + 1, column='S', value=c_move)

    odata_cols = {
        'Yr': {'v': '5d', 'h': '>5s'},
        'M': {'v': '2d', 'h': '>2s'},
        'D': {'v': '2d', 'h': '>2s'},
        'Hr': {'v': '2d', 'h': '>2s'},
        'Mi': {'v': '2d', 'h': '>2s'},
        'Se': {'v': '2d', 'h': '>2s'},
        'Index': {'v': '5d', 'h': '5s'},
        'S': {'v': '1d', 'h': '1s'},
        'RnMeas': {'v': '7.4f', 'h': '>7s'},
        'RnMod': {'v': '7.4f', 'h': '>7s'},
        'RnDiff': {'v': '7.4f', 'h': '>7s'},
    }
    odata_col_seq = ['Yr', 'M', 'D', 'Hr', 'Mi', 'Se', 'Index', 'S', 'RnMeas', 'RnMod', 'RnDiff']
    odata = pd.concat([merge[i].apply(lambda x: f'{x:{odata_cols[i]["v"]}}') for i in odata_col_seq], axis=1)
    odata.columns = [f'{i:{odata_cols[i]["h"]}}' for i in odata_col_seq]

    # NOTE (not changed): to_csv with sep=' ' wraps every padded field in double
    # quotes (e.g. " 2021"), as in the original script. If InTEM needs plain
    # fixed-width text, write with open(path,'w').write(odata.to_string(index=False)).
    odata.to_csv(path, sep=' ', index=False)
    return merge


# =============================================================================
#   PART 2a: two classes (match current InTEM retention)
# =============================================================================
def two_class_file(site, save=True):
    merge = _rn_4h_relative_difference(site)

    for s in config.SEASONS:
        values = _seasonal_values(merge, s)
        m_s = merge[merge['Season'] == s]
        scale = 1 - (m_s['radon'].isna().sum()) / len(m_s.index)  # SCALE ACCEPTANCE RATE TO ACCOUNT FOR NANS
        new_accept = DIC_ACCEPT[site.upper()][s] / scale

        if new_accept > 100:
            merge.loc[(merge['Season'] == s) & (np.isfinite(merge['relative difference'])), 'class'] = int(1)
            merge.loc[(merge['Season'] == s) & (np.isnan(merge['relative difference'])), 'class'] = int(0)
        else:
            lp = (100 - new_accept) / 2
            hp = 100 - lp
            _classify_central(merge, s, values, lp, hp, site)

    merge['class'] = merge['class'].fillna(0.0).astype(int)

    if save:
        merge.to_csv(config.sel_4h_2class(site), index=False)
        _write_intem_file(merge, site, config.sel_4h_2class_txt(site))
    return merge


# =============================================================================
#   PART 2b: three classes -> retain small + medium (central 60 %)
# =============================================================================
def three_class_file(site, save=True):
    merge = _rn_4h_relative_difference(site)

    for s in config.SEASONS:
        values = _seasonal_values(merge, s)
        m_s = merge[merge['Season'] == s]
        prop_nan = (m_s['radon'].isna().sum()) / len(m_s.index)

        if prop_nan > 0.5:
            # Too many missing measurements to rescale: plain 20th-80th percentiles
            lp = 20
            hp = 80
        else:
            scale = 1 - prop_nan  # SCALE ACCEPTANCE RATE TO ACCOUNT FOR NANS
            new_accept = 60 / scale
            lp = (100 - new_accept) / 2
            hp = 100 - lp
        _classify_central(merge, s, values, lp, hp, site)

    merge['class'] = merge['class'].fillna(0.0).astype(int)

    if save:
        merge.to_csv(config.sel_4h_3class(site), index=False)
        _write_intem_file(merge, site, config.sel_4h_3class_txt(site))
    return merge


# %%
if __name__ == '__main__':
    for site in config.SITE_LIST:
        two_class_file(site)
        three_class_file(site)
