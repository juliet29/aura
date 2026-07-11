import networkx as nx
import shapely
from polyfix.adjacencies.zonal import capture_zone_adjacencies
from polyfix.geometry.layout import Layout
from polyfix.layout.main.plan import create_move_graph_for_all_surfaces_along_axis

OVERLAP_TOL = 1e-4  # m^2; shared edges give ~0 intersection area, real overlaps are larger


def shape_factor(polygon) -> float:
    return polygon.length**2 / polygon.area  # 16 for a square, larger = less compact


def room_metrics(layout: Layout) -> dict[str, dict[str, float]]:
    return {
        d.name: {"area": d.polygon.area, "shape_factor": shape_factor(d.polygon)}
        for d in layout.domains
    }


def floor_metrics(layout: Layout) -> dict[str, float]:
    poly = shapely.unary_union([d.polygon for d in layout.domains])
    return {"area": poly.area, "shape_factor": shape_factor(poly)}


def adjacency_graph(layout: Layout) -> nx.Graph:
    # compose the X- and Y-plan graphs WITHOUT moving; used for both before and
    # after layouts so the two graphs are computed identically
    gx = create_move_graph_for_all_surfaces_along_axis(layout, "X")
    gy = create_move_graph_for_all_surfaces_along_axis(layout, "Y")
    G = nx.Graph()
    for room, nbs in capture_zone_adjacencies(gx, gy).items():
        G.add_node(room)
        for nb in nbs:
            G.add_edge(room, nb)
    nx.set_node_attributes(G, {n: n for n in G.nodes}, "name")
    return G


def graph_edit_distance(g_before: nx.Graph, g_after: nx.Graph) -> float:
    # rooms keep identity by name, so only added/removed adjacencies cost
    return nx.graph_edit_distance(
        g_before, g_after, node_match=lambda a, b: a["name"] == b["name"], timeout=10
    )


def is_valid(layout: Layout) -> tuple[bool, str]:
    polys = []
    for d in layout.domains:
        try:
            p = d.polygon
        except Exception as e:
            return False, f"bad polygon {d.name}: {e}"
        if not p.is_valid:
            return False, f"invalid polygon: {d.name}"
        if not d.is_orthogonal:
            return False, f"non-orthogonal: {d.name}"
        polys.append((d.name, p))
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            (na, pa), (nb, pb) = polys[i], polys[j]
            overlap = pa.intersection(pb).area
            if overlap > OVERLAP_TOL:
                return False, f"overlap {na}&{nb}: {overlap:.3g}"
    return True, "valid"
