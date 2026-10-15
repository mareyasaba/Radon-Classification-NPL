"""
TITLE: util_nc_type01.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: NetCDF reading helpers (read_nc, read_nc_batch) for footprints, flux maps and observations.

SOURCE FILE: Regional_modelling/New_code/util_nc_type01.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Standard Library imports
import numpy as np
import os
import pandas as pd
import xarray as xr


DIM_LIST = ['time', 'height', 'lat', 'lon']


def read_nc(date, f, params):
    r"""Read netCDF variables based on the time axis.

    Parameters
    ----------
    date : Timestamp
        Model timestamp.
    f : Path-like
        Data file.
    params : dict
        Parameters for data selection/modification.

    Returns
    -------
    output : dict
        Raw data.
    """
    output = {}
    with xr.open_dataset(f) as ds_open:
        with ds_open.load() as ds:
            for k, v in params['var'].items():
                dims = [i for i in DIM_LIST if i in ds[v].dims]
                if 'time' not in dims:
                    output[k] = (
                        ds[v].transpose(*dims).values * params['scale'][k]
                    )
                elif ds.time.size == 1:
                    output[k] = (
                        ds[v].transpose(*dims).values[0] * params['scale'][k]
                    )
                    dims.remove('time')
                else:
                    t = ds.time
                    td_min = (
                        t.diff('time').astype('timedelta64[D]').values
                        / np.timedelta64(1,  'D')
                    ).min()
                    if td_min >= 365.0:  # annual
                        t_ref = np.datetime64(date).replace(month=1, day=1)
                        t_sel = min(
                            t,
                            key=lambda x: abs(x - t_ref)
                        )
                    elif td_min >= 28.0:  # monthly
                        t_ref = np.datetime64(date)
                        t_sel = min(
                            t[t.dt.month==date.month],
                            key=lambda x: abs(x - t_ref)
                        )
                    else:  # daily or lower
                        t_sel = date.strftime('%Y-%m')
                    output[k] = (
                        ds[v].transpose(*dims).sel(time=t_sel).values
                        * params['scale'][k]
                    )
                if 'dim' in params and k in params['dim']:
                    output[f'dim_{k}'] = {
                        i:
                        ds[i].sel(time=t_sel).values
                        if i == 'time' else
                        ds[i].values
                        for i in dims
                    }
    return output


def read_nc_batch(date, settings):
    r"""Read netCDF files in a batch.

    Parameters
    ----------
    date : Timestamp
        Model timestamp.
    settings : dict
        Data file settings.

    Returns
    -------
    output : dict
        Raw data.
    """
    combine = settings['combine']
    if combine == "skip":
        return
    inter = {}
    for f, params in settings.items():
        if f == 'combine':
            continue
        year_in_name = any([i in f for i in ['%Y']])
        f_not_exist = not os.path.exists(f)
        if (year_in_name and f_not_exist):
            init_size = check_time2(date, date.strftime(f), params)
            if init_size:
                date_f = date
            else:
                sim_year = [
                    y
                    for y in range(date.year-50, date.year+51)
                    if os.path.exists(
                        pd.to_datetime(f'{y}-{date.month}').strftime(f)
                    )
                    and y != date.year
                ]
                sim_size = {
                    y:
                    check_time2(
                        pd.to_datetime(f'{y}-{date.month}'),
                        pd.to_datetime(f'{y}-{date.month}').strftime(f),
                        params
                    )
                    for y in sim_year
                }
                val_year = [y for y in sim_year if sim_size[y]]
                date_f = pd.to_datetime(
                    f'{min(val_year, key=lambda x: abs(x-date.year))}'
                    f'-{date.month}'
                )
        else:
            date_f = date
        try:
            inter[f] = read_nc(date_f, date_f.strftime(f), params)
        except:
            pass
    final_variables = {k for ks in inter.values() for k in ks}
    if combine == "sum":
        output = {
            var:
            np.sum(
                [
                    v
                    for f, ks in inter.items()
                    for k, v in ks.items()
                    if k == var
                ],
                axis=0
            )
            if not var.startswith(('dim')) else
            [
                v
                for f, ks in inter.items()
                for k, v in ks.items()
                if k == var
            ][0]
            for var in final_variables
        }
    elif combine == "mean":
        output = {
            var:
            np.mean(
                [
                    v
                    for f, ks in inter.items()
                    for k, v in ks.items()
                    if k == var
                ],
                axis=0
            )
            if not var.startswith(('dim')) else
            [
                v
                for f, ks in inter.items()
                for k, v in ks.items()
                if k == var
            ][0]
            for var in final_variables
        }
    return output


def check_time(date, f):
    r"""Check if data for a given time exist in the file.

    Parameters
    ----------
    date : str
        str that can be interpreted as a Timestamp.
    f : Path-like
        Data file.

    Returns
    -------
    exist : dict
        If data for that timestamp exist.
    """
    try:
        with xr.open_dataset(f) as ds_open:
            with ds_open.load() as ds:
                exist = ds['time'].sel(time=date).size > 0
    except:
        exist = False
    return exist


def check_time2(date, f, params):
    r"""Check if data for a given time exist in the file.

    Parameters
    ----------
    date : str
        str that can be interpreted as a Timestamp.
    f : Path-like
        Data file.

    Returns
    -------
    exist : dict
        If data for that timestamp exist.
    """
    try:
        exist = all([
            v.size
            for v in read_nc(date, date.strftime(f), params).values()
        ])
    except:
        exist = False
    return exist