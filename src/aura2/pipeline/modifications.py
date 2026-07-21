from __future__ import annotations

from dataclasses import dataclass

from plan2eplus.ops.afn.user_interface import AFNInput, AFNVentingInput
from plan2eplus.ops.constructions.interfaces import (
    BaseConstructionSet,
    EPConstructionSet,
)
from plan2eplus.ops.constructions.user_interface import (
    ConstructionInput,
    default_construction_input,
)
from plan2eplus.ops.schedules.interfaces.year import create_year_from_single_value
from plan2eplus.ops.subsurfaces.user_interfaces import Detail
from plan2eplus.prob_door.functions import create_venting_year
from plan2eplus.prob_door.interfaces import VentingState

from aura2.geom.details import DETAILS, DetailType
from aura2.pipeline.spec import Modification


def window_details(option: str) -> dict[DetailType, Detail]:
    factor = {"-30%": 0.7, "+30%": 1.3}[option]
    win = DETAILS["Window"]
    return {**DETAILS, "Window": win._replace(dimension=win.dimension.modify_area(factor))}


def vent_input(option: str) -> AFNInput:
    if option == "Always Closed":
        return AFNInput([AFNVentingInput("Doors", create_year_from_single_value(VentingState.CLOSE.value))])
    if option == "Dynamic":
        return AFNInput([AFNVentingInput("Doors", create_venting_year())])
    return AFNInput()


def construction_input(option: str) -> ConstructionInput:
    cset = EPConstructionSet(
        wall=BaseConstructionSet(f"{option} Partitions", f"{option} Exterior Wall"),
        floor=BaseConstructionSet(f"{option} Floor", f"{option} Floor"),
        roof=BaseConstructionSet(f"{option} Roof/Ceiling", f"{option} Roof/Ceiling"),
        window=BaseConstructionSet("Sgl Clr 6mm", "Sgl Clr 6mm"),
        door=BaseConstructionSet(f"{option} Furnishings", f"{option} Furnishings"),
    )
    return default_construction_input._replace(construction_set=cset)


@dataclass(frozen=True)
class BuildInputs:
    details: dict[DetailType, Detail]
    afn: AFNInput
    construction: ConstructionInput


def resolve(modification: Modification) -> BuildInputs:
    details, afn, construction = DETAILS, AFNInput(), default_construction_input
    if modification:
        var, opt = modification
        if var == "window_dimension":
            details = window_details(opt)
        elif var == "door_vent_schedule":
            afn = vent_input(opt)
        elif var == "construction_set":
            construction = construction_input(opt)
        else:
            raise ValueError(f"unknown modification variable {var!r}")
    return BuildInputs(details, afn, construction)
