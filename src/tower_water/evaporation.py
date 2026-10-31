"""Evaporation models for wet cooling towers.

Every model is evaluated at the same operating point (water in/out temperature,
water flow, heat rejected, air flow, inlet air), so differences come from the
physics alone. Equations and references: docs/METHODS.md (section numbers in
brackets below).

  latent_only        [3.1]  all heat leaves as latent heat, E = Q / h_fg
  rule_of_thumb      [3.2]  E = 0.00085 gpm/(gpm F) x flow x range (Perry's / CTI practice)
  loss_factor        [3.3]  EnergyPlus LossFactor, E = k x range x flow
  eplus_saturated_exit [3.4] EnergyPlus SaturatedExit replica (moist-air basis, as coded in v22-v26)
  merkel_saturated_exit [3.4] Merkel energy balance + saturated exit air, dry-air basis
  braun_entu         [3.5]  Braun, Klein & Mitchell (1989) effectiveness model with unsaturated exit humidity
  poppe              [3.6]  Poppe & Roegener (1991) / Kloppers & Kroger (2005), Bosnjakovic Lewis factor
  poppe(lewis=1.0)   [3.6]  Poppe with Le_f = 1 (isolates the Lewis-factor effect)

Also:
  merkel_number_chebyshev / merkel_number_exact  [3.7]  fill demand Me from Merkel's method
  outlet_temperature_*                            [3.8]  rating mode: outlet water temperature for a given fill Me
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import psychro as ps
from .psychro import CP_AIR, CP_VAPOR, CP_WATER, H_FG0

# Status codes
OK = 0
IDLE = 1          # no load or no water flow
NO_AIRFLOW = 2    # load with zero air flow
INFEASIBLE = 3    # operating point not physical for this air flow (driving force vanishes)
CLIPPED = 4       # result limited to saturated exit air (model predicted supersaturation it cannot represent)
ADJUSTED = 5      # operating point marginally beyond the thermodynamic limit; solved with the smallest air-flow increase

_LEWIS_BASE = 0.865 ** 0.667


@dataclass
class EvapResult:
    evap_kg_s: float
    t_air_out: float = float("nan")
    w_air_out: float = float("nan")
    supersaturated: bool = False
    merkel: float = float("nan")
    ntu: float = float("nan")
    status: int = OK
    converged: bool = True    # Poppe only: exit-humidity fixed point met |dw| < 1e-8 kg/kg within max_iter passes


# ---------------------------------------------------------------------------
# 3.1 - 3.3  Empirical / bounding methods
# ---------------------------------------------------------------------------
def latent_only(q_w: float, t_w_in: float, t_w_out: float) -> float:
    """[3.1] E = Q / h_fg(T_w,avg) [kg/s]. Upper bound when no sensible heat goes to the air."""
    if q_w <= 0.0:
        return 0.0
    return q_w / ps.h_fg(0.5 * (t_w_in + t_w_out))


def rule_of_thumb(t_w_in: float, t_w_out: float, m_w: float) -> float:
    """[3.2] E = 0.00085 x 1.8 x range[K] x flow  [kg/s] (= 0.153 %/K)."""
    return max(0.00085 * 1.8 * (t_w_in - t_w_out) * m_w, 0.0)


def loss_factor_kg(factor_pct_per_k: float, t_w_in: float, t_w_out: float, m_w: float) -> float:
    """[3.3] EnergyPlus LossFactor in kg/s. factor in percent per K (EnergyPlus default 0.2)."""
    return max(factor_pct_per_k / 100.0 * (t_w_in - t_w_out) * m_w, 0.0)


def loss_factor(factor_pct_per_k: float, t_w_in: float, t_w_out: float, m_w: float) -> float:
    """EnergyPlus LossFactor in m3/s (EnergyPlus divides by water density at the mean water temperature)."""
    return loss_factor_kg(factor_pct_per_k, t_w_in, t_w_out, m_w) / ps.rho_water(0.5 * (t_w_in + t_w_out))


# ---------------------------------------------------------------------------
# 3.4  Saturated exit air (Merkel energy balance)
# ---------------------------------------------------------------------------
_EP_CPA, _EP_HFG, _EP_CPV = 1.00484e3, 2.50094e6, 1.85895e3   # EnergyPlus PsyHFnTdbW constants


def _ep_h(t: float, w: float) -> float:
    return _EP_CPA * t + max(w, 1e-5) * (_EP_HFG + _EP_CPV * t)


def _ep_tsat_from_h(h: float, p: float) -> float:
    lo, hi = -60.0, 100.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _ep_h(mid, ps.w_sat(mid, p)) > h:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def eplus_air_mass_flow(air_flow_ratio: float, design_air_vdot: float, cells_on: float,
                        cells: int, t_db: float, w: float, p: float) -> float:
    """Air mass flow as EnergyPlus computes it [kg/s] (moist-air density x volume flow)."""
    return air_flow_ratio * design_air_vdot * ps.rho_moist_air(t_db, w, p) * cells_on / cells


def eplus_saturated_exit(q_w: float, m_air: float, t_db: float, t_wb: float, w: float, p: float) -> float:
    """[3.4] EnergyPlus SaturatedExit [m3/s], reproduced line by line from CoolingTower::calculateWaterUsage."""
    if m_air <= 0.0 or q_w <= 0.0:
        return 0.0
    h_in = _ep_h(t_wb, ps.w_sat(t_wb, p))
    h_out = h_in + q_w / m_air
    t_out = _ep_tsat_from_h(h_out, p)
    w_out = (h_out - _EP_CPA * t_out) / (_EP_HFG + _EP_CPV * t_out)
    dq = w_out / (1.0 + w_out) - w / (1.0 + w)
    rho = ps.rho_water(max(0.5 * (t_db + t_out), 4.0))
    return max(m_air * dq / rho, 0.0)


def merkel_saturated_exit(q_w: float, m_a: float, t_db: float, w: float, p: float) -> EvapResult:
    """[3.4] Merkel: exit air saturated at h_out = h_in + Q/m_a; dry-air basis."""
    if q_w <= 0.0:
        return EvapResult(0.0, status=IDLE)
    if m_a <= 0.0:
        return EvapResult(0.0, status=NO_AIRFLOW)
    h_out = ps.h_air(t_db, w) + q_w / m_a
    t_out = ps.t_sat_from_h(h_out, p)
    w_out = ps.w_sat(t_out, p)
    return EvapResult(max(m_a * (w_out - w), 0.0), t_out, w_out)


# ---------------------------------------------------------------------------
# 3.5  Braun, Klein & Mitchell (1989) effectiveness model
# ---------------------------------------------------------------------------
def braun_ntu_from_operating_point(q_w, t_w_in, t_w_out, m_w, m_a, h_a_in, p):
    """Air-side NTU implied by the operating point (counterflow, saturation-specific-heat linearisation).

    Returns (ntu, m_star) or (None, None) if infeasible.
    """
    h_swi, h_swo = ps.h_sat(t_w_in, p), ps.h_sat(t_w_out, p)
    cs = (h_swi - h_swo) / (t_w_in - t_w_out)
    m_star = m_a * cs / (m_w * CP_WATER)
    if h_swi - h_a_in <= 0.0:
        return None, None
    eps = (q_w / m_a) / (h_swi - h_a_in)
    if eps <= 0.0:
        return None, None
    if abs(1.0 - m_star) < 1e-6:
        return (eps / (1.0 - eps) if eps < 1.0 else None), m_star
    arg = (1.0 - eps * m_star) / (1.0 - eps)
    if eps >= 1.0 or arg <= 0.0:
        return None, None
    ntu = math.log(arg) / (1.0 - m_star)
    return (ntu if ntu > 0 else None), m_star


def braun_entu(q_w: float, t_w_in: float, t_w_out: float, m_w: float, m_a: float,
               t_db: float, w: float, p: float) -> EvapResult:
    """[3.5] Exit humidity w_o = w_s,e + (w_i - w_s,e) exp(-NTU), h_s,e = h_i + (h_o - h_i)/(1 - exp(-NTU))."""
    if q_w <= 0.0 or t_w_in - t_w_out < 1e-3 or m_w <= 0.0:
        return EvapResult(0.0, status=IDLE)
    if m_a <= 0.0:
        return EvapResult(0.0, status=NO_AIRFLOW)
    h_in = ps.h_air(t_db, w)
    ntu, _ = braun_ntu_from_operating_point(q_w, t_w_in, t_w_out, m_w, m_a, h_in, p)
    if ntu is None:
        return EvapResult(0.0, status=INFEASIBLE)
    h_out = h_in + q_w / m_a
    x = math.exp(-ntu)
    h_se = h_in + (h_out - h_in) / (1.0 - x)
    w_se = ps.w_sat(ps.t_sat_from_h(h_se, p), p)
    w_out = w_se + (w - w_se) * x
    t_out = ps.t_from_h_w(h_out, w_out)
    status = OK
    if w_out > ps.w_sat(t_out, p):        # model cannot represent fog: limit to saturated exit
        t_out = ps.t_sat_from_h(h_out, p)
        w_out = ps.w_sat(t_out, p)
        status = CLIPPED
    return EvapResult(max(m_a * (w_out - w), 0.0), t_out, w_out, ntu=ntu, status=status)


# ---------------------------------------------------------------------------
# 3.6  Poppe
# ---------------------------------------------------------------------------
def lewis_bosnjakovic(ws_w: float, w: float) -> float:
    """Bosnjakovic (1965) Lewis factor, Le_f = 0.865^(2/3) (x - 1)/ln x, x = (w_s,w + 0.622)/(w + 0.622)."""
    x = (ws_w + 0.622) / (w + 0.622)
    if abs(x - 1.0) < 1e-9:
        return _LEWIS_BASE
    return _LEWIS_BASE * (x - 1.0) / math.log(x)


def _t_supersat(h: float, w: float, p: float) -> float:
    lo, hi = -50.0, 90.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        wsa = ps.w_sat(mid, p)
        f = CP_AIR * mid + wsa * (H_FG0 + CP_VAPOR * mid) + (w - wsa) * CP_WATER * mid - h
        if f > 0.0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-5:
            break
    return 0.5 * (lo + hi)


def air_state(h: float, w: float, p: float):
    """(t_air, w_sat at t_air, supersaturated) for air with enthalpy h and total water content w."""
    t = ps.t_from_h_w(h, w)
    wsa = ps.w_sat(t, p)
    if w <= wsa or t < -50.0 or t > 90.0:
        return t, wsa, False
    t = _t_supersat(h, w, p)
    return t, ps.w_sat(t, p), True


def _derivs(tw, w, h, mw_ma, p, lewis):
    if not (0.0 <= w < 0.5) or not (-60.0 < ps.t_from_h_w(h, w) < 100.0) or mw_ma <= 0.0:
        return None   # unphysical intermediate state (solver overshoot near a pinch)
    ws_w = ps.w_sat(tw, p)
    h_sw = ps.h_air(tw, ws_w)
    h_v = H_FG0 + CP_VAPOR * tw
    _, ws_a, supersat = air_state(h, w, p)
    if not supersat:
        lef = lewis_bosnjakovic(ws_w, w) if lewis is None else lewis
        dw_drive = ws_w - w
        denom = (h_sw - h) + (lef - 1.0) * ((h_sw - h) - dw_drive * h_v) - dw_drive * CP_WATER * tw
    else:
        lef = lewis_bosnjakovic(ws_w, ws_a) if lewis is None else lewis
        dw_drive = ws_w - ws_a
        denom = ((h_sw - h) + (lef - 1.0) * ((h_sw - h) - dw_drive * h_v + (w - ws_a) * CP_WATER * tw)
                 + (w - ws_w) * CP_WATER * tw)
    if denom <= 1e-3 or dw_drive <= 0.0:
        return None
    return (CP_WATER * mw_ma * dw_drive / denom,
            CP_WATER * mw_ma * (1.0 + dw_drive * CP_WATER * tw / denom),
            CP_WATER / denom)


def poppe(t_w_in: float, t_w_out: float, m_w_in: float, m_a: float,
          t_db_in: float, w_in: float, p: float, n_steps: int = 10, max_iter: int = 6,
          lewis=None) -> EvapResult:
    """[3.6] Poppe evaporation for a known operating point (integration over water temperature, RK4).

    lewis: None for Bosnjakovic, or a constant Lewis factor (e.g. 1.0).
    """
    if m_w_in <= 0.0 or t_w_in - t_w_out < 1e-3:
        return EvapResult(0.0, status=IDLE)
    if m_a <= 0.0:
        return EvapResult(0.0, status=NO_AIRFLOW)

    h_in = ps.h_air(t_db_in, w_in)
    dtw = (t_w_in - t_w_out) / n_steps
    h_out_guess = h_in + m_w_in * CP_WATER * (t_w_in - t_w_out) / m_a
    w_out = ps.w_sat(ps.t_sat_from_h(h_out_guess, p), p)

    w = h = me = 0.0
    converged = False
    for _ in range(max_iter):
        w, h, me = w_in, h_in, 0.0
        tw = t_w_out
        base = m_w_in / m_a - w_out
        for _ in range(n_steps):
            k1 = _derivs(tw, w, h, base + w, p, lewis)
            if k1 is None:
                return EvapResult(0.0, status=INFEASIBLE)
            w2, h2 = w + 0.5 * dtw * k1[0], h + 0.5 * dtw * k1[1]
            k2 = _derivs(tw + 0.5 * dtw, w2, h2, base + w2, p, lewis)
            if k2 is None:
                return EvapResult(0.0, status=INFEASIBLE)
            w3, h3 = w + 0.5 * dtw * k2[0], h + 0.5 * dtw * k2[1]
            k3 = _derivs(tw + 0.5 * dtw, w3, h3, base + w3, p, lewis)
            if k3 is None:
                return EvapResult(0.0, status=INFEASIBLE)
            w4, h4 = w + dtw * k3[0], h + dtw * k3[1]
            k4 = _derivs(tw + dtw, w4, h4, base + w4, p, lewis)
            if k4 is None:
                return EvapResult(0.0, status=INFEASIBLE)
            w += dtw / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            h += dtw / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            me += dtw / 6.0 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
            tw += dtw
        converged = abs(w - w_out) < 1e-8
        w_out = w
        if converged:
            break

    t_out, _, supersat = air_state(h, w, p)
    return EvapResult(m_a * (w - w_in), t_out, w, supersat, me, status=OK, converged=converged)


# ---------------------------------------------------------------------------
# 3.7  Merkel number (fill demand) from Merkel's method
# ---------------------------------------------------------------------------
def _merkel_integrand(tw, t_w_out, m_w, m_a, h_a_in, p):
    h_a = h_a_in + m_w * CP_WATER * (tw - t_w_out) / m_a
    d = ps.h_sat(tw, p) - h_a
    return None if d <= 0 else CP_WATER / d


def merkel_number_chebyshev(t_w_in, t_w_out, m_w, m_a, h_a_in, p):
    """[3.7] Me = integral cpw dTw / (h_sw - h_a), four-point Chebyshev (CTI ATC-105 practice)."""
    r = t_w_in - t_w_out
    s = 0.0
    for f in (0.1, 0.4, 0.6, 0.9):
        v = _merkel_integrand(t_w_out + f * r, t_w_out, m_w, m_a, h_a_in, p)
        if v is None:
            return float("nan")
        s += v
    return r / 4.0 * s


def merkel_number_exact(t_w_in, t_w_out, m_w, m_a, h_a_in, p, n=40):
    """[3.7] Same integral by composite Simpson's rule."""
    r = t_w_in - t_w_out
    if n % 2:
        n += 1
    hstep = r / n
    s = 0.0
    for i in range(n + 1):
        v = _merkel_integrand(t_w_out + i * hstep, t_w_out, m_w, m_a, h_a_in, p)
        if v is None:
            return float("nan")
        s += v * (1 if i in (0, n) else (4 if i % 2 else 2))
    return s * hstep / 3.0


# ---------------------------------------------------------------------------
# 3.8  Rating mode: outlet water temperature for a given fill Merkel number
# ---------------------------------------------------------------------------
def _solve_tw_out(me_fn, me_fill, t_w_in, t_lo):
    """Find Tw_out with Me_required(Tw_out) = Me_fill. Me_required falls as Tw_out rises."""
    lo, hi = t_lo + 1e-3, t_w_in - 0.01
    if not (me_fn(hi) <= me_fill):
        return float("nan")
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        v = me_fn(mid)
        if math.isnan(v) or v > me_fill:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-4:
            break
    return 0.5 * (lo + hi)


def outlet_temperature_merkel(me_fill, t_w_in, m_w, m_a, t_db, w, p):
    h_in = ps.h_air(t_db, w)
    t_wb = ps.t_wb_from_w(t_db, w, p)
    return _solve_tw_out(lambda to: merkel_number_exact(t_w_in, to, m_w, m_a, h_in, p), me_fill, t_w_in, t_wb)


def outlet_temperature_poppe(me_fill, t_w_in, m_w, m_a, t_db, w, p, lewis=None, n_steps=10):
    t_wb = ps.t_wb_from_w(t_db, w, p)

    def me(to):
        r = poppe(t_w_in, to, m_w, m_a, t_db, w, p, n_steps=n_steps, lewis=lewis)
        return r.merkel if r.status == OK else float("nan")
    return _solve_tw_out(me, me_fill, t_w_in, t_wb)


def outlet_temperature_entu(me_fill, t_w_in, m_w, m_a, t_db, w, p):
    """Braun effectiveness model with NTU = Me x m_w / m_a; cs from an inner fixed-point iteration."""
    h_in = ps.h_air(t_db, w)
    ntu = me_fill * m_w / m_a
    h_swi = ps.h_sat(t_w_in, p)
    t_out = t_w_in - 5.0
    for _ in range(50):
        cs = (h_swi - ps.h_sat(t_out, p)) / max(t_w_in - t_out, 1e-6)
        ms = m_a * cs / (m_w * CP_WATER)
        if abs(1.0 - ms) < 1e-9:
            eps = ntu / (1.0 + ntu)
        else:
            e = math.exp(-ntu * (1.0 - ms))
            eps = (1.0 - e) / (1.0 - ms * e)
        q = eps * m_a * (h_swi - h_in)
        new = t_w_in - q / (m_w * CP_WATER)
        if abs(new - t_out) < 1e-6:
            break
        t_out = 0.5 * (t_out + new)
    return t_out
