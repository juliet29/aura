from cyclopts import App
from plan2eplus.ezcase.ez import EZ

from aura2.main import make_basic_case, make_case_plot, transform_case
from aura2.paths import FileNames, ProjectDir

rp = App("rp")

CURR_CASE = ProjectDir.a


@rp.command()
def transform():
    transform_case(CURR_CASE)


@rp.command()
def make():
    case = make_basic_case(CURR_CASE, run=True)


@rp.command()
def plot():
    case = EZ(idf_path=CURR_CASE.model / FileNames.idf)
    make_case_plot(case, CURR_CASE.temp_dir)
