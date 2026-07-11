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

from aura2.cli.studies.eplus_compare import run_case
from aura2.cli.studies.robustness.run import (
    RESULTS_DIR,
    ROBUST_DIR,
    SHRINKS,
    discover_plans,
    rob,
)
from aura2.cli.studies.robustness.select import select_extremes
from aura2.geom.adjacencies import read_subsurface_inputs
from aura2.geom.zones import get_eplus_rooms_from_path


def build_and_run(workdir: Path):
    # No AirflowNetwork: auto adjacencies + real-plan geometry give invalid AFN
    # inputs (zones without openings, door edges between non-adjacent rooms) and
    # E+ fatals. Free-floating zone temperature is the reproducibility QOI.
    out = workdir / "eplus"
    rooms = get_eplus_rooms_from_path(workdir / "ymove/out.json")
    subs = read_subsurface_inputs(workdir / "out.adj.yaml", strict=False)
    case = EZ(output_path=out).add_zones(rooms).add_subsurfaces(subs).add_constructions()
    run_case(case, out)
    return out


def summarize(out: Path, plan, shrink, seed) -> list[dict]:
    idf, sql = out / Constants.idf_name, out / Constants.sql_path
    q = QOIandData(QOIRegistry.temp, sql)
    q.set_array(q.original_arr)
    df = to_dataframe(q).join(create_space_df(idf), on=XArrayNames.SPACE).to_pandas()
    g = df.groupby("space_names")["temp"]
    rows = []
    for stat, series in (("peak", g.max()), ("mean", g.mean())):
        for room, value in series.items():
            rows.append({
                "plan": plan, "shrink": shrink, "seed": seed,
                "room": room, "qoi": "temp", "stat": stat, "value": value,
            })
    return rows


@rob.command
def energy():
    # run E+ only on the selected extreme cases (baseline/best/median/worst per plan)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sel = select_extremes()
    sel.to_csv(RESULTS_DIR / "extremes.csv", index=False)
    logger.info(f"selected {len(sel)} cases for energy analysis")
    rows = []
    for _, r in sel.iterrows():
        tag = f"shrink{int(r['shrink'] * 100)}_seed{int(r['seed'])}"
        workdir = ROBUST_DIR / r["plan"] / tag
        try:
            out = build_and_run(workdir)
            for rec in summarize(out, r["plan"], r["shrink"], int(r["seed"])):
                rec["role"] = r["role"]
                rows.append(rec)
        except Exception as e:
            logger.warning(f"energy {r['plan']} {tag}: {type(e).__name__}: {e}")
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "thermal_extremes.csv", index=False)


@rob.command
def thermal(seeds: int = 3):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    conditions = [(0.0, 0)] + [(s, seed) for s in SHRINKS for seed in range(seeds)]
    rows = []
    for plan in discover_plans():
        for shrink, seed in conditions:
            workdir = ROBUST_DIR / plan / f"shrink{int(shrink * 100)}_seed{seed}"
            try:
                out = build_and_run(workdir)
                rows.extend(summarize(out, plan, shrink, seed))
            except Exception as e:
                logger.warning(f"thermal {plan} shrink={shrink} seed={seed}: {e}")
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "thermal.csv", index=False)
