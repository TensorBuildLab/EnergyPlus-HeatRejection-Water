#!/usr/bin/env python3
"""Summarize an annual run of datacenter_chiller_tower*.idf or datacenter_chiller_hybrid*.idf (stdlib only).

    python3 models/summarize_dc_run.py RUN_OUT_DIR [--idf MODEL.idf] [--json out.json]

RUN_OUT_DIR is the EnergyPlus output directory (run with -r so eplusout.csv exists).
Reports PUE, end uses, tower water balance, WUE, chiller loading, temperatures, unmet hours.
Hybrid dry-cooler models (FluidCooler:TwoSpeed "Hybrid Cooler N"): no tower water; reports cooler
heat, fan energy and speed stage, cooler air inlet node vs outdoor air, condenser supply vs setpoint.
Chiller curve validity: hours (and timestep-hours, when timestep output exists) in which a running
chiller is outside the min/max limits of its performance curves.  The limits are read from the model
IDF: --idf, or the single *.idf in the parent of RUN_OUT_DIR (the runs/<site>/model.idf convention).
"""
import argparse
import csv
import json
import os
import re
import statistics as st
import glob

J2KWH = 1 / 3.6e6


def load(outdir):
    with open(os.path.join(outdir, "eplusout.csv"), newline="") as f:
        r = csv.reader(f)
        hdr = next(r)
        rows = [row for row in r]
    hourly = {h: [] for h in hdr}
    runperiod = {}
    for row in rows:
        for h, v in zip(hdr, row):
            if "(RunPeriod)" in h:
                if v.strip():
                    runperiod[h] = float(v)
            elif h != "Date/Time" and v.strip():
                hourly[h].append(float(v))
    return hdr, hourly, runperiod


def col(hourly, pattern):
    ks = [k for k in hourly if re.search(pattern, k) and hourly[k]]
    return ks


# ------------------------------------------------------------------ chiller curve limits from the IDF
def _idf_objects(path):
    t = open(path, encoding="latin-1", errors="ignore").read()
    t = re.sub(r"!.*", "", t)
    return [[x.strip() for x in o.split(",")] for o in t.split(";") if o.strip()]


def chiller_curve_limits(idf):
    """{chiller name (upper): {'type', 'chw': (lo, hi), 'cond': (lo, hi), 'cond_var', 'plr': (lo, hi)}}.
    Limits are the intersection over CAPFT, EIRFT and EIRFPLR (EnergyPlus clamps each curve input)."""
    objs = _idf_objects(idf)
    curves = {f[1].upper(): f for f in objs if f[0].lower().startswith("curve:")}

    def lim(name):
        f = curves.get(name.upper())
        if f is None:
            return None
        c = f[0].lower()
        try:
            if c == "curve:biquadratic":
                return [float(x) for x in f[8:12]]
            if c == "curve:bicubic":
                return [float(x) for x in f[12:16]]
            if c in ("curve:quadratic", "curve:cubic"):
                k = 5 if c == "curve:quadratic" else 6
                return [float(x) for x in f[k:k + 2]]
        except ValueError:
            return None
        return None
    out = {}
    for f in objs:
        c = f[0].lower()
        if c not in ("chiller:electric:eir", "chiller:electric:reformulatedeir"):
            continue
        cap, eir = lim(f[8]), lim(f[9])
        if c == "chiller:electric:eir":
            plr = lim(f[10])                        # f(PLR)
            plr_l = plr[0:2] if plr else None
            cond_l = None
            var = "entering condenser"
        else:
            plr = lim(f[11])                        # f(LCW, PLR) bicubic
            plr_l = plr[2:4] if plr else None
            cond_l = plr[0:2] if plr else None
            var = "leaving condenser"
        if not cap or not eir:
            continue
        chw = (max(cap[0], eir[0]), min(cap[1], eir[1]))
        cond = [max(cap[2], eir[2]), min(cap[3], eir[3])]
        if cond_l:
            cond = [max(cond[0], cond_l[0]), min(cond[1], cond_l[1])]
        out[f[1].upper()] = {"type": f[0], "chw": chw, "cond": tuple(cond), "cond_var": var,
                             "plr": tuple(plr_l) if plr_l else None,
                             "curves": f[8:10] + ([f[10]] if c == "chiller:electric:eir" else [f[11]])}
    return out


def find_idf(outdir):
    c = glob.glob(os.path.join(os.path.dirname(os.path.abspath(outdir).rstrip("/")), "*.idf"))
    return c[0] if len(c) == 1 else None


def curve_hours(H, name, L, freq, tol=0.01):
    """Hours a running chiller (PLR > 1e-3) is outside its curve limits, by variable and side."""
    g = lambda v: H.get(f"{name}:{v}({freq})", [])
    plr = g("Chiller Part Load Ratio []")
    chw = g("Chiller Evaporator Outlet Temperature [C]")
    cond = g("Chiller Condenser Outlet Temperature [C]" if L["cond_var"] == "leaving condenser"
             else "Chiller Condenser Inlet Temperature [C]")
    if not (plr and chw and cond):
        return None
    dt = 1.0 if freq == "Hourly" else 8760.0 / len(plr)
    r = {"on": 0.0, "CHW leaving < min": 0.0, "CHW leaving > max": 0.0, f"{L['cond_var']} < min": 0.0,
         f"{L['cond_var']} > max": 0.0, "PLR < min": 0.0, "PLR > max": 0.0, "any limit": 0.0,
         f"max {L['cond_var']} T when on [C]": None, f"max excess above {L['cond_var']} limit [K]": 0.0}
    tmax = None
    flags = []
    for p, a, b in zip(plr, chw, cond):
        flags.append(False)
        if p <= 1e-3:
            continue
        r["on"] += dt
        out = False
        if a < L["chw"][0] - tol: r["CHW leaving < min"] += dt; out = True
        if a > L["chw"][1] + tol: r["CHW leaving > max"] += dt; out = True
        if b < L["cond"][0] - tol: r[f"{L['cond_var']} < min"] += dt; out = True
        if b > L["cond"][1] + tol: r[f"{L['cond_var']} > max"] += dt; out = True
        if L["plr"]:
            if p < L["plr"][0] - 1e-3: r["PLR < min"] += dt; out = True
            if p > L["plr"][1] + 1e-3: r["PLR > max"] += dt; out = True
        if out:
            r["any limit"] += dt
            flags[-1] = True
        tmax = b if tmax is None else max(tmax, b)
    r[f"max {L['cond_var']} T when on [C]"] = tmax
    r[f"max excess above {L['cond_var']} limit [K]"] = max(0.0, (tmax or 0) - L["cond"][1])
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flags, dt


def summarize(outdir, idf=None):
    hdr, H, R = load(outdir)
    hybrid = bool(col(H, r"^HYBRID COOLER \d+:Cooling Tower Heat Transfer Rate"))
    idf = idf or find_idf(outdir)
    fc_fan = {}                                  # FluidCooler:TwoSpeed high-speed fan power [W] from the IDF
    if idf and os.path.exists(idf):
        for f in _idf_objects(idf):
            if f[0].lower() == "fluidcooler:twospeed" and len(f) > 16:
                try:
                    fc_fan[f[1].upper()] = float(f[16])
                except ValueError:
                    pass
    def rp(m):
        # run-period meter value; falls back to the sum of the hourly meter (ReadVarsESO can drop the
        # last RunPeriod column of a wide CSV that mixes TimeStep and Hourly output)
        u = "m3" if (m.endswith("Water") or "Water:" in m) else "J"
        v = R.get(f"{m} [{u}](RunPeriod)")
        if v is None and H.get(f"{m} [{u}](Hourly)"):
            v = sum(H[f"{m} [{u}](Hourly)"])
        v = v or 0.0
        return v * J2KWH if u == "J" else v
    s = {}
    fac = rp("Electricity:Facility")
    cpu, fan, ups = rp("ITE-CPU:InteriorEquipment:Electricity"), rp("ITE-Fans:InteriorEquipment:Electricity"), rp("ITE-UPS:InteriorEquipment:Electricity")
    it = cpu + fan
    s["IT energy (CPU+server fans) [MWh]"] = it / 1e3
    s["Mean IT power [kW]"] = it / 8760
    s["Facility electricity [MWh]"] = fac / 1e3
    s["PUE (facility / IT)"] = fac / it
    for lab, m in [("UPS losses", "ITE-UPS:InteriorEquipment:Electricity"), ("Chillers", "Cooling:Electricity"),
                   ("Dry-cooler fans" if hybrid else "Tower fans", "HeatRejection:Electricity"), ("Pumps", "Pumps:Electricity"),
                   ("CRAH fans", "Fans:Electricity"), ("Lighting", "InteriorLights:Electricity")]:
        s[f"{lab} [MWh]"] = rp(m) / 1e3
        s[f"{lab} share of IT [%]"] = 100 * rp(m) / it
    # hourly PUE range
    fH = H["Electricity:Facility [J](Hourly)"]
    iH = [a + b for a, b in zip(H["ITE-CPU:InteriorEquipment:Electricity [J](Hourly)"], H["ITE-Fans:InteriorEquipment:Electricity [J](Hourly)"])]
    pue_h = [a / b for a, b in zip(fH, iH)]
    s["Hourly PUE min/mean/max"] = (min(pue_h), st.mean(pue_h), max(pue_h))
    # monthly PUE
    n = len(fH)
    mdays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    mp, i0 = [], 0
    for d in mdays:
        i1 = i0 + 24 * d
        mp.append(round(sum(fH[i0:i1]) / sum(iH[i0:i1]), 3))
        i0 = i1
    s["Monthly PUE"] = mp

    # towers
    towers = sorted({k.split(":")[0] for k in col(H, r"Cooling Tower Heat Transfer Rate \[W\]\(Hourly\)")})
    tw = {}
    for t in towers:
        g = lambda v: H.get(f"{t}:{v}", [])
        q = g("Cooling Tower Heat Transfer Rate [W](Hourly)")
        d = {
            "heat rejected [MWh]": sum(q) * 3600 * J2KWH / 1e3,
            "peak heat rejection [kW]": max(q) / 1e3,
            "evaporation [m3]": sum(g("Cooling Tower Water Evaporation Volume Flow Rate [m3/s](Hourly)")) * 3600,
            "drift [m3]": sum(g("Cooling Tower Water Drift Volume Flow Rate [m3/s](Hourly)")) * 3600,
            "blowdown [m3]": sum(g("Cooling Tower Water Blowdown Volume Flow Rate [m3/s](Hourly)")) * 3600,
            "makeup [m3]": sum(g("Cooling Tower Make Up Water Volume [m3](Hourly)")),
            "fan energy [MWh]": sum(g("Cooling Tower Fan Electricity Energy [J](Hourly)")) * J2KWH / 1e3,
            "hours with water flow": sum(1 for m in g("Cooling Tower Mass Flow Rate [kg/s](Hourly)") if m > 1e-3),
            "hours with zero flow but evaporation>0": sum(1 for m, e in zip(g("Cooling Tower Mass Flow Rate [kg/s](Hourly)"),
                                                          g("Cooling Tower Water Evaporation Volume Flow Rate [m3/s](Hourly)")) if m <= 1e-3 and e > 0),
        }
        fsr = g("Cooling Tower Fan Speed Ratio [](Hourly)")
        if fsr:
            d["fan speed ratio min/mean/max"] = (min(fsr), st.mean(fsr), max(fsr))
            bins = [0, 0.2001, 0.4, 0.6, 0.8, 1.0001]
            d["fan speed ratio hours by bin (0-0.2,..0.8-1)"] = [sum(1 for x in fsr if lo <= x < hi) for lo, hi in zip(bins[:-1], bins[1:])]
        cells = g("Cooling Tower Operating Cells Count [](Hourly)")
        if cells:
            d["operating cells min/mean/max"] = (min(cells), st.mean(cells), max(cells))
        tin, tout = g("Cooling Tower Inlet Temperature [C](Hourly)"), g("Cooling Tower Outlet Temperature [C](Hourly)")
        d["inlet T min/max [C]"] = (min(tin), max(tin))
        d["outlet T min/max [C]"] = (min(tout), max(tout))
        tw[t] = d
    if hybrid:
        for t, d in tw.items():
            for k in [k for k in d if k.startswith(("evaporation", "drift", "blowdown", "makeup", "hours with zero flow"))]:
                del d[k]
            # two-speed stage from fan power (E+ cycles low<->off and high<->low within a timestep)
            for freq in ("TimeStep", "Hourly"):
                fp = H.get(f"{t}:Cooling Tower Fan Electricity Rate [W]({freq})", [])
                if fp:
                    break
            if fp:
                dt = 1.0 if freq == "Hourly" else 8760.0 / len(fp)
                phi = fc_fan.get(t.upper())
                if phi:
                    d["design high-speed fan power [kW]"] = phi / 1e3
                    d[f"hours at full high-speed fan [{freq} data]"] = round(dt * sum(1 for x in fp if x >= 0.999 * phi), 2)
                d["max fan power [kW]"] = max(fp) / 1e3
                d["mean fan power [kW]"] = st.mean(fp) / 1e3
    s["Towers" if not hybrid else "Hybrid coolers"] = tw
    if not hybrid:
        evap = sum(d["evaporation [m3]"] for d in tw.values())
        mk = sum(d["makeup [m3]"] for d in tw.values())
        s["Tower evaporation total [m3]"] = evap
        s["Tower makeup total [m3]"] = mk
        s["Water:Facility meter [m3]"] = R.get("Water:Facility [m3](RunPeriod)")
        s["WUE site (makeup / IT) [L/kWh]"] = mk * 1000 / it
        s["Evaporation / IT [L/kWh]"] = evap * 1000 / it
    else:
        s["Heat-rejection water use"] = "none in EnergyPlus (dry coolers); pad water comes from the plugin"
        s["Dry-cooler fan energy total [MWh]"] = sum(d["fan energy [MWh]"] for d in tw.values())
    qt = sum(d["heat rejected [MWh]"] for d in tw.values())

    # chillers
    ch = sorted({k.split(":")[0] for k in col(H, r"Chiller Part Load Ratio")})
    evapQ = elecC = condQ = 0.0
    cs = {}
    on_counts = [0] * n
    for c in ch:
        g = lambda v: H[f"{c}:{v}"]
        plr = g("Chiller Part Load Ratio [](Hourly)")
        e = g("Chiller Electricity Rate [W](Hourly)")
        qe = g("Chiller Evaporator Cooling Rate [W](Hourly)")
        qc = g("Chiller Condenser Heat Transfer Rate [W](Hourly)")
        on = [p for p in plr if p > 1e-3]
        for i, p in enumerate(plr):
            if p > 1e-3:
                on_counts[i] += 1
        evapQ += sum(qe); elecC += sum(e); condQ += sum(qc)
        cs[c] = {"hours on": len(on), "PLR mean/min/max when on": (st.mean(on), min(on), max(on)) if on else None,
                 "annual COP": sum(qe) / sum(e) if sum(e) > 0 else None,
                 "ECW min/max when on [C]": (min(t for t, p in zip(g("Chiller Condenser Inlet Temperature [C](Hourly)"), plr) if p > 1e-3),
                                             max(t for t, p in zip(g("Chiller Condenser Inlet Temperature [C](Hourly)"), plr) if p > 1e-3)) if on else None}
    s["Chillers"] = cs
    s["Hours by number of chillers running [0,1,2,3]"] = [on_counts.count(k) for k in range(4)]
    s["Plant annual COP (evap Q / chiller elec)"] = evapQ / elecC
    s["Dry-cooler heat rejected [MWh]" if hybrid else "Tower heat rejected [MWh]"] = qt
    s["Chiller condenser heat [MWh]"] = condQ * 3600 * J2KWH / 1e3
    s["Chiller evap Q + chiller elec [MWh]"] = (evapQ + elecC) * 3600 * J2KWH / 1e3
    s["IT + UPS + lights + CRAH fans [MWh] (zone/air-side gains)"] = (it + ups + rp("InteriorLights:Electricity") + rp("Fans:Electricity")) / 1e3
    s[("Cooler" if hybrid else "Tower") + " Q / (IT + chiller elec)"] = qt * 1e3 / (it + rp("Cooling:Electricity"))
    s["Fan energy / heat rejected [%]"] = 100 * rp("HeatRejection:Electricity") / (qt * 1e3) if qt > 0 else None

    # chiller performance-curve validity
    if idf and os.path.exists(idf):
        lims = chiller_curve_limits(idf)
        cv = {}
        union = {}
        for c in ch:
            L = lims.get(c.upper())
            if not L:
                continue
            e = {"curves": ", ".join(L["curves"]), "valid CHW leaving [C]": L["chw"],
                 f"valid {L['cond_var']} [C]": L["cond"], "valid PLR": L["plr"]}
            for freq in ("TimeStep", "Hourly"):
                res = curve_hours(H, c, L, freq)
                if res:
                    r, flags, dt = res
                    e[f"hours outside limits ({freq} data)"] = r
                    u = union.setdefault(freq, [[], dt])
                    u[0] = [x or y for x, y in zip(u[0], flags)] if u[0] else flags
            cv[c] = e
        freq = "TimeStep" if "TimeStep" in union else ("Hourly" if union else None)
        if freq:
            s[f"Chiller hours outside curve limits (any running chiller, {freq} data)"] = round(
                union[freq][1] * sum(union[freq][0]), 2)
        s["Chiller curve validity (from " + os.path.basename(idf) + ")"] = cv
    else:
        s["Chiller curve validity"] = "not evaluated (give --idf)"

    hx = col(H, r"Fluid Heat Exchanger Heat Transfer Rate")
    if hx:
        q = H[hx[0]]
        s["WSE heat transfer [MWh]"] = sum(q) * 3600 * J2KWH / 1e3
        s["WSE share of chiller-plant cooling [%]"] = 100 * sum(q) / (sum(q) + evapQ) if (sum(q) + evapQ) > 0 else 0
        s["WSE hours active (>10 kW)"] = sum(1 for x in q if x > 1e4)
        s["Full free-cooling hours (no chiller)"] = on_counts.count(0)
    # temperatures
    def rng(k):
        v = H[k]
        return (round(min(v), 2), round(st.mean(v), 2), round(max(v), 2))
    s["CHW supply T min/mean/max [C]"] = rng("CHW SUPPLY OUTLET NODE:System Node Temperature [C](Hourly)")
    s["CHW return T min/mean/max [C]"] = rng("CHW SUPPLY INLET NODE:System Node Temperature [C](Hourly)")
    s["CW supply T min/mean/max [C]"] = rng("CW SUPPLY OUTLET NODE:System Node Temperature [C](Hourly)")
    s["CW return T min/mean/max [C]"] = rng("CW SUPPLY INLET NODE:System Node Temperature [C](Hourly)")
    cws, cwsp = H["CW SUPPLY OUTLET NODE:System Node Temperature [C](Hourly)"], H["CW SUPPLY OUTLET NODE:System Node Setpoint Temperature [C](Hourly)"]
    s["Hours CW supply > setpoint + 0.5 K"] = sum(1 for a, b in zip(cws, cwsp) if a > b + 0.5)
    s["Hours CW supply < setpoint - 0.5 K"] = sum(1 for a, b in zip(cws, cwsp) if a < b - 0.5)
    s["CW supply setpoint min/mean/max [C]"] = rng("CW SUPPLY OUTLET NODE:System Node Setpoint Temperature [C](Hourly)")
    if hybrid:
        ts = "CW SUPPLY OUTLET NODE:System Node Temperature [C](TimeStep)"
        tsp = "CW SUPPLY OUTLET NODE:System Node Setpoint Temperature [C](TimeStep)"
        if H.get(ts) and H.get(tsp):
            dt = 8760.0 / len(H[ts])
            ex = [a - b for a, b in zip(H[ts], H[tsp])]
            s["Hours CW supply > setpoint + 0.5 K (timestep data)"] = round(dt * sum(1 for x in ex if x > 0.5), 2)
            s["Hours CW supply > setpoint + 2 K (timestep data)"] = round(dt * sum(1 for x in ex if x > 2.0), 2)
            s["Max CW supply - setpoint [K] (timestep data)"] = round(max(ex), 2)
        node = "HYBRID COOLER AIR INLET:System Node Temperature [C](Hourly)"
        odb = H.get("Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)", [])
        if H.get(node) and odb:
            s["Cooler air inlet node DB min/mean/max [C]"] = rng(node)
            s["Outdoor DB min/mean/max [C]"] = (round(min(odb), 1), round(st.mean(odb), 1), round(max(odb), 1))
            s["Mean outdoor DB - cooler inlet DB [K] (pre-cooling)"] = round(st.mean(a - b for a, b in zip(odb, H[node])), 3)
        nwb = "HYBRID COOLER AIR INLET:System Node Wetbulb Temperature [C](Hourly)"
        if H.get(nwb):
            s["Cooler air inlet node WB min/mean/max [C]"] = rng(nwb)
        s["Hours CW supply at setpoint max (pinned)"] = sum(1 for b in cwsp if b >= max(cwsp) - 1e-6)
        s["Hours CW supply setpoint at min"] = sum(1 for b in cwsp if b <= min(cwsp) + 1e-6)
    chws = H["CHW SUPPLY OUTLET NODE:System Node Temperature [C](Hourly)"]
    s["Hours CHW supply > 10.5 C"] = sum(1 for a in chws if a > 10.5)
    owb = H["Environment:Site Outdoor Air Wetbulb Temperature [C](Hourly)"]
    s["Outdoor WB min/mean/max [C]"] = (round(min(owb), 1), round(st.mean(owb), 1), round(max(owb), 1))
    for z in ("DATAHALL1", "DATAHALL2"):
        s[f"{z} zone T min/mean/max [C]"] = rng(f"{z}:Zone Air Temperature [C](Hourly)")
        s[f"{z} ITE inlet T min/mean/max [C]"] = rng(f"{z} ITE:ITE Air Inlet Dry-Bulb Temperature [C](Hourly)")
        s[f"{z} hours zone T > 31.5 C"] = sum(1 for x in H[f"{z}:Zone Air Temperature [C](Hourly)"] if x > 31.5)
        s[f"{z} ITE inlet out-of-range hours (class A1)"] = sum(H[f"{z} ITE:ITE Air Inlet Operating Range Exceeded Time [hr](Hourly)"])
    for k in col(H, r"Plant Supply Side Unmet Demand Rate"):
        v = H[k]
        s[k.split(":")[0] + " hours with unmet demand > 1 kW"] = sum(1 for x in v if abs(x) > 1000)
    # tabular unmet hours
    tbl = os.path.join(outdir, "eplustbl.csv")
    if os.path.exists(tbl):
        txt = open(tbl, errors="ignore").read()
        m = re.search(r"Time Setpoint Not Met During Occupied Cooling,([\d.]+)", txt)
        m2 = re.search(r"Time Setpoint Not Met During Occupied Heating,([\d.]+)", txt)
        if m:
            s["Unmet cooling setpoint hours (facility, table)"] = float(m.group(1))
    return s


def fmt(v):
    if isinstance(v, float):
        return f"{v:,.3f}" if abs(v) < 100 else f"{v:,.1f}"
    if isinstance(v, (tuple, list)):
        return "(" + ", ".join(fmt(x) for x in v) + ")"
    return str(v)


def show(s, ind=""):
    for k, v in s.items():
        if isinstance(v, dict):
            print(f"{ind}{k}:")
            show(v, ind + "    ")
        else:
            print(f"{ind}{k}: {fmt(v)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--idf", help="model IDF (for chiller curve limits); default: the single *.idf next to outdir")
    ap.add_argument("--json")
    a = ap.parse_args()
    s = summarize(a.outdir, a.idf)
    show(s)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(s, f, indent=1, default=str)
