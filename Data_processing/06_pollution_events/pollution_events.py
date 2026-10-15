"""
TITLE: pollution_events.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Combine, for every 4 h window in Mar 2021 - Feb 2022, the current
         InTEM selection (S), the two-class and three-class radon selections
         (class_2cl, class_3cl), the CH4 pollution enhancement above baseline
         (Poll) and NAME PBLH / wind speed, then keep the pollution periods
         (Poll > 200 nmol/mol).
           -> {SITE}_all_class_rdiff.csv
           -> {SITE}_all_class_rdiff_poll_events.csv   (Fig 11)

SOURCE FILE: Radon_Method/Exclusion_Windows_FINAL_UPDATES_NEW_RELATIVE_DIFF/All_plots/
             Pollution_plots/NEW_relative_difference/makefile.ipynb
CHANGES:
  - Runs for all four sites in a loop (the notebook had `site = 'WAO'` set by hand).
  - Paths from config.py.
  - FIX: the notebook merged with `df_rs` (radiosonde PBLH, HFD only), but the
    cell that created df_rs was commented out, so the notebook raised a
    NameError when re-run. The radiosonde merge is removed; its column (hcon)
    was not used by Fig 11.
  - FIX: the pollution filter was df_all[df['Poll'] > 200], i.e. a mask built
    on `df` applied to `df_all` (different rows after the inner merge with
    PBLH). It is now df_all[df_all['Poll'] > 200]. Re-check the Fig 11 counts
    against the current figure after re-running.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from common import to_4h  # noqa: E402


def pollution_events(site, save=True):
    site_l = site.lower()
    mod = config.rn_mod_col(site_l)

    # Current InTEM selection (S = 1 retained) with Poll column
    one = pd.read_csv(config.intem_obs_selection(site_l, 2021), sep=r'\s+', skiprows=6)
    two = pd.read_csv(config.intem_obs_selection(site_l, 2022), sep=r'\s+', skiprows=6)
    ali = pd.concat([one, two], ignore_index=True)
    ali.insert(loc=0, column='time', value=pd.to_datetime(dict(year=ali.Yr, month=ali.M, day=ali.D,
                                                               hour=ali.Hr, minute=ali.Mi, second=ali.Se)))
    ali.drop(columns=['Yr', 'M', 'D', 'Hr', 'Mi', 'Se', 'Index', 'ObsVr', 'ObsVF', 'UMult'], inplace=True)

    # Radon method
    rn2 = pd.read_csv(config.sel_4h_2class(site_l), parse_dates=[0])
    rn3 = pd.read_csv(config.sel_4h_3class(site_l), parse_dates=[0])
    rn2.drop(columns=[mod], inplace=True)
    rn3.drop(columns=['Season', 'radon', mod], inplace=True)

    # Merge dataframes
    df = ali.merge(rn2, how='inner', on='time').merge(rn3, how='inner', on='time', suffixes=['_2cl', '_3cl'])

    # Time series of modelled PBLH and wind speed, 4 hourly average
    df_fp = to_4h(pd.read_csv(config.pblh_ws(site_l), parse_dates=[0]))

    df_all = df.merge(df_fp, how='inner', on='time')
    df_all = df_all[['time', 'Season', 'Poll', 'radon', 'S', 'class_2cl', 'class_3cl', 'wind_speed', 'PBLH']]

    df_poll = df_all[df_all['Poll'] > 200]

    if save:
        df_all.to_csv(config.pollution_all(site_l), index=False)
        df_poll.to_csv(config.pollution_events(site_l), index=False)
    return df_poll


# %%
if __name__ == '__main__':
    for site in config.SITE_LIST:
        pollution_events(site)
