from pathlib import Path

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


class ProjectPaths:
    svgs = SVGPaths
    geoms = GeomPaths


class FileNames:
    config = "config.yaml"
    svg = "out.svg"
