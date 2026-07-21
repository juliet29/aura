from pathlib import Path

import matplotlib.pyplot as plt

from aura2.paths import ProjectDir, StaticPaths

STAGES = [
    ("init", "in.png", "Init"),
    ("xplan", "out.png", "X-Plan"),
    ("xmove", "out.png", "X-Move"),
    ("yplan", "out.png", "Y-Plan"),
    ("ymove", "out.png", "Y-Move"),
    ("reconcile", "out.png", "Reconcile"),
]


def make_geom_stages(
    case: str = "b", out: Path | None = None, ncols: int = 3, crop_top: float = 0.09
) -> Path:
    geom = ProjectDir[case].geom
    out = out or StaticPaths.figures / "real_plans" / f"geom_stages_{case}.png"
    nrows = -(-len(STAGES) // ncols)
    fig, axs = plt.subplots(
        nrows, ncols, figsize=(4 * ncols, 3.3 * nrows), constrained_layout=True
    )
    axs = axs.flatten()
    for ax, (stage, img, label) in zip(axs, STAGES):
        arr = plt.imread(geom / stage / img)
        ax.imshow(arr[int(arr.shape[0] * crop_top):, :])  # crop baked-in subtitle
        ax.set_title(label, fontsize=16)
        ax.axis("off")
    for ax in axs[len(STAGES):]:
        ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    return out


if __name__ == "__main__":
    print(make_geom_stages())
