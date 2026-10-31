"""Blowdown from water chemistry (docs/METHODS.md section 5).

Cycles of concentration N (COC) are limited by:
  * fixed concentration limits of individual constituents      [5.2]   N_i = limit_i / c_i
  * solubility-product type limits (e.g. Ca x alkalinity)        [5.2]   N_ij = sqrt(K / (c_i c_j))
  * calcium carbonate scaling, Langelier Saturation Index        [5.3]   LSI(N) <= LSI_max at hot-water temperature
  * amorphous silica solubility (temperature dependent)          [5.4]   N_SiO2 = f S(T_cold) / c_SiO2
then N = clip(min, N_min, N_max), and blowdown B = E/(N - 1) - D, B >= 0   [5.1]

Concentrations are mg/L; hardness and alkalinity as CaCO3; silica as SiO2.
Three operating modes:
  fixed        N given (EnergyPlus ConcentrationRatio)
  constituent  N from constituent limits only (constant)
  dynamic      N recomputed each timestep with LSI and silica limits at current temperatures
               (idealised conductivity control that always runs at the allowable N)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

CONSTITUENTS = ("silica", "calcium_hardness", "m_alkalinity", "chloride", "sulfate", "tds")


@dataclass
class WaterQuality:
    name: str = "makeup"
    conc: Dict[str, float] = field(default_factory=dict)


@dataclass
class TreatmentLimits:
    name: str = "treatment"
    limits: Dict[str, float] = field(default_factory=dict)
    product_limits: Dict[str, float] = field(default_factory=dict)
    lsi_max: Optional[float] = None          # e.g. 2.5 with a stabiliser (placeholder)
    ph_cycled: Optional[float] = None        # recirculating-water pH (acid-feed setpoint)
    silica_solubility_factor: Optional[float] = None   # allowable multiple of amorphous-silica solubility
    min_cycles: float = 1.5
    max_cycles: float = 10.0


# ---------------------------------------------------------------------------
# 5.3 Langelier / Ryznar indices
# ---------------------------------------------------------------------------
def ph_s(tds: float, t_c: float, ca_caco3: float, alk_caco3: float) -> float:
    """Saturation pH, pHs = (9.3 + A + B) - (C + D) (Langelier 1936; Standard Methods form)."""
    a = (math.log10(tds) - 1.0) / 10.0
    b = -13.12 * math.log10(t_c + 273.15) + 34.55
    c = math.log10(ca_caco3) - 0.4
    d = math.log10(alk_caco3)
    return (9.3 + a + b) - (c + d)


def lsi(ph: float, tds: float, t_c: float, ca: float, alk: float) -> float:
    return ph - ph_s(tds, t_c, ca, alk)


def rsi(ph: float, tds: float, t_c: float, ca: float, alk: float) -> float:
    """Ryznar (1944) stability index, RSI = 2 pHs - pH."""
    return 2.0 * ph_s(tds, t_c, ca, alk) - ph


def cycles_lsi_limit(water: WaterQuality, ph: float, lsi_max: float, t_c: float) -> Optional[float]:
    """Max N with LSI(N) <= lsi_max. Ca, alkalinity and TDS all scale with N, so
    pHs(N) = pHs(1) - 1.9 log10 N and N_max = 10^((lsi_max - pH + pHs(1)) / 1.9)."""
    c = water.conc
    if not all(c.get(k) for k in ("tds", "calcium_hardness", "m_alkalinity")):
        return None
    phs1 = ph_s(c["tds"], t_c, c["calcium_hardness"], c["m_alkalinity"])
    return 10.0 ** ((lsi_max - ph + phs1) / 1.9)


# ---------------------------------------------------------------------------
# 5.4 Silica solubility
# ---------------------------------------------------------------------------
def silica_solubility(t_c: float) -> float:
    """Amorphous silica solubility [mg/kg SiO2], log10 S = 4.52 - 731/T (Fournier 1977)."""
    return 10.0 ** (4.52 - 731.0 / (t_c + 273.15))


# ---------------------------------------------------------------------------
# 5.1 / 5.2
# ---------------------------------------------------------------------------
def cycles_of_concentration(water: WaterQuality, treat: TreatmentLimits,
                            t_hot: Optional[float] = None, t_cold: Optional[float] = None) -> Tuple[float, str]:
    """(N, limiting constraint). LSI and silica-solubility limits apply only when temperatures are given."""
    best, which = treat.max_cycles, "max_cycles"

    def consider(n, name):
        nonlocal best, which
        if n is not None and n < best:
            best, which = n, name

    for key, lim in treat.limits.items():
        c = water.conc.get(key)
        if c and c > 0.0:
            consider(lim / c, key)
    for key, lim in treat.product_limits.items():
        a, b = key.split("*")
        ca, cb = water.conc.get(a), water.conc.get(b)
        if ca and cb:
            consider(math.sqrt(lim / (ca * cb)), key)
    if t_hot is not None and treat.lsi_max is not None and treat.ph_cycled is not None:
        consider(cycles_lsi_limit(water, treat.ph_cycled, treat.lsi_max, t_hot), "LSI")
    if t_cold is not None and treat.silica_solubility_factor and water.conc.get("silica"):
        consider(treat.silica_solubility_factor * silica_solubility(t_cold) / water.conc["silica"], "silica_solubility")
    if best < treat.min_cycles:
        best, which = treat.min_cycles, which + " (raised to min_cycles)"
    return best, which


def blowdown(evap: float, drift: float, coc: float) -> float:
    if coc <= 1.0:
        raise ValueError("cycles of concentration must be > 1")
    return max(evap / (coc - 1.0) - drift, 0.0)


LIMIT_CODES = {"fixed": 0, "max_cycles": 1, "silica": 2, "calcium_hardness": 3, "m_alkalinity": 4,
               "chloride": 5, "sulfate": 6, "tds": 7, "LSI": 8, "silica_solubility": 9}


def limit_code(which: str) -> int:
    base = which.split(" ")[0]
    return LIMIT_CODES.get(base, 10)


@dataclass
class ChemistryModel:
    water: WaterQuality
    treatment: TreatmentLimits
    mode: str = "constituent"            # fixed | constituent | dynamic
    fixed_cycles: Optional[float] = None

    def cycles(self, t_hot: Optional[float] = None, t_cold: Optional[float] = None) -> Tuple[float, str]:
        if self.mode == "fixed" or self.fixed_cycles:
            return float(self.fixed_cycles), "fixed"
        if self.mode == "dynamic":
            return cycles_of_concentration(self.water, self.treatment, t_hot, t_cold)
        return cycles_of_concentration(self.water, self.treatment)

    @classmethod
    def from_library(cls, path: str, source: str, treatment: str, fixed_cycles: Optional[float] = None,
                     mode: Optional[str] = None):
        with open(path) as fh:
            lib = json.load(fh)
        src = lib["sources"][source]
        trt = lib["treatments"][treatment]
        water = WaterQuality(source, {k: v for k, v in src.items() if k in CONSTITUENTS})
        limits = TreatmentLimits(
            treatment, dict(trt.get("limits", {})), dict(trt.get("product_limits", {})),
            trt.get("lsi_max"), trt.get("ph_cycled"), trt.get("silica_solubility_factor"),
            trt.get("min_cycles", 1.5), trt.get("max_cycles", 10.0))
        if mode is None:
            mode = "fixed" if fixed_cycles else "constituent"
        return cls(water, limits, mode, fixed_cycles)
