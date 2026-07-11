from pathlib import Path
from typing import NamedTuple

import pyprojroot

BASE_PATH = pyprojroot.find_root(pyprojroot.has_dir(".git"))
TEMP_PATH = "/scratch/users/jnwagwu/aura"


class StaticPaths:
    inputs = Path(BASE_PATH) / "static/1_inputs"
    temp = Path(TEMP_PATH) / "4_temp"
    figures = Path(TEMP_PATH) / "5_figures"


class SVGPaths:
    base = StaticPaths.inputs
    eplus = base / "eplus_compare"
    a = base / "real_plans/a"
    b = base / "real_plans/b"
    c = base / "real_plans/c"


class GeomPaths:
    base = StaticPaths.temp / "geoms"
    eplus = base / "eplus_compare"
    a = base / "real_plans/a"
    b = base / "real_plans/b"
    c = base / "real_plans/c"


# TODO: this probably needs to be resturcuted to not be so repetititive..


class CaseFolder(NamedTuple):
    name: str
    inputs: Path = StaticPaths.inputs
    temp: Path = StaticPaths.temp

    @property
    def _init(self):
        return self.inputs / self.name

    @property
    def _intermed(self):
        return self.temp / self.name

    @property
    def init(self):
        return self._intermed / "init"

    @property
    def geom(self):
        return self._intermed / "geom"

    @property
    def model(self):
        return self._intermed / "model"


class ProjectDirectories:
    eplus_compare = CaseFolder("eplus_compare")
    a = CaseFolder("real_plans/a")
    b = CaseFolder("real_plans/b")
    c = CaseFolder("real_plans/c")


class ProjectPaths:
    svgs = SVGPaths
    geoms = GeomPaths


# ok for FileNames to coexist here because this is a root repo
class FileNames:
    config = "config.yaml"
    svg = "out.svg"
    adjacencies = "eplus.adj.yaml"
    geom = "ymove/out.json"  # will change after final polyfix check
