import pandas as pd

from aura2.validation.robustness.paths import RESULTS_DIR


def zone_area_error(geom: pd.DataFrame) -> pd.DataFrame:
    z = geom[geom["scope"] != "FLOOR"].copy()
    z["rel"] = (z["area_after"] - z["area_before"]).abs() / z["area_before"]
    return (
        z.groupby(["plan", "shrink", "seed"], as_index=False)["rel"]
        .mean()
        .rename(columns={"rel": "area_err"})
    )


def norm(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng else s * 0.0


def distortion_table() -> pd.DataFrame:
    geom = pd.read_csv(RESULTS_DIR / "geometry.csv")
    runs = pd.read_csv(RESULTS_DIR / "runs.csv")
    df = runs.merge(zone_area_error(geom), on=["plan", "shrink", "seed"], how="left")
    df = df[df["valid"]].copy()
    df["distortion"] = df.groupby("plan")["area_err"].transform(norm)
    return df


def select_extremes() -> pd.DataFrame:
    df = distortion_table()
    picks = []
    for _, g in df.groupby("plan"):
        base = g[g["shrink"] == 0]
        if not base.empty:
            picks.append(("baseline", base.iloc[0]))
        pert = g[g["shrink"] > 0].sort_values("distortion")
        if not pert.empty:
            med = (pert["distortion"] - pert["distortion"].median()).abs().idxmin()
            picks.append(("best", pert.iloc[0]))
            picks.append(("median", pert.loc[med]))
            picks.append(("worst", pert.iloc[-1]))
    rows = [
        {
            "role": role,
            "plan": r["plan"],
            "shrink": r["shrink"],
            "seed": int(r["seed"]),
            "distortion": round(r["distortion"], 3),
            "area_err": round(r["area_err"], 4),
        }
        for role, r in picks
    ]
    return pd.DataFrame(rows).drop_duplicates(subset=["plan", "shrink", "seed"])
