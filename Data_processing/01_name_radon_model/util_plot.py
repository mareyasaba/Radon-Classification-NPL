"""
TITLE: util_plot.py
AUTHOR: Mareya Saba
DATE CREATED:
DATE LAST EDITED:
PURPOSE: Generic diagnostic plotting used by core.py (main_<site>_YYYY-MM.png).

SOURCE FILE: Regional_modelling/New_code/util_plot.py (copied unchanged apart from this header).
NOTE: This file is part of the NAME forward-model framework. The data-settings
      template it came with points to /hpc-work/ec5/..., so the framework may
      originate from a co-author: please confirm the original author and credit
      them here before publishing.
"""

# Local imports
from util_func import rgetattr

# matplotlib not imported as package functions are not directly called.


def generic(
        fig,
        axs,
        pobjs,
        new_axs,
        new_pobjs,
        texts=[],
        legend_params=[[], [], {}],
        ):
    r"""Create generic plots

    Parameters
    ----------
    fig : Figure
        Figure object to draw upon.
    axs : dict
        Dict containing axes objects
    pobjs : dict
        Dict containing plots/texts etc.
    new_axs : dict
        {
            ax_name: [{kwargs}, {bound methods}, {extra}]
            }
        kwargs include {rect, projection, sharex, sharey, label}
        bound methods include {
            tick_params, xaxis_date,
            set_xlim, set_ylim, set_xticks, set_yticks,
            ax.set_xticklabels, ax.set_yticklabels,
            xaxis.set_major_formatter, xaxis.set_major_locator,
            }
        extra include {
            patch_alpha
            }
        New axes added into axs.
    new_pobjs : dict
        {
            key: [
                axs_key, plot_type, [*args], {**kwargs},
                ]
            }
        New plots added into pojbs. args and kwargs are directly fed into the
        plot function depending on plot_type.
    texts : list of dict
        Each dict is kwargs for fig.text object, i.e. fig.text(**kwargs).
    legend_params : list
        [list of str, list of str, kwargs]
        list of keys.
        kwargs for ax.legend.

    """
    for k, v in new_axs.items():
        axs[k] = fig.add_axes(**v[0])
        for k1, (v1, v2) in v[1].items():
            rgetattr(axs[k], k1)(*v1, **v2)
        if 'patch_alpha' in v[2]:
            axs[k].patch.set_alpha(v[2]['patch_alpha'])
    legObj = {}
    for k, v in new_pobjs.items():
        pobjs[k] = rgetattr(axs[v[0]], v[1])(*v[2], **v[3])
        if k in legend_params[0]:
            legObj[k] = pobjs[k]
    if legend_params[0]:
        leg = fig.legend(
            handles=[legObj[k] for k in legend_params[0]],
            labels=legend_params[1],
            **legend_params[2]
            )
    for text in texts:
        if text:
            fig.text(**text)