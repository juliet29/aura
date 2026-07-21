from __future__ import annotations

import altair as alt
import polars as pl

from aura2.analysis.sources.weather_io import (
    TEMPERATURE,
    WIND_DIRECTION,
    WIND_SPEED,
    read_epw,
)
from aura2.pipeline.paths import CAMPAIGN_EPW

qois = [TEMPERATURE, WIND_SPEED, WIND_DIRECTION]
units = ["[ºC]", "[m/s]", "[º]"]


def make_site_temp():
    epw = read_epw(CAMPAIGN_EPW).with_columns(
        month=pl.col.datetime.dt.month(),
        hour=pl.col.datetime.dt.hour(),
        month_string=pl.col.datetime.dt.strftime("%B"),
    )
    data = (
        epw.group_by(pl.col.month, pl.col.hour, maintain_order=True)
        .agg(
            pl.col(TEMPERATURE).mean(),
            pl.col(WIND_SPEED).median(),
            pl.col(WIND_DIRECTION).median(),
            pl.col("month_string").first(),
        )
        .filter(pl.col.month.is_in(range(6, 11)))
    )
    row = alt.hconcat()
    for qoi, unit in zip(qois, units):
        row |= data.plot.line(
            x=alt.X("hour").title("Hour of Day"),
            y=alt.Y(f"{qoi}:Q").scale(zero=False).title(f"{qoi} {unit}"),
            color=alt.Color("month_string:O").scale(scheme="viridis").title("Months").sort(),
        )
    return row
