"""Moist-air and water properties.

Standard library only, so the same code runs in the EnergyPlus embedded
Python (3.8) and in a normal Python environment.

Units: temperature in degC, pressure in Pa, humidity ratio in kg/kg dry air,
enthalpy in J/kg dry air.
"""
from __future__ import annotations

import math

# Constants used by the Poppe model (Kloppers & Kroger, 2005)
CP_AIR = 1006.0        # J/kg-K, dry air
CP_VAPOR = 1860.0      # J/kg-K, water vapor
CP_WATER = 4186.0      # J/kg-K, liquid water
H_FG0 = 2.501e6        # J/kg, latent heat at 0 degC
MW_RATIO = 0.621945    # molar mass ratio water / dry air


def p_sat(t_c: float) -> float:
    """Saturation pressure of water vapor [Pa] (Hyland-Wexler, ASHRAE Fundamentals).

    Over ice below 0 degC, over liquid water above. Valid -100 to 200 degC.
    """
    t_c = min(max(t_c, -100.0), 200.0)   # valid range of the correlation; keeps solvers from failing on overshoot
    t = t_c + 273.15
    if t_c < 0.0:
        ln_p = (-5.6745359e3 / t + 6.3925247 - 9.6778430e-3 * t
                + 6.2215701e-7 * t ** 2 + 2.0747825e-9 * t ** 3
                - 9.4840240e-13 * t ** 4 + 4.1635019 * math.log(t))
    else:
        ln_p = (-5.8002206e3 / t + 1.3914993 - 4.8640239e-2 * t
                + 4.1764768e-5 * t ** 2 - 1.4452093e-8 * t ** 3
                + 6.5459673 * math.log(t))
    return math.exp(ln_p)


def w_sat(t_c: float, p: float) -> float:
    """Saturation humidity ratio [kg/kg]."""
    pw = p_sat(t_c)
    return MW_RATIO * pw / (p - pw)


def w_from_rh(t_c: float, rh: float, p: float) -> float:
    pw = rh * p_sat(t_c)
    return MW_RATIO * pw / (p - pw)


def w_from_twb(t_db: float, t_wb: float, p: float) -> float:
    """Humidity ratio from dry-bulb and thermodynamic wet-bulb (ASHRAE Fundamentals)."""
    ws = w_sat(t_wb, p)
    if t_wb >= 0.0:
        return ((2501.0 - 2.326 * t_wb) * ws - 1.006 * (t_db - t_wb)) / (2501.0 + 1.86 * t_db - 4.186 * t_wb)
    return ((2830.0 - 0.24 * t_wb) * ws - 1.006 * (t_db - t_wb)) / (2830.0 + 1.86 * t_db - 2.1 * t_wb)


def h_air(t_c: float, w: float) -> float:
    """Moist-air enthalpy [J/kg dry air], unsaturated."""
    return CP_AIR * t_c + w * (H_FG0 + CP_VAPOR * t_c)


def h_sat(t_c: float, p: float) -> float:
    """Enthalpy of saturated air at t_c [J/kg dry air]."""
    return h_air(t_c, w_sat(t_c, p))


def t_from_h_w(h: float, w: float) -> float:
    """Dry-bulb of unsaturated air from enthalpy and humidity ratio."""
    return (h - w * H_FG0) / (CP_AIR + w * CP_VAPOR)


def t_sat_from_h(h: float, p: float) -> float:
    """Temperature of saturated air that has enthalpy h (bisection, then secant)."""
    lo, hi = -60.0, 100.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if h_sat(mid, p) > h:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def h_fg(t_c: float) -> float:
    """Latent heat of vaporisation of water [J/kg] (Henderson-Sellers 1984)."""
    t = t_c + 273.15
    return 1.91846e6 * (t / (t - 33.91)) ** 2


def t_wb_from_w(t_db: float, w: float, p: float) -> float:
    """Thermodynamic wet-bulb from dry-bulb and humidity ratio (bisection on ASHRAE relation)."""
    lo, hi = -40.0, t_db
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if w_from_twb(t_db, mid, p) > w:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def rho_moist_air(t_c: float, w: float, p: float) -> float:
    """Moist-air density [kg moist air / m3] (ideal gas, same form as EnergyPlus)."""
    return p / (287.0 * (t_c + 273.15) * (1.0 + 1.6077687 * max(w, 1e-5)))


def rho_water(t_c: float) -> float:
    """Liquid water density [kg/m3] (Kell 1975), 0-150 degC."""
    t = max(t_c, 0.0)
    num = (999.83952 + 16.945176 * t - 7.9870401e-3 * t ** 2 - 46.170461e-6 * t ** 3
           + 105.56302e-9 * t ** 4 - 280.54253e-12 * t ** 5)
    return num / (1.0 + 16.879850e-3 * t)
