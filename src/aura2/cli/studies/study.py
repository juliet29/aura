from cyclopts import App
from utils4plans.logs import logset

from aura2.cli.studies.eplus_compare import epc

app = App()
app.command(epc)


@app.command
def fc():
    pass


def main():
    logset(to_stderr=True)
    app()


if __name__ == "__main__":
    main()
