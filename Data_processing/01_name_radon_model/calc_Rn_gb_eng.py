"""
TITLE: calc_Rn_gb_eng.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Calculation module for radon: reads NAME footprints, radon flux maps and radon observations (get_raw), builds model inputs (raw2input) and computes modelled radon activity concentrations C = rho_air * sum(Q * D) (forward / simple_forward, output2y).

SOURCE FILE: Regional_modelling/New_code/calc_Rn_gb_eng.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Standard Library imports
import numpy as np
import pandas as pd
import xarray as xr

# Local imports
from region_EU import inv_regions, allocate_lonlat
from util_calc import replace_nan
from util_nc_type01 import read_nc, read_nc_batch


def get_raw(date, settings):
    r"""Get raw data from files.

    Parameters
    ----------
    date : Timestamp
        Model timestamp.
    settings : dict
        Data file settings.

    Returns
    -------
    odata : dict
        Raw data.
    """
    odata = {}
    odata['date'] = date
    sites = settings['sites'] 
    odata['sites'] = sites
    odata['species'] = settings['species']
    # Grid
    regions_list = inv_regions(['gb_eng'])
    odata['regions'] = np.full((293, 391), 0)
    for n, i in enumerate(['gb_eng']):
        allocate_lonlat(
            grid=odata['regions'],
            lon=np.array(regions_list[i]['lon']) + 238,
            lat=np.array(regions_list[i]['lat']) + 110,
            cat=n+1
        )
    # Met
    odata['met'] = {
        species: {site: {} for site in sites}
        for species, params in settings['met'].items()
    }
    for species, params in settings['met'].items():
        for site in sites:
            odata['met'][species][site].update(
                read_nc(date, date.strftime(params[f'f_{site}']), params)
            )
    # Emissions
    odata['Q'] = {
        species: read_nc_batch(date, fs)
        for species, fs in settings['Q'].items()
    }
    # Observations
    odata['obs'] = read_nc_batch(date, settings['obs'])
    odata['obs'].update({
        f'dim_{k}': {'time': np.array([], dtype='datetime64[ns]')}
        for f in settings['obs']
        if f != 'combine'
        for k in settings['obs'][f]['var']
        if k not in odata['obs'] and k.startswith('v')
    })
    odata['obs'].update({
        k: np.array([])
        for f in settings['obs']
        if f != 'combine'
        for k in settings['obs'][f]['var']
        if k not in odata['obs']
    })
    # Background
    odata['bg'] = {
        species: read_nc_batch(date, fs)
        for species, fs in settings['bg'].items()
    }
    return odata


def raw2input(idata, settings):
    r"""Convert raw data to model input data.

    Parameters
    ----------
    idata : Timestamp
        Raw data.
    settings : dict
        Inversion settings.

    Returns
    -------
    odata : dict
        Model input data.
    """
    odata = {}
    odata['dim'] = {}
    # Dates
    odata['dim']['tAll'] = pd.date_range(
        idata['date'],
        idata['date'] + pd.DateOffset(months=1),
        freq='1H',
        closed='left'
    )
    odata['dim']['tHour'] = odata['dim']['tAll']
    # Constants
    odata.update({k: idata[k] for k in ['sites', 'species']})
    # Met
    odata['met'] = idata['met']
    # Emissions (build final array per species)
    odata['v_rn-i0_Q'] = np.tile(
        (
            replace_nan(
                idata['Q']['rn']['v_rn-i0_Q-1'],
                idata['Q']['rn']['v_rn-i0_Q-0']
            )[np.newaxis]
            if idata['Q']['rn']['v_rn-i0_Q-1'].ndim == 2 else
            np.array([
                replace_nan(i, idata['Q']['rn']['v_rn-i0_Q-0'])
                for i in idata['Q']['rn']['v_rn-i0_Q-1']
            ])
        )[:, np.newaxis],
        (2, 1, 1)
    )
    odata['v_rn-i0_Q'][..., 0, idata['regions'] != 0] = 0.0
    odata['v_rn-i0_Q'][..., 1, idata['regions'] != 1] = 0.0
    # Observations
    ## ToDo do the resampling outside
    odata.update({
        k:
        pd.Series(v, index=idata['obs'][f'dim_{k}']['time'])
        .resample('1H').mean()
        .reindex(odata['dim']['tHour'])
        .values
        for k, v in idata['obs'].items()
        if k.startswith('v_')
        })
    # Dimnsions
    odata['dims'] = {
        'time': odata['dim']['tHour'].to_numpy(),
        'cat': np.arange(2),
    }
    return odata


def simple_forward(theta):
    r"""Forward model but simpler.

    Parameters
    ----------
    theta : dict
        Should include (with v_, u_ and h_ prefix as appropriate).

    Returns
    -------
    output : dict
        Model output
    """
    output = {}
    # Forward model
    met_species = {k: v['met'] for k, v in theta['species'].items()}
    met = {k: theta['met'][met_species[v]] for k, v in met_species.items()}
    for site in theta['sites']:
        output.update({
            f'enh_rn-i0_ac_{site}':
            (
                (
                    theta['v_rn-i0_Q']
                    if not (
                        met['rn'][site]['D'].shape[0]
                        == theta['v_rn-i0_Q'].shape[0] * 24
                    ) else
                    np.repeat(theta['v_rn-i0_Q'], 24, axis=0)
                )
                * met['rn'][site]['D'][:, np.newaxis]
            ).sum((-2, -1))
            * theta['species']['rn']['scale']
        })
        if f'v_rn-i0_ac_{site}' in theta:
            output[f'v_rn-i0_ac_{site}'] = (
                output[f'enh_rn-i0_ac_{site}'].sum(-1)
            )
    return output


def forward(theta, idx):
    r"""Forward model.

    Parameters
    ----------
    theta : dict
        Should include (with v_, u_ and h_ prefix as appropriate).

    Returns
    -------
    output : dict
        Model output
    """
    output = {}
    return output


def output2y(model_input, model_output, settings):
    r"""Create observations vector for inversion.

    Parameters
    ----------
    model_input, model_output, settings : dict
        Model input data, output data and inversion settings.
    """
    return


# Default parameters for plots
style = {
        'v_rn-i0_ac': dict(
        ylim=[-1., 16.],
        yticks=np.arange(0., 16.1, 4.),
        label='$C\mathregular{_{^{222}Rn}}$ (Bq m$^{-3}$)',
    )
}