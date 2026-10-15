"""
TITLE: set_222rn_traceRadon_noah_monthly.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Data-settings module (-dset) for the NAME radon forward model used in
         the paper: sites HFD 100 m, RGL 90 m, TAC 185 m, WAO 20 m; NAME radon
         footprints; radon flux = Zhang et al. (2011) global map (cat 0) and the
         traceRadon GLDAS-Noah monthly European map (cat 1); CEDA radon
         observations.

SOURCE FILE: Regional_modelling/New_code/set_222rn_traceRadon_noah_monthly.py
CHANGES: Hard-coded Windows paths replaced by config.py paths. Settings values
         (scales, variable names, combine rules) unchanged.
NOTES:
  - basis_functions and country_mask still point to the original HPC paths
    (/hpc-work/ec5/...). They are kept as found; check whether
    calc_Rn_gb_eng.py actually reads them before publishing.
  - The NAME radon footprints are not in the original Modelling/ directory.
  - The other five set_222rn_* variants (ERA5-Land, daily, InGOS) were not used
    in the paper and are not carried over.
"""

# Standard Library import
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

dset = {
    "sites": ["hfd100", "rgl090", "tac185", "wao020"],
    "basis_functions": {
        "f": "/hpc-work/ec5/work/isotope_testing/isotope_testing_files/basis_functions/uk-3x3_EUROPE_2019.nc",
        "var": {"val": "basis"}
    },
    "country_mask": {
        "f": "/hpc-work/ec5/work/isotope_testing/isotope_testing_files/countrymask/country-ukmo_EUROPE.nc",
        "var": {"val": "country"}
    },
    "species": {
        "rn": {
            "met": "rn",
            "scale": 101325.0 / 8.314 / 288.15
        }
    },
    "bg": {
        "rn": {
            "combine": "skip",
        }
    },
    "met": {
        "rn": {
            "f_hfd100": config.name_rn_footprint_pattern('hfd'),
            "f_rgl090": config.name_rn_footprint_pattern('rgl'),
            "f_tac185": config.name_rn_footprint_pattern('tac'),
            "f_wao020": config.name_rn_footprint_pattern('wao'),
            "var": {
                "D": "fp",
                "edge_n": "particle_locations_n",
                "edge_e": "particle_locations_e",
                "edge_s": "particle_locations_s",
                "edge_w": "particle_locations_w"
            },
            "scale": {
                "D": 1.0,
                "edge_n": 1.0,
                "edge_e": 1.0,
                "edge_s": 1.0,
                "edge_w": 1.0
            }
        }
    },
    "Q": {
        "rn": {
            "combine": "mean",
            str(config.RADON_FLUX_ZHANG): {
                "var": {"v_rn-i0_Q-0": "rnemis"},
                "scale": {"v_rn-i0_Q-0": 1.e4 * np.log(2.0) / 3.8232 / 86400.0}
            },
            str(config.RADON_FLUX_TRACERADON): {
                "var": {"v_rn-i0_Q-1": "rn_flux"},
                "scale": {"v_rn-i0_Q-1": 1.0}
            }
        }
    },
    "obs": {
        "combine": "mean",
        str(config.radon_obs('hfd')): {
            "var": {
                "v_rn-i0_ac_hfd100": "radon",
                "sd_rn-i0_ac_hfd100": "radon_uncertainty"
            },
            "scale": {
                "v_rn-i0_ac_hfd100": 1.0,
                "sd_rn-i0_ac_hfd100": 1.0
            },
            "dim": [
                "v_rn-i0_ac_hfd100"
            ]
        },
        str(config.radon_obs('rgl')): {
            "var": {
                "v_rn-i0_ac_rgl090": "radon",
                "sd_rn-i0_ac_rgl090": "radon_uncertainty"
            },
            "scale": {
                "v_rn-i0_ac_rgl090": 1.0,
                "sd_rn-i0_ac_rgl090": 1.0
            },
            "dim": [
                "v_rn-i0_ac_rgl090"
            ]
        },
        str(config.radon_obs('tac')): {
            "var": {
                "v_rn-i0_ac_tac185": "radon",
                "sd_rn-i0_ac_tac185": "radon_uncertainty"
            },
            "scale": {
                "v_rn-i0_ac_tac185": 1.0,
                "sd_rn-i0_ac_tac185": 1.0
            },
            "dim": [
                "v_rn-i0_ac_tac185"
            ]
        },
        str(config.radon_obs('wao')): {
            "var": {
                "v_rn-i0_ac_wao020": "radon",
                "sd_rn-i0_ac_wao020": "radon_uncertainty"
            },
            "scale": {
                "v_rn-i0_ac_wao020": 1.0,
                "sd_rn-i0_ac_wao020": 1.0
            },
            "dim": [
                "v_rn-i0_ac_wao020"
            ]
        }
    }
}
