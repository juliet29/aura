from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

Modification = tuple[str, str] | None


@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    case_name: str
    modification: Modification = None

    @property
    def is_baseline(self) -> bool:
        return self.modification is None

    @property
    def category(self) -> str:
        return self.modification[0] if self.modification else "Default"

    @property
    def option(self) -> str:
        return self.modification[1] if self.modification else "Default"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_name": self.case_name,
            "modification": list(self.modification) if self.modification else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ExperimentSpec":
        mod = d.get("modification")
        return cls(
            id=d["id"],
            case_name=d["case_name"],
            modification=(mod[0], mod[1]) if mod else None,
        )


@dataclass(frozen=True)
class ExperimentResult:
    spec: ExperimentSpec
    out_path: Path
    idf_path: Path
    sql_path: Path | None = None

    @property
    def has_run(self) -> bool:
        return self.sql_path is not None

    def with_sql(self, sql_path: Path) -> "ExperimentResult":
        return replace(self, sql_path=sql_path)
