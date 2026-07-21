from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import altair as alt
import polars as pl
from plan2eplus.results.sql import get_qoi

from aura2.analysis.utils.data import Experiment, all_experiments, get_afn_zone_names
from aura2.analysis.utils.order import CATEGORY_NAMES, DOOR_VENT, ORDER, add_order_to_temp_df


class Row(NamedTuple):
    case: str
    category: str
    option: str
    value: float


def space_time_avg(exp: Experiment, qoi: str, idx=None) -> float:
    data = get_qoi(qoi, exp.sql_path).data_arr
    if idx is not None:  # restrict to a subset of timesteps (e.g. a climatic section)
        data = data.isel(datetimes=idx)
    if qoi == "Zone Mean Air Temperature":
        afn = data.space_names.isin(get_afn_zone_names(exp.idf_path))
        return float(data.sel(space_names=afn).mean())
    if qoi == "AFN Linkage Node 1 to Node 2 Volume Flow Rate":
        f21 = get_qoi("AFN Linkage Node 2 to Node 1 Volume Flow Rate", exp.sql_path).data_arr
        if idx is not None:
            f21 = f21.isel(datetimes=idx)
        return float(abs(data - f21).mean())
    return float(data.mean())


def create_data_set(qoi: str, idx=None) -> pl.DataFrame:
    return pl.DataFrame(
        [Row(e.case_name, e.category, e.option, space_time_avg(e, qoi, idx)) for e in all_experiments()]
    )


def handle_df_filter(df: pl.DataFrame, dvent: bool = False, dont_split: bool = False):
    df1 = add_order_to_temp_df(df)
    if dont_split:
        return df1
    return df1.filter(pl.col.category == DOOR_VENT) if dvent else df1.filter(pl.col.category != DOOR_VENT)


def plot_sensitivity(df: pl.DataFrame, qoi: str, unit: str, dvent=False, dont_split=False):
    case_df = handle_df_filter(df, dvent, dont_split)
    return (
        alt.Chart(case_df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=100))
        .encode(
            x=alt.X("value").scale(zero=False).title(f"{qoi} [{unit}]"),
            y=alt.Y(f"{CATEGORY_NAMES}:N").title(None),
            color=alt.Color("category").legend(None),
            shape=alt.Shape(f"{ORDER}:O").legend(None),
            row=alt.Row("case").title(None).header(labelFontSize=15, labelAngle=0),
        )
        .resolve_axis(x="shared")
        .properties(height=50, width=400)
    )


def make_sens_temp():
    df = create_data_set("Zone Mean Air Temperature")
    return plot_sensitivity(df, "Zone Mean Air Temperature", "C") | plot_sensitivity(
        df, "Zone Mean Air Temperature", "C", dvent=True
    )


def make_sens_flow():
    df = create_data_set("AFN Linkage Node 1 to Node 2 Volume Flow Rate")
    return plot_sensitivity(df, "Flow Rate", "m3/s", dont_split=True)
