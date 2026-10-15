"""
TITLE: util_calc.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Small numerical helpers (replace_nan) for the NAME forward model.

SOURCE FILE: Regional_modelling/New_code/util_calc.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Standard Library imports
import numpy as np


def replace_nan(a, b):
    r"""Replace nan in a with b.

    Parameters
    ----------
    a : ndarray
        Input array.
    b : float
        Value to replace nan with.

    Returns
    -------
    c : ndarray
        Modified array.
    """
    c = a.copy()
    c[np.isnan(a)] = b[np.isnan(a)]
    return c