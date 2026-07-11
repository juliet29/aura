from pathlib import Path

from plan2eplus.ezcase.ez import EZ
from plan2eplus.visuals.simple_plots import make_base_plot
from sv2.pfix.config import CaseConfig
from sv2.pfix.main import transform_svg
from utils4plans.io.extras.figures import save_mpl_fig
from utils4plans.io.extras.yaml import read_yaml

from aura2.geom.adjacencies import read_subsurface_inputs
from aura2.geom.zones import get_eplus_rooms_from_path
from aura2.paths import FileNames as fn
from aura2.paths import ProjectPaths


def transform(indir: Path, outdir: Path):
    data = read_yaml(indir / fn.config)
    pixel = data["pixel"]
    meter = data["meter"]

    config = CaseConfig(indir / fn.svg, pixel, meter, outdir)
    transform_svg(config)
    return config


def get_case_inputs(path: Path):
    rooms = get_eplus_rooms_from_path(path / fn.geom)
    subsurface_inputs = read_subsurface_inputs(path / fn.adjacencies)
    return rooms, subsurface_inputs


def make_basic_case(path: Path):
    rooms, subsurface_inputs = get_case_inputs(path)
    output_path = ProjectPaths.geoms.eplus
    case = EZ(output_path=output_path)
    case.add_zones(rooms)
    case.add_subsurfaces(subsurface_inputs)

    bp = make_base_plot(case).finalize()
    save_mpl_fig(bp.fig, output_path / "case.png")
    return case
