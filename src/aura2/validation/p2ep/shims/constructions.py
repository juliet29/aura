from plan2eplus.ezcase.ez import EZ
from plan2eplus.ezcase.utils import open_idf

from aura2.validation.p2ep.paths import REF_IDF

REF_CONSTRUCTIONS = {
    "WALL_EXT": "EXTWALL80",
    "WALL_INT": "PARTITION06",
    "FLOOR": "FLOOR SLAB 8 IN",
    "ROOF": "ROOF34",
    "WINDOW": "WIN-CON-LIGHT",
    "DOOR": "DOOR-CON",
}


def match_reference_constructions(case: EZ):
    idf = case.idf
    ref = open_idf(REF_IDF)
    for key in (
        "MATERIAL",
        "MATERIAL:NOMASS",
        "MATERIAL:AIRGAP",
        "WINDOWMATERIAL:GLAZING",
        "WINDOWMATERIAL:GAS",
        "CONSTRUCTION",
    ):
        for obj in ref.idfobjects[key]:
            if not idf.getobject(key, obj.Name):
                idf.copyidfobject(obj)

    for s in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        t = s.Surface_Type.upper()
        if t == "WALL":
            external = s.Outside_Boundary_Condition.upper() == "OUTDOORS"
            s.Construction_Name = REF_CONSTRUCTIONS[
                "WALL_EXT" if external else "WALL_INT"
            ]
        elif t == "FLOOR":
            s.Construction_Name = REF_CONSTRUCTIONS["FLOOR"]
        elif t in ("ROOF", "CEILING"):
            s.Construction_Name = REF_CONSTRUCTIONS["ROOF"]
    for w in idf.idfobjects["WINDOW"]:
        w.Construction_Name = REF_CONSTRUCTIONS["WINDOW"]
    for d in idf.idfobjects["DOOR:INTERZONE"]:
        d.Construction_Name = REF_CONSTRUCTIONS["DOOR"]

    for s in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        if s.Surface_Type.upper() == "FLOOR":
            s.Outside_Boundary_Condition = "Surface"
            s.Outside_Boundary_Condition_Object = s.Name
            s.Sun_Exposure = "NoSun"
            s.Wind_Exposure = "NoWind"
