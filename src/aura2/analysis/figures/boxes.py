from __future__ import annotations

from typing import Literal, NamedTuple, get_args

import altair as alt
import polars as pl
import xarray as xr
from plan2eplus.results.sql import get_qoi

from aura2.analysis.utils.common import convert_xarray_to_polars, group_dataset_by_time
from aura2.analysis.utils.data import Experiment, default_experiments, get_afn_zone_names

TIME_OF_DAY = Literal["Day", "Night"]


def find_max_dif(arr: xr.DataArray, token: str) -> xr.DataArray:
    a = arr.loc[:, arr.space_names.str.contains(token)]
    return a.max(dim="space_names") - a.min(dim="space_names")


def dataset_by_case(pairs: list[tuple[str, xr.DataArray]]) -> xr.Dataset:
    return xr.Dataset(data_vars={name: arr for name, arr in pairs})


def afn_zone_mean(exp: Experiment) -> xr.DataArray:
    data = get_qoi("Zone Mean Air Temperature", exp.sql_path).data_arr
    afn = data.space_names.isin(get_afn_zone_names(exp.idf_path))
    return data.sel(space_names=afn).mean(dim="space_names")


def get_data_for_pressure():
    pairs = [
        (e.case_name, get_qoi("AFN Node Total Pressure", e.sql_path).data_arr)
        for e in default_experiments()
    ]
    internal = dataset_by_case([(n, find_max_dif(a, "BLOCK")) for n, a in pairs])
    external = dataset_by_case([(n, find_max_dif(a, "EXTERNAL_NODE")) for n, a in pairs])
    return internal, external


def get_data_for_flow():
    def flow(e: Experiment):
        f12 = get_qoi("AFN Linkage Node 1 to Node 2 Volume Flow Rate", e.sql_path).data_arr
        f21 = get_qoi("AFN Linkage Node 2 to Node 1 Volume Flow Rate", e.sql_path).data_arr
        return abs(f12 - f21).mean(dim="space_names")

    return dataset_by_case([(e.case_name, flow(e)) for e in default_experiments()])


def get_data_for_temperature_simple():
    return dataset_by_case([(e.case_name, afn_zone_mean(e)) for e in default_experiments()])


def get_data_for_temperature_deviation():
    exps = default_experiments()
    site = get_qoi("Site Outdoor Air Drybulb Temperature", exps[0].sql_path).data_arr.squeeze()
    return dataset_by_case([(e.case_name, afn_zone_mean(e) - site) for e in exps])


class DayNightData(NamedTuple):
    day: xr.Dataset
    night: xr.Dataset

    def to_polars(self):
        def one(ds: xr.Dataset, tod: TIME_OF_DAY):
            cases = list(ds.data_vars)
            return (
                convert_xarray_to_polars(ds)
                .unpivot(on=cases, index="datetimes")
                .drop_nulls()
                .with_columns(time_of_day=pl.lit(tod))
            )

        return pl.concat([one(ds, tod) for ds, tod in zip((self.day, self.night), get_args(TIME_OF_DAY))])


def plot_qoi_box(df: pl.DataFrame, name: str):
    return (
        alt.Chart(df)
        .mark_boxplot()
        .encode(
            x=alt.X("variable").title(None).axis(labelAngle=0, labelFontSize=15),
            y=alt.Y("value").title(name).scale(zero=False),
            color=alt.Color("variable").scale(scheme="dark2").legend(None),
            column=alt.Column("time_of_day:N").title(None),
        )
        .properties(width=200, height=300)
    )


def split(ds: xr.Dataset) -> pl.DataFrame:
    return DayNightData(*group_dataset_by_time(ds)).to_polars()


def make_box_pressure():
    internal, external = get_data_for_pressure()
    c1 = plot_qoi_box(split(external), "Maximum Difference in External Pressure [Pa]")
    c2 = plot_qoi_box(split(internal), "Maximum Difference in Internal Pressure [Pa]")
    return c1 | c2


def make_box_vent():
    return plot_qoi_box(split(get_data_for_flow()), "Space-Averaged Flow Rate [m3/s]")


def make_box_temp():
    c1 = plot_qoi_box(split(get_data_for_temperature_simple()), "Temperature [ºC]")
    c2 = plot_qoi_box(split(get_data_for_temperature_deviation()), "Temperature Deviation [ºC]")
    return c1 | c2
