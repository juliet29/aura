from cyclopts import App
from utils4plans.logs import logset

from aura2.cli.validate.p2ep import epc
from aura2.cli.validate.robustness import rob

app = App()
app.command(epc)
app.command(rob)


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
