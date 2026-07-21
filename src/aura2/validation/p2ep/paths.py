import re
from pathlib import Path

from plan2eplus.ep_paths import ep_paths
from plan2eplus.ops.run_settings.user_interfaces import AnalysisPeriod
from plyze.qoi.registries.main import QOIRegistry

from aura2.paths import FileNames as fn
from aura2.paths import ProjectDir

CURR_CASE = ProjectDir.eplus_compare

REF_IDF = CURR_CASE.inputs_dir / "AirflowNetwork3zVent.idf"
ADJ_PATH = CURR_CASE.temp_dir / fn.adjacencies
CHICAGO_EPW = ep_paths.get_path(
    Path(ep_paths.config.ep_dir.weather_files)
    / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
)
RUN_PERIOD = AnalysisPeriod("validate", 7, 7, 1, 2)
QOIS = [QOIRegistry.temp, QOIRegistry.vent_vol, QOIRegistry.mix_vol]
NORM_BY = {"temp": "range", "vent_vol": "peak", "mix_vol": "peak"}

CASE_NAMES = ("reference", "built")


class ValidationPaths:
    def __init__(self, base: Path) -> None:
        self.base = base

    def case(self, name: str) -> Path:
        return self.base / name

    def qois(self, name: str) -> Path:
        return self.case(name) / "qois.parquet"

    def figure(self, name: str) -> Path:
        return self.base / f"{name}.png"


VALIDATE = ValidationPaths(CURR_CASE.temp_dir / "validate")


def canonical_room(name: str) -> str:
    m = re.search(r"NORTH|SOUTH|EAST|WEST", name.upper())
    return m.group(0) if m else name
