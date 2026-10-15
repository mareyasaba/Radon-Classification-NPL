"""
TITLE: util_io.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: NetCDF writing (write_nc) and output metadata for the NAME forward model.

SOURCE FILE: Regional_modelling/New_code/util_io.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Standard Library imports
import netCDF4
import numpy as np
import pandas as pd
import re
import traceback


REF_TIME = pd.to_datetime('2000-01-01T00:00:00').to_numpy()


def r_instaar(fpath, dtype):
    r"""Read INSTAAR file

    Parameters
    ----------
    fpath : path-like
        Path of the data file.
    dtype : {'event', 'month'}
        Event file or monthly baseline.

    Returns
    -------
    odata : DataFrame
        Output data.

    """
    with open(fpath) as fline:
        line = next(fline)
        header_no = int(line.split(':')[1].strip())
        for i, line in enumerate(fline):
            if i == header_no - 2:
                col_name = line
                break
    col_name = re.sub('# data_fields: ', '', col_name)
    col_name = [name.strip() for name in col_name.split(' ')]
    idata = pd.read_csv(
                fpath,
                sep=r'\s+',
                skiprows=header_no,
                header=None,
                names=col_name
                )
    if dtype == 'month':
        idata['date'] = pd.to_datetime((idata['year']*100 +
                                        idata['month']).astype('i8'),
                                       format='%Y%m')
        idata.set_index('date', inplace=True)
        date = pd.date_range(idata.index[0], idata.index[-1], freq='MS')
        odata = idata['value'].reindex(date, fill_value=np.nan)#.interpolate()
    else:
        idata = idata[idata['analysis_flag'].str.match('\.(.){2}')]
        idata['date'] = pd.to_datetime(
                (idata['sample_year']*1e10
                    + idata['sample_month'].astype('i8')*1e8
                    + idata['sample_day'].astype('i8')*1e6
                    + idata['sample_hour'].astype('i8')*1e4
                    + idata['sample_minute'].astype('i8')*1e2
                    + idata['sample_seconds'].astype('i8')
                    ).astype('i8').astype(str),
                format='%Y%m%d%H%M%S'
                )
        idata.set_index('date', inplace=True)
        odata = idata['analysis_value'].groupby('date').mean()
    return odata


def write_nc(var, metadata, ofile):
    r"""Write data to netCDF.
    
    Parameters
    ----------
    var : dict
        Variables names and values.
    metadata : dict
        Metadata for each variables.
    ofile : path-like
        Output file.
    """
    with netCDF4.Dataset(ofile, 'w', format='NETCDF4') as ds:
        for (k, v) in var:
            try:
                k_meta = [i for i in metadata if k.startswith(i)][0]
                if not k_meta:
                    continue
                if metadata[k_meta]['kwargs']['dimensions'] == (k,):  # Dimension
                    ds.createDimension(
                        dimname=k, size=v.size
                    )
                ds.createVariable(
                    varname=k,
                    **metadata[k_meta]['kwargs']
                )
                in_dtype = (
                    metadata[k_meta]['dtype']
                    if 'dtype' in metadata[k_meta] else
                    ''
                )
                in_tunit = (
                    metadata[k_meta]['tunit']
                    if 'tunit' in metadata[k_meta] else
                    ''
                )
                out_dtype = metadata[k_meta]['kwargs']['datatype']
                ds[k][:] = (
                    (v - REF_TIME).astype(in_tunit).astype(out_dtype)
                    if in_dtype == 'datetime' else
                    v.astype(in_tunit).astype(out_dtype)
                    if in_dtype == 'timedelta' else
                    v.astype(out_dtype)
                )
                for ak, av in metadata[k_meta]['kwattrs'].items():
                    setattr(ds[k], ak, av)
            except Exception as e:
                print(k, v.shape)
                traceback.print_tb(e.__traceback__)


METADATA = {
    'time': {
        'dtype': 'datetime',
        'tunit': 'timedelta64[s]',
        'kwargs': {
            'dimensions': ('time',),
            'datatype': 'f8',
            'zlib': True
        },
        'kwattrs': {
            'units': f'seconds since {pd.to_datetime(REF_TIME)}',
            'calendar': 'standard',
        },
    },
    'cat': {
        'kwargs': {
            'dimensions': ('cat',),
            'datatype': 'i4',
            'zlib': True
        },
        'kwattrs': {
            'units': '',
            'comment': 'Flux category'
        },
    },
    'v_ch4-i_chi': {
        'kwargs': {
            'dimensions': ('time',),
            'datatype': 'f4',
            'zlib': True
        },
        'kwattrs': {
            'units': 'nmol mol-1',
            'comment': 'Amount fraction of CH4 in air'
        },
    },
    **{
        f'v_ch4-i{i}_d': {
            'kwargs': {
                'dimensions': ('time',),
                'datatype': 'f4',
                'zlib': True
            },
            'kwattrs': {
                'units': 'nmol mol-1',
                'comment': f'delta {s} in air'
            },
        }
        for (i, s) in [
            ('1', '13CH4'),
            ('2', '12CH3D'),
        ]
    },
    **{
        f'bg_ch4-i{i}_chi': {
            'kwargs': {
                'dimensions': ('time',),
                'datatype': 'f4',
                'zlib': True
            },
            'kwattrs': {
                'units': 'nmol mol-1',
                'comment': f'Background amount of {s} in air'
            },
        }
        for (i, s) in [
            ('', 'CH4'),
            ('0', '12CH4'),
            ('1', '13CH4'),
            ('2', '12CH3D'),
        ]
    },
    **{
        f'enh_ch4-i{i}_chi': {
            'kwargs': {
                'dimensions': ('time', 'cat'),
                'datatype': 'f4',
                'zlib': True
            },
            'kwattrs': {
                'units': 'nmol mol-1',
                'comment': f'Enhanced amount fraction of {s} in air'
            },
        }
        for (i, s) in [
            ('', 'CH4'),
            ('0', '12CH4'),
            ('1', '13CH4'),
            ('2', '12CH3D'),
        ]
    },
    'v_rn-i0_ac': {
        'kwargs': {
            'dimensions': ('time',),
            'datatype': 'f4',
            'zlib': True
        },
        'kwattrs': {
            'units': 'Bq m-3',
            'comment': 'Activity concentration of 222Rn in air'
        },
    },
    'enh_rn-i0_ac': {
        'kwargs': {
            'dimensions': ('time', 'cat'),
            'datatype': 'f4',
            'zlib': True
        },
        'kwattrs': {
            'units': 'Bq m-3',
            'comment': 'Enhanced activity concentration of 222Rn in air'
        },
    },
}