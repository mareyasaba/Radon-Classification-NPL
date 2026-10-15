"""
TITLE: config.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Single place for every file path and site setting used by the
         Data_processing scripts. Replaces the hard-coded Windows and macOS
         paths in the original scripts (C:\\Users\\ms20\\..., /Users/mareyasaba/...).
         Edit DATA_DIR (and OUTPUT_DIR if wanted) once and every step follows.

LAYOUT ASSUMED
  data/raw/            inputs not produced by this repository (CEDA/ICOS radon,
                       CH4 exports, radon flux maps, NAME footprints, InTEM files)
  Data_processing/outputs/<step>/   everything written by the scripts here
"""

from pathlib import Path

import numpy as np
import pandas as pd

# =============================================================================
#   Top-level directories
# =============================================================================
REPO_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
OUTPUT_DIR = REPO_DIR / 'Data_processing' / 'outputs'

# Radon flux map used for the paper (traceRadon GLDAS-Noah, monthly)
RADON_MAP = 'noah_monthly'

# Two errors were found in the original scripts while consolidating them:
#   (a) the RGL current-InTEM averages used HFD's InTEM classes
#       (04_current_intem/current_intem.py, Fig 7 RGL 'Current' panels);
#   (b) the hourly 2-class files for RGL, TAC and WAO used the ABSOLUTE
#       difference Rn_mod - Rn_meas instead of the relative difference
#       (05_radon_classification/radon_hourly_classes.py; Supplement
#       cumulative plots for those sites).
# False (default): the corrected behaviour.
# True: reproduce the files exactly as they were made for the current figures.
REPRODUCE_ORIGINAL_OUTPUTS = False

# Analysis year used in the paper (Mar 2021 - Feb 2022)
YEAR_START = '2021-02-28 23:00'   # strictly after
YEAR_END = '2022-03-01'           # strictly before

# =============================================================================
#   Site settings
# =============================================================================
# rn_ext   : suffix of the modelled radon variable, e.g. 'enh_rn-i0_ac_hfd100'
# fp_dir   : footprint folder name used for PBLH / wind speed
# fp_name  : NAME release name used in the footprint file names
# ch4      : CH4 inlet heights (m a.g.l.) used for the signed inlet difference
SITES = {
    'hfd': {'rn_ext': 'hfd100', 'fp_dir': 'HFD100', 'fp_name': 'HFD-100magl',
            'ch4': {'low': '50', 'high': '100'}},
    'tac': {'rn_ext': 'tac185', 'fp_dir': 'TAC185', 'fp_name': 'TAC-185magl',
            'ch4': {'low': '54', 'mid': '100', 'high': '185'}},
    'rgl': {'rn_ext': 'rgl090', 'fp_dir': 'RGL90', 'fp_name': 'RGL-90magl',
            'ch4': {'low': '45', 'high': '90'}},
    'wao': {'rn_ext': 'wao020', 'fp_dir': 'WAO20', 'fp_name': 'WAO-20magl',
            'ch4': {}},  # single CH4 inlet: no signed inlet difference
}
SITE_LIST = ['hfd', 'tac', 'rgl', 'wao']


def rn_mod_col(site):
    """Name of the modelled radon column for a site, e.g. 'enh_rn-i0_ac_hfd100'."""
    return f'enh_rn-i0_ac_{SITES[site]["rn_ext"]}'


# =============================================================================
#   Raw inputs (data/raw)
# =============================================================================
def radon_obs(site):
    """Measured radon (CEDA NetCDF), one file per site."""
    return RAW_DIR / 'radon_obs' / f'{site.upper()}_ceda.nc'


RADON_FLUX_ZHANG = RAW_DIR / 'radon_flux_maps' / 'E3.nc'
RADON_FLUX_TRACERADON = (RAW_DIR / 'radon_flux_maps'
                         / 'name_traceRadon_rnflux_GLDAS-Noah_month_2006-2022_v0.6.nc')


def name_rn_footprint_pattern(site):
    """NAME radon footprints (strftime pattern). NOT in the original directory."""
    d = SITES[site]
    return str(RAW_DIR / 'name_footprints' / 'radon' / d['fp_dir']
               / f'{d["fp_name"]}_UKV_rn_EUROPE_%Y%m.nc')


def name_met_footprint_glob(site):
    """NAME CH4 footprints with PBLH and wind speed. NOT in the original directory."""
    d = SITES[site]
    return str(RAW_DIR / 'name_footprints' / 'methane' / d['fp_dir']
               / f'{d["fp_name"]}_UKV_EUROPE_*.nc')


def ch4_raw_60min(site, height):
    """CH4 export at one inlet (was Regional_modelling/Data/METHANE/obs/Raw_exported_data)."""
    return RAW_DIR / 'ch4_obs' / f'{site}{height}_60min.csv'


def ch4_raw_min(site, height):
    """Minute CH4 at one inlet, used only by the Fig 5 top panel
    (was Regional_modelling/Data/METHANE/obs/Processed_raw_data/{site}{h}_min.csv)."""
    return RAW_DIR / 'ch4_obs' / f'{site}{height}_min.csv'


def intem_current_dir(site):
    """Monthly current-InTEM time series files (was Alistair_InTEM_2020-22/{SITE}/)."""
    return RAW_DIR / 'intem_current' / site.upper()


def intem_obs_selection(site, year):
    """Current-InTEM observation selection file (was Alistair_InTEM_2020-22/{SITE}_NN_obs_selection_{year}.txt)."""
    return RAW_DIR / 'intem_current' / f'{site.upper()}_NN_obs_selection_{year}.txt'


# =============================================================================
#   Outputs written by Data_processing (Data_processing/outputs/<step>/)
# =============================================================================
def out_dir(step):
    p = OUTPUT_DIR / step
    p.mkdir(parents=True, exist_ok=True)
    return p


# 01 NAME radon model
def name_rn_output_dir():
    return out_dir('01_name_radon_model') / f'output_traceRadon_{RADON_MAP}'


def rn_mod_all_months_nc():
    return name_rn_output_dir() / f'for_all_months_{RADON_MAP}.nc'


def rn_mod_all_months_csv():
    return name_rn_output_dir() / f'for_{RADON_MAP}_202001-202212.csv'


# 02 CH4 obs processing
def ch4_60min_processed(site, height):
    return out_dir('02_ch4_obs_processing') / f'{site}{height}_60min_processed.csv'


def ch4_hour_interp(site, height):
    return out_dir('02_ch4_obs_processing') / f'{site}{height}_hour.csv'


def vdiff_interp(site):
    return out_dir('02_ch4_obs_processing') / f'{site}_vdiff_interp.csv'


# 03 NAME met (PBLH, wind speed)
def pblh_ws(site):
    return out_dir('03_name_met') / f'{site}_pblh_ws.csv'


def pblh_ws_allyears_nc(site):
    return out_dir('03_name_met') / f'{SITES[site]["fp_name"]}_allyears.nc'


# 04 current InTEM
def intem_missing_windows(site):
    return out_dir('04_current_intem') / f'{site.upper()}_missing_windows.csv'


def intem_classes_allhours(site):
    return out_dir('04_current_intem') / f'{site.upper()}_alistair_classes_allhours.csv'


def intem_seasonal_avg(site, average='seasonal', year='2021'):
    y = year.replace('/', '-')
    return out_dir('04_current_intem') / f'{site}_alistair_{average}_{y}.csv'


def intem_seasonal_counts(site):
    # Original name in Exclusion_Windows_New/{SITE}_exclusion_windows/Alistair/2021_only/
    # was {SITE}_alistair_classes_allhours.csv (same name as the hourly classes file);
    # renamed here so the two files can no longer be confused.
    return out_dir('04_current_intem') / f'{site.upper()}_alistair_classes_allhours_counts.csv'


# 05 radon classification
def sel_4h_2class(site):
    return out_dir('05_radon_classification') / f'{site}_4h_2class_rel.csv'


def sel_4h_2class_txt(site):
    return out_dir('05_radon_classification') / f'{site.upper()}_Rn_Rel_2cl_selection_1yr.txt'


def sel_4h_3class(site):
    return out_dir('05_radon_classification') / f'{site}_4h_3class_rel.csv'


def sel_4h_3class_txt(site):
    return out_dir('05_radon_classification') / f'{site.upper()}_Rn_Rel_3cl_selection_1yr.txt'


def hourly_class(site, classes):
    return out_dir('05_radon_classification') / f'{site}_{classes}class_NS_rel.csv'


def hourly_class_avg(site, classes, average='seasonal'):
    return out_dir('05_radon_classification') / f'{site}_{average}_{classes}class_rel.csv'


def hourly_class_counts(site, classes, average='seasonal'):
    return out_dir('05_radon_classification') / f'{site}_{average}_{classes}class_counts_rel.csv'


def intem_2class_avg(site, average='seasonal'):
    return out_dir('05_radon_classification') / f'{site}_intem_{average}_rel.csv'


def intem_2class_counts(site, average='seasonal'):
    return out_dir('05_radon_classification') / f'{site}_intem_{average}_counts_rel.csv'


def intem_2class_counts_4h(site, average='seasonal'):
    return out_dir('05_radon_classification') / f'{site}_intem_{average}_4h_counts_rel.csv'


# 06 pollution events
def pollution_all(site):
    return out_dir('06_pollution_events') / f'{site.upper()}_all_class_rdiff.csv'


def pollution_events(site):
    return out_dir('06_pollution_events') / f'{site.upper()}_all_class_rdiff_poll_events.csv'


# =============================================================================
#   Shared helpers
# =============================================================================
MONTH_TO_SEASON = np.array([
    None,
    'DJF', 'DJF',
    'MAM', 'MAM', 'MAM',
    'JJA', 'JJA', 'JJA',
    'SON', 'SON', 'SON',
    'DJF'])
SEASONS = ['DJF', 'MAM', 'JJA', 'SON']


def season_of(times):
    """Season label ('DJF', 'MAM', 'JJA', 'SON') for a datetime Series."""
    return MONTH_TO_SEASON[pd.Series(times).dt.month]


def in_paper_year(times):
    """Boolean mask for Mar 2021 - Feb 2022 (same bounds as every original script)."""
    return (times < YEAR_END) & (times > YEAR_START)
