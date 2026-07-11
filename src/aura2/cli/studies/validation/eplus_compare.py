import re
from pathlib import Path

import altair as alt
import polars as pl
import yaml
from cyclopts import App
from plan2eplus.ep_paths import ep_paths
from plan2eplus.ezcase.ez import EZ
from plan2eplus.ezcase.utils import RunVariablesInput, open_idf
from plan2eplus.geometry.directions import WallNormal
from plan2eplus.ops.run_settings.user_interfaces import AnalysisPeriod
from plan2eplus.ops.subsurfaces.interfaces import ZoneDirectionEdge, ZoneEdge
from plan2eplus.ops.subsurfaces.logic.select import (
    get_surface_between_zone_and_direction,
    get_surface_between_zones,
    get_zones_by_plan_name,
)
from plan2eplus.paths import Constants
from plan2eplus.visuals.simple_plots import make_base_plot
from plyze.qoi.data.data import to_dataframe
from plyze.qoi.data.interfaces import CaseQOIandData, QOIandData
from plyze.qoi.data.spaces import create_space_df
from plyze.qoi.registries.main import QOIRegistry
from plyze.utils import XArrayNames
from sv2.pfix.config import CaseConfig
from sv2.pfix.main import transform_svg
from utils4plans.io.extras.figures import save_mpl_fig

from aura2.geom.adjacencies import EdgeTypes, read_adjacencies, read_subsurface_inputs
from aura2.geom.zones import get_eplus_rooms_from_path
from aura2.paths import FileNames as fn
from aura2.paths import ProjectPaths

epc = App("epc")

REF_IDF = ProjectPaths.svgs.eplus / "AirflowNetwork3zVent.idf"
ADJ_PATH = ProjectPaths.geoms.eplus / "eplus.adj.yaml"
VALIDATE_DIR = ProjectPaths.geoms.eplus / "validate"
CHICAGO_EPW = ep_paths.get_path(
    Path(ep_paths.config.ep_dir.weather_files)
    / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
)
RUN_PERIOD = AnalysisPeriod("validate", 7, 7, 1, 2)
QOIS = [QOIRegistry.temp, QOIRegistry.vent_vol, QOIRegistry.mix_vol]


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


@epc.command
def fe():
    rooms = fc()
    subsurface_inputs = fd()
    output_path = ProjectPaths.geoms.eplus
    case = EZ(output_path=output_path)
    case.add_zones(rooms)
    case.add_subsurfaces(subsurface_inputs)

    bp = make_base_plot(case).finalize()
    save_mpl_fig(bp.fig, output_path / "case.png")
    return case


def canonical_room(name: str) -> str:
    m = re.search(r"NORTH|SOUTH|EAST|WEST", name.upper())
    return m.group(0) if m else name


# ============================================================================
# VALIDATION SHIM (temporary) - match built AFN venting control to the reference
# AirflowNetwork3zVent model. plan2eplus's IDFAFNZone only writes Constant/NoVent
# control, so built windows end up always-open (opening factor 1). Here we set the
# reference's per-zone Temperature control + copy its WindowVentSched, and set the
# surface opening factor to 0.5, so windows modulate thermostatically like the ref.
# TODO: integrate Temperature venting control into plan2eplus IDFAFNZone and remove.
# (zone name -> ventilation control mode, min open factor, dT low, dT high)
REF_ZONE_VENTING = {
    "WEST": ("Temperature", 0.3, 5, 10),
    "NORTH": ("Temperature", 1.0, 0, 100),
    "EAST": ("NoVent", 1.0, 0, 100),
}


def match_reference_venting_control(idf):
    ref = open_idf(REF_IDF)
    for key, name in (("SCHEDULETYPELIMITS", "Any Number"),
                      ("SCHEDULE:COMPACT", "WindowVentSched")):
        if not idf.getobject(key, name):
            idf.copyidfobject(ref.getobject(key, name))

    for z in idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:ZONE"]:
        mode, min_factor, dt_lo, dt_hi = REF_ZONE_VENTING[canonical_room(z.Zone_Name)]
        z.Ventilation_Control_Mode = mode
        z.Ventilation_Control_Zone_Temperature_Setpoint_Schedule_Name = (
            "WindowVentSched" if mode == "Temperature" else ""
        )
        z.Minimum_Venting_Open_Factor = min_factor
        z.Indoor_and_Outdoor_Temperature_Difference_Lower_Limit_For_Maximum_Venting_Open_Factor = dt_lo
        z.Indoor_and_Outdoor_Temperature_Difference_Upper_Limit_for_Minimum_Venting_Open_Factor = dt_hi
        z.Indoor_and_Outdoor_Enthalpy_Difference_Lower_Limit_For_Maximum_Venting_Open_Factor = 0
        z.Indoor_and_Outdoor_Enthalpy_Difference_Upper_Limit_for_Minimum_Venting_Open_Factor = 300000

    for s in idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:SURFACE"]:
        s.Ventilation_Control_Mode = "ZoneLevel"  # defer to zone-level control
        s.WindowDoor_Opening_Factor_or_Crack_Factor = 0.5  # reference window factor
# ============================================================================


# ============================================================================
# VALIDATION SHIM (temporary) - add the crack edges (EdgeTypes.CRACK, filtered
# out of SubsurfaceInputs) to the built model as wall leakage, matching the
# reference's CR-1 crack + ReferenceCrackConditions. Zone-zone cracks go on the
# shared interior wall; zone-direction cracks go on the exterior wall (reusing
# the per-direction WPC curve via a new external node). Call AFTER the venting
# shim so only openings get venting control.
# TODO: route EdgeTypes.CRACK through the adjacencies -> AFN pipeline properly.
# ============================================================================
def add_reference_cracks(case: EZ):
    idf, zones = case.idf, case.objects.zones
    ref = open_idf(REF_IDF)
    for key, name in (
        ("AIRFLOWNETWORK:MULTIZONE:REFERENCECRACKCONDITIONS", "ReferenceCrackConditions"),
        ("AIRFLOWNETWORK:MULTIZONE:SURFACE:CRACK", "CR-1"),
    ):
        if not idf.getobject(key, name):
            idf.copyidfobject(ref.getobject(key, name))

    cracks = [a for a in read_adjacencies(ADJ_PATH) if a.edge_type is EdgeTypes.CRACK]

    # a zone touched by an interzone crack must itself be an AFN zone; zones with
    # no controllable openings (e.g. East) never got one, so add them as NoVent
    afn_zone_names = {z.Zone_Name for z in idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:ZONE"]}
    crack_rooms = {
        n for a in cracks for n in (a.edge.space_a, a.edge.space_b)
        if n not in WallNormal.keys()
    }
    for room in crack_rooms:
        zone = get_zones_by_plan_name(room, zones)
        if zone.zone_name not in afn_zone_names:
            idf.newidfobject(
                "AIRFLOWNETWORK:MULTIZONE:ZONE",
                Zone_Name=zone.zone_name,
                Ventilation_Control_Mode="NoVent",
            )

    nodes: set[str] = set()
    walls: set[str] = set()
    for a in cracks:
        e = a.edge
        if a.group_type == "Zone_Zone":
            wall, _ = get_surface_between_zones(ZoneEdge(e.space_a, e.space_b), zones)
            ext_node = ""
        else:
            drn = e.space_a if e.space_a in WallNormal.keys() else e.space_b
            room = e.space_b if e.space_a in WallNormal.keys() else e.space_a
            wall = get_surface_between_zone_and_direction(
                ZoneDirectionEdge(room, WallNormal[drn]), zones
            )
            ext_node = f"Crack_ExtNode_{drn}_{room}"
            if ext_node not in nodes:
                nodes.add(ext_node)
                idf.newidfobject(
                    "AIRFLOWNETWORK:MULTIZONE:EXTERNALNODE",
                    Name=ext_node,
                    External_Node_Height=0,
                    Wind_Pressure_Coefficient_Curve_Name=f"AFN_Pressure_Coefficient_Values_{drn}",
                )
        if wall.surface_name in walls:
            continue  # one crack per wall
        walls.add(wall.surface_name)
        idf.newidfobject(
            "AIRFLOWNETWORK:MULTIZONE:SURFACE",
            Surface_Name=wall.surface_name,
            Leakage_Component_Name="CR-1",
            External_Node_Name=ext_node,
            WindowDoor_Opening_Factor_or_Crack_Factor=1,
        )
# ============================================================================


# ============================================================================
# VALIDATION SHIM (temporary) - swap the built model's generic geomeppy
# constructions ("Medium Exterior Wall" etc.) for the reference's ASHRAE
# constructions so thermal mass (and thus indoor temp / temperature-driven
# venting) matches. Copies the reference Construction + Material objects and
# reassigns built surfaces by type.
# TODO: make constructions a real ConstructionInput in the build pipeline.
# ============================================================================
REF_CONSTRUCTIONS = {  # built surface type -> reference construction name
    "WALL_EXT": "EXTWALL80",
    "WALL_INT": "PARTITION06",
    "FLOOR": "FLOOR SLAB 8 IN",
    "ROOF": "ROOF34",
    "WINDOW": "WIN-CON-LIGHT",
    "DOOR": "DOOR-CON",
}


def match_reference_constructions(case: EZ):
    idf = case.idf
    ref = open_idf(REF_IDF)
    for key in ("MATERIAL", "MATERIAL:NOMASS", "MATERIAL:AIRGAP",
                "WINDOWMATERIAL:GLAZING", "WINDOWMATERIAL:GAS", "CONSTRUCTION"):
        for obj in ref.idfobjects[key]:
            if not idf.getobject(key, obj.Name):
                idf.copyidfobject(obj)

    for s in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        t = s.Surface_Type.upper()
        if t == "WALL":
            external = s.Outside_Boundary_Condition.upper() == "OUTDOORS"
            s.Construction_Name = REF_CONSTRUCTIONS["WALL_EXT" if external else "WALL_INT"]
        elif t == "FLOOR":
            s.Construction_Name = REF_CONSTRUCTIONS["FLOOR"]
        elif t in ("ROOF", "CEILING"):
            s.Construction_Name = REF_CONSTRUCTIONS["ROOF"]
    for w in idf.idfobjects["WINDOW"]:
        w.Construction_Name = REF_CONSTRUCTIONS["WINDOW"]
    for d in idf.idfobjects["DOOR:INTERZONE"]:
        d.Construction_Name = REF_CONSTRUCTIONS["DOOR"]

    # reference floors are adiabatic (BC=Surface->self, NoSun/NoWind); built floors
    # default to Ground -> steady heat loss to cool ground makes built ~2C cooler
    for s in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        if s.Surface_Type.upper() == "FLOOR":
            s.Outside_Boundary_Condition = "Surface"
            s.Outside_Boundary_Condition_Object = s.Name
            s.Sun_Exposure = "NoSun"
            s.Wind_Exposure = "NoWind"
# ============================================================================


# ============================================================================
# VALIDATION SHIM (temporary) - the reference is an office model with internal
# gains (People/Lights/ElectricEquipment); the built model has none, so it runs
# ~2C cooler and the temperature-driven venting differs. Copy the reference gain
# objects (remapping the zone field, obj[2], to the matching built zone) and
# their schedules.
# TODO: model internal gains as a real build-pipeline input.
# ============================================================================
def match_reference_internal_gains(case: EZ):
    idf = case.idf
    ref = open_idf(REF_IDF)
    built_zone = {canonical_room(z.zone_name): z.zone_name for z in case.objects.zones}

    for key in ("SCHEDULETYPELIMITS", "SCHEDULE:COMPACT", "SCHEDULE:CONSTANT",
                "SCHEDULE:DAY:HOURLY", "SCHEDULE:WEEK:DAILY", "SCHEDULE:YEAR"):
        for obj in ref.idfobjects[key]:
            if not idf.getobject(key, obj.Name):
                idf.copyidfobject(obj)

    for key in ("PEOPLE", "LIGHTS", "ELECTRICEQUIPMENT"):
        for obj in ref.idfobjects[key]:
            room = canonical_room(obj.obj[2])  # field 2 = zone name
            if room in built_zone:
                idf.copyidfobject(obj).obj[2] = built_zone[room]
# ============================================================================


def run_case(case: EZ, output_path: Path):
    case.save_and_run(
        run_vars=RunVariablesInput(epw_path=CHICAGO_EPW, analysis_period=RUN_PERIOD),
        output_path=output_path,
        run=True,
    )


def build_case_df(idf: Path, sql: Path):
    # full 2-day series (no time downsampling); one column per QOI nickname
    def qoi_df(qoi):
        q = QOIandData(qoi, sql)
        q.set_array(q.original_arr)
        return to_dataframe(q)

    dfs = [qoi_df(q) for q in QOIS]
    df = dfs[0]
    for other in dfs[1:]:
        df = df.join(other, on=[XArrayNames.DATETIME, XArrayNames.SPACE])
    return df.join(create_space_df(idf), on=XArrayNames.SPACE)


def save_case_qois(case_name: str, output_path: Path):
    idf = output_path / Constants.idf_name
    sql = output_path / Constants.sql_path
    df = build_case_df(idf, sql).with_columns(
        room=pl.col("space_names").map_elements(canonical_room, return_dtype=pl.String)
    )
    CaseQOIandData(case_name, df).write(output_path / "qois.parquet")


@epc.command
def ff():
    VALIDATE_DIR.mkdir(parents=True, exist_ok=True)

    ref_out = VALIDATE_DIR / "reference"
    ref = EZ(idf_path=REF_IDF, output_path=ref_out, read_existing=False)
    # only simulate the weather run period so the sql has a single environment
    ref.idf.idfobjects["SIMULATIONCONTROL"][0].Run_Simulation_for_Sizing_Periods = "No"
    run_case(ref, ref_out)
    save_case_qois("reference", ref_out)

    built_out = VALIDATE_DIR / "built"
    built = (
        EZ(output_path=built_out)
        .add_zones(fc())
        .add_subsurfaces(fd())
        .add_constructions()
        .add_airflow_network()
    )
    match_reference_venting_control(built.idf)  # VALIDATION SHIM (see above)
    add_reference_cracks(built)  # VALIDATION SHIM (see above)
    match_reference_constructions(built)  # VALIDATION SHIM (see above)
    match_reference_internal_gains(built)  # VALIDATION SHIM (see above)
    # sample at the same rate as the reference (6 timesteps/hour = 10-min)
    built.idf.idfobjects["TIMESTEP"][0].Number_of_Timesteps_per_Hour = 6
    run_case(built, built_out)
    save_case_qois("built", built_out)


@epc.command
def fg():
    cases = [
        CaseQOIandData.read(VALIDATE_DIR / name / "qois.parquet")
        for name in ("reference", "built")
    ]
    cols = ["datetimes", "room", "temp", "vent_vol", "mix_vol"]
    df = pl.concat(
        [c.dataframe.select(cols).with_columns(case=pl.lit(c.case_name)) for c in cases]
    )

    def qoi_chart(qoi):
        return (
            alt.Chart(df, title=qoi.label)
            .mark_line()
            .encode(
                x=alt.X("datetimes:T").title("Time"),
                y=alt.Y(f"{qoi.nickname}:Q").title(qoi.unit).scale(zero=False),
                color=alt.Color("case:N").title("Case"),
            )
            .properties(width=220, height=130)
            .facet(column=alt.Column("room:N").title(None))
        )

    chart = alt.vconcat(*[qoi_chart(q) for q in QOIS]).resolve_scale(color="independent")
    chart.save(str(VALIDATE_DIR / "validation.png"))
    return chart
