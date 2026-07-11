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


# validation experiment: ~5 m2 x2 windows = 10 m2 total glazing to match the
# reference's solar aperture (orig 0.71 x 1.52)
WINDOW = WindowDetail(id=1, width=2.5, height=2.0)
DOOR = DoorDetail(id=0, width=0.81, height=2.03, thickness=0.30)

DETAILS: dict[DetailType, Detail] = {
    "Window": WINDOW.true_detail,
    "Door": DOOR.true_detail,
    # TODO: "Crack" / "AirBoundary" details once their semantics are defined
}
