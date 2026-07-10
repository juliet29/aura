# zones
from pathlib import Path

from plan2eplus.ops.zones.user_interface import Room
from polyfix.geometry.ortho import FancyOrthoDomain
from polyfix.main.process import read_layout_from_path

DEFAULT_HEIGHT = 3.00  # m


def get_eplus_rooms_from_path(path: Path, height: float = DEFAULT_HEIGHT):
    def to_room(id: int, dom: FancyOrthoDomain) -> Room:
        # A FancyOrthoDomain isn't a plan2eplus Domain, so Room.coords takes the
        # `else` branch and reads dom.tuple_list directly.
        return Room(id=id, name=dom.name, domain=dom, height=height)

    layout = read_layout_from_path(path)
    rooms = [to_room(i, dom) for i, dom in enumerate(layout.domains)]
    return rooms
