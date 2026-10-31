"""Evaporation-method registry: evaluate every method on one operating point.

Each method maps an OperatingPoint to an EvapResult (kg/s). Method IDs are
short and stable because they become EnergyPlus variable names
(<prefix>_E_<ID>). See docs/METHODS.md for equations and references.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from . import evaporation as ev
from . import psychro as ps


@dataclass
class OperatingPoint:
    t_w_in: float     # C, water entering tower
    t_w_out: float    # C, water leaving tower
    m_w: float        # kg/s, water entering
    q: float          # W, heat rejected (EnergyPlus: m_w cp (Tin - Tout))
    m_a: float        # kg/s DRY air
    m_air_ep: float   # kg/s air as EnergyPlus computes it (moist-air density x volume)
    t_db: float
    t_wb: float
    w: float          # kg/kg
    p: float          # Pa


# Density used to convert every method's kg/s to the m3/s reported to EnergyPlus.
RHO_REF = ps.rho_water(20.0)


def _wrap(kg_s):
    return ev.EvapResult(max(kg_s, 0.0))


def _lat(op, cfg):
    return _wrap(ev.latent_only(op.q, op.t_w_in, op.t_w_out))


def _rot(op, cfg):
    return _wrap(ev.rule_of_thumb(op.t_w_in, op.t_w_out, op.m_w))


def _lf(op, cfg):
    return _wrap(ev.loss_factor_kg(cfg.get("loss_factor_pct_per_k", 0.2), op.t_w_in, op.t_w_out, op.m_w))


def _ep(op, cfg):
    vdot = ev.eplus_saturated_exit(op.q, op.m_air_ep, op.t_db, op.t_wb, op.w, op.p)
    return _wrap(vdot * RHO_REF)  # exact EnergyPlus m3/s after dividing by RHO_REF


def _msat(op, cfg):
    return ev.merkel_saturated_exit(op.q, op.m_a, op.t_db, op.w, op.p)


def _braun(op, cfg):
    return ev.braun_entu(op.q, op.t_w_in, op.t_w_out, op.m_w, op.m_a, op.t_db, op.w, op.p)


def _poppe(op, cfg):
    return ev.poppe(op.t_w_in, op.t_w_out, op.m_w, op.m_a, op.t_db, op.w, op.p,
                    n_steps=cfg.get("poppe_steps", 10))


def _poppe_le1(op, cfg):
    return ev.poppe(op.t_w_in, op.t_w_out, op.m_w, op.m_a, op.t_db, op.w, op.p,
                    n_steps=cfg.get("poppe_steps", 10), lewis=1.0)


# ID -> (function, short description, reference key in docs/METHODS.md)
METHODS = OrderedDict([
    ("LAT", (_lat, "Latent-only bound E = Q/h_fg", "3.1")),
    ("ROT", (_rot, "Rule of thumb 0.00085 x 1.8 x range x flow", "3.2")),
    ("LF", (_lf, "EnergyPlus LossFactor (k %/K x range x flow)", "3.3")),
    ("EPSAT", (_ep, "EnergyPlus SaturatedExit replica", "3.4")),
    ("MSAT", (_msat, "Merkel energy balance, saturated exit, dry-air basis", "3.4")),
    ("BRAUN", (_braun, "Braun et al. (1989) e-NTU, unsaturated exit humidity", "3.5")),
    ("POPPE", (_poppe, "Poppe, Bosnjakovic Lewis factor", "3.6")),
    ("POPPE1", (_poppe_le1, "Poppe, Lewis factor = 1", "3.6")),
])
REFERENCE = "POPPE"
# methods that need air flow and fall back to EPSAT-equivalent MSAT when they cannot solve
NEEDS_AIR = {"EPSAT", "MSAT", "BRAUN", "POPPE", "POPPE1"}


AIR_SCALES = (1.01, 1.02, 1.03, 1.05, 1.08, 1.12, 1.2, 1.35, 1.5)


def _with_air(op, scale):
    return OperatingPoint(op.t_w_in, op.t_w_out, op.m_w, op.q, op.m_a * scale, op.m_air_ep * scale,
                          op.t_db, op.t_wb, op.w, op.p)


def evaluate(op: OperatingPoint, methods=None, cfg=None):
    """Return OrderedDict id -> EvapResult.

    If a physical method finds the operating point INFEASIBLE (driving force vanishes, i.e. the EnergyPlus
    operating point lies beyond this model's thermodynamic limit, typically within a few percent of the pinch),
    it is re-solved with the smallest air-flow increase in AIR_SCALES that makes it feasible; status ADJUSTED and
    the factor (r.air_scale) are recorded. If none up to 1.5x works, or the method raises, the MSAT value is
    used (status kept) so totals stay complete.
    """
    cfg = cfg or {}
    ids = methods or list(METHODS)
    out = OrderedDict()
    msat = None
    for mid in ids:
        fn = METHODS[mid][0]
        try:
            r = fn(op, cfg)
            r.air_scale = 1.0
            if r.status == ev.INFEASIBLE and mid in NEEDS_AIR and cfg.get("adjust_air", True):
                for sc in AIR_SCALES:
                    r2 = fn(_with_air(op, sc), cfg)
                    if r2.status in (ev.OK, ev.CLIPPED):
                        r2.status, r2.air_scale = ev.ADJUSTED, sc
                        r = r2
                        break
        except (ValueError, ZeroDivisionError, OverflowError):
            r = ev.EvapResult(0.0, status=ev.INFEASIBLE)
            r.air_scale = float("nan")
        if r.status in (ev.NO_AIRFLOW, ev.INFEASIBLE):
            if msat is None:
                msat = _msat(op, cfg)
            r.evap_kg_s = msat.evap_kg_s if msat.status == ev.OK else ev.latent_only(op.q, op.t_w_in, op.t_w_out)
        out[mid] = r
    return out
