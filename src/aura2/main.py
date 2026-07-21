import shutil
from pathlib import Path

from loguru import logger
from plan2eplus.ezcase.ez import EZ
from plan2eplus.ezcase.utils import RunVariablesInput
from plan2eplus.ops.run_settings.user_interfaces import AnalysisPeriod
from plan2eplus.visuals.simple_plots import make_base_plot
from sv2.pfix.config import CaseConfig
from sv2.pfix.main import transform_svg
from utils4plans.io.extras.figures import save_mpl_fig
from utils4plans.io.extras.yaml import read_yaml

from aura2.geom.adjacencies import read_subsurface_inputs
from aura2.geom.details import DETAILS, Detail, DetailType
from aura2.geom.zones import get_eplus_rooms_from_path
from aura2.paths import FileNames as fn
from aura2.paths import ProjectDir
from aura2.pipeline.modifications import resolve
from aura2.pipeline.spec import ExperimentSpec


def make_case_plot(case: EZ, path: Path):
    bp = make_base_plot(case).finalize()
    bp.axes.set_aspect("equal")

    save_mpl_fig(bp.fig, path / fn.base_plot)


MIN_ROOM_SIZE = 0.5  # m


def filter_small_rooms(rooms, min_size: float = MIN_ROOM_SIZE):
    kept = []
    for room in rooms:
        xs = [c[0] for c in room.coords]
        ys = [c[1] for c in room.coords]
        width, height = max(xs) - min(xs), max(ys) - min(ys)
        if width < min_size or height < min_size:
            logger.warning(f"dropping room {room.name}: {width:.2f}x{height:.2f} m below {min_size} m")
            continue
        kept.append(room)
    return kept


def get_case_inputs(path: Path, details: dict[DetailType, Detail] = DETAILS):
    adj = path.parent / fn.adjacencies
    if not adj.exists():
        raise FileNotFoundError(
            f"missing adjacency file {adj}; author it at "
            f"{path.parent.name}/{fn.adjacencies} in the case inputs and re-run transform"
        )
    rooms = filter_small_rooms(get_eplus_rooms_from_path(path / fn.corrected_geom))
    subsurface_inputs = read_subsurface_inputs(adj, details=details)
    return rooms, subsurface_inputs


def transform_case(pd: ProjectDir):
    # first copy data from inputs to temp
    shutil.copytree(pd.inputs_dir, pd.raw, dirs_exist_ok=True)

    data = read_yaml(pd.raw / fn.config)
    pixel = data["pixel"]
    meter = data["meter"]

    config = CaseConfig(pd.raw / fn.svg, pixel, meter, pd.geom)
    transform_svg(config)

    shutil.copy(pd.geom / fn.gen_adjacencies, pd.temp_dir / fn.copied_adjacencies)
    return config


def make_basic_case(pd: ProjectDir, run: bool = False):
    rooms, subsurface_inputs = get_case_inputs(pd.geom)

    case = EZ(output_path=pd.model)
    case.add_zones(rooms)
    case.add_subsurfaces(subsurface_inputs)
    case.add_constructions()
    case.add_airflow_network()
    case.save_and_run(save=True, run=run)

    return case


def make_campaign_case(spec: ExperimentSpec, out_path: Path, run: bool = False):
    pd = ProjectDir[spec.case_name]
    b = resolve(spec.modification)
    rooms, subsurface_inputs = get_case_inputs(pd.geom, details=b.details)
    case = EZ(output_path=out_path)
    case.add_zones(rooms)
    case.add_subsurfaces(subsurface_inputs)
    case.add_constructions(b.construction)
    case.add_airflow_network(b.afn)
    case.save_and_run(save=True, run=run)
    return case


# default analysis period: full summer cooling season (matches p1gen config.py)
SUMMER_COOLING_SEASON = AnalysisPeriod("summer_cooling_season", 6, 10, 1, 31)


def run_campaign_case(
    idf_path: Path,
    out_path: Path,
    epw: Path | None = None,
    analysis_period: AnalysisPeriod | None = None,
):
    case = EZ(idf_path=idf_path, read_existing=False)
    period = analysis_period if analysis_period is not None else SUMMER_COOLING_SEASON
    run_vars = RunVariablesInput(epw_path=epw, analysis_period=period)
    case.save_and_run(run_vars=run_vars, output_path=out_path, run=True, save=False)
    return case
