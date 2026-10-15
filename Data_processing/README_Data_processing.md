# Data_processing

TITLE: Data_processing README
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Run order, inputs and outputs of the data-processing scripts behind Figs 1–11.

All paths are set in `config.py`. Raw inputs go in `../data/raw/`; every script writes to
`outputs/<step folder>/`. Run the scripts from any directory, in this order:

| Step | Script | Needs | Writes (used by) |
|---|---|---|---|
| 01 | `01_name_radon_model/run_radon_model.py` | NAME radon footprints, radon flux maps | modelled radon, all months (Figs 2–11) |
| 02 | `02_ch4_obs_processing/ch4_obs_processing.py` | `data/raw/ch4_obs/` | hourly CH4 and inlet differences (Figs 7, 9, 10) |
| 03 | `03_name_met/pblh_ws_extract.py` | NAME methane footprints | PBLH and wind speed (Figs 7, 9, 10, 11) |
| 04 | `04_current_intem/current_intem.py` | `data/raw/intem_current/` | current InTEM classes, averages, counts (Table 2, Figs 7, 8) |
| 05a | `05_radon_classification/radon_selection_files.py` | steps 01 + radon obs | 4 h 2-class and 3-class selection files (Figs 5, 6, 11) |
| 05b | `05_radon_classification/radon_hourly_classes.py` | steps 01–03 | hourly classes, averages, counts (Figs 4, 9, 10, Supplement) |
| 05c | `05_radon_classification/radon_intem_2class.py` | steps 02, 03, 05a | 2-class composites and counts (Figs 7, 8) |
| 06 | `06_pollution_events/pollution_events.py` | steps 03, 05a + InTEM obs selection | pollution-event table (Fig 11) |

Raw inputs expected under `data/raw/`:

- `radon_obs/{SITE}_ceda.nc`
- `radon_flux_maps/` (Zhang E3 and traceRadon GLDAS-Noah)
- `name_footprints/radon/` and `name_footprints/methane/`
- `ch4_obs/{site}{height}_60min.csv`
- `intem_current/{SITE}/` monthly files and `intem_current/{SITE}_NN_obs_selection_{year}.txt`

`config.REPRODUCE_ORIGINAL_OUTPUTS` is `False` by default, which applies the corrections described in
`config.py`. Set it to `True` to reproduce the files behind the current figures exactly.

Python 3 with numpy, pandas, xarray, netCDF4 (tested with pandas 3).
