from cyclopts import App
from utils4plans.logs import logset

from aura2.cli.studies.real_plans import rp

app = App()
app.command(rp)


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
