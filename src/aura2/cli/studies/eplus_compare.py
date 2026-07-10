import yaml
from cyclopts import App
from sv2.pfix.config import CaseConfig
from sv2.pfix.main import transform_svg

from aura2.geom.adjacencies import read_subsurface_inputs
from aura2.geom.zones import get_eplus_rooms_from_path
from aura2.paths import FileNames as fn
from aura2.paths import ProjectPaths

epc = App("epc")


@epc.command
def transform():
    indir = ProjectPaths.svgs.eplus
    outdir = ProjectPaths.geoms.eplus

    # TODO use utils yaml
    with open(indir / fn.config) as f:
        data = yaml.safe_load(f)
    pixel = data["pixel"]
    meter = data["meter"]

    config = CaseConfig(indir / fn.svg, pixel, meter, outdir)
    transform_svg(config)
    return config


@epc.command
def fc():
    path = ProjectPaths.geoms.eplus / "ymove/out.json"
    return get_eplus_rooms_from_path(path)
    # read plans
    #


@epc.command
def fd():
    path = ProjectPaths.geoms.eplus / "eplus.adj.yaml"
    return read_subsurface_inputs(path)
    # read plans
