import hashlib
from dataclasses import dataclass

import pandas as pd
from loguru import logger
from polyfix.main.execute import execute_polyfix
from polyfix.main.process import read_layout_from_path
from utils4plans.io.base import make_dir

from aura2.validation.robustness import metrics
from aura2.validation.robustness.paths import (
    RESULTS_DIR,
    SHRINKS,
    discover_plans,
    prepare_workdir,
)


def geometry_hash(layout) -> str:
    items = sorted(
        (d.name, tuple(round(v, 6) for p in d.coords for v in p.as_tuple))
        for d in layout.domains
    )
    return hashlib.sha256(repr(items).encode()).hexdigest()[:16]


@dataclass
class RunResult:
    valid: bool
    reason: str
    geometry_rows: list[dict]


def geometry_rows(plan, shrink, seed, before, after) -> list[dict]:
    rb, ra = metrics.room_metrics(before), metrics.room_metrics(after)
    fb, fa = metrics.floor_metrics(before), metrics.floor_metrics(after)

    def row(scope, b, a):
        return {
            "plan": plan, "shrink": shrink, "seed": seed, "scope": scope,
            "area_before": b["area"], "area_after": a["area"],
            "sf_before": b["shape_factor"], "sf_after": a["shape_factor"],
        }

    rows = [row(name, rb[name], ra[name]) for name in sorted(set(rb) & set(ra))]
    rows.append(row("FLOOR", fb, fa))
    return rows


def run_condition(plan: str, shrink: float, seed: int) -> RunResult:
    tag = f"shrink{int(shrink * 100)}_seed{seed}"
    paths = prepare_workdir(plan, shrink, seed, tag)
    try:
        execute_polyfix(paths.base, save_adj=True)
    except Exception as e:
        logger.warning(f"{plan} {tag} failed: {type(e).__name__}")
        return RunResult(False, f"polyfix error: {type(e).__name__}", [])

    before = read_layout_from_path(paths.init)
    after = read_layout_from_path(paths.ymove)

    valid, reason = metrics.is_valid(after)
    rows = geometry_rows(plan, shrink, seed, before, after)
    return RunResult(valid, reason, rows)


def run_all(seeds: int = 10):
    conditions = [(0.0, 0)] + [(s, seed) for s in SHRINKS for seed in range(seeds)]
    geom, runs = [], []
    for plan in discover_plans():
        for shrink, seed in conditions:
            res = run_condition(plan, shrink, seed)
            geom.extend(res.geometry_rows)
            runs.append({
                "plan": plan, "shrink": shrink, "seed": seed,
                "valid": res.valid, "reason": res.reason,
            })
    make_dir(RESULTS_DIR / "geometry.csv")
    pd.DataFrame(geom).to_csv(RESULTS_DIR / "geometry.csv", index=False)
    pd.DataFrame(runs).to_csv(RESULTS_DIR / "runs.csv", index=False)


def determinism_check(repeats: int = 3):
    rows = []
    for plan in discover_plans():
        hashes = []
        for r in range(repeats):
            paths = prepare_workdir(plan, 0.0, 0, f"determinism_{r}")
            execute_polyfix(paths.base, save_adj=True)
            hashes.append(geometry_hash(read_layout_from_path(paths.ymove)))
        rows.append({
            "plan": plan, "repeats": repeats,
            "identical": len(set(hashes)) == 1, "hash": hashes[0],
        })
    make_dir(RESULTS_DIR / "determinism.csv")
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "determinism.csv", index=False)
