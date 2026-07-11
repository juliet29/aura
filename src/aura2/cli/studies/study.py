from cyclopts import App
from utils4plans.logs import logset

from aura2.cli.studies.eplus_compare import epc
from aura2.cli.studies.robustness import report, thermal  # noqa: F401 register rob.commands
from aura2.cli.studies.robustness.run import rob

app = App()
app.command(epc)
app.command(rob)


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
