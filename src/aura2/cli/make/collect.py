import shutil
from pathlib import Path

from loguru import logger
from utils4plans.io.base import make_dir

from aura2.paths import BASE_PATH, StaticPaths
from aura2.validation.p2ep.paths import VALIDATE
from aura2.validation.robustness.paths import RESULTS_DIR

PUBLISHED = Path(BASE_PATH) / "static" / "5_figures"

ROBUSTNESS_FILES = [
    "fig2_zones.png",
    "fig_failure_modes.png",
    "fig_energy.png",
    "table3_energy.csv",
    "table1_validity.csv",
]
EPLUS_FILES = ["validation.png"]
RESULTS_SRC = StaticPaths.figures / "real_plans"


def copy_to(src: Path, dst_dir: Path) -> bool:
    if not src.exists():
        logger.warning(f"missing {src}")
        return False
    dst = dst_dir / src.name
    make_dir(dst)
    shutil.copy(src, dst)
    logger.info(f"{src.name} -> {dst}")
    return True


def collect_figures():
    n = 0
    for name in ROBUSTNESS_FILES:
        n += copy_to(RESULTS_DIR / name, PUBLISHED / "validation")
    for name in EPLUS_FILES:
        n += copy_to(VALIDATE.base / name, PUBLISHED / "validation")
    for src in sorted(RESULTS_SRC.glob("*")):
        if src.is_file():
            n += copy_to(src, PUBLISHED / "results")
    logger.info(f"collected {n} files into {PUBLISHED}")
