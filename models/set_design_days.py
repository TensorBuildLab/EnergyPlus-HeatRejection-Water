#!/usr/bin/env python3
"""Make an IDF climate-specific for sizing: replace its design days with those of a .ddy file.

    python3 models/set_design_days.py IN.idf SITE.ddy OUT.idf [--no-tower-update] [--pad-effectiveness 0.85]

What it does (stdlib only, Python 3.8+):
  1. Removes every SizingPeriod:DesignDay and Site:Location object from IN.idf.
  2. Inserts the .ddy's Site:Location and three design days:
       - Annual cooling 0.4 % dry-bulb  => mean coincident wet-bulb  ("Ann Clg .4% Condns DB=>MWB")
       - Annual cooling 0.4 % wet-bulb  => mean coincident dry-bulb  ("Ann Clg .4% Condns WB=>MDB")
         (the "evaporation" design condition; heat-rejection equipment is sized on it)
       - Annual heating 99.6 % dry-bulb ("Ann Htg 99.6% Condns DB")
  3. Unless --no-tower-update: sets every CoolingTower:VariableSpeed:Merkel
     "Design Inlet Air Dry-Bulb / Wet-Bulb Temperature" to the WB=>MDB condition, and every
     condenser-type Sizing:Plant "Design Loop Exit Temperature" to design WB + tower design
     approach (approach read from the first Merkel tower, default 3.9 K).  The Merkel tower
     solves its design UA from these values, so the tower is sized for this climate.

  4. Hybrid adiabatic dry-cooler models (FluidCooler:TwoSpeed objects carrying a
     "! hybrid-design:" comment, written by build_datacenter_idf.py --heat-rejection hybrid), unless
     --no-tower-update: the coolers are sized for WET operation at the 0.4 % DB=>MWB condition:
       Design Entering Air Temperature   = DB - eps (DB - MWB)          (eps = --pad-effectiveness)
       Design Entering Air Wet-bulb      = MWB
       Design Entering Water Temperature = entering air + approach + range
       High Fan Speed Air Flow Rate      = Q_nom / (rho cp dT_air)  at the entering air state and
                                           site pressure (EnergyPlus' own autosizing of this field
                                           is not physical, see DATACENTER_MODEL.md section 6)
       Low Fan Speed Air Flow Rate       = 0.5 x high-speed air flow
       Low Speed Nominal Capacity        = capacity that makes EnergyPlus size UA_low = low_UA_frac x UA_high
                                           (hard values: E+ 22.2 cannot combine a hard-sized low-speed
                                           capacity with an autocalculated low-speed air flow)
     and the condenser Sizing:Plant Design Loop Exit Temperature = entering air + approach.
     Nominal capacity, water flow and fan power are not climate dependent and are left alone.

The new objects are placed between marker comments so the script can be re-applied to its
own output.  Objects that are not touched keep their original text and comments.
"""
import argparse
import re
import sys

MARK_BEGIN = "! >>> set_design_days.py: location and design days (auto-generated) >>>"
MARK_END = "! <<< set_design_days.py <<<"

PATTERNS = {
    "cooling_db": r"Ann Clg \.4% Condns DB=>MC?WB",
    "cooling_wb": r"Ann Clg \.4% Condns WB=>MC?DB",
    "heating": r"Ann Htg 99\.6% Condns DB\s*$",
}

MERKEL = "coolingtower:variablespeed:merkel"
MERKEL_DB, MERKEL_WB, MERKEL_APPROACH = 25, 26, 27   # 0-based index; 0 = class name, 1 = Name
FLUIDCOOLER2 = "fluidcooler:twospeed"
# 0-based field indices of FluidCooler:TwoSpeed (0 = class name)
FC_QNOM, FC_QLOW, FC_EWT, FC_EAT, FC_EAWB, FC_VW, FC_VAIR, FC_VAIR_LO = 8, 9, 11, 12, 13, 14, 15, 17
HYB_LOW_AIR_FRAC = 0.5      # low-speed / high-speed air flow (E+ default sizing factor)
HYB_TAG = "! hybrid-design:"
PAD_EFF_DEFAULT = 0.85


# ------------------------------------------------------------------ psychrometrics (stdlib, SI)
def p_sat(t):
    """Saturation vapour pressure [Pa], ASHRAE Handbook-Fundamentals 2017 ch. 1 eq. 5/6 (Hyland-Wexler)."""
    import math
    T = t + 273.15
    if t < 0:
        c = (-5.6745359e3, 6.3925247, -9.6778430e-3, 6.2215701e-7, 2.0747825e-9, -9.4840240e-13, 4.1635019)
        return math.exp(c[0] / T + c[1] + c[2] * T + c[3] * T**2 + c[4] * T**3 + c[5] * T**4 + c[6] * math.log(T))
    c = (-5.8002206e3, 1.3914993, -4.8640239e-2, 4.1764768e-5, -1.4452093e-8, 6.5459673)
    return math.exp(c[0] / T + c[1] + c[2] * T + c[3] * T**2 + c[4] * T**3 + c[5] * math.log(T))


def w_from_db_wb(db, wb, p):
    """Humidity ratio [kg/kg] from dry-bulb, wet-bulb [C] and pressure [Pa] (ASHRAE 2017 ch. 1 eq. 33)."""
    ws = 0.621945 * p_sat(wb) / (p - p_sat(wb))
    return ((2501.0 - 2.326 * wb) * ws - 1.006 * (db - wb)) / (2501.0 + 1.86 * db - 4.186 * wb)


def site_pressure(elev_m):
    """Standard-atmosphere barometric pressure [Pa] (as EnergyPlus' Site:Location default)."""
    return 101325.0 * (1.0 - 2.25577e-5 * elev_m) ** 5.2559


def ep_fluid_cooler_q(ua, m_w, cp_w, v_air, rho_a, cp_a, dt_in):
    """Heat rate [W] of the EnergyPlus 22.2 FluidCooler model (FluidCoolers.cc CalcFluidCoolerOutlet:
    cross-flow e-NTU with eta = NTU^0.22) for inlet temperature difference dt_in = Tw,in - Ta,in."""
    import math
    cw, ca = m_w * cp_w, v_air * rho_a * cp_a
    cmin, cmax = min(cw, ca), max(cw, ca)
    cr, ntu = cmin / cmax, ua / cmin
    eta = ntu ** 0.22
    a = cr * ntu / eta
    return (1.0 - math.exp((math.exp(-a) - 1.0) / (cr / eta))) * cmin * dt_in


def ep_solve_ua(q, m_w, cp_w, v_air, rho_a, cp_a, dt_in):
    """UA [W/K] that EnergyPlus' NominalCapacity sizing finds for capacity q (bisection)."""
    lo, hi = 1e-4 * q, 1.0 * q          # same bracket as FluidCoolers.cc
    if ep_fluid_cooler_q(hi, m_w, cp_w, v_air, rho_a, cp_a, dt_in) < q:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if ep_fluid_cooler_q(mid, m_w, cp_w, v_air, rho_a, cp_a, dt_in) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def hybrid_low_speed_capacity(q_nom, v_w, v_air, ewt, eat, eawb, low_ua_frac, p, low_air_frac=HYB_LOW_AIR_FRAC):
    """Low-speed nominal capacity that makes EnergyPlus size UA_low = low_ua_frac * UA_high.
    Replicates the E+ sizing state: StdBaroPress (= standard-atmosphere pressure at the site
    elevation), water rho at 5.05 C, cp_w ~4180."""
    w = max(w_from_db_wb(eat, eawb, p), 1e-5)
    rho = p / (287.0 * (eat + 273.15) * (1.0 + 1.6077687 * w))
    cp = 1.00484e3 + 1.85895e3 * w
    m_w, cp_w = 999.9 * v_w, 4180.0
    ua_hi = ep_solve_ua(q_nom, m_w, cp_w, v_air, rho, cp, ewt - eat)
    if ua_hi is None:
        return None, None, None
    q_lo = ep_fluid_cooler_q(low_ua_frac * ua_hi, m_w, cp_w, low_air_frac * v_air, rho, cp, ewt - eat)
    return q_lo, ua_hi, rho * cp * v_air


def hybrid_design(info, q_nom, approach, rng, air_dt, eps=PAD_EFF_DEFAULT, v_w=None, low_ua_frac=None):
    """Wet design point of a hybrid adiabatic cooler at the 0.4 % DB=>MWB condition.

    Returns dict with eat, eawb, ewt, exit (design loop exit = eat + approach), pressure, rho, cp
    and vair = q_nom / (rho cp air_dt).  rho and cp use the EnergyPlus formulas
    (PsyRhoAirFnPbTdbW, PsyCpAirFnW) at the entering air state and site pressure."""
    db, wb = info["db_db"], info["db_wb"]
    eat = db - eps * (db - wb)
    notes = []
    if eat <= wb + 0.1:                       # IDD/E+ check: entering air T must exceed its wet-bulb
        notes.append(f"WARNING: entering air {eat:.2f} C not above wet-bulb {wb} C; using wet-bulb + 0.1 K")
        eat = wb + 0.1
    if wb <= 0.0:
        notes.append(f"WARNING: design wet-bulb {wb} C <= 0 violates the IDD minimum (>0); using 0.1 C")
        wb = 0.1
    p = site_pressure(info.get("elevation", 0.0))
    w = max(w_from_db_wb(eat, wb, p), 1e-5)
    rho = p / (287.0 * (eat + 273.15) * (1.0 + 1.6077687 * w))
    cp = 1.00484e3 + 1.85895e3 * w
    d = {"eat": eat, "eawb": wb, "ewt": eat + approach + rng, "exit": eat + approach, "pressure": p,
         "w": w, "rho": rho, "cp": cp, "vair": round(q_nom / (rho * cp * air_dt), 3), "eps": eps, "notes": notes}
    if v_w and low_ua_frac:
        q_lo, ua_hi, ca = hybrid_low_speed_capacity(q_nom, v_w, d["vair"], d["ewt"], eat, wb, low_ua_frac, p)
        if q_lo is None:
            raise SystemExit("hybrid cooler design infeasible: nominal capacity not reachable with these inputs")
        d.update(qlow=q_lo, ua_hi=ua_hi, ntu_hi=ua_hi / min(ca, 999.9 * 4180.0 * v_w))
    return d


def parse_hyb_tag(lines):
    """Parse 'key=value' pairs of the '! hybrid-design:' comment line (returns {} if absent)."""
    for l in lines:
        if l.strip().startswith(HYB_TAG):
            return {k: float(v) for k, v in (kv.split("=") for kv in l.strip()[len(HYB_TAG):].split())}
    return {}


def hyb_tag(d):
    return HYB_TAG + " " + " ".join(f"{k}={d[k]:g}" for k in ("approach", "range", "air_dT", "low_UA_frac", "pad_eff"))


def read_text(path):
    with open(path, encoding="latin-1") as f:
        return f.read()


# ------------------------------------------------------------------ minimal IDF tokenizer
def split_objects(text):
    """Yield (start, end, body) spans; body excludes comments. end is just past the ';'
    plus any trailing same-line comment and newline."""
    i, n = 0, len(text)
    start = 0
    body = []
    while i < n:
        c = text[i]
        if c == "!":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == ";":
            j = text.find("\n", i)
            end = n if j < 0 else j + 1
            yield start, end, "".join(body) + ";"
            body = []
            start = end
            i = end
            continue
        body.append(c)
        i += 1


def fields_of(body):
    return [f.strip() for f in body.rstrip(";").split(",")]


def class_of(body):
    return fields_of(body)[0].strip().lower()


def labelled_fields(objtext):
    """Return list of (value, label) for an object's text, keeping '!-' labels."""
    vals, labels = [], []
    cur = []
    for line in objtext.split("\n"):
        code, _, com = line.partition("!")
        label = com[1:].strip() if com.startswith("-") else ""
        parts = code.split(",")
        for k, p in enumerate(parts):
            cur.append(p)
            if k < len(parts) - 1:          # a comma closed a field
                vals.append("".join(cur).strip())
                labels.append(None)
                cur = []
        if ";" in code:
            last = "".join(cur)
            vals.append(last.split(";")[0].strip())
            labels.append(None)
            cur = []
        # attach the line's label to the last field closed on this line
        if label and labels:
            for idx in range(len(labels) - 1, -1, -1):
                if labels[idx] is None:
                    labels[idx] = label
                    break
    leading = [l for l in objtext.split("\n") if l.strip().startswith("!")]
    return vals, [l or "" for l in labels], leading


def format_object(vals, labels):
    out = [f"  {vals[0]},"]
    rest = list(zip(vals[1:], labels[1:]))
    for k, (v, lab) in enumerate(rest):
        end = ";" if k == len(rest) - 1 else ","
        s = f"    {v}{end}"
        out.append(f"{s:<40}!- {lab}" if lab else s)
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ DDY handling
def pick_design_days(ddy_text):
    loc = None
    found = {}
    for s, e, body in split_objects(ddy_text):
        f = fields_of(body)
        cls = f[0].lower()
        if cls == "site:location" and loc is None:
            loc = ddy_text[s:e]
            loc_name = f[1]
            loc_body = body
        elif cls == "sizingperiod:designday":
            name = f[1]
            for key, pat in PATTERNS.items():
                if key not in found and re.search(pat, name):
                    found[key] = (ddy_text[s:e], f)
    missing = [k for k in PATTERNS if k not in found]
    if loc is None or missing:
        raise SystemExit(f"DDY lacks Site:Location or design days: {missing}")
    wbf = found["cooling_wb"][1]
    dbf = found["cooling_db"][1]
    try:
        elev = float(fields_of(loc_body)[5])
    except (IndexError, ValueError):
        elev = 0.0
    info = {
        "location": loc_name,
        "elevation": elev,
        "wb_db": float(wbf[5]), "wb_wb": float(wbf[10]),
        "db_db": float(dbf[5]), "db_wb": float(dbf[10]),
        "heating_db": float(found["heating"][1][5]),
        "names": [found[k][1][1] for k in ("cooling_db", "cooling_wb", "heating")],
    }
    def clean(t):
        # keep the object plus only the comment lines directly above it; ASCII only
        t = t.encode("ascii", "ignore").decode()
        lines = t.strip("\n").split("\n")
        k = max(i for i, l in enumerate(lines) if not l.strip().startswith("!") and l.strip())
        start = 0
        for i, l in enumerate(lines):
            if not l.strip() and i < k:
                start = i + 1
        body = [l for l in lines[start:] if l.strip()]
        # drop leading lines that are object text of nothing (safety)
        return "\n".join(body) + "\n"
    dds = [clean(found[k][0]) for k in ("cooling_db", "cooling_wb", "heating")]
    return clean(loc), dds, info


# ------------------------------------------------------------------ main transform
def apply(idf_text, ddy_text, tower_update=True, log=print, pad_eff=PAD_EFF_DEFAULT):
    loc, dds, info = pick_design_days(ddy_text)
    # drop old marker block contents (they are re-inserted)
    idf_text = re.sub(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n?", MARK_BEGIN + "\n" + MARK_END + "\n",
                      idf_text, flags=re.S)
    pieces = []
    last = 0
    insert_at = None
    approach = 3.9
    spans = list(split_objects(idf_text))
    for s, e, body in spans:
        f = fields_of(body)
        if f[0].lower() == MERKEL and len(f) > MERKEL_APPROACH:
            try:
                approach = float(f[MERKEL_APPROACH])
                break
            except ValueError:
                pass
    des_exit = info["wb_wb"] + approach
    hyb = None                                 # hybrid dry-cooler model: design point of the first cooler
    for s, e, body in spans:
        f = fields_of(body)
        if f[0].lower() == FLUIDCOOLER2:
            tag = parse_hyb_tag(idf_text[s:e].split("\n"))
            if tag:
                hyb = hybrid_design(info, float(f[FC_QNOM]), tag["approach"], tag["range"], tag["air_dT"], pad_eff,
                                    v_w=float(f[FC_VW]), low_ua_frac=tag["low_UA_frac"])
                hyb["tag"] = dict(tag, pad_eff=pad_eff)
                for nt in hyb["notes"]:
                    log(nt)
                break
    n_removed = 0
    for s, e, body in spans:
        cls = class_of(body)
        pieces.append(idf_text[last:s])
        objtext = idf_text[s:e]
        if cls in ("sizingperiod:designday", "site:location"):
            n_removed += 1
            if insert_at is None:
                insert_at = len(pieces)
                pieces.append(None)
            last = e
            continue
        if tower_update and cls == MERKEL:
            vals, labels, lead = labelled_fields(objtext)
            while len(vals) <= MERKEL_WB:
                vals.append(""); labels.append("")
            vals[MERKEL_DB] = f"{max(info['wb_db'], 20.0):.1f}"
            vals[MERKEL_WB] = f"{max(info['wb_wb'], 20.0):.1f}"
            if info["wb_wb"] < 20.0:
                log(f"WARNING: design WB {info['wb_wb']} C below IDD minimum 20 C for {vals[1]}; using 20.0")
            objtext = "\n".join(lead) + ("\n" if lead else "") + format_object(vals, labels)
            log(f"tower {vals[1]}: design inlet air DB/WB = {vals[MERKEL_DB]}/{vals[MERKEL_WB]} C")
        elif tower_update and hyb and cls == FLUIDCOOLER2:
            vals, labels, lead = labelled_fields(objtext)
            if parse_hyb_tag(lead):
                vals[FC_EWT] = f"{hyb['ewt']:.2f}"
                vals[FC_EAT] = f"{hyb['eat']:.2f}"
                vals[FC_EAWB] = f"{hyb['eawb']:.2f}"
                vals[FC_VAIR] = f"{hyb['vair']:.3f}"
                vals[FC_QLOW] = f"{hyb['qlow']:.0f}"
                vals[FC_VAIR_LO] = f"{HYB_LOW_AIR_FRAC * float(vals[FC_VAIR]):.3f}"
                lead = [hyb_tag(hyb["tag"]) if l.strip().startswith(HYB_TAG) else l for l in lead]
                objtext = "\n".join(lead) + "\n" + format_object(vals, labels)
                log(f"fluid cooler {vals[1]}: design entering air {vals[FC_EAT]} C (WB {vals[FC_EAWB]} C, "
                    f"pad eff {pad_eff}), entering water {vals[FC_EWT]} C, high-speed air {vals[FC_VAIR]} m3/s, "
                    f"low-speed capacity {vals[FC_QLOW]} W (expected E+ UA_high {hyb['ua_hi']:.0f} W/K, NTU {hyb['ntu_hi']:.2f})")
        elif tower_update and hyb and cls == "sizing:plant":
            vals, labels, lead = labelled_fields(objtext)
            if vals[2].lower() == "condenser":
                vals[3] = f"{hyb['exit']:.2f}"
                objtext = "\n".join(lead) + ("\n" if lead else "") + format_object(vals, labels)
                log(f"Sizing:Plant {vals[1]}: design loop exit = {vals[3]} C (hybrid cooler entering air "
                    f"{hyb['eat']:.2f} + approach {hyb['tag']['approach']})")
        elif tower_update and cls == "sizing:plant":
            vals, labels, lead = labelled_fields(objtext)
            if vals[2].lower() == "condenser":
                vals[3] = f"{des_exit:.2f}"
                objtext = "\n".join(lead) + ("\n" if lead else "") + format_object(vals, labels)
                log(f"Sizing:Plant {vals[1]}: design loop exit = {vals[3]} C (WB {info['wb_wb']} + approach {approach})")
                if des_exit > 29.44:
                    log("WARNING: condenser design exit temperature above 29.4 C (85 F)")
        pieces.append(objtext)
        last = e
    pieces.append(idf_text[last:])
    block = [loc] + dds
    if MARK_BEGIN in idf_text:
        # put the block inside the existing marker pair
        text = "".join(p for p in pieces if p is not None)
        text = text.replace(MARK_BEGIN + "\n" + MARK_END, MARK_BEGIN + "\n" + "\n".join(block) + MARK_END, 1)
    else:
        if insert_at is None:
            insert_at = 1
            pieces.insert(1, None)
        pieces[insert_at] = MARK_BEGIN + "\n" + "\n".join(block) + MARK_END + "\n"
        text = "".join(p for p in pieces if p is not None)
    log(f"removed {n_removed} Site:Location/SizingPeriod:DesignDay objects outside the marker block; "
        f"inserted {info['location']}:")
    for nm in info["names"]:
        log(f"  {nm}")
    return text, info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("idf")
    ap.add_argument("ddy")
    ap.add_argument("out")
    ap.add_argument("--no-tower-update", action="store_true",
                    help="only swap location/design days; leave tower/cooler design conditions and condenser Sizing:Plant alone")
    ap.add_argument("--pad-effectiveness", type=float, default=PAD_EFF_DEFAULT,
                    help="hybrid dry-cooler models only: wetted-pad effectiveness used for the design "
                         "entering air temperature (default %(default)s)")
    a = ap.parse_args(argv)
    if not 0.0 <= a.pad_effectiveness < 1.0:
        raise SystemExit("--pad-effectiveness must be in [0, 1)")
    text, info = apply(read_text(a.idf), read_text(a.ddy), tower_update=not a.no_tower_update,
                       pad_eff=a.pad_effectiveness)
    with open(a.out, "w", encoding="latin-1") as f:
        f.write(text)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
