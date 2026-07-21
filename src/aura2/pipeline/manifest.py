from __future__ import annotations

import json
from pathlib import Path

from aura2.pipeline.spec import ExperimentSpec

MANIFEST_NAME = "campaign_manifest.json"


def write_manifest(path: Path, campaign_name: str, specs: list[ExperimentSpec]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"campaign_name": campaign_name, "specs": [s.to_dict() for s in specs]}
    path.write_text(json.dumps(payload, indent=2))
    return path


def read_manifest(path: Path) -> list[ExperimentSpec]:
    payload = json.loads(path.read_text())
    return [ExperimentSpec.from_dict(d) for d in payload["specs"]]
