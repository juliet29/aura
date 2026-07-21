from plan2eplus.ezcase.ez import EZ
from plan2eplus.ezcase.utils import open_idf
from plan2eplus.geometry.directions import WallNormal
from plan2eplus.ops.subsurfaces.interfaces import ZoneDirectionEdge, ZoneEdge
from plan2eplus.ops.subsurfaces.logic.select import (
    get_surface_between_zone_and_direction,
    get_surface_between_zones,
    get_zones_by_plan_name,
)

from aura2.geom.adjacencies import EdgeTypes, read_adjacencies
from aura2.validation.p2ep.paths import ADJ_PATH, REF_IDF


def add_reference_cracks(case: EZ):
    idf, zones = case.idf, case.objects.zones
    ref = open_idf(REF_IDF)
    for key, name in (
        (
            "AIRFLOWNETWORK:MULTIZONE:REFERENCECRACKCONDITIONS",
            "ReferenceCrackConditions",
        ),
        (
            "AIRFLOWNETWORK:MULTIZONE:SURFACE:CRACK",
            "CR-1",
        ),
        (
            "AIRFLOWNETWORK:MULTIZONE:SURFACE:CRACK",
            "CRcri",
        ),
    ):
        if not idf.getobject(key, name):
            idf.copyidfobject(ref.getobject(key, name))

    cracks = [a for a in read_adjacencies(ADJ_PATH) if a.edge_type is EdgeTypes.CRACK]

    afn_zone_names = {
        z.Zone_Name for z in idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:ZONE"]
    }
    crack_rooms = {
        n
        for a in cracks
        for n in (a.edge.space_a, a.edge.space_b)
        if n not in WallNormal.keys()
    }
    for room in crack_rooms:
        zone = get_zones_by_plan_name(room, zones)
        if zone.zone_name not in afn_zone_names:
            idf.newidfobject(
                "AIRFLOWNETWORK:MULTIZONE:ZONE",
                Zone_Name=zone.zone_name,
                Ventilation_Control_Mode="NoVent",
            )

    nodes: set[str] = set()
    walls: set[str] = set()
    for a in cracks:
        e = a.edge
        if a.group_type == "Zone_Zone":
            wall, _ = get_surface_between_zones(ZoneEdge(e.space_a, e.space_b), zones)
            ext_node = ""
            crack_comp = "CRcri"
        else:
            crack_comp = "CR-1"
            drn = e.space_a if e.space_a in WallNormal.keys() else e.space_b
            room = e.space_b if e.space_a in WallNormal.keys() else e.space_a
            wall = get_surface_between_zone_and_direction(
                ZoneDirectionEdge(room, WallNormal[drn]), zones
            )
            ext_node = f"Crack_ExtNode_{drn}_{room}"
            if ext_node not in nodes:
                nodes.add(ext_node)
                idf.newidfobject(
                    "AIRFLOWNETWORK:MULTIZONE:EXTERNALNODE",
                    Name=ext_node,
                    External_Node_Height=0,
                    Wind_Pressure_Coefficient_Curve_Name=f"AFN_Pressure_Coefficient_Values_{drn}",
                )
        if wall.surface_name in walls:
            continue
        walls.add(wall.surface_name)
        idf.newidfobject(
            "AIRFLOWNETWORK:MULTIZONE:SURFACE",
            Surface_Name=wall.surface_name,
            Leakage_Component_Name=crack_comp,
            External_Node_Name=ext_node,
            WindowDoor_Opening_Factor_or_Crack_Factor=1,
        )
