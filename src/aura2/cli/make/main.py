from pathlib import Path
from typing import Annotated

import pandas as pd
from cyclopts import App, Parameter
from loguru import logger
from tqdm import tqdm
from plyze.qoi.data.data import to_dataframe
from plyze.qoi.data.interfaces import QOIandData
from plyze.qoi.data.spaces import create_space_df
from plyze.qoi.registries.main import QOIRegistry
from plan2eplus.ops.run_settings.user_interfaces import AnalysisPeriod
from plyze.utils import XArrayNames
from utils4plans.logs import logset

from aura2.analysis.utils.common import save_chart
from aura2.analysis.build import FIGURES
from aura2.main import make_campaign_case, run_campaign_case, transform_case
from aura2.paths import ProjectDir
from aura2.pipeline.defn import CAMPAIGN_NAME, campaign_defn
from aura2.pipeline.design import enumerate_specs
from aura2.pipeline.manifest import read_manifest, write_manifest
from aura2.cli.make.collect import collect_figures

campaign = App(name="campaign")


@campaign.command
def manifest(out: Path):
    write_manifest(out, CAMPAIGN_NAME, enumerate_specs(campaign_defn))


@campaign.command
def transform(case: str):
    transform_case(ProjectDir[case])


@campaign.command
def build(id: str, manifest: Path, idf_path: Path):
    logger.info(f"[build] {id}")
    spec = {s.id: s for s in read_manifest(manifest)}[id]
    make_campaign_case(spec, idf_path.parent, run=False)


@campaign.command
def run(
    id: str,
    idf_path: Path,
    sql_path: Path,
    epw: Path | None = None,
    period_name: str | None = None,
    st_month: int | None = None,
    end_month: int | None = None,
    st_day: int | None = None,
    end_day: int | None = None,
):
    period = None
    if period_name is not None:
        period = AnalysisPeriod(period_name, st_month, end_month, st_day, end_day)
    logger.info(f"[run] {id} (period={period_name or 'summer_cooling_season (default)'})")
    run_campaign_case(idf_path, idf_path.parent, epw=epw, analysis_period=period)


@campaign.command
def qoi(id: str, idf_path: Path, sql_path: Path, out: Path):
    logger.info(f"[qoi] {id}")
    q = QOIandData(QOIRegistry.temp, sql_path)
    q.set_array(q.original_arr)
    df = to_dataframe(q).join(create_space_df(idf_path), on=XArrayNames.SPACE).to_pandas()
    g = df.groupby("space_names")["temp"]
    rows = [
        {"id": id, "room": room, "qoi": "temp", "stat": stat, "value": value}
        for stat, series in (("peak", g.max()), ("mean", g.mean()))
        for room, value in series.items()
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out)


@campaign.command
def dataset(
    in_paths: Annotated[list[Path], Parameter(consume_multiple=True)],
    manifest: Path,
    out: Path,
):
    specs = {s.id: s for s in read_manifest(manifest)}
    frames = []
    for p in tqdm(in_paths, desc="[dataset] consolidating", unit="exp"):
        df = pd.read_parquet(p)
        s = specs[df["id"].iloc[0]]
        df["case_name"], df["category"], df["option"] = s.case_name, s.category, s.option
        frames.append(df)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_parquet(out)


@campaign.command
def figure(name: str, out: Path):
    save_chart(FIGURES[name](), out)


@campaign.command
def tables(out: Path, split_climate: bool = False):
    from aura2.analysis.tables import make_tables

    for name, tbl in make_tables(out, split_climate=split_climate).items():
        print(f"\n### {name}\n")
        print(tbl.to_markdown())


app = App()
app.command(campaign)


@app.command
def collect():
    collect_figures()


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
