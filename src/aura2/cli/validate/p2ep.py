from cyclopts import App

from aura2.validation.p2ep import build, figures, metrics

epc = App("epc")


@epc.command
def transform():
    build.transform()


@epc.command
def rooms():
    return build.case_inputs()[0]


@epc.command
def subsurfaces():
    return build.case_inputs()[1]


@epc.command
def inspect():
    return build.inspect_case()


@epc.command
def run():
    build.run_validation(run=True)


@epc.command
def figure():
    return figures.timeseries()


@epc.command
def rmse():
    return metrics.rmse()
