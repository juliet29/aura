from pathlib import Path

import pandas as pd
from loguru import logger
from plan2eplus.ezcase.ez import EZ
from plan2eplus.paths import Constants
from plyze.qoi.data.data import to_dataframe
from plyze.qoi.data.interfaces import QOIandData
from plyze.qoi.data.spaces import create_space_df
from plyze.qoi.registries.main import QOIRegistry
from plyze.utils import XArrayNames
from utils4plans.io.base import make_dir

from aura2.geom.adjacencies import read_subsurface_inputs
from aura2.geom.zones import get_eplus_rooms_from_path
from aura2.validation.p2ep.build import run_case
from aura2.validation.robustness.paths import RESULTS_DIR, ROBUST_DIR
from aura2.validation.robustness.select import select_extremes


def build_and_run(workdir: Path):
    out = workdir / "eplus"
    rooms = get_eplus_rooms_from_path(workdir / "ymove/out.json")
    subs = read_subsurface_inputs(workdir / "out.adj.yaml", strict=False)
    case = (
        EZ(output_path=out).add_zones(rooms).add_subsurfaces(subs).add_constructions()
    )
    run_case(case, out)
    return out


def temp_series(out: Path) -> pd.DataFrame:
    idf, sql = out / Constants.idf_name, out / Constants.sql_path
    q = QOIandData(QOIRegistry.temp, sql)
    q.set_array(q.original_arr)
    df = to_dataframe(q).join(create_space_df(idf), on=XArrayNames.SPACE).to_pandas()
    return df[["datetimes", "space_names", "temp"]]


def summarize(df: pd.DataFrame, plan, shrink, seed) -> list[dict]:
    g = df.groupby("space_names")["temp"]
    rows = []
    for stat, series in (("peak", g.max()), ("mean", g.mean())):
        for room, value in series.items():
            rows.append(
                {
                    "plan": plan,
                    "shrink": shrink,
                    "seed": seed,
                    "room": room,
                    "qoi": "temp",
                    "stat": stat,
                    "value": value,
                }
            )
    return rows


def nrmse_rows(
    df: pd.DataFrame, base_df: pd.DataFrame | None, plan, shrink, seed
) -> list[dict]:
    if base_df is None:
        return []
    m = df.merge(base_df, on=["datetimes", "space_names"], suffixes=("", "_base"))
    rows = []
    for room, d in m.groupby("space_names"):
        rmse = float(((d["temp"] - d["temp_base"]) ** 2).mean() ** 0.5)
        rng = float(d["temp_base"].max() - d["temp_base"].min())
        rows.append(
            {
                "plan": plan,
                "shrink": shrink,
                "seed": seed,
                "room": room,
                "qoi": "temp",
                "stat": "nrmse",
                "value": 100 * rmse / rng if rng > 1e-9 else 0.0,
            }
        )
    return rows


def energy_study():
    sel = select_extremes()
    logger.info(f"selected {len(sel)} cases for energy analysis")
    sel = sel.assign(_ord=(sel["role"] != "baseline").astype(int)).sort_values(
        ["plan", "_ord"]
    )
    rows, base_by_plan = [], {}
    for _, r in sel.iterrows():
        plan, shrink, seed = r["plan"], r["shrink"], int(r["seed"])
        tag = f"shrink{int(shrink * 100)}_seed{seed}"
        try:
            df = temp_series(build_and_run(ROBUST_DIR / plan / tag))
        except Exception as e:
            logger.warning(f"energy {plan} {tag}: {type(e).__name__}: {e}")
            continue
        if r["role"] == "baseline":
            base_by_plan[plan] = df
        recs = summarize(df, plan, shrink, seed) + nrmse_rows(
            df, base_by_plan.get(plan), plan, shrink, seed
        )
        for rec in recs:
            rec["role"] = r["role"]
        rows.extend(recs)
    make_dir(RESULTS_DIR / "thermal_extremes.csv")
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "thermal_extremes.csv", index=False)
