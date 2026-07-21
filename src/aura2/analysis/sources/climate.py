from __future__ import annotations

import numpy as np
import pandas as pd
from plan2eplus.results.sql import get_qoi

from aura2.analysis.utils.data import all_experiments
from aura2.analysis.sources.weather_io import WIND_DIRECTION, read_epw
from aura2.pipeline.paths import CAMPAIGN_EPW

# PA summer is a north/west see-saw (~97% of hours); east/south are negligible.
# day/night match the box-plot convention (day = 06-18h).
def section_masks() -> dict[str, np.ndarray]:
    exp = all_experiments()[0]
    dts = pd.DatetimeIndex(
        get_qoi("Zone Mean Air Temperature", exp.sql_path).data_arr["datetimes"].values
    )
    # key on (month, day, hour) since the sql year (2017) differs from the epw year
    epw = read_epw(CAMPAIGN_EPW).to_pandas()
    epw["k"] = list(zip(epw.datetime.dt.month, epw.datetime.dt.day, epw.datetime.dt.hour))
    lookup = dict(zip(epw["k"], epw[WIND_DIRECTION]))
    wd = np.array([lookup[k] for k in zip(dts.month, dts.day, dts.hour)])
    hour = dts.hour.values
    return {
        "north": (wd >= 315) | (wd < 45),
        "west": (wd >= 225) & (wd < 315),
        "day": (hour >= 6) & (hour < 18),
        "night": (hour < 6) | (hour >= 18),
    }
