"""Hybrid adiabatic dry cooler: pad / spray pre-cooling, water accounting, wet/dry control.

A dry fluid cooler (EnergyPlus FluidCooler) is preceded by wetted media pads (or a spray system). In wet mode
the air entering the coil is cooled adiabatically:

  T_pre = T_db - eps (T_db - T_wb)                                       [6.1]
  adiabatic saturation:  i_in + (w_pre - w_in) c_pw T_wb = i_pre          [6.1]
  evaporation:           E = m_a,dry (w_pre - w_in)                       [6.2]

Pad effectiveness depends on face velocity through the pad NTU (forced-convection scaling h ~ V^n):
  NTU = -ln(1 - eps_d),   NTU(V) = NTU_d (V/V_d)^(n-1),   eps(V) = 1 - exp(-NTU(V))   [6.1]

Water systems [6.2]:
  media (recirculating):  bleed B = E / (N - 1)        (N cycles from tower_water.chemistry)
  spray (once-through):   applied = E / eta_spray,  runoff = applied - E
Pad pressure drop adds fan power  dP(V) = dP_d (V/V_d)^m,  P_pad = dP V / eta_fan   [6.3]

Air flow through a two-speed EnergyPlus fluid cooler is recovered exactly from its fan power [6.4]:
  P <= P_low : fan cycles at low speed,  f = P / P_low          -> states [(f, V_low)]
  P >  P_low : cycles low/high,          f = (P - P_low)/(P_high - P_low) -> [(f, V_high), (1 - f, V_low)]

Wet/dry control strategies [6.5]: "dry", "wet" (always, above the freeze limit), "threshold" (wet when
T_db >= T_on, off below T_on - hysteresis), each with an optional minimum wet-bulb depression.

Equations and assumptions: docs/METHODS.md section 6.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import psychro as ps
from .psychro import CP_AIR, CP_VAPOR, CP_WATER, H_FG0


# ---------------------------------------------------------------------------
# 6.1 Pad physics
# ---------------------------------------------------------------------------
def pad_effectiveness(eps_design: float, v_ratio: float = 1.0, n: float = 0.8) -> float:
    """Effectiveness at face velocity V = v_ratio x V_design (NTU scaling with h ~ V^n)."""
    if v_ratio <= 0.0:
        return 0.0
    eps_design = min(max(eps_design, 1e-6), 0.999999)
    ntu = -math.log(1.0 - eps_design) * v_ratio ** (n - 1.0)
    return 1.0 - math.exp(-ntu)


@dataclass
class PreCooled:
    t_db: float      # air leaving the pad [C]
    w: float         # humidity ratio leaving the pad [kg/kg]
    t_wb: float      # wet-bulb (unchanged by adiabatic saturation) [C]
    dw: float        # humidity added [kg/kg dry air]


def precool(t_db: float, w: float, p: float, eps: float) -> PreCooled:
    """Adiabatic pre-cooling with effectiveness eps. Exact adiabatic-saturation energy balance."""
    t_wb = ps.t_wb_from_w(t_db, w, p)
    t_out = t_db - eps * (t_db - t_wb)
    h_in = ps.h_air(t_db, w)
    # h_in + (w_out - w) cpw t_wb = cpa t_out + w_out (hfg0 + cpv t_out)
    w_out = (h_in - w * CP_WATER * t_wb - CP_AIR * t_out) / (H_FG0 + CP_VAPOR * t_out - CP_WATER * t_wb)
    w_out = min(max(w_out, w), ps.w_sat(t_out, p))
    return PreCooled(t_out, w_out, t_wb, w_out - w)


# ---------------------------------------------------------------------------
# 6.4 Air flow from EnergyPlus two-speed fan power
# ---------------------------------------------------------------------------
def fan_states(p_fan: float, p_high: float, p_low: float, v_high: float, v_low: float) -> List[Tuple[float, float]]:
    """[(time fraction, air volume flow m3/s)] for a FluidCooler:TwoSpeed from its fan power."""
    if p_fan <= 1e-6:
        return []
    if p_low > 0.0 and p_fan <= p_low * (1.0 + 1e-9):
        return [(min(p_fan / p_low, 1.0), v_low)]
    f = min(max((p_fan - p_low) / max(p_high - p_low, 1e-9), 0.0), 1.0)
    return [(f, v_high), (1.0 - f, v_low)] if f < 1.0 else [(1.0, v_high)]


def single_speed_states(p_fan: float, p_high: float, v_high: float) -> List[Tuple[float, float]]:
    if p_fan <= 1e-6:
        return []
    return [(min(p_fan / p_high, 1.0), v_high)]


# ---------------------------------------------------------------------------
# 6.2 / 6.3 Water and fan-energy accounting for one timestep
# ---------------------------------------------------------------------------
@dataclass
class PadConfig:
    eps_design: float = 0.85          # assumption: rigid cellulose media ~150-200 mm at design face velocity
    v_design: float = 0.0             # design air flow through the pads [m3/s] (= high-speed flow); 0 = no velocity effect
    n_exp: float = 0.8                # h ~ V^n (forced convection)
    system: str = "media"             # media | spray
    spray_efficiency: float = 0.6     # fraction of sprayed water that evaporates (assumption)
    dp_design: float = 0.0            # pad pressure drop at design velocity [Pa] (0 = ignore)
    dp_exp: float = 1.8
    fan_efficiency: float = 0.6
    pads_in_airstream_when_dry: bool = True


@dataclass
class PadResult:
    evap_kg_s: float = 0.0
    t_pre: float = float("nan")
    eps_mean: float = 0.0
    air_kg_s: float = 0.0             # time-averaged dry-air flow through the coil
    fan_penalty_w: float = 0.0


def pad_timestep(states: List[Tuple[float, float]], wet: bool, t_db: float, w: float, p: float,
                 cfg: PadConfig) -> PadResult:
    """Evaporation and pad fan penalty, time-averaged over the fan states of one timestep."""
    rho = ps.rho_moist_air(t_db, w, p)
    res = PadResult()
    num_eps = 0.0
    for frac, vdot in states:
        m_dry = frac * vdot * rho / (1.0 + w)
        res.air_kg_s += m_dry
        vr = vdot / cfg.v_design if cfg.v_design > 0 else 1.0
        if cfg.dp_design > 0 and (wet or cfg.pads_in_airstream_when_dry):
            res.fan_penalty_w += frac * cfg.dp_design * vr ** cfg.dp_exp * vdot / cfg.fan_efficiency
        if wet:
            eps = pad_effectiveness(cfg.eps_design, vr, cfg.n_exp)
            pc = precool(t_db, w, p, eps)
            res.evap_kg_s += m_dry * pc.dw
            num_eps += eps * m_dry
    if wet and res.air_kg_s > 0:
        res.eps_mean = num_eps / res.air_kg_s
    return res


def water_supply(evap_kg_s: float, cfg: PadConfig, cycles: Optional[float]) -> Tuple[float, float]:
    """(applied/makeup kg/s, bleed-or-runoff kg/s)."""
    if evap_kg_s <= 0.0:
        return 0.0, 0.0
    if cfg.system == "spray":
        applied = evap_kg_s / cfg.spray_efficiency
        return applied, applied - evap_kg_s
    bleed = evap_kg_s / (cycles - 1.0) if cycles and cycles > 1.0 else 0.0
    return evap_kg_s + bleed, bleed


# ---------------------------------------------------------------------------
# 6.5 Wet/dry controller
# ---------------------------------------------------------------------------
@dataclass
class Controller:
    strategy: str = "threshold"       # dry | wet | threshold
    t_on: float = 26.0                # switch-over dry-bulb [C]
    hysteresis: float = 2.0
    t_freeze: float = 5.0             # no wetting below this dry-bulb
    min_depression: float = 0.0       # require T_db - T_wb >= this [K]
    wet: bool = field(default=False, init=False)
    switches: int = field(default=0, init=False)

    def step(self, t_db: float, t_wb: float) -> bool:
        if self.strategy == "dry":
            new = False
        elif t_db < self.t_freeze or (t_db - t_wb) < self.min_depression:
            new = False
        elif self.strategy == "wet":
            new = True
        elif self.strategy == "threshold":
            new = t_db >= self.t_on or (self.wet and t_db >= self.t_on - self.hysteresis)
        else:
            raise ValueError("unknown strategy %r" % self.strategy)
        if new != self.wet:
            self.switches += 1
        self.wet = new
        return new
