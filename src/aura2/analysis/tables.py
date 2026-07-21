from pathlib import Path

import pandas as pd

from aura2.analysis.figures.sensitivity import create_data_set

QOIS = [
    ("temp", "Zone Mean Air Temperature", "°C"),
    ("flow", "AFN Linkage Node 1 to Node 2 Volume Flow Rate", "m³/s"),
]
NICE_VAR = {
    "window_dimension": "Window Dimension",
    "door_vent_schedule": "Door Ventilation",
    "construction_set": "Construction",
}


def sensitivity_frame(qoi_name: str):
    df = create_data_set(qoi_name).to_pandas()
    base = df[df.option == "Default"].groupby("case")["value"].first()
    mods = df[df.option != "Default"].copy()
    mods["baseline"] = mods["case"].map(base)
    mods["delta"] = mods["value"] - mods["baseline"]
    mods["pct"] = 100 * mods["delta"] / mods["baseline"]
    return base, mods


def baseline_table() -> pd.DataFrame:
    cols = {}
    for key, qoi, unit in QOIS:
        base, _ = sensitivity_frame(qoi)
        cols[f"{key} [{unit}]"] = base.round(3)
    out = pd.DataFrame(cols)
    out.index.name = "case"
    return out


def delta_table(qoi_name: str, value: str = "delta") -> pd.DataFrame:
    _, mods = sensitivity_frame(qoi_name)
    piv = mods.pivot_table(index=["category", "option"], columns="case", values=value)
    piv["mean"] = piv.mean(axis=1)
    piv = piv.reset_index()
    piv["category"] = piv["category"].map(NICE_VAR)
    return (
        piv.rename(columns={"category": "modification"})
        .set_index(["modification", "option"])
        .round(3)
    )


FACTOR_ORDER = ["PLAN (layout)", "Window Dimension", "Door Ventilation", "Construction"]
METRIC_LABEL = {"temp": "ΔT [°C]", "flow": "ΔV̇ [m³/s]"}


def factor_spread_table(idx=None) -> pd.DataFrame:
    frames = {}
    for key, qoi, _ in QOIS:
        df = create_data_set(qoi, idx).to_pandas()
        base = df[df.option == "Default"].groupby("case")["value"].first()
        cases = sorted(base.index)
        rows = {"PLAN (layout)": {cases[0]: base.max() - base.min()}}
        for cat, g in df.groupby("category"):
            per = g.groupby("case")["value"].agg(lambda s: s.max() - s.min())
            rows[NICE_VAR[cat]] = {c: per.get(c) for c in cases}
        frame = pd.DataFrame(rows).T.reindex(FACTOR_ORDER)
        frame.columns = [c.upper() for c in cases]
        frames[METRIC_LABEL[key]] = frame
    out = pd.concat(frames, axis=1)
    out.index.name = "factor"
    return out.round(3)


def make_tables(out_dir: Path, split_climate: bool = False) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {"baselines": baseline_table(), "factor_spread": factor_spread_table()}
    for key, qoi, _ in QOIS:
        tables[f"sensitivity_{key}"] = delta_table(qoi, "delta")
        tables[f"sensitivity_{key}_pct"] = delta_table(qoi, "pct")
    if split_climate:
        import numpy as np

        from aura2.analysis.sources.climate import section_masks

        masks = section_masks()
        for name, m in masks.items():
            tables[f"factor_spread_{name}"] = factor_spread_table(np.where(m)[0])
    for name, tbl in tables.items():
        tbl.to_csv(out_dir / f"{name}.csv")
    return tables
