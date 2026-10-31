"""EnergyPlus Python Plugin: multi-method, physics-based cooling tower water use.

Runs beside the stock tower objects (accounting mode: EnergyPlus's thermal solution
is not changed). At the end of each system timestep, for each tower, it reads the
operating point and evaluates every evaporation method in tower_water.methods on it,
then a water balance (drift, chemistry-based blowdown, makeup) for the reference
method. See docs/METHODS.md.

Supported: CoolingTower:VariableSpeed, CoolingTower:VariableSpeed:Merkel.
Use tools/prepare_model.py to generate the config, plugin module and IDF objects.
"""
from __future__ import annotations

import json

try:
    from pyenergyplus.plugin import EnergyPlusPlugin
except ImportError:  # outside EnergyPlus: allows importing compute_tower for tests
    class EnergyPlusPlugin(object):
        def __init__(self):
            pass

from . import evaporation as ev
from . import methods as mt
from . import psychro as ps
from .chemistry import ChemistryModel, limit_code

VS = "CoolingTower:VariableSpeed"
MERKEL = "CoolingTower:VariableSpeed:Merkel"
SUPPORTED = (VS, MERKEL)

# (suffix, units, type) of the non-method outputs, per tower
BALANCE_OUTPUTS = [
    ("Drift", "m3/s", "Averaged"),
    ("Blowdown", "m3/s", "Averaged"),
    ("Makeup", "m3/s", "Averaged"),
    ("MakeupVol", "m3", "Summed"),
    ("Cycles", "", "Averaged"),
    ("CycLimit", "", "Averaged"),
    ("AirMass", "kg/s", "Averaged"),
    ("AirOutT", "C", "Averaged"),
    ("AirOutW", "kgWater/kgDryAir", "Averaged"),
    ("Fog", "", "Averaged"),
    ("MePoppe", "", "Averaged"),
    ("MeMerkel", "", "Averaged"),
    ("NTU", "", "Averaged"),
    ("AirScale", "", "Averaged"),
    ("Status", "", "Averaged"),
]


def outputs(method_ids):
    return [("E_" + m, "m3/s", "Averaged") for m in method_ids] + BALANCE_OUTPUTS


TOWER_VARS = {
    VS: {
        "t_in": "Cooling Tower Inlet Temperature",
        "t_out": "Cooling Tower Outlet Temperature",
        "m_w": "Cooling Tower Mass Flow Rate",
        "q": "Cooling Tower Heat Transfer Rate",
        "afr": "Cooling Tower Air Flow Rate Ratio",
        "cells_on": "Cooling Tower Operating Cells Count",
        "plr": "Cooling Tower Fan Part Load Ratio",
    },
    MERKEL: {
        "t_in": "Cooling Tower Inlet Temperature",
        "t_out": "Cooling Tower Outlet Temperature",
        "m_w": "Cooling Tower Mass Flow Rate",
        "q": "Cooling Tower Heat Transfer Rate",
        "afr": "Cooling Tower Fan Speed Ratio",   # Merkel towers report the air-flow ratio under this name
        "cells_on": "Cooling Tower Operating Cells Count",
    },
}

SITE_VARS = {
    "t_db": "Site Outdoor Air Drybulb Temperature",
    "t_wb": "Site Outdoor Air Wetbulb Temperature",
    "w": "Site Outdoor Air Humidity Ratio",
    "p": "Site Outdoor Air Barometric Pressure",
}


def required_output_variables(config: dict):
    pairs = [("Environment", v) for v in SITE_VARS.values()]
    for t in config["towers"]:
        pairs += [(t["name"], v) for v in TOWER_VARS[t["type"]].values()]
    return pairs


def setup_tower(t: dict, cfg: dict) -> dict:
    """Attach the chemistry model and constant cycles to a tower config dict."""
    t["_chem"] = ChemistryModel.from_library(cfg["water_library"], t["water_source"], t["treatment"],
                                             t.get("fixed_cycles"), t.get("coc_mode"))
    t["_coc"], t["_limit"] = t["_chem"].cycles()
    return t


class TowerWaterPlugin(EnergyPlusPlugin):
    """Base plugin. prepare_model.py sets CONFIG_PATH."""

    CONFIG_PATH = None

    def __init__(self):
        super().__init__()
        with open(self.CONFIG_PATH) as fh:
            self.cfg = json.load(fh)
        self.methods = self.cfg.get("methods") or list(mt.METHODS)
        self.towers = [setup_tower(t, self.cfg) for t in self.cfg["towers"]]
        self.outs = outputs(self.methods)
        self.ready = False

    def _get_handles(self, state) -> bool:
        x = self.api.exchange
        self.site = {k: x.get_variable_handle(state, v, "Environment") for k, v in SITE_VARS.items()}
        missing = [SITE_VARS[k] for k, h in self.site.items() if h < 0]
        for t in self.towers:
            tv = TOWER_VARS[t["type"]]
            t["_in"] = {k: x.get_variable_handle(state, v, t["name"]) for k, v in tv.items()}
            missing += ["%s / %s" % (t["name"], tv[k]) for k, h in t["_in"].items() if h < 0]
            t["_out"] = {s: x.get_global_handle(state, t["prefix"] + "_" + s) for s, _, _ in self.outs}
            missing += [t["prefix"] + "_" + s for s, h in t["_out"].items() if h < 0]
        if missing:
            self.api.runtime.issue_severe(state, "TowerWaterPlugin: missing handles: " + "; ".join(missing))
            return False
        return True

    def on_end_of_system_timestep_before_hvac_reporting(self, state) -> int:
        x = self.api.exchange
        if not self.ready:
            if not x.api_data_fully_ready(state):
                return 0
            if not self._get_handles(state):
                return 1
            self.ready = True
        site = {k: x.get_variable_value(state, h) for k, h in self.site.items()}
        dt_s = x.system_time_step(state) * 3600.0
        for t in self.towers:
            v = {k: x.get_variable_value(state, h) for k, h in t["_in"].items()}
            out = compute_tower(t, v, site, self.cfg, self.methods)
            out["MakeupVol"] = out["Makeup"] * dt_s
            for s, h in t["_out"].items():
                x.set_global_value(state, h, out[s])
        return 0


def air_volume_flow(t: dict, v: dict) -> float:
    """Tower air volume flow [m3/s] for this timestep (all cells).

    VariableSpeed: EnergyPlus reports, in the fan-off and fan-cycling regimes, an air-flow ratio built
      from the free-convection *capacity* fraction. We replace it with a time average of the minimum-speed
      air flow (fan on, fraction = fan part-load ratio) and the free-convection air flow (fan off).
    Merkel: air-flow ratio is 0 in free convection although heat is rejected; use the free-convection air flow.
    """
    design = t["design_air_flow"]
    fc = t.get("free_conv_air_flow", 0.0)
    if t["type"] == MERKEL:
        if v["afr"] > 0.0:
            return v["afr"] * design * _cells_frac(t, v)
        return fc if v["q"] > 0.0 else 0.0
    min_afr = t.get("min_air_flow_ratio", 0.2)
    plr = v.get("plr", 1.0)
    if v["afr"] < min_afr - 1e-6 and plr < 1.0:
        return (plr * min_afr * design) * _cells_frac(t, v) + (1.0 - plr) * fc
    return v["afr"] * design * _cells_frac(t, v)


def _cells_frac(t, v):
    cells = int(t.get("cells", 1))
    on = v["cells_on"] if v["cells_on"] > 0 else cells
    return on / cells


def compute_tower(t: dict, v: dict, site: dict, cfg: dict = None, method_ids=None) -> dict:
    """Multi-method water balance for one tower and one timestep (pure function)."""
    cfg = cfg or {}
    method_ids = method_ids or list(mt.METHODS)
    p, t_db, t_wb, w = site["p"], site["t_db"], site["t_wb"], site["w"]
    vdot = air_volume_flow(t, v)
    rho_a = ps.rho_moist_air(t_db, w, p)
    cells = int(t.get("cells", 1))
    cells_on = v["cells_on"] if v["cells_on"] > 0 else (cells if v["afr"] > 0 else 0)
    m_air_ep = ev.eplus_air_mass_flow(v["afr"], t["design_air_flow"], cells_on, cells, t_db, w, p)
    op = mt.OperatingPoint(v["t_in"], v["t_out"], v["m_w"], v["q"], vdot * rho_a / (1.0 + w), m_air_ep,
                           t_db, t_wb, w, p)
    out = {}
    if v["q"] <= 0.0 or v["m_w"] <= 0.0:
        for m in method_ids:
            out["E_" + m] = 0.0
        res = {}
        status = ev.IDLE
    else:
        res = mt.evaluate(op, method_ids, cfg)
        for m, r in res.items():
            out["E_" + m] = r.evap_kg_s / mt.RHO_REF
        status = res[mt.REFERENCE].status if mt.REFERENCE in res else ev.OK

    ref = res.get(mt.REFERENCE)
    drift = t["design_water_flow"] * t.get("drift_fraction", 0.0) * (op.m_a > 0) * min(
        1.0, vdot / max(t["design_air_flow"], 1e-9)) if v["q"] > 0 else 0.0
    if t["_chem"].mode == "dynamic":
        coc, which = t["_chem"].cycles(t_hot=v["t_in"], t_cold=v["t_out"])
    else:
        coc, which = t["_coc"], t["_limit"]
    e_ref = out.get("E_" + mt.REFERENCE, 0.0)
    blow = max(e_ref / (coc - 1.0) - drift, 0.0)
    ok = ref is not None and ref.status in (ev.OK, ev.ADJUSTED)
    out.update({
        "Drift": drift,
        "Blowdown": blow,
        "Makeup": e_ref + drift + blow,
        "Cycles": coc,
        "CycLimit": float(limit_code(which)),
        "AirMass": op.m_a,
        "AirOutT": ref.t_air_out if ok else 0.0,
        "AirOutW": ref.w_air_out if ok else 0.0,
        "Fog": 1.0 if ok and ref.supersaturated else 0.0,
        "MePoppe": ref.merkel if ok else 0.0,
        "MeMerkel": _nan0(ev.merkel_number_chebyshev(op.t_w_in, op.t_w_out, op.m_w, op.m_a,
                                                     ps.h_air(t_db, w), p)) if ok else 0.0,
        "NTU": _nan0(res["BRAUN"].ntu) if "BRAUN" in res else 0.0,
        "AirScale": _nan0(getattr(ref, "air_scale", 1.0)) if ref is not None else 0.0,
        "Status": float(status),
    })
    return out


def _nan0(x):
    return 0.0 if x != x else x
