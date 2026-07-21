from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import altair as alt
import polars as pl
import xarray as xr
from matplotlib.figure import Figure

STUDY_DATE = (2017, 7, 1)
STUDY_HOUR = 12

AltairChart = (
    alt.Chart | alt.HConcatChart | alt.VConcatChart | alt.FacetChart | alt.ConcatChart
)


class NamedData(NamedTuple):
    case_name: str
    data_arr: xr.DataArray


def filter_to_time(arr: xr.DataArray, date_=STUDY_DATE, hour: int = STUDY_HOUR):
    return arr.sel(datetimes=datetime(*date_, hour=hour, minute=0))


def group_dataset_by_time(ds_: xr.Dataset):
    MORN_END, DAY_END, DATE_END = 6, 18, 23
    ds = ds_.resample(datetimes="3h").mean()
    morning = ds.isel(datetimes=ds.datetimes.dt.hour.isin(range(0, MORN_END)))
    night = ds.isel(datetimes=ds.datetimes.dt.hour.isin(range(DAY_END, DATE_END)))
    full_night = xr.concat([morning, night], dim="datetimes")
    day = ds.isel(datetimes=ds.datetimes.dt.hour.isin(range(MORN_END, DAY_END)))
    return day, full_night


def convert_xarray_to_polars(data: xr.DataArray | xr.Dataset, name: str = ""):
    if name:
        data.name = name
    return pl.from_pandas(data.to_dataframe(), include_index=True)


def save_chart(chart: AltairChart | Figure, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(chart, Figure):
        chart.savefig(out, dpi=300, bbox_inches="tight")
    else:
        chart.save(str(out), ppi=300)
