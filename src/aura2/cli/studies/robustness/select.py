import pandas as pd

from aura2.cli.studies.robustness.run import RESULTS_DIR

# distortion = equal blend of zone-area error and adjacency edits (GED); floor
# shape is intended to change by design (see framing), so it is excluded
W_AREA = 0.5
W_GED = 0.5


def zone_area_error(geom: pd.DataFrame) -> pd.DataFrame:
    z = geom[geom["scope"] != "FLOOR"].copy()
    z["rel"] = (z["area_after"] - z["area_before"]).abs() / z["area_before"]
    return (z.groupby(["plan", "shrink", "seed"], as_index=False)["rel"].mean()
            .rename(columns={"rel": "area_err"}))


def norm(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng else s * 0.0


def distortion_table() -> pd.DataFrame:
    geom = pd.read_csv(RESULTS_DIR / "geometry.csv")
    runs = pd.read_csv(RESULTS_DIR / "runs.csv")
    df = runs.merge(zone_area_error(geom), on=["plan", "shrink", "seed"], how="left")
    df = df[df["valid"] & df["ged"].notna()].copy()  # only runnable layouts
    df["area_n"] = df.groupby("plan")["area_err"].transform(norm)  # normalized per plan
    df["ged_n"] = df.groupby("plan")["ged"].transform(norm)
    df["distortion"] = W_AREA * df["area_n"] + W_GED * df["ged_n"]
    return df


def select_extremes() -> pd.DataFrame:
    # per plan: unperturbed baseline + best/median/worst valid perturbed runs
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
    rows = [{"role": role, "plan": r["plan"], "shrink": r["shrink"],
             "seed": int(r["seed"]), "distortion": round(r["distortion"], 3),
             "area_err": round(r["area_err"], 4), "ged": r["ged"]}
            for role, r in picks]
    return pd.DataFrame(rows).drop_duplicates(subset=["plan", "shrink", "seed"])
