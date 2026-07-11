import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from loguru import logger
from polyfix.geometry.layout import Layout
from polyfix.main.execute import execute_polyfix
from polyfix.main.process import read_layout_from_path
from polyfix.main.workflow_paths import SingleWorkflowPaths

from aura2.cli.studies.robustness.perturb import select_indices
from aura2.cli.studies.robustness.run import FRACTION, RESULTS_DIR, ROBUST_DIR, rob

METRICS = {  # display name -> (pre column, post column)
    "area": ("area_before", "area_after"),
    "shape_factor": ("sf_before", "sf_after"),
}


def pct(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["shrink"] = (df["shrink"] * 100).round().astype(int).astype(str) + "%"
    return df


def scatter_metric(df: pd.DataFrame, name: str, ax, band: float | None = None) -> None:
    pre, post = METRICS[name]
    sns.scatterplot(df, x=pre, y=post, hue="shrink", style="plan", s=60, ax=ax)
    lo = min(df[pre].min(), df[post].min())
    hi = max(df[pre].max(), df[post].max())
    ax.plot([lo, hi], [lo, hi], ls="--", c="grey", lw=1, zorder=0)  # y=x reference
    title = name
    if band:  # shade post within +/- band of pre (a ratio tolerance, so a wedge)
        xs = np.linspace(lo, hi, 100)
        ax.fill_between(xs, (1 - band) * xs, (1 + band) * xs, color="grey",
                        alpha=0.12, zorder=0)
        title = f"{name} (±{int(band * 100)}% band)"
    ax.set(xlabel="pre-modification (init)", ylabel="post-modification (ymove)", title=title)


def plot_layout(ax, layout: Layout, title: str, highlight=frozenset()) -> None:
    for dom in layout.domains:
        xs = [c.x for c in dom.coords] + [dom.coords[0].x]
        ys = [c.y for c in dom.coords] + [dom.coords[0].y]
        hot = dom.name in highlight
        ax.fill(xs, ys, alpha=0.5 if hot else 0.3,
                color="tab:red" if hot else "tab:blue", ec="k", lw=0.8)
        c = dom.centroid
        ax.text(c.x, c.y, dom.name.replace("_", "\n"), fontsize=5, ha="center", va="center")
    ax.set_aspect("equal")
    ax.invert_yaxis()  # SVG y-down, so it reads like a floorplan
    ax.set_title(title, fontsize=9)


def failure_mode_figure() -> None:
    # auto-pick the most illustrative failure (highest shrink), reproduce the
    # crash from its existing workdir, and plot baseline / perturbed / overlap
    runs = pd.read_csv(RESULTS_DIR / "runs.csv")
    failed = runs[(~runs["valid"]) & (runs["shrink"] > 0)]
    if failed.empty:
        return
    row = failed.sort_values(["shrink", "plan", "seed"], ascending=[False, True, True]).iloc[0]
    plan, shrink, seed = row["plan"], float(row["shrink"]), int(row["seed"])
    wd = SingleWorkflowPaths(ROBUST_DIR / plan / f"shrink{int(shrink * 100)}_seed{seed}")
    base_wd = SingleWorkflowPaths(ROBUST_DIR / plan / "shrink0_seed0")
    try:
        base = read_layout_from_path(base_wd.init)
        pert = read_layout_from_path(wd.init)
    except Exception as e:
        logger.warning(f"failure-mode figure skipped (workdirs missing?): {e}")
        return

    concave = max(base.domains, key=lambda d: len(d.coords)).name
    shrunk = {base.domains[i].name for i in select_indices(len(base.domains), FRACTION, seed)}
    bad, overlap = set(), None
    try:
        execute_polyfix(wd.base, save_adj=False)  # deterministically re-triggers the crash
    except Exception as e:
        if e.args and isinstance(e.args[0], list):
            bad = {d.name for d in e.args[0]}
        overlap = next((a for a in e.args if isinstance(a, Layout)), None)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    plot_layout(axes[0], base, f"{plan}: baseline init (concave room red)", {concave})
    plot_layout(axes[1], pert,
                f"{plan}: perturbed {int(shrink * 100)}% seed {seed} (shrunk red)", shrunk)
    if overlap is not None:
        plot_layout(axes[2], overlap, "rejected layout — overlap (red)", bad)
    else:
        axes[2].set_axis_off()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "fig_failure_modes.png", dpi=200)


@rob.command
def figures():
    geom = pct(pd.read_csv(RESULTS_DIR / "geometry.csv"))
    runs = pct(pd.read_csv(RESULTS_DIR / "runs.csv"))

    # Figure 1 - floor level (2x2): area (+/-10% band) | shape | GED by plan | failures
    floor = geom[geom["scope"] == "FLOOR"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    scatter_metric(floor, "area", axes[0, 0], band=0.10)  # floor area should be conserved
    scatter_metric(floor, "shape_factor", axes[0, 1])  # shape is meant to change (no band)

    ged = runs.dropna(subset=["ged"])
    sns.histplot(ged, x="ged", hue="plan", multiple="dodge", discrete=True, ax=axes[1, 0])
    axes[1, 0].set(xlabel="graph edit distance", title="graph edit distance (by plan)")

    fails = (runs.assign(failed=~runs["valid"])
             .groupby(["plan", "shrink"], as_index=False)["failed"].sum())
    sns.barplot(fails, x="shrink", y="failed", hue="plan", ax=axes[1, 1])
    axes[1, 1].set(xlabel="shrink", ylabel="failed (invalid) runs",
                   title="failures by plan and shrink")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "fig1_floor.png", dpi=200)

    # Figure 2 - zone level: same scatter, each zone averaged across seeds
    zones = geom[geom["scope"] != "FLOOR"]
    cols = ["area_before", "area_after", "sf_before", "sf_after"]
    zavg = zones.groupby(["plan", "shrink", "scope"], as_index=False)[cols].mean()
    fig2, axes2 = plt.subplots(1, 2, figsize=(10, 4.5))
    scatter_metric(zavg, "area", axes2[0], band=0.10)
    scatter_metric(zavg, "shape_factor", axes2[1], band=0.10)
    fig2.tight_layout()
    fig2.savefig(RESULTS_DIR / "fig2_zones.png", dpi=200)

    # GED heatmaps: raw (median, integer) + normalized GED = GED/(E_before+E_after);
    # shrink rows ordered with 0% at the bottom
    gh = ged.copy()
    gh["nged"] = gh["ged"] / (gh["edges_before"] + gh["edges_after"])
    rows_order = ["30%", "20%", "10%", "0%"]  # 0% at bottom of the heatmap
    raw = (gh.pivot_table(index="shrink", columns="plan", values="ged", aggfunc="median")
           .round().astype(int).reindex(rows_order))
    nrm = (gh.pivot_table(index="shrink", columns="plan", values="nged", aggfunc="median")
           .reindex(rows_order))
    fig_h, axes_h = plt.subplots(1, 2, figsize=(10, 4))
    sns.heatmap(raw, annot=True, fmt="d", cmap="viridis", ax=axes_h[0],
                cbar_kws={"label": "graph edit distance"})
    axes_h[0].set(xlabel="plan (case)", ylabel="shrink", title="graph edit distance (median)")
    sns.heatmap(nrm, annot=True, fmt=".2f", cmap="viridis", ax=axes_h[1],
                cbar_kws={"label": "normalized GED"})
    axes_h[1].set(xlabel="plan (case)", ylabel="shrink", title="normalized GED (median)")
    fig_h.tight_layout()
    fig_h.savefig(RESULTS_DIR / "fig_ged_heatmap.png", dpi=200)

    # Energy (optional) - zone temp across extreme cases, aggregated per plan
    epath = RESULTS_DIR / "thermal_extremes.csv"
    if epath.exists() and epath.stat().st_size > 1:
        ext = pd.read_csv(epath)
        order = ["baseline", "best", "median", "worst"]
        stats = ["mean", "peak"]
        agg = ext.groupby(["plan", "role", "stat"], as_index=False)["value"].mean()
        agg["role"] = pd.Categorical(agg["role"], order, ordered=True)
        g = sns.catplot(agg.sort_values("role"), x="role", y="value", col="stat",
                        col_order=stats, hue="plan", kind="point", sharey=False)
        # fix each panel to a +/-2C band around its mean so the (tiny) real change
        # isn't visually exaggerated by autoscaling to a 0.2C window
        for ax, stat in zip(g.axes.flat, stats):
            c = agg.loc[agg["stat"] == stat, "value"].mean()
            ax.set_ylim(c - 2, c + 2)
        g.set_axis_labels("case (increasing distortion →)", "zone temp (°C)")
        g.savefig(RESULTS_DIR / "fig_energy.png", dpi=200)

    failure_mode_figure()  # diagnostic: reproduces one failing case's overlap


@rob.command
def tables():
    runs = pd.read_csv(RESULTS_DIR / "runs.csv")
    geom = pd.read_csv(RESULTS_DIR / "geometry.csv")

    # Table 1 - validity rate by shrink + determinism flag (items 1 & 3)
    valid = (runs.groupby(["plan", "shrink"])["valid"].mean().mul(100)
             .unstack("shrink").round(0))
    det_path = RESULTS_DIR / "determinism.csv"
    if det_path.exists():
        det = pd.read_csv(det_path).set_index("plan")["identical"]
        valid["deterministic"] = det
    valid.to_csv(RESULTS_DIR / "table1_validity.csv")
    print("Table 1 - validity % by shrink + determinism\n", valid.to_markdown())

    # Table 2 - baseline fidelity (unperturbed floor before/after + GED)
    base = geom[(geom["shrink"] == 0) & (geom["scope"] == "FLOOR")].set_index("plan")
    ged0 = runs[runs["shrink"] == 0].set_index("plan")["ged"]
    t2 = base[["area_before", "area_after", "sf_before", "sf_after"]].copy()
    t2["ged"] = ged0
    t2.round(2).to_csv(RESULTS_DIR / "table2_baseline.csv")
    print("Table 2 - baseline fidelity\n", t2.round(2).to_markdown())

    # Table 3 - energy: change from baseline in degC and %, grouped by stat then plan
    epath = RESULTS_DIR / "thermal_extremes.csv"
    if epath.exists() and epath.stat().st_size > 1:
        order = ["baseline", "best", "median", "worst"]
        agg = (pd.read_csv(epath).groupby(["stat", "plan", "role"])["value"].mean()
               .unstack("role")[order])
        absdiff = agg.sub(agg["baseline"], axis=0)  # signed degC change from baseline

        abs_lbl = absdiff.map(lambda v: f"{v:+.3f}")
        abs_lbl.to_csv(RESULTS_DIR / "table3_energy_abs.csv")
        print("Table 3a - zone-temp change from baseline (°C)\n",
              abs_lbl.to_markdown(disable_numparse=True))

        pctchg = absdiff.div(agg["baseline"], axis=0).mul(100)
        labeled = pctchg.map(lambda v: f"{v:+.2f}%")  # explicit % so cells can't be misread
        labeled.to_csv(RESULTS_DIR / "table3_energy.csv")
        print("Table 3b - zone-temp change from baseline (%)\n", labeled.to_markdown())
