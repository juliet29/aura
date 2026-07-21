from polyfix.main.process import read_layout_from_path, write_layout
from polyfix.main.workflow_paths import SingleWorkflowPaths
from sv2.pfix.main import calculate_scaling_factor, write_initial_model
from utils4plans.io.extras.yaml import read_yaml

from aura2.paths import FileNames as fn
from aura2.paths import GeomPaths, StaticPaths
from aura2.validation.robustness.perturb import perturb_layout

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
    data = read_yaml(PLANS_DIR / plan / fn.config)
    return calculate_scaling_factor(data["pixel"], data["meter"])


def prepare_workdir(plan: str, shrink: float, seed: int, tag: str) -> SingleWorkflowPaths:
    workdir = ROBUST_DIR / plan / tag
    write_initial_model(PLANS_DIR / plan / fn.svg, workdir, read_scaling(plan))
    paths = SingleWorkflowPaths(workdir)
    if shrink > 0:
        layout = perturb_layout(read_layout_from_path(paths.init), FRACTION, shrink, seed)
        write_layout(layout, paths.init)
    return paths
