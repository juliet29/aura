from cyclopts import App

from aura2.validation.robustness import report as report_mod
from aura2.validation.robustness import run as run_mod
from aura2.validation.robustness import thermal as thermal_mod

rob = App("rob")


@rob.command
def run(seeds: int = 10):
    run_mod.run_all(seeds)


@rob.command
def determinism(repeats: int = 3):
    run_mod.determinism_check(repeats)


@rob.command
def energy():
    thermal_mod.energy_study()


@rob.command
def figures():
    report_mod.make_figures()


@rob.command
def tables():
    report_mod.make_tables()
