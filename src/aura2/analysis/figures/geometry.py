from __future__ import annotations

from typing import NamedTuple

import matplotlib as mpl
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from astropy.visualization import HistEqStretch, ImageNormalize, MinMaxInterval
from matplotlib.axes import Axes
from matplotlib.colors import Colormap, FuncNorm, LinearSegmentedColormap, Normalize, SymLogNorm
from matplotlib.figure import Figure
from plan2eplus.ezcase.ez import EZ
from plan2eplus.results.sql import get_qoi
from plan2eplus.visuals.data.filter import handle_external_node_data
from plan2eplus.visuals.data.many_data_plot import DataPlot

from aura2.analysis.utils.common import filter_to_time
from aura2.analysis.utils.data import Experiment, default_experiments


class ColorNorm(NamedTuple):
    cmap: Colormap
    norm: Normalize


def get_pressure(exp: Experiment, hour: int):
    return filter_to_time(get_qoi("AFN Node Total Pressure", exp.sql_path).data_arr, hour=hour)


def get_zone_pressure(exp: Experiment, hour: int):
    # interior zone nodes only (BLOCK ...); drops the AFN_EXTERNAL_NODE_* boundary
    # driving pressures, which are ~2-3x larger and otherwise swamp the room color scale
    p = get_pressure(exp, hour)
    mask = ["BLOCK" in str(n) for n in p.space_names.values]
    return p.isel(space_names=[i for i, m in enumerate(mask) if m])


def get_external_pressure(exp: Experiment, hour: int):
    # cardinal driving nodes only, transformed to N/S/E/W exactly as the plot colors them
    return handle_external_node_data(get_pressure(exp, hour))


def get_net_flow(exp: Experiment, hour: int):
    f12 = filter_to_time(get_qoi("AFN Linkage Node 1 to Node 2 Volume Flow Rate", exp.sql_path).data_arr, hour=hour)
    f21 = filter_to_time(get_qoi("AFN Linkage Node 2 to Node 1 Volume Flow Rate", exp.sql_path).data_arr, hour=hour)
    return f12 - f21


def make_cnorm(arrs: list[xr.DataArray], cmap_name: str, absval: bool = False) -> ColorNorm:
    arr = xr.concat(arrs, dim="_c", join="outer")
    if absval:
        arr = abs(arr)
    norm = Normalize(vmin=float(arr.min()), vmax=float(arr.max()))
    return ColorNorm(mpl.colormaps[cmap_name], norm)


def truncate_cmap(cmap_name: str, lo: float = 0.1, hi: float = 0.9, n: int = 256) -> Colormap:
    # sample only the middle of the map so the extremes read as muted (not fully saturated)
    base = mpl.colormaps[cmap_name]
    return LinearSegmentedColormap.from_list(f"{cmap_name}_trunc", base(np.linspace(lo, hi, n)))


def make_symmetric_cnorm(
    arrs: list[xr.DataArray], cmap_name: str = "RdYlBu_r", clip_pct: float | None = None
) -> ColorNorm:
    # symmetric about 0 so the diverging map's neutral color lands exactly on 0 Pa
    # (even negative/positive), instead of the rank-based HistEqStretch which offsets it.
    # clip_pct shrinks the range to the given percentile of |data| so low-magnitude values
    # get more color resolution (outliers clip to the ends).
    data = np.concatenate([a.values.ravel() for a in arrs])
    data = data[np.isfinite(data)]
    m = float(np.abs(data).max() if clip_pct is None else np.percentile(np.abs(data), clip_pct))
    return ColorNorm(truncate_cmap(cmap_name), Normalize(vmin=-m, vmax=m))


def make_split_end_cnorm(
    arrs: list[xr.DataArray], inner: float = 0.75, compress: float = 0.25, cmap_name: str = "RdYlBu_r"
) -> ColorNorm:
    # symmetric about 0, but piecewise: linear for |p| <= inner so low-magnitude values get
    # most of the colormap, then a compressed (slope `compress`) band out to ±max so the
    # extremes stay visually distinct instead of clipping. Knees sit at ±inner.
    data = np.concatenate([a.values.ravel() for a in arrs])
    data = data[np.isfinite(data)]
    m = float(np.abs(data).max())

    def fwd(x):
        x = np.asarray(x, float)
        return np.sign(x) * np.where(np.abs(x) <= inner, np.abs(x), inner + compress * (np.abs(x) - inner))

    def inv(y):
        y = np.asarray(y, float)
        return np.sign(y) * np.where(np.abs(y) <= inner, np.abs(y), inner + (np.abs(y) - inner) / compress)

    return ColorNorm(truncate_cmap(cmap_name), FuncNorm((fwd, inv), vmin=-m, vmax=m))


def make_symlog_cnorm(
    arrs: list[xr.DataArray], linthresh: float = 0.15, cmap_name: str = "RdBu_r"
) -> ColorNorm:
    # symmetric-log about 0: linear within ±linthresh, logarithmic beyond, so both the
    # near-zero values and the (dark) extremes keep a smooth gradient without a hard knee
    data = np.concatenate([a.values.ravel() for a in arrs])
    data = data[np.isfinite(data)]
    m = float(np.abs(data).max())
    return ColorNorm(truncate_cmap(cmap_name), SymLogNorm(linthresh=linthresh, vmin=-m, vmax=m, base=10))


def make_pressure_cnorm(arrs: list[xr.DataArray], cmap_name: str = "RdYlBu_r") -> ColorNorm:
    # histogram-equalized (rank-based) norm: allocates color by the data distribution so
    # tightly-clustered rooms (e.g. plan A, all ~+0.3 Pa) still show a gradient instead of
    # a single flat band. Mirrors p1gen's ZScale intent for non-uniformly distributed
    # pressures; the boundary driver nodes fall outside the range and clip to the ends.
    data = np.concatenate([a.values.ravel() for a in arrs])
    data = data[np.isfinite(data)]
    norm = ImageNormalize(data, interval=MinMaxInterval(), stretch=HistEqStretch(data))
    return ColorNorm(truncate_cmap(cmap_name), norm)


def plot_case(
    exp: Experiment,
    geom: ColorNorm,
    flow: ColorNorm,
    fig: Figure,
    ax: Axes,
    hour: int,
    ext: ColorNorm | None = None,
):
    case = EZ(idf_path=exp.idf_path)
    net_flow, pressure = get_net_flow(exp, hour), get_pressure(exp, hour)
    dp = DataPlot(case.objects.zones, cardinal_expansion_factor=1.3)
    dp.fig, dp.axes = fig, ax
    dp.plot_zone_names()
    dp.plot_zones_with_data(pressure, *geom)
    dp.plot_cardinal_names_with_data(pressure, *(ext or geom))
    dp.plot_subsurfaces_and_surfaces(
        case.objects.airflow_network, case.objects.airboundaries, case.objects.subsurfaces
    )
    dp.plot_connections_with_data(net_flow, case.objects.airflow_network.afn_surfaces, *flow)
    dp.set_limits()


def make_pressure_geom(hour: int = 12):
    plt.rcParams.update({"font.size": 18})
    exps = default_experiments()
    geom_cnorm = make_pressure_cnorm([get_zone_pressure(e, hour) for e in exps])
    flow_cnorm = make_cnorm([get_net_flow(e, hour) for e in exps], "PuBu", absval=True)

    fig, axs = plt.subplots(ncols=len(exps), figsize=(11 * len(exps), 15))
    for exp, ax in zip(exps, axs):
        plot_case(exp, geom_cnorm, flow_cnorm, fig, ax, hour)

    # keep the endpoints (data min/max) plus a few round interior ticks
    p_ticks = [geom_cnorm.norm.vmin, -0.4, 0.0, 0.4, geom_cnorm.norm.vmax]
    fig.subplots_adjust(left=0.04, right=0.83, wspace=0.22)
    for left, cn, label, ticks in [
        (0.86, geom_cnorm, "Total Pressure [Pa]", p_ticks),
        (0.93, flow_cnorm, "Net Ventilation Flow Rate [m3/s]", None),
    ]:
        cax = fig.add_axes([left, 0.12, 0.012, 0.76])
        cbar = fig.colorbar(cm.ScalarMappable(norm=cn.norm, cmap=cn.cmap), cax=cax, ticks=ticks)
        cbar.set_label(label)
    return fig


def make_pressure_geom_alt(hour: int = 12):
    # comparison variant: symmetric 0-centered scale for interior zones, and a dedicated
    # symmetric scale/colorbar for the external cardinal nodes so they no longer clip to
    # a single saturated band against the (smaller) interior pressures
    plt.rcParams.update({"font.size": 18})
    exps = default_experiments()
    linthresh = 0.15
    geom_cnorm = make_symlog_cnorm([get_zone_pressure(e, hour) for e in exps], linthresh=linthresh)
    ext_cnorm = make_symmetric_cnorm([get_external_pressure(e, hour) for e in exps], cmap_name="RdBu_r")
    flow_cnorm = make_cnorm([get_net_flow(e, hour) for e in exps], "PuBu", absval=True)

    fig, axs = plt.subplots(ncols=len(exps), figsize=(11 * len(exps), 15))
    for exp, ax in zip(exps, axs):
        plot_case(exp, geom_cnorm, flow_cnorm, fig, ax, hour, ext=ext_cnorm)

    def sym_ticks(cn: ColorNorm) -> list[float]:
        m = cn.norm.vmax
        return [-m, -m / 2, 0.0, m / 2, m]

    # horizontal colorbars along the bottom (journal multi-panel layout)
    fig.subplots_adjust(left=0.03, right=0.99, bottom=0.13, top=0.95, wspace=0.15)
    m = geom_cnorm.norm.vmax
    geom_ticks = [-m, -0.5, -linthresh, 0.0, linthresh, 0.5, m]
    for left, cn, label, ticks in [
        (0.06, geom_cnorm, "Interior Zone Pressure [Pa] (symlog)", geom_ticks),
        (0.39, ext_cnorm, "External Node Pressure [Pa]", sym_ticks(ext_cnorm)),
        (0.72, flow_cnorm, "Net Ventilation Flow Rate [m³/s]", None),
    ]:
        cax = fig.add_axes([left, 0.06, 0.22, 0.02])
        cbar = fig.colorbar(
            cm.ScalarMappable(norm=cn.norm, cmap=cn.cmap), cax=cax, ticks=ticks, orientation="horizontal"
        )
        cbar.set_label(label)
    return fig
