# from aura2.cli.studies.robustness import (  # noqa: F401 register rob.commands
#     report,
#     thermal,
# )
from cyclopts import App
from utils4plans.logs import logset

from aura2.cli.studies.real_plans import rp

app = App()
# app.command(epc)
# app.command(rob)
app.command(rp)


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
