import shutil
from pathlib import Path

import polars as pl
from plan2eplus.ezcase.ez import EZ
from plan2eplus.ezcase.utils import RunVariablesInput
from plan2eplus.paths import Constants
from plyze.qoi.data.data import to_dataframe
from plyze.qoi.data.interfaces import CaseQOIandData, QOIandData
from plyze.qoi.data.spaces import create_space_df
from plyze.utils import XArrayNames
from utils4plans.io.base import make_dir

from aura2.geom.details import DETAILS, WindowDetail
from aura2.main import (
    get_case_inputs,
    make_case_plot,
    run_campaign_case,
    transform_case,
)
from aura2.validation.p2ep.paths import (
    ADJ_PATH,
    CHICAGO_EPW,
    CURR_CASE,
    QOIS,
    REF_IDF,
    RUN_PERIOD,
    VALIDATE,
    canonical_room,
)
from aura2.validation.p2ep.shims import apply_shims


def run_vars() -> RunVariablesInput:
    return RunVariablesInput(epw_path=CHICAGO_EPW, analysis_period=RUN_PERIOD)


VALIDATION_WINDOW = WindowDetail(id=1, width=2.5, height=2.0)
VALIDATION_DETAILS = {**DETAILS, "Window": VALIDATION_WINDOW.true_detail}


def transform():
    transform_case(CURR_CASE)
    shutil.copy(CURR_CASE.inputs_dir / "eplus.adj.yaml", ADJ_PATH)


def case_inputs():
    return get_case_inputs(CURR_CASE.geom, details=VALIDATION_DETAILS)


def inspect_case() -> EZ:
    rooms, subsurface_inputs = case_inputs()
    case = EZ(output_path=CURR_CASE.model)
    case.add_zones(rooms)
    case.add_subsurfaces(subsurface_inputs)
    make_case_plot(case, CURR_CASE.temp_dir)
    return case


def build_reference(out: Path) -> EZ:
    ref = EZ(idf_path=REF_IDF, output_path=out, read_existing=False)
    ref.idf.idfobjects["SIMULATIONCONTROL"][0].Run_Simulation_for_Sizing_Periods = "No"
    ref.save_and_run(run_vars=run_vars(), output_path=out, run=False, save=True)
    return ref


def build_built(out: Path) -> EZ:
    rooms, subsurface_inputs = case_inputs()
    built = (
        EZ(output_path=out)
        .add_zones(rooms)
        .add_subsurfaces(subsurface_inputs)
        .add_constructions()
        .add_airflow_network()
    )
    apply_shims(built)
    built.idf.idfobjects["TIMESTEP"][0].Number_of_Timesteps_per_Hour = 6
    built.save_and_run(run_vars=run_vars(), output_path=out, run=False, save=True)
    return built


def simulate(out: Path):
    run_campaign_case(
        out / Constants.idf_name, out, epw=CHICAGO_EPW, analysis_period=RUN_PERIOD
    )


def run_case(case: EZ, out: Path):
    case.save_and_run(run_vars=run_vars(), output_path=out, run=True)


def build_case_df(idf: Path, sql: Path):
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
    make_dir(output_path / "qois.parquet")
    CaseQOIandData(case_name, df).write(output_path / "qois.parquet")


def run_validation(run: bool = True):
    build_reference(VALIDATE.case("reference"))
    build_built(VALIDATE.case("built"))
    if not run:
        return

    for name in ("reference", "built"):
        simulate(VALIDATE.case(name))
        save_case_qois(name, VALIDATE.case(name))
