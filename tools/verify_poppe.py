#!/usr/bin/env python3
"""Code verification of the Poppe implementation against an independent formulation.

Independent model: the original height-wise conservation equations of a counterflow fill
(Poppe & Roegener 1991; Kloppers & Kroger 2005, eqs. before rearrangement), with the fill
transfer coefficient K = h_d a_fi A_fr L [kg/s] prescribed, solved as a boundary-value
problem by shooting on the bottom water temperature with SciPy's adaptive RK45/LSODA:

    dm_w/dz  = K (w_sw - w)                               (water lost = vapour gained)
    dw/dz    = K (w_sw - w) / m_a
    dh/dz    = K [Le_f c_pma (T_w - T_a) + (w_sw - w) h_v(T_w)] / m_a
    d(m_w c_pw T_w)/dz = m_a dh/dz                        (energy)

z in [0, 1] from the bottom (air inlet) to the top (water inlet). In supersaturated air the vapour stays at
saturation (w_sa at T_a), the driving force is (w_sw - w_sa), and the excess water is carried as mist with the air
enthalpy i_ss = c_pa T_a + w_sa (i_fg0 + c_pv T_a) + (w - w_sa) c_pw T_a (ev.air_state gives T_a).

The tower_water.evaporation.poppe() result at the same (T_w,in, T_w,out, m_w,in, m_a, air)
must reproduce Me = K / m_w,in and the evaporation rate. Prints a table; exits non-zero on failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tower_water import evaporation as ev  # noqa: E402
from tower_water import psychro as ps  # noqa: E402

P = 101325.0


def height_model(K, m_a, m_w_in, t_w_in, t_db, w_in, lewis=None):
    """Return (T_w,out, evaporation kg/s, exit T_a, exit w) from the height-wise formulation."""
    h_in = ps.h_air(t_db, w_in)

    def rhs(z, y):
        tw, mw, w, h = y
        # air state: unsaturated, or supersaturated (vapour at saturation w_sa + liquid mist w - w_sa)
        ta, wsa, supersat = ev.air_state(h, w, P)
        wv = wsa if supersat else w                      # vapour content that drives mass transfer
        wsw = ps.w_sat(tw, P)
        lef = ev.lewis_bosnjakovic(wsw, wv) if lewis is None else lewis
        cpma = ps.CP_AIR + wv * ps.CP_VAPOR
        hv = ps.H_FG0 + ps.CP_VAPOR * tw
        mdot = K * (wsw - wv)
        dh = K * (lef * cpma * (tw - ta) + (wsw - wv) * hv) / m_a
        dw = mdot / m_a
        dmw = mdot
        # d(mw cpw tw) = ma dh  ->  cpw (mw dtw + tw dmw) = ma dh
        dtw = (m_a * dh - ps.CP_WATER * tw * dmw) / (ps.CP_WATER * mw)
        return [dtw, dmw, dw, dh]

    def shoot(tw_out):
        evap_guess = 0.0
        for _ in range(20):          # m_w at the bottom = m_w,in - evaporation (fixed point)
            sol = solve_ivp(rhs, (0, 1), [tw_out, m_w_in - evap_guess, w_in, h_in],
                            method="LSODA", rtol=1e-10, atol=1e-12)
            evap = sol.y[1, -1] - (m_w_in - evap_guess)
            if abs(evap - evap_guess) < 1e-12:
                break
            evap_guess = evap
        return sol, evap

    def resid(to):
        try:
            with np.errstate(all="raise"):
                sol, _ = shoot(to)
            return sol.y[0, -1] - t_w_in if sol.success else float("nan")
        except (ValueError, FloatingPointError, ZeroDivisionError):
            return float("nan")

    t_wb = ps.t_wb_from_w(t_db, w_in, P)
    grid = np.linspace(t_wb + 0.05, t_w_in - 0.01, 41)
    vals = [resid(g) for g in grid]
    br = [(a, b) for a, b, fa, fb in zip(grid, grid[1:], vals, vals[1:])
          if np.isfinite(fa) and np.isfinite(fb) and fa * fb < 0]
    if not br:
        raise RuntimeError("no bracket for T_w,out")
    tw_out = brentq(resid, *br[0], xtol=1e-10)
    sol, evap = shoot(tw_out)
    w_o, h_o = sol.y[2, -1], sol.y[3, -1]
    # Me defined on the local water flow, Me = integral K dz / m_w(z) (the form the rearranged equations use)
    z = np.linspace(0, 1, 2001)
    dense = solve_ivp(rhs, (0, 1), sol.y[:, 0], method="LSODA", rtol=1e-10, atol=1e-12, dense_output=True)
    me_local = np.trapezoid(K / dense.sol(z)[1], z)
    return tw_out, evap, ps.t_from_h_w(h_o, w_o), w_o, me_local


CASES = [
    # name, t_db, RH, Tw_in, m_w, m_a, K
    ("temperate design", 25.0, 0.50, 35.0, 10.0, 9.0, 12.0),
    ("hot-dry (Phoenix-like)", 42.0, 0.12, 33.0, 10.0, 9.0, 12.0),
    ("hot-humid (Singapore-like)", 31.0, 0.75, 36.0, 10.0, 10.0, 14.0),
    ("mild, high L/G", 20.0, 0.60, 32.0, 10.0, 5.0, 8.0),
    ("cool, low L/G", 12.0, 0.55, 28.0, 10.0, 14.0, 10.0),
    # near-pinch, very high NTU (review M8): exit air approaches saturation at the hot-water temperature
    ("near pinch, mild (Dublin-like)", 16.0, 0.55, 23.0, 10.0, 6.0, 40.0),
    ("near pinch, hot-dry", 38.0, 0.15, 30.0, 10.0, 6.5, 40.0),
]


def main():
    print("%-28s %8s %8s %8s %10s %10s %9s %9s %9s" % ("case", "Tw,out", "K/mw_in", "Me_ref", "Me_code",
                                                    "E_ref g/s", "E_code", "dE %", "dMe(40) %"))
    worst_e = worst_me = 0.0
    for name, t_db, rh, tw_in, mw, ma, K in CASES:
        w = ps.w_from_rh(t_db, rh, P)
        tw_out, e_ref, ta_o, w_o, me_local = height_model(K, ma, mw, tw_in, t_db, w)
        r = ev.poppe(tw_in, tw_out, mw, ma, t_db, w, P, n_steps=10)        # plugin default
        r40 = ev.poppe(tw_in, tw_out, mw, ma, t_db, w, P, n_steps=40)      # Me converges slower near the pinch
        de = 100 * (r.evap_kg_s / e_ref - 1)
        dme = 100 * (r40.merkel / me_local - 1)
        worst_e = max(worst_e, abs(de))
        worst_me = max(worst_me, abs(dme))
        print("%-28s %8.3f %8.4f %8.4f %10.4f %10.3f %9.3f %9.5f %9.5f %s" % (
            name, tw_out, K / mw, me_local, r.merkel, 1e3 * e_ref, 1e3 * r.evap_kg_s, de, dme, "supersat" if r.supersaturated else ""))
    print("max |error|: evaporation (10 RK4 steps) %.4f %%, Me_P (40 steps) %.4f %%" % (worst_e, worst_me))
    return 0 if worst_e < 0.05 and worst_me < 0.2 else 1


if __name__ == "__main__":
    sys.exit(main())
