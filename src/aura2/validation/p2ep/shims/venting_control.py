from plan2eplus.ezcase.utils import open_idf

from aura2.validation.p2ep.paths import REF_IDF, canonical_room

REF_ZONE_VENTING = {
    "WEST": ("Temperature", 0.3, 5, 10),
    "NORTH": ("Temperature", 1.0, 0, 100),
}


def match_reference_venting_control(idf):
    ref = open_idf(REF_IDF)
    for key, name in (
        ("SCHEDULETYPELIMITS", "Any Number"),
        ("SCHEDULE:COMPACT", "WindowVentSched"),
    ):
        if not idf.getobject(key, name):
            idf.copyidfobject(ref.getobject(key, name))

    for z in idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:ZONE"]:
        mode, min_factor, dt_lo, dt_hi = REF_ZONE_VENTING[canonical_room(z.Zone_Name)]
        z.Ventilation_Control_Mode = mode
        z.Ventilation_Control_Zone_Temperature_Setpoint_Schedule_Name = (
            "WindowVentSched" if mode == "Temperature" else ""
        )
        z.Minimum_Venting_Open_Factor = min_factor
        z.Indoor_and_Outdoor_Temperature_Difference_Lower_Limit_For_Maximum_Venting_Open_Factor = dt_lo
        z.Indoor_and_Outdoor_Temperature_Difference_Upper_Limit_for_Minimum_Venting_Open_Factor = dt_hi
        z.Indoor_and_Outdoor_Enthalpy_Difference_Lower_Limit_For_Maximum_Venting_Open_Factor = 0
        z.Indoor_and_Outdoor_Enthalpy_Difference_Upper_Limit_for_Minimum_Venting_Open_Factor = 300000

    for s in idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:SURFACE"]:
        s.Ventilation_Control_Mode = "ZoneLevel"
        s.WindowDoor_Opening_Factor_or_Crack_Factor = 0.5
