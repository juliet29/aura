from __future__ import annotations

import csv
from pathlib import Path

import polars as pl

TEMPERATURE = "Dry Bulb Temperature"
WIND_SPEED = "Wind Speed"
WIND_DIRECTION = "Wind Direction"

EPW_COLUMNS = [
    "Year", "Month", "Day", "Hour", "Minute", "Data Source and Uncertainty Flags",
    "Dry Bulb Temperature", "Dew Point Temperature", "Relative Humidity",
    "Atmospheric Station Pressure", "Extraterrestrial Horizontal Radiation",
    "Extraterrestrial Direct Normal Radiation", "Horizontal Infrared Radiation Intensity",
    "Global Horizontal Radiation", "Direct Normal Radiation", "Diffuse Horizontal Radiation",
    "Global Horizontal Illuminance", "Direct Normal Illuminance", "Diffuse Horizontal Illuminance",
    "Zenith Luminance", "Wind Direction", "Wind Speed", "Total Sky Cover",
    "Opaque Sky Cover (used if Horizontal IR Intensity missing)", "Visibility",
    "Ceiling Height", "Present Weather Observation", "Present Weather Codes",
    "Precipitable Water", "Aerosol Optical Depth", "Snow Depth", "Days Since Last Snowfall",
    "Albedo", "Liquid Precipitation Depth", "Liquid Precipitation Quantity",
]


def first_climate_row(fp: Path) -> int:
    with open(fp, newline="") as f:
        for i, row in enumerate(csv.reader(f, delimiter=",", quotechar='"')):
            if row[0].isdigit():
                return i
    return 0


def read_epw(fp: Path) -> pl.DataFrame:
    df = pl.read_csv(fp, skip_rows=first_climate_row(fp), has_header=False, new_columns=EPW_COLUMNS)
    return (
        df.with_columns(pl.col("Hour") - 1)
        .insert_column(
            0,
            pl.concat_str(
                [
                    pl.col("Year"),
                    pl.col("Month").cast(pl.String).str.pad_start(2, "0"),
                    pl.col("Day").cast(pl.String).str.pad_start(2, "0"),
                    pl.col("Hour").cast(pl.String).str.pad_start(2, "0"),
                    pl.col("Minute").cast(pl.String).str.pad_start(2, "0"),
                ],
                separator="-",
            ).alias("datetime"),
        )
        .with_columns(pl.col("datetime").str.to_datetime(format="%Y-%m-%d-%H-%M"))
        .drop(["Year", "Month", "Day", "Hour", "Minute"])
    )
