from plan2eplus.ezcase.ez import EZ

REF_DISCHARGE_COEFFICIENT = 0.6


def match_reference_discharge_coefficient(case: EZ):
    for o in case.idf.idfobjects["AIRFLOWNETWORK:MULTIZONE:COMPONENT:SIMPLEOPENING"]:
        o.Discharge_Coefficient = REF_DISCHARGE_COEFFICIENT
