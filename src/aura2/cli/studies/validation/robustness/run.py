import hashlib
from dataclasses import dataclass

import pandas as pd
import yaml
from cyclopts import App
from loguru import logger
from polyfix.main.execute import execute_polyfix
from polyfix.main.process import read_layout_from_path, write_layout
from polyfix.main.workflow_paths import SingleWorkflowPaths
from sv2.pfix.main import calculate_scaling_factor, write_initial_model

from aura2.cli.studies.robustness import metrics
from aura2.cli.studies.robustness.perturb import perturb_layout
from aura2.paths import FileNames as fn
from aura2.paths import GeomPaths, StaticPaths

rob = App("rob")

PLANS_DIR = StaticPaths.inputs / "real_plans"
ROBUST_DIR = GeomPaths.base / "robustness"
RESULTS_DIR = ROBUST_DIR / "results"
FRACTION = 0.5
SHRINKS = [0.10, 0.20, 0.30]


def discover_plans() -> list[str]:
    return sorted(
        p.name
        for p in PLANS_DIR.iterdir()
        if (p / fn.config).exists() and (p / fn.svg).exists()
    )


def read_scaling(plan: str) -> float:
    with open(PLANS_DIR / plan / fn.config) as f:
        data = yaml.safe_load(f)
    return calculate_scaling_factor(data["pixel"], data["meter"])


def prepare_workdir(plan: str, shrink: float, seed: int, tag: str) -> SingleWorkflowPaths:
    workdir = ROBUST_DIR / plan / tag
    write_initial_model(PLANS_DIR / plan / fn.svg, workdir, read_scaling(plan))
    paths = SingleWorkflowPaths(workdir)
    if shrink > 0:
        layout = perturb_layout(read_layout_from_path(paths.init), FRACTION, shrink, seed)
        write_layout(layout, paths.init)
    return paths


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
    ged: float | None
    edges_before: int | None
    edges_after: int | None
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
        return RunResult(False, f"polyfix error: {type(e).__name__}", None, None, None, [])

    before = read_layout_from_path(paths.init)          # geometry: raw perturbed init
    simplified = read_layout_from_path(paths.simplify)  # adjacency baseline (orthogonalized)
    after = read_layout_from_path(paths.ymove)

    valid, reason = metrics.is_valid(after)
    g_before = metrics.adjacency_graph(simplified)
    g_after = metrics.adjacency_graph(after)
    ged = metrics.graph_edit_distance(g_before, g_after)
    rows = geometry_rows(plan, shrink, seed, before, after)
    return RunResult(valid, reason, ged,
                     g_before.number_of_edges(), g_after.number_of_edges(), rows)


@rob.command
def run(seeds: int = 10):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    conditions = [(0.0, 0)] + [(s, seed) for s in SHRINKS for seed in range(seeds)]
    geom, runs = [], []
    for plan in discover_plans():
        for shrink, seed in conditions:
            res = run_condition(plan, shrink, seed)
            geom.extend(res.geometry_rows)
            runs.append({
                "plan": plan, "shrink": shrink, "seed": seed,
                "valid": res.valid, "reason": res.reason, "ged": res.ged,
                "edges_before": res.edges_before, "edges_after": res.edges_after,
            })
    pd.DataFrame(geom).to_csv(RESULTS_DIR / "geometry.csv", index=False)
    pd.DataFrame(runs).to_csv(RESULTS_DIR / "runs.csv", index=False)


@rob.command
def determinism(repeats: int = 3):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
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
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "determinism.csv", index=False)
