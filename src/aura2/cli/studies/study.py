import yaml
from cyclopts import App
from sv2.pfix.config import CaseConfig
from sv2.pfix.main import transform_svg
from utils4plans.logs import logset

from aura2.paths import FileNames as fn
from aura2.paths import ProjectPaths

app = App()


@app.command
def fc():
    # indir = ProjectPaths.svgs.eplus
    # outdir = ProjectPaths.geoms.eplus

    indir = ProjectPaths.svgs.c
    outdir = ProjectPaths.geoms.c
    # TODO: to utils4plans..
    with open(indir / fn.config) as f:
        data = yaml.safe_load(f)
    pixel = data["pixel"]
    meter = data["meter"]

    config = CaseConfig(indir / fn.svg, pixel, meter, outdir)
    transform_svg(config)
    return config


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
