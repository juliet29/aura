import shutil
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
from aura2.paths import ProjectDir


def make_case_plot(case: EZ, path: Path):
    bp = make_base_plot(case).finalize()
    save_mpl_fig(bp.fig, path / fn.base_case)


def get_case_inputs(path: Path):
    rooms = get_eplus_rooms_from_path(path / fn.corrected_geom)
    subsurface_inputs = read_subsurface_inputs(path / fn.adjacencies)
    return rooms, subsurface_inputs


def transform_case(pd: ProjectDir):
    # first copy data from inputs to temp
    shutil.copytree(pd.inputs_dir, pd.raw, dirs_exist_ok=True)

    data = read_yaml(pd.raw / fn.config)
    pixel = data["pixel"]
    meter = data["meter"]

    config = CaseConfig(pd.raw / fn.svg, pixel, meter, pd.geom)
    transform_svg(config)
    return config


def make_basic_case(pd: ProjectDir):
    rooms, subsurface_inputs = get_case_inputs(pd.geom)

    case = EZ(output_path=pd.model)
    case.add_zones(rooms)
    case.add_subsurfaces(subsurface_inputs)
    case.save_and_run(save=True, run=False)

    return case
