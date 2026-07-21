import os
from enum import Enum
from pathlib import Path

import pyprojroot
from dotenv import load_dotenv

BASE_PATH = pyprojroot.find_root(pyprojroot.has_dir(".git"))
load_dotenv(Path(BASE_PATH) / ".env")
TEMP_PATH = os.getenv("TEMP_PATH", "static/4_temp")


class StaticPaths:
    inputs = Path(BASE_PATH) / "static/1_inputs"
    temp = Path(BASE_PATH) / TEMP_PATH / "4_temp"
    figures = Path(BASE_PATH) / TEMP_PATH / "5_figures"


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


class ProjectDir(Enum):
    eplus_compare = "eplus_compare"
    a = "real_plans/a"
    b = "real_plans/b"
    c = "real_plans/c"

    @property
    def inputs_dir(self):
        return StaticPaths.inputs / self.value

    @property
    def temp_dir(self):
        return StaticPaths.temp / self.value

    @property
    def raw(self):
        return self.temp_dir / "raw"

    @property
    def geom(self):
        return self.temp_dir / "geom"

    @property
    def model(self):
        return self.temp_dir / "model"


# ok for FileNames to coexist here because this is a root repo
class FileNames:
    config = "config.yaml"
    svg = "out.svg"

    gen_adjacencies = "out.adj.yaml"
    copied_adjacencies = "copy.adj.yaml"
    adjacencies = "adj.yaml"
    corrected_geom = "reconcile/out.json"  # polyfix reconcile stage closes ymove gaps

    # figures
    base_plot = "base.png"

    # modeling
    idf = "out.idf"


class ProjectPaths:  # TODO: validation studies still depend on these, but needs to integrape with new ProjectDir schema
    svgs = SVGPaths
    geoms = GeomPaths
