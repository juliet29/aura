from typing import Literal

from plan2eplus.ops.subsurfaces.interfaces import Dimension, Location, SubsurfaceType
from plan2eplus.ops.subsurfaces.user_interfaces import Detail
from pydantic import BaseModel

DetailType = SubsurfaceType | Literal["Crack", "AirBoundary"]


class WindowDetail(BaseModel):
    id: int
    width: float
    height: float
    # head_height: float  # TODO incorporate this into how we read subsurfaces

    @property
    def true_detail(self) -> Detail:
        return Detail(
            dimension=Dimension(self.width, self.height),
            location=Location("mm", "CENTROID", "CENTROID"),
            type_="Window",
        )


class DoorDetail(BaseModel):
    id: int
    width: float
    height: float
    thickness: float
    # TODO validate thickness against the material width

    @property
    def true_detail(self) -> Detail:
        return Detail(
            dimension=Dimension(self.width, self.height),
            location=Location("bm", "SOUTH", "SOUTH"),
            type_="Door",
        )


# p1gen reference window (case_amb_b1): Andersen casement, 0.71 x 1.52 = 1.08 m2
WINDOW = WindowDetail(id=1, width=0.71, height=1.52)
DOOR = DoorDetail(id=0, width=0.81, height=2.03, thickness=0.30)

DETAILS: dict[DetailType, Detail] = {
    "Window": WINDOW.true_detail,
    "Door": DOOR.true_detail,
    # TODO: "Crack" / "AirBoundary" details once their semantics are defined
}
