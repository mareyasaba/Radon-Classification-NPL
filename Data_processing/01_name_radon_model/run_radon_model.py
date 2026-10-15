"""
TITLE: run_radon_model.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Run the NAME radon forward model month by month (Jan 2020 - Dec 2022)
         with the traceRadon GLDAS-Noah monthly flux map, then merge the
         monthly outputs into the two files every later step reads:
           for_all_months_noah_monthly.nc   (time x cat, all four sites)
           for_noah_monthly_202001-202212.csv (cat 0 + cat 1 summed; used by Fig 3)

SOURCE FILES:
  - Regional_modelling/New_code/loop_rn.py          (monthly loop)
  - Regional_modelling/New_code/radon_output_merge.ipynb (merge cells)
CHANGES:
  - loop_rn.py looped over ERA5-Land and GLDAS-Noah maps and a partial list of
    months (its last edit re-ran only 2020-06/08/09/10). Here it loops over the
    paper's map only and all 36 months; pass a subset with --months to re-run
    a few months.
  - os.system replaced by subprocess.run (same command line).
  - The merge cell for ERA5-Land is dropped.

USAGE (from this folder):
  python run_radon_model.py                 # run all months, then merge
  python run_radon_model.py --merge-only    # just rebuild the merged files
  python run_radon_model.py --months 2020-06 2020-08
"""

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config  # noqa: E402

ALL_MONTHS = [d.strftime('%Y-%m') for d in pd.date_range('2020-01-01', '2022-12-01', freq='MS')]


def run_months(months, radon_map=config.RADON_MAP):
    """Run core.py once per month (was loop_rn.py)."""
    odir = config.name_rn_output_dir()
    odir.mkdir(parents=True, exist_ok=True)
    for date in months:
        cmd = [sys.executable, 'core.py',
               '-date', date,
               '-iset', '',
               '-dset', f'set_222rn_traceRadon_{radon_map}',
               '-cfile', 'calc_Rn_gb_eng',
               '-rmode', '0',
               '-odir', str(odir)]
        print(' '.join(cmd))
        subprocess.run(cmd, cwd=HERE, check=True)


def merge_outputs(radon_map=config.RADON_MAP):
    """Merge monthly for_YYYY-MM.nc files (was radon_output_merge.ipynb)."""
    odir = config.name_rn_output_dir()

    # Cell 1: all months into one NetCDF
    ds = xr.open_mfdataset(str(odir / 'for_*-*.nc'))
    ds.to_netcdf(path=config.rn_mod_all_months_nc(), mode='w', format='NETCDF4')

    # Cell 2: add category 0 and 1 (we need the total modelled radon) and save as CSV
    ds = xr.open_dataset(config.rn_mod_all_months_nc())
    df = ds.to_dataframe().reset_index()
    df_grouped = df.groupby(['time']).sum(numeric_only=True).reset_index().drop(columns=['cat'])
    df_grouped.to_csv(config.rn_mod_all_months_csv(), sep=',', index=False)
    return df_grouped


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--months', nargs='*', default=ALL_MONTHS)
    parser.add_argument('--merge-only', action='store_true')
    args = parser.parse_args()

    if not args.merge_only:
        run_months(args.months)
    merge_outputs()
