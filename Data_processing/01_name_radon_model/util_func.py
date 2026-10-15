"""
TITLE: util_func.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Generic helper (rgetattr) used by util_plot.py.

SOURCE FILE: Regional_modelling/New_code/util_func.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Standard Library imports
import functools


def rgetattr(obj, attr, *args):
    r"""Recursive getattr.

    getattr(a, 'b') is possible but getattr(a, 'b.c') is not, hence the
    function was created to do the latter.

    Paremters
    ---------
    obj : object
        An object.
    attr : string
        An attribute.

    Returns
    -------
    output : obj
        Attribute object.
    """
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))