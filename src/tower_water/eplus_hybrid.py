"""EnergyPlus Python Plugin: hybrid adiabatic dry cooler bank.

A bank of FluidCooler:TwoSpeed objects shares one OutdoorAir:Node. Each zone timestep the plugin decides wet or
dry mode (tower_water.hybrid.Controller) and, when wet, overrides the node's dry-bulb with the pad-leaving
temperature and keeps the wet-bulb (EMS actuators "Outdoor Air System Node"). EnergyPlus then simulates the
coolers (and any setpoint manager that follows the node) with pre-cooled air. At the end of each system
timestep the plugin books pad evaporation from the coolers' actual air flow (recovered from fan power),
bleed or runoff, makeup and the pad fan penalty.

Unlike tower_water.eplus_plugin (accounting mode), this plugin changes the EnergyPlus solution.
Use tools/prepare_hybrid.py to generate the config, plugin module and IDF objects.
"""
from __future__ import annotations

import json

try:
    from pyenergyplus.plugin import EnergyPlusPlugin
except ImportError:  # outside EnergyPlus
    class EnergyPlusPlugin(object):
        def __init__(self):
            pass

from . import hybrid as hy
from . import psychro as ps
from .chemistry import ChemistryModel

PREFIX = "HC"
OUTPUTS = [
    ("Wet", "", "Averaged"),
    ("PreT", "C", "Averaged"),
    ("PreW", "kgWater/kgDryAir", "Averaged"),
    ("Eps", "", "Averaged"),
    ("Air", "kg/s", "Averaged"),
    ("Heat", "W", "Averaged"),
    ("FanPower", "W", "Averaged"),
    ("FanPenalty", "W", "Averaged"),
    ("Evap", "m3/s", "Averaged"),
    ("Bleed", "m3/s", "Averaged"),
    ("Makeup", "m3/s", "Averaged"),
    ("MakeupVol", "m3", "Summed"),
    ("Cycles", "", "Averaged"),
]
COOLER_VARS = {"q": "Cooling Tower Heat Transfer Rate", "p_fan": "Cooling Tower Fan Electricity Rate",
               "t_in": "Cooling Tower Inlet Temperature", "t_out": "Cooling Tower Outlet Temperature"}
SITE_VARS = {"t_db": "Site Outdoor Air Drybulb Temperature", "t_wb": "Site Outdoor Air Wetbulb Temperature",
             "w": "Site Outdoor Air Humidity Ratio", "p": "Site Outdoor Air Barometric Pressure"}
RHO_W = ps.rho_water(20.0)


def required_output_variables(cfg):
    pairs = [("Environment", v) for v in SITE_VARS.values()]
    for c in cfg["coolers"]:
        pairs += [(c["name"], v) for v in COOLER_VARS.values()]
    return pairs


class HybridState:
    """Pure-Python state machine shared by the plugin and the tests."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.pad = hy.PadConfig(**cfg.get("pad", {}))
        self.ctrl = hy.Controller(**cfg.get("controller", {}))
        chem = ChemistryModel.from_library(cfg["water_library"], cfg["water_source"], cfg["treatment"],
                                           cfg.get("fixed_cycles"), cfg.get("coc_mode"))
        self.cycles = chem.cycles()[0]
        self.wet = False
        self.pre = None
        self.amb = None

    def begin_timestep(self, t_db, t_wb, w, p):
        """Decide the mode; return (node dry-bulb, node wet-bulb) to impose."""
        self.amb = (t_db, t_wb, w, p)
        self.wet = self.ctrl.step(t_db, t_wb)
        if self.wet:
            self.pre = hy.precool(t_db, w, p, self.pad.eps_design)
            return self.pre.t_db, t_wb
        self.pre = None
        return t_db, t_wb

    def end_timestep(self, coolers, dt_s):
        """coolers: list of (cooler cfg, {q, p_fan, ...}). Returns output dict."""
        t_db, t_wb, w, p = self.amb
        pad = hy.PadConfig(**dict(self.pad.__dict__, v_design=0.0))   # constant eps: consistent with actuation
        tot = hy.PadResult()
        heat = fan = 0.0
        for c, v in coolers:
            states = hy.fan_states(v["p_fan"], c["p_high"], c["p_low"], c["v_high"], c["v_low"])
            r = hy.pad_timestep(states, self.wet, t_db, w, p, pad)
            tot.evap_kg_s += r.evap_kg_s
            tot.air_kg_s += r.air_kg_s
            tot.fan_penalty_w += r.fan_penalty_w
            heat += max(v["q"], 0.0)
            fan += v["p_fan"]
        makeup, bleed = hy.water_supply(tot.evap_kg_s, self.pad, self.cycles)
        return {
            "Wet": 1.0 if self.wet else 0.0,
            "PreT": self.pre.t_db if self.pre else t_db,
            "PreW": self.pre.w if self.pre else w,
            "Eps": self.pad.eps_design if self.wet else 0.0,
            "Air": tot.air_kg_s, "Heat": heat, "FanPower": fan, "FanPenalty": tot.fan_penalty_w,
            "Evap": tot.evap_kg_s / RHO_W, "Bleed": bleed / RHO_W, "Makeup": makeup / RHO_W,
            "MakeupVol": makeup / RHO_W * dt_s, "Cycles": self.cycles if self.pad.system == "media" else 0.0,
        }


class HybridCoolerPlugin(EnergyPlusPlugin):
    CONFIG_PATH = None

    def __init__(self):
        super().__init__()
        with open(self.CONFIG_PATH) as fh:
            self.cfg = json.load(fh)
        self.st = HybridState(self.cfg)
        self.ready = False

    def _handles(self, state):
        x = self.api.exchange
        node = self.cfg["node"]
        self.h_db = x.get_actuator_handle(state, "Outdoor Air System Node", "Drybulb Temperature", node)
        self.h_wb = x.get_actuator_handle(state, "Outdoor Air System Node", "Wetbulb Temperature", node)
        self.site = {k: x.get_variable_handle(state, v, "Environment") for k, v in SITE_VARS.items()}
        self.cool = [(c, {k: x.get_variable_handle(state, v, c["name"]) for k, v in COOLER_VARS.items()})
                     for c in self.cfg["coolers"]]
        self.outs = {s: x.get_global_handle(state, PREFIX + "_" + s) for s, _, _ in OUTPUTS}
        missing = []
        if self.h_db < 0 or self.h_wb < 0:
            missing.append("actuators on node " + node)
        missing += [SITE_VARS[k] for k, h in self.site.items() if h < 0]
        missing += ["%s / %s" % (c["name"], COOLER_VARS[k]) for c, hs in self.cool for k, h in hs.items() if h < 0]
        missing += [PREFIX + "_" + s for s, h in self.outs.items() if h < 0]
        if missing:
            self.api.runtime.issue_severe(state, "HybridCoolerPlugin: missing handles: " + "; ".join(missing))
            return False
        return True

    def _ensure(self, state):
        if self.ready:
            return True
        if not self.api.exchange.api_data_fully_ready(state):
            return False
        if not self._handles(state):
            raise RuntimeError("HybridCoolerPlugin: missing handles (see severe error)")
        self.ready = True
        return True

    def on_begin_timestep_before_predictor(self, state) -> int:
        if not self._ensure(state):
            return 0
        x = self.api.exchange
        s = {k: x.get_variable_value(state, h) for k, h in self.site.items()}
        db, wb = self.st.begin_timestep(s["t_db"], s["t_wb"], s["w"], s["p"])
        x.set_actuator_value(state, self.h_db, db)
        x.set_actuator_value(state, self.h_wb, wb)
        return 0

    def on_end_of_system_timestep_before_hvac_reporting(self, state) -> int:
        if not self.ready or self.st.amb is None:
            return 0
        x = self.api.exchange
        coolers = [(c, {k: x.get_variable_value(state, h) for k, h in hs.items()}) for c, hs in self.cool]
        out = self.st.end_timestep(coolers, x.system_time_step(state) * 3600.0)
        for s, h in self.outs.items():
            x.set_global_value(state, h, out[s])
        return 0
