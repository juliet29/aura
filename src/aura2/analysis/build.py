from aura2.analysis.figures.boxes import make_box_pressure, make_box_temp, make_box_vent
from aura2.analysis.figures.geometry import make_pressure_geom, make_pressure_geom_alt
from aura2.analysis.figures.sensitivity import make_sens_flow, make_sens_temp
from aura2.analysis.figures.weather import make_site_temp

FIGURES = {
    "box_temp": make_box_temp,
    "box_pressure": make_box_pressure,
    "box_vent": make_box_vent,
    "sens_temp": make_sens_temp,
    "sens_flow": make_sens_flow,
    "pressure_geom": make_pressure_geom,
    "pressure_geom_alt": make_pressure_geom_alt,
    "site_temp": make_site_temp,
}
