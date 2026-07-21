from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from plan2eplus.geometry.directions import WallNormalNamesList
from plan2eplus.ops.subsurfaces.interfaces import Edge, SubsurfaceType
from plan2eplus.ops.subsurfaces.user_interfaces import (
    Detail,
    EdgeGroup,
    EdgeGroupType,
    SubsurfaceInputs,
)
from utils4plans.io.extras.yaml import read_yaml

from aura2.geom.details import DETAILS, DetailType


class EdgeTypes(StrEnum):
    DEFAULT = "default"  # bare entry -> type is inferred to be window  / door depending on if its connected to an external node or another zone
    CRACK = "c"
    AIRBOUNDARY = "a"


SUBSURFACE_BY_GROUP: dict[EdgeGroupType, SubsurfaceType] = {
    "Zone_Zone": "Door",
    "Zone_Direction": "Window",
}

DETAIL_BY_EDGE_TYPE: dict[EdgeTypes, DetailType] = {
    EdgeTypes.CRACK: "Crack",
    EdgeTypes.AIRBOUNDARY: "AirBoundary",
}

RawEntry = (
    str | list
)  # <other zone / external node> name>  or  [<other zone / extrnal node>, <EdgeType>]


@dataclass(frozen=True)
class Adjacency:
    edge: Edge
    edge_type: EdgeTypes

    @property
    def group_type(self) -> EdgeGroupType:
        return "Zone_Direction" if self.edge.is_directed_edge else "Zone_Zone"

    @property
    def subsurface(self) -> SubsurfaceType:
        return SUBSURFACE_BY_GROUP[self.group_type]

    @property
    def detail(self) -> DetailType:
        if self.edge_type is EdgeTypes.DEFAULT:
            return self.subsurface
        return DETAIL_BY_EDGE_TYPE[self.edge_type]


def split_entry(entry: RawEntry) -> tuple[str, EdgeTypes, int]:
    # second element is either a leakage code ('c'/'a') or a wall index (int)
    if not isinstance(entry, (list, tuple)):
        return entry, EdgeTypes.DEFAULT, 0
    target, modifier = entry
    if isinstance(modifier, int):
        return target, EdgeTypes.DEFAULT, modifier
    return target, EdgeTypes(modifier), 0


def validate_target(room: str, target: str, rooms: set[str]) -> None:
    if target not in rooms and target not in WallNormalNamesList:
        raise ValueError(
            f"'{room}' connects to '{target}', which is neither a known room "
            f"{sorted(rooms)} nor an exterior direction {WallNormalNamesList}"
        )


def to_adjacency(room: str, entry: RawEntry, rooms: set[str]) -> Adjacency:
    target, edge_type, index = split_entry(entry)
    validate_target(room, target, rooms)
    return Adjacency(Edge(room, target, index), edge_type)


def parse_adjacencies(
    adj: dict[str, list[RawEntry]], strict: bool = True
) -> list[Adjacency]:
    # a room can appear only as a target (polyfix writes each edge once), so the
    # room set is the keys plus every non-direction target
    targets = {split_entry(e)[0] for entries in adj.values() for e in entries}
    rooms = set(adj.keys()) | {t for t in targets if t not in WallNormalNamesList}
    adjacencies = [
        to_adjacency(room, entry, rooms)
        for room, entries in adj.items()
        for entry in entries
    ]
    if strict:  # hand-authored input: a double-sided edge is an authoring error
        check_single_sided(adjacencies)
        return adjacencies
    return dedupe_room_edges(adjacencies)  # auto adjacency lists edges from both sides


def dedupe_room_edges(adjacencies: list[Adjacency]) -> list[Adjacency]:
    seen: set[tuple[frozenset[str], int]] = set()
    out = []
    for a in adjacencies:
        if a.group_type == "Zone_Zone":
            key = (frozenset(a.edge.as_tuple), a.edge.index)
            if key in seen:
                continue
            seen.add(key)
        out.append(a)
    return out


def check_single_sided(adjacencies: list[Adjacency]) -> None:
    seen: dict[tuple[frozenset[str], int], EdgeTypes] = {}
    for a in adjacencies:
        if a.group_type != "Zone_Zone":
            continue  # a room may face the same exterior twice (e.g. two S windows)
        key = (frozenset(a.edge.as_tuple), a.edge.index)
        if key in seen:
            raise ValueError(
                f"room-room edge {a.edge.as_tuple} (wall #{a.edge.index}) listed "
                f"from both sides (edge_type {seen[key]} vs {a.edge_type}); list it once"
            )
        seen[key] = a.edge_type


# ── assembling plan2eplus inputs ─────────────────────────────────────────────


def to_edge_groups(adjacencies: list[Adjacency]) -> list[EdgeGroup]:
    grouped: dict[tuple[EdgeGroupType, DetailType], list[Edge]] = defaultdict(list)
    for a in adjacencies:
        grouped[(a.group_type, a.detail)].append(a.edge)

    return [
        EdgeGroup(edges, detail=detail, type_=group_type)
        for (group_type, detail), edges in grouped.items()
    ]


def to_subsurface_inputs(
    adjacencies: list[Adjacency], details: dict[DetailType, Detail] = DETAILS
) -> SubsurfaceInputs:
    edge_groups = to_edge_groups(adjacencies)
    # filtering for now to avoid dealing with cracks right now
    filtered_edge_groups = [i for i in edge_groups if i.detail in ["Door", "Window"]]
    return SubsurfaceInputs(filtered_edge_groups, details)


def read_adjacencies(path: Path, strict: bool = True) -> list[Adjacency]:
    return parse_adjacencies(read_yaml(path), strict=strict)


def read_subsurface_inputs(
    path: Path, strict: bool = True, details: dict[DetailType, Detail] = DETAILS
) -> SubsurfaceInputs:
    adj = read_adjacencies(path, strict=strict)
    return to_subsurface_inputs(adj, details)
