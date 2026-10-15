"""
TITLE: core.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Driver for the NAME forward model: reads a data-settings module (-dset) and a calculation module (-cfile), runs the forward model for one month (-date) and writes obs_YYYY-MM.nc, for_YYYY-MM.nc and diagnostic plots to -odir.

SOURCE FILE: Regional_modelling/New_code/core.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Standard Library imports
import argparse
import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re
import xarray as xr

# Standard Library imports
from collections import OrderedDict
from importlib import import_module

# Local imports
from util_io import write_nc, METADATA
from util_plot import generic as plot


# =============================================================================
#   Pre-processing
# =============================================================================
print('Start Process')

# Argument Parser
parser = argparse.ArgumentParser()
## Date
parser.add_argument("-date", required=True)
## Inversion settings file
parser.add_argument("-iset", required=True)
## Data settings file
parser.add_argument("-dset", required=True)
## Calculation file
parser.add_argument("-cfile", required=True)
## Run mode (0: forward only; 1: inversion)
parser.add_argument("-rmode", required=True, type=int)
## Output dir
parser.add_argument("-odir", required=True)
## Parse
args = parser.parse_args()


# Read settings file: Obsertion sites and variables
iset = None
dset = getattr(
    import_module(args.dset), 'dset'
)

# Import calculation file: create data etc.
get_raw = getattr(
    import_module(args.cfile), 'get_raw'
)
raw2input = getattr(
    import_module(args.cfile), 'raw2input'
)
forward = getattr(
    import_module(args.cfile), 'forward'
)
simple_forward = getattr(
    import_module(args.cfile), 'simple_forward'
)
output2y = getattr(
    import_module(args.cfile), 'output2y'
)
style = getattr(
    import_module(args.cfile), 'style'
)
if not os.path.exists(args.odir):
    os.makedirs(args.odir)
raw_data = get_raw(
    date=pd.to_datetime(args.date),
    settings=dset
)

# =============================================================================
#   Main processing
# =============================================================================
print("Main processing")
# Create input values
forward_input = raw2input(raw_data, iset)
# Run forward model
forward_output = simple_forward(forward_input)
# Further modelling
if args.rmode == 1:  # inversion
    import pymc3 as pm
    import theano
    model = pm.Model()
    model_input = theta2input(model, raw_data)
    with model:
        model_output = forward(model_input)
    model_y = output2y(model_output)
    with model:
        trace = pm.sample(
            draws,
            cores,
            chains,
            tune,
            random_seed,
            return_inferencedata=False
        )
        result = pm.save_trace(trace, directory=args.odir, overwrite=True)
        
# =============================================================================
#   Post-processing
# =============================================================================
print("Post-processing")
obs_variables = sorted([
    k
    for k in raw_data['obs']
    if k.startswith('v_')
])
output_variables = sorted([
    k
    for k in forward_output
    if k.startswith(('v_', 'bg_', 'enh_'))
])

date=pd.to_datetime(args.date)
#print('date =', date)
date_str = date.strftime('%Y-%m')
print('date_str =', date_str)

# Save measured observations
write_nc(
    var=[
        *[(k, v) for k, v in forward_input['dims'].items()],
        *[(k, forward_input[k]) for k in obs_variables]
    ],
    metadata=METADATA,
    ofile=os.path.join(args.odir, f'obs_{date_str}.nc')
)
# Save model outputs
write_nc(
    var=[
        *[(k, v) for k, v in forward_input['dims'].items()],
        *[(k, forward_output[k]) for k in output_variables]
    ],
    metadata=METADATA,
    ofile=os.path.join(args.odir, f'for_{date_str}.nc')
)

# Plot and save images
figs = {}
axs = {}
pobjs = {}
colours = {
    'obs': '#000000',
    'mo1': '#FF8800',
    'bas': '#886600',
    'mo2': '#8888FF',
}
fig_param = dict(
    pw=6.0, ph=5.0,
    sw=5.4, sh=1.5,
    sm=0.05,
    ml=0.6, mb=0.5,
    nsx=1, nsy=1,
    nml=1, nmb=1,
    fs=8,
)
fig_param_def = fig_param.copy()

for site in dset['sites']:
    panel_variables = sorted([
        re.sub(f'_{site}$', '', k)
        for k in raw_data['obs']
        if k.startswith('v_') and k.endswith(site)
    ])
    fk = f'main_{site}'
    fig_param['nsy'] = len(panel_variables)
    fig_param['ph'] = (
        fig_param['nsy'] * fig_param['sh']
        + fig_param['nmb'] * fig_param['mb']
    )
    figs[fk] = plt.figure(figsize=(fig_param['pw'], fig_param['ph']), dpi=300)
    axs[fk] = {}
    pobjs[fk] = {}
    plot(
        fig=figs[fk],
        axs=axs[fk],
        pobjs=pobjs[fk],
        new_axs={
            f'{j}_1': [
                dict(
                    rect=[
                        (
                            fig_param['ml'] + 1 * fig_param['sm']
                        )
                        / fig_param['pw'],
                        (
                            fig_param['ph']
                            - (j + 1) * fig_param['sh']
                            + fig_param['sm']
                        )
                        / fig_param['ph'],
                        (
                            fig_param['sw'] - 2 * fig_param['sm']
                        )
                        / fig_param['pw'],
                        (
                            fig_param['sh'] - 2 * fig_param['sm']
                        )
                        / fig_param['ph'],
                    ],
                    projection=None,
                ),
                dict(
                    set_yticks=[[style[k]['yticks']], {}],
                    set_ylim=[[style[k]['ylim']], {}],
                    **{
                        'xaxis.set_major_locator': [
                            [mdates.WeekdayLocator(byweekday=6)], {}
                        ],
                        'xaxis.set_major_formatter': [
                            [mdates.DateFormatter('%Y-%m-%d')], {}
                        ]
                    },
                    set_xlim=[
                        [
                            forward_input['dim']['tHour'][0]
                            - pd.to_timedelta('1 D'),
                            forward_input['dim']['tHour'][-1]
                            + pd.to_timedelta('1 D')
                        ],
                        {}
                    ],
                    tick_params=[
                        [],
                        dict(
                            axis='both', which='major', direction='in',
                            labelsize=fig_param['fs'],
                            left=True,
                            right=False,
                            top=True,
                            bottom=True,
                            labelleft=True,
                            labelright=False,
                            labeltop=False,
                            labelbottom=(
                                True if (j+1) == fig_param['nsy'] else False
                            )
                        )
                    ]
                ),
                dict(
                    patch_alpha=0.0
                )
            ]
            for j, k in enumerate(panel_variables)
        },
        new_pobjs={
            **{
                f'{k}_{l}': [
                    f'{j}_1',
                    'plot',
                    [
                        forward_input['dim']['tHour'],
                        d[f'{k}_{site}'],
                        'o'
                    ],
                    dict(
                        label=l,
                        c=c,
                        ms=2.0, mew=0.0,
                    )
                ]
                for j, k in enumerate(panel_variables)
                for l, d, c in zip(
                    ['Measured', 'Modelled'],
                    [forward_input, forward_output],
                    [colours['obs'], colours['mo1']]
                )
            },
            'leg': (
                '0_1',
                'legend',
                [],
                dict(
                    loc='upper right',
                    fontsize=fig_param['fs'], ncol=3,
                    handletextpad=0.2, columnspacing=1.0,
                    borderpad=0.2, borderaxespad=0.2
                )
            )
        },
        texts=[
            *[
                dict(  # y- axis
                    x=(fig_param['sm'] / fig_param['pw']),
                    y=(
                        fig_param['ph']
                        - (j + 0.5) * fig_param['sh']
                    )
                    / fig_param['ph'],
                    s=style[k]['label'],
                    ha='left', va='center',
                    size=fig_param['fs'],
                    rotation=90.
                )
                for j, k in enumerate(panel_variables)
            ]
        ]
    )
    for l in axs[fk][f'{len(panel_variables)-1}_1'].get_xticklabels():
        l.set_ha("right")
        l.set_rotation(30)
for k, fig in figs.items():
    fig.savefig(os.path.join(args.odir, f'{k}_{date_str}.png'))