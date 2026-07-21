from pathlib import Path

from aura2.paths import FileNames, StaticPaths
from aura2.pipeline.manifest import MANIFEST_NAME

# mirrors ProjectDir real-plan layout, but templatable with a "{case}" token
REAL_PLANS = StaticPaths.temp / "real_plans"

# campaign weather (Palo Alto 2024, matches p1gen); keep in sync with config/campaign.yaml
CAMPAIGN_EPW = StaticPaths.inputs / "weather" / "CA_PALO-ALTO-AP_724937_24.EPW"


def case_geom(case: str) -> Path:
    return REAL_PLANS / case / "geom" / FileNames.corrected_geom


def case_adj(case: str) -> Path:
    return REAL_PLANS / case / FileNames.adjacencies


class CampaignPaths:
    def __init__(self, name: str) -> None:
        self.name = name
        self.base = StaticPaths.temp / "campaigns" / name

    def figure(self, fig_name: str) -> Path:
        return StaticPaths.figures / self.name / f"{fig_name}.png"

    @property
    def manifest(self) -> Path:
        return self.base / MANIFEST_NAME

    @property
    def dataset(self) -> Path:
        return self.base / "dataset.parquet"

    def exp(self, id: str) -> Path:
        return self.base / "exp" / id

    def exp_idf(self, id: str) -> Path:
        return self.exp(id) / FileNames.idf

    def exp_sql(self, id: str) -> Path:
        return self.exp(id) / "results/eplusout.sql"

    def exp_qoi(self, id: str) -> Path:
        return self.exp(id) / "qoi.parquet"
