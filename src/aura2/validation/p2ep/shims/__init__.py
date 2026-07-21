from plan2eplus.ezcase.ez import EZ

from aura2.validation.p2ep.shims.constructions import match_reference_constructions
from aura2.validation.p2ep.shims.cracks import add_reference_cracks
from aura2.validation.p2ep.shims.discharge_coefficient import (
    match_reference_discharge_coefficient,
)
from aura2.validation.p2ep.shims.venting_control import match_reference_venting_control

__all__ = ["apply_shims"]


def apply_shims(case: EZ) -> None:
    match_reference_venting_control(case.idf)
    add_reference_cracks(case)
    match_reference_constructions(case)
    match_reference_discharge_coefficient(case)
