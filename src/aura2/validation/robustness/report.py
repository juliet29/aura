import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from loguru import logger
from polyfix.geometry.layout import Layout
from polyfix.main.execute import execute_polyfix
from polyfix.main.process import read_layout_from_path
from polyfix.main.workflow_paths import SingleWorkflowPaths

from aura2.validation.robustness.paths import FRACTION, RESULTS_DIR, ROBUST_DIR
from aura2.validation.robustness.perturb import select_indices

METRICS = {
    "area": ("area_before", "area_after"),
    "shape_factor": ("sf_before", "sf_after"),
}


def pct(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["shrink"] = (df["shrink"] * 100).round().astype(int).astype(str) + "%"
    return df


def cap_legend(leg) -> None:
    if leg is None:
        return
    if leg.get_title().get_text():
        leg.set_title(leg.get_title().get_text().capitalize())
    for t in leg.get_texts():
        s = t.get_text()
        if s in ("shrink", "plan"):
            t.set_text(s.capitalize())
        elif s in ("a", "b", "c"):
            t.set_text(s.upper())


def scatter_metric(df: pd.DataFrame, name: str, ax, bands: bool = False,
                   jitter: float = 0.0, alpha: float = 1.0, thin: float = 0.0) -> None:
    pre, post = METRICS[name]
    if thin:
        xr = (df[pre].max() - df[pre].min()) or 1.0
        yr = (df[post].max() - df[post].min()) or 1.0
        keep = []
        for _, g in df.groupby(["plan", "shrink"]):
            kept = []
            for idx, r in g.sample(frac=1, random_state=0).iterrows():
                p = (r[pre] / xr, r[post] / yr)
                if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= thin ** 2 for q in kept):
                    kept.append(p)
                    keep.append(idx)
        df = df.loc[keep]
    if jitter:
        rng = np.random.default_rng(0)
        df = df.copy()
        for col in (pre, post):
            df[col] = df[col] + rng.normal(0, jitter * (df[col].max() - df[col].min()), len(df))
    sns.scatterplot(df, x=pre, y=post, hue="shrink", style="plan", s=60, ax=ax, alpha=alpha)
    cap_legend(ax.get_legend())
    lo = min(df[pre].min(), df[post].min())
    hi = max(df[pre].max(), df[post].max())
    ax.plot([lo, hi], [lo, hi], ls="--", c="grey", lw=1, zorder=0)
    if bands:
        xs = np.linspace(lo, hi, 100)
        h10 = ax.fill_between(xs, 0.90 * xs, 1.10 * xs, color="tab:purple", alpha=0.18,
                              zorder=0, label="±10%")
        ax.fill_between(xs, 1.10 * xs, 1.25 * xs, color="tab:olive", alpha=0.18, zorder=0)
        h25 = ax.fill_between(xs, 0.75 * xs, 0.90 * xs, color="tab:olive", alpha=0.18,
                              zorder=0, label="±25%")
        main = ax.get_legend()
        ax.legend(handles=[h10, h25], loc="lower right", title="Band")
        if main is not None:
            ax.add_artist(main)
    ax.set(xlabel="Pre-modification", ylabel="Post-modification",
           title=name.replace("_", " ").capitalize())


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
    ax.invert_yaxis()
    ax.set_title(title, fontsize=9)


def failure_mode_figure() -> None:
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
        execute_polyfix(wd.base, save_adj=False)
    except Exception as e:
        if e.args and isinstance(e.args[0], list):
            bad = {d.name for d in e.args[0]}
        overlap = next((a for a in e.args if isinstance(a, Layout)), None)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    plot_layout(axes[0], base, f"Plan {plan}: baseline init (concave room red)", {concave})
    plot_layout(axes[1], pert,
                f"Plan {plan}: perturbed {int(shrink * 100)}% seed {seed} (shrunk red)", shrunk)
    if overlap is not None:
        plot_layout(axes[2], overlap, "Rejected layout — overlap (red)", bad)
    else:
        axes[2].set_axis_off()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "fig_failure_modes.png", dpi=200)


def make_figures():
    geom = pct(pd.read_csv(RESULTS_DIR / "geometry.csv"))

    zones = geom[geom["scope"] != "FLOOR"]
    cols = ["area_before", "area_after", "sf_before", "sf_after"]
    zavg = zones.groupby(["plan", "shrink", "scope"], as_index=False)[cols].mean()
    fig2, axes2 = plt.subplots(1, 2, figsize=(10, 4.5))
    scatter_metric(zavg, "area", axes2[0], bands=True, thin=0.06, jitter=0.006, alpha=0.85)
    scatter_metric(zavg, "shape_factor", axes2[1], bands=True, thin=0.06, jitter=0.006, alpha=0.85)
    fig2.tight_layout()
    fig2.savefig(RESULTS_DIR / "fig2_zones.png", dpi=200)

    epath = RESULTS_DIR / "thermal_extremes.csv"
    if epath.exists() and epath.stat().st_size > 1:
        ext = pd.read_csv(epath)
        order = ["baseline", "best", "median", "worst"]
        stats = ["mean", "peak"]
        agg = ext.groupby(["plan", "role", "stat"], as_index=False)["value"].mean()
        agg["role"] = pd.Categorical(agg["role"], order, ordered=True)
        g = sns.catplot(agg.sort_values("role"), x="role", y="value", col="stat",
                        col_order=stats, hue="plan", kind="point", sharey=False)
        for ax, stat in zip(g.axes.flat, stats):
            c = agg.loc[agg["stat"] == stat, "value"].mean()
            ax.set_ylim(c - 2, c + 2)
            ax.set_title(stat.capitalize())
        g.set_axis_labels("Case (increasing distortion →)", "Zone temp (°C)")
        cap_legend(g.legend)
        g.savefig(RESULTS_DIR / "fig_energy.png", dpi=200)

    failure_mode_figure()


def make_tables():
    runs = pd.read_csv(RESULTS_DIR / "runs.csv")

    valid = (runs.groupby(["plan", "shrink"])["valid"].mean().mul(100)
             .unstack("shrink").round(0))
    det_path = RESULTS_DIR / "determinism.csv"
    if det_path.exists():
        det = pd.read_csv(det_path).set_index("plan")["identical"]
        valid["deterministic"] = det
    valid.to_csv(RESULTS_DIR / "table1_validity.csv")
    print("Table 1 - validity % by shrink + determinism\n", valid.to_markdown())

    epath = RESULTS_DIR / "thermal_extremes.csv"
    if epath.exists() and epath.stat().st_size > 1:
        order = ["baseline", "best", "median", "worst"]
        ext = pd.read_csv(epath)
        pm = ext[ext["stat"].isin(["peak", "mean"])]
        agg = pm.groupby(["stat", "plan", "role"])["value"].mean().unstack("role")[order]
        absdiff = agg.sub(agg["baseline"], axis=0)
        pctchg = absdiff.div(agg["baseline"], axis=0).mul(100)
        labeled = pctchg.map(lambda v: f"{v:+.2f}%")
        labeled.to_csv(RESULTS_DIR / "table3_energy.csv")
        print("Table 3 - zone-temp change from baseline (%)\n", labeled.to_markdown())
