from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from plan2eplus.ezcase.ez import EZ

from aura2.paths import FileNames
from aura2.pipeline.defn import CAMPAIGN_NAME
from aura2.pipeline.manifest import read_manifest
from aura2.pipeline.paths import CampaignPaths

CATEGORIES = ["window_dimension", "door_vent_schedule", "construction_set"]


@dataclass(frozen=True)
class Experiment:
    case_name: str
    category: str
    option: str
    path: Path

    @property
    def sql_path(self) -> Path:
        return self.path / "results/eplusout.sql"

    @property
    def idf_path(self) -> Path:
        return self.path / FileNames.idf


def campaign_paths() -> CampaignPaths:
    return CampaignPaths(CAMPAIGN_NAME)


def default_experiments() -> list[Experiment]:
    cp = campaign_paths()
    return [
        Experiment(s.case_name, "Default", "Default", cp.exp(s.id))
        for s in read_manifest(cp.manifest)
        if s.modification is None
    ]


def all_experiments() -> list[Experiment]:
    # baselines are replicated across every category as the "Default" point so each
    # sensitivity line has a midpoint (mirrors p1gen assemble_comparison_data)
    cp = campaign_paths()
    out: list[Experiment] = []
    for s in read_manifest(cp.manifest):
        if s.modification is None:
            out += [Experiment(s.case_name, cat, "Default", cp.exp(s.id)) for cat in CATEGORIES]
        else:
            out.append(Experiment(s.case_name, s.category, s.option, cp.exp(s.id)))
    return out


def get_afn_zone_names(idf_path: Path) -> list[str]:
    case = EZ(idf_path=idf_path)
    return [z.zone_name.upper() for z in case.objects.airflow_network.zones]
