#!/usr/bin/env python3
"""Generate the representative water-cooled data center IDF (EnergyPlus 22.2).

    python3 models/build_datacenter_idf.py                 # -> models/datacenter_chiller_tower.idf
    python3 models/build_datacenter_idf.py --idle-tower-test [--tower2-threshold W] --out runs/dcdev/idle.idf
    python3 models/build_datacenter_idf.py --wse --out runs/dcdev/wse.idf   # EXPERIMENTAL, see DATACENTER_MODEL.md
    python3 models/build_datacenter_idf.py --heat-rejection hybrid    # -> models/datacenter_chiller_hybrid.idf

--heat-rejection tower (default) is the evaporative Merkel-tower plant; its output is unchanged.
--heat-rejection hybrid replaces the tower with N_HYB parallel FluidCooler:TwoSpeed dry coolers
("Hybrid Cooler 1..N") that share one OutdoorAir:Node ("Hybrid Cooler Air Inlet"), a dry-bulb
condenser reset ("Hybrid Condenser Setpoint") and a high-lift chiller curve set.  Without an
EMS/Python plugin acting on that node it is a plain dry-cooler plant; a plugin that overrides the
node dry-bulb/wet-bulb turns it into a hybrid adiabatic (wetted-pad) cooler.

The generated IDF carries Phoenix design days.  Use models/set_design_days.py to make it
climate-specific for another site.  See models/DATACENTER_MODEL.md for the design basis.
Stdlib only.
"""
import argparse
import sys
sys.dont_write_bytecode = True
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- design parameters
HALLS = ["DataHall1", "DataHall2"]
HALL_X, HALL_Y, HALL_H = 25.0, 20.0, 4.5          # m; 500 m2 per hall
IT_W_PER_M2 = 1000.0                               # -> 500 kW IT per hall, 1.0 MW total
ITE_FAN_FRAC = 0.10                                # server fan share of design ITE power
ITE_FLOW_PER_W = 7.5e-5                            # m3/s per W (server dT ~ 11 K)
UPS_EFF = 0.95
RECIRC = 0.05
T_SUPPLY = 20.0                                    # CRAH supply air (C)
T_COIL_OUT = 19.5                                  # coil leaving air; fan heat ~0.5 K
T_RETURN_SP = 31.0                                 # zone (hot-aisle/return) cooling setpoint
CRAH_DP = 400.0                                    # Pa
CRAH_EFF = 0.65
T_CHW = 10.0
DT_CHW = 6.0
CHW_PUMP_HEAD = 250000.0                           # Pa
CW_PUMP_HEAD = 200000.0                            # Pa
DT_CW = 5.6
APPROACH = 3.9
CW_MIN, CW_MAX = 18.0, 29.4
WSE_DT_MIN = 1.0
WSE_UA = 1.15e6 / 1.5                              # plate HX: ~1.5 K approach at ~1.15 MW (assumption)
CW_MIN_WSE = 7.0                                   # WSE variant: let the tower make cold water
WSE_TOWER_SIZING_FACTOR = 0.653                    # = sum(chiller CW flow)/(chiller + HX CW flow): same tower as base
TOWER_CELLS = 3
DRIFT_PCT = 0.001
COC = 4.0
CHILLER = "ElectricEIRChiller Carrier 19XR 1407kW/6.04COP/VSD"  # DataSets/Chillers.idf
# --plant modern: equipment-informed variant (docs/EQUIPMENT_SPECS.md). Values set in set_modern().
MODERN = False
SETS_CHILLER = "ASHRAE901 SetS Centrifugal PathB"   # 90.1-2019 App. J (2022 App. L) Set S, 150-300 t, 0.635/0.400 kW/ton
TOWER_MIN_AFR = 0.2
CELL_MIN_WFR, CELL_MAX_WFR = 0.33, 2.5

# ---- hybrid adiabatic dry-cooler variant (--heat-rejection hybrid); see DATACENTER_MODEL.md section 6
# Widest-range water-cooled curve set in DataSets/Chillers.idf that also covers 10 C CHW:
# leaving CHW 6.11-10.0 C, leaving condenser water 26.77-41.11 C (intersection of CAPFT/EIRFT/EIRFPLR).
HYB_CHILLER = "ReformEIRChiller Trane CVHE 1329kW/5.38COP/Vanes"
HYB_CHILLER_COP, HYB_CHILLER_TCHW_REF, HYB_CHILLER_TCOND_REF = 5.38, 6.11, 34.80
HYB_CHILLER_PLR = ("0.29", "1.02", "1.0", "0.29")  # min, max, optimum, min unloading (dataset values)
HYB_CHILLER_DESIGN_CAP = 552.0e3                   # W per chiller (reference capacity, hard-sized): autosized value of the base model (Phoenix);
                                                   # 549.6-551.9 kW over the 14 study sites (IT-load driven)
N_HYB = 3                                          # coolers: one per chiller -> 2 duty + 1 standby (N+1)
HYB_APPROACH = 5.6                                 # K, leaving water - entering air at design (10 F)
HYB_RANGE = DT_CW                                  # K, 5.6 (10 F), same as the condenser loop design dT
HYB_AIR_DT = 8.0                                   # K, design air temperature rise (assumption; 10 K gave NTU 5.2 and an unsizeable low speed at >600 m elevation)
HYB_LOW_UA_FRAC = 0.6                              # UA at low (half) fan speed / UA at high speed (assumption)
HYB_LOW_FAN_FRAC = 0.16                            # low-speed / high-speed fan power (E+ default sizing factor)
HYB_FAN_W_PER_W = 0.02                             # W fan per W nominal capacity at high speed (assumption)
HYB_PAD_EFF = 0.85                                 # design pad effectiveness (sizing only; set_design_days.py)
HYB_CW_MIN, HYB_CW_MAX = 23.0, 40.0                # condenser supply setpoint limits (C)
HYB_NODE = "Hybrid Cooler Air Inlet"
HYB_SPM = "Hybrid Condenser Setpoint"
HYB_RHO_W, HYB_CP_W = 999.9, 4180.0                # water properties used for the hard-sized flows

# Phoenix design days (ASHRAE 2017 via EnergyPlus DDY); set_design_days.py replaces them
PHX_DDY = os.path.join(os.path.dirname(HERE), "weather", "phx",
                       "USA_AZ_Phoenix-Sky.Harbor.Intl.AP.722780_TMY3.ddy")


# ---------------------------------------------------------------- IDF writer helpers
OUT = []


def obj(cls, *fields, comment=None):
    """fields: list of (value, label) tuples."""
    lines = []
    if comment:
        for c in comment.strip().split("\n"):
            lines.append("! " + c)
    lines.append(f"  {cls},")
    n = len(fields)
    for i, (v, lab) in enumerate(fields):
        end = ";" if i == n - 1 else ","
        s = f"    {v}{end}"
        lines.append(f"{s:<40}!- {lab}")
    OUT.append("\n".join(lines) + "\n")


def raw(text):
    OUT.append(text.strip("\n") + "\n")


def section(title):
    OUT.append("\n!" + "=" * 78 + "\n! " + title + "\n!" + "=" * 78 + "\n")


# ---------------------------------------------------------------- pieces
def simulation_control(timestep):
    section("Simulation control")
    obj("Version", ("22.2", "Version Identifier"))
    obj("SimulationControl", ("Yes", "Do Zone Sizing Calculation"),
        ("Yes", "Do System Sizing Calculation"), ("Yes", "Do Plant Sizing Calculation"),
        ("No", "Run Simulation for Sizing Periods"),
        ("Yes", "Run Simulation for Weather File Run Periods"),
        ("No", "Do HVAC Sizing Simulation for Sizing Periods"),
        ("1", "Maximum Number of HVAC Sizing Simulation Passes"))
    obj("Building", ("Representative Water-Cooled Data Center 1MW IT", "Name"),
        ("0", "North Axis"), ("City", "Terrain"),
        ("0.04", "Loads Convergence Tolerance Value"),
        ("0.2", "Temperature Convergence Tolerance Value"),
        ("MinimalShadowing", "Solar Distribution"),
        ("25", "Maximum Number of Warmup Days"), ("6", "Minimum Number of Warmup Days"))
    obj("Timestep", (str(timestep), "Number of Timesteps per Hour"))
    obj("ConvergenceLimits", ("1", "Minimum System Timestep"),
        ("20", "Maximum HVAC Iterations"), ("2", "Minimum Plant Iterations"),
        ("8", "Maximum Plant Iterations"))
    obj("RunPeriod", ("Annual", "Name"), ("1", "Begin Month"), ("1", "Begin Day of Month"),
        ("", "Begin Year"), ("12", "End Month"), ("31", "End Day of Month"), ("", "End Year"),
        ("", "Day of Week for Start Day"), ("Yes", "Use Weather File Holidays and Special Days"),
        ("Yes", "Use Weather File Daylight Saving Period"), ("No", "Apply Weekend Holiday Rule"),
        ("Yes", "Use Weather File Rain Indicators"), ("Yes", "Use Weather File Snow Indicators"))
    obj("GlobalGeometryRules", ("UpperLeftCorner", "Starting Vertex Position"),
        ("Counterclockwise", "Vertex Entry Direction"), ("Relative", "Coordinate System"))
    obj("Sizing:Parameters", ("1.0", "Heating Sizing Factor"), ("1.0", "Cooling Sizing Factor"),
        ("6", "Timesteps in Averaging Window"))


def location_and_design_days():
    section("Location and design days (replace with models/set_design_days.py)")
    import importlib.util
    spec = importlib.util.spec_from_file_location("sdd", os.path.join(HERE, "set_design_days.py"))
    sdd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sdd)
    ddy = sdd.read_text(PHX_DDY)
    loc, dds, info = sdd.pick_design_days(ddy)
    raw(sdd.MARK_BEGIN)
    raw(loc)
    for d in dds:
        raw(d)
    raw(sdd.MARK_END)
    return info


def schedules():
    section("Schedules")
    obj("ScheduleTypeLimits", ("Fraction", "Name"), ("0", "Lower Limit Value"),
        ("1", "Upper Limit Value"), ("Continuous", "Numeric Type"))
    obj("ScheduleTypeLimits", ("Temperature", "Name"), ("-60", "Lower Limit Value"),
        ("200", "Upper Limit Value"), ("Continuous", "Numeric Type"), ("Temperature", "Unit Type"))
    obj("ScheduleTypeLimits", ("Control Type", "Name"), ("0", "Lower Limit Value"),
        ("4", "Upper Limit Value"), ("Discrete", "Numeric Type"))
    obj("ScheduleTypeLimits", ("On/Off", "Name"), ("0", "Lower Limit Value"),
        ("1", "Upper Limit Value"), ("Discrete", "Numeric Type"))

    def const(name, limits, val):
        obj("Schedule:Compact", (name, "Name"), (limits, "Schedule Type Limits Name"),
            ("Through: 12/31", "Field 1"), ("For: AllDays", "Field 2"),
            ("Until: 24:00", "Field 3"), (val, "Field 4"))
    const("Always On", "On/Off", "1")
    const("ITE Installed Fraction", "Fraction", "1.0")
    const("Lights Fraction", "Fraction", "0.5")
    const("Zone Cooling Setpoint", "Temperature", f"{T_RETURN_SP}")
    const("Zone Control Type", "Control Type", "2")
    const("CRAH Supply Air Setpoint", "Temperature", f"{T_SUPPLY}")
    const("CHW Supply Setpoint", "Temperature", f"{T_CHW}")
    # CPU utilisation: mild diurnal + weekly variation, 0.70-0.90; 1.0 on design days so
    # that equipment is sized at full design IT load.
    obj("Schedule:Compact", ("ITE CPU Utilization", "Name"), ("Fraction", "Schedule Type Limits Name"),
        ("Through: 12/31", "Field 1"),
        ("For: SummerDesignDay WinterDesignDay", "Field 2"), ("Until: 24:00", "Field 3"), ("1.0", "Field 4"),
        ("For: Weekdays", "Field 5"),
        ("Until: 06:00", "Field 6"), ("0.75", "Field 7"),
        ("Until: 09:00", "Field 8"), ("0.80", "Field 9"),
        ("Until: 18:00", "Field 10"), ("0.90", "Field 11"),
        ("Until: 22:00", "Field 12"), ("0.85", "Field 13"),
        ("Until: 24:00", "Field 14"), ("0.78", "Field 15"),
        ("For: Weekends Holidays", "Field 16"),
        ("Until: 06:00", "Field 17"), ("0.70", "Field 18"),
        ("Until: 18:00", "Field 19"), ("0.80", "Field 20"),
        ("Until: 24:00", "Field 21"), ("0.75", "Field 22"),
        ("For: AllOtherDays", "Field 23"), ("Until: 24:00", "Field 24"), ("0.80", "Field 25"))


def envelope():
    section("Envelope: single-storey shell, two data halls, no windows")
    obj("Material", ("Metal Panel Skin", "Name"), ("Smooth", "Roughness"), ("0.0008", "Thickness"),
        ("45.0", "Conductivity"), ("7800", "Density"), ("500", "Specific Heat"))
    obj("Material", ("PIR Insulation 100mm", "Name"), ("MediumRough", "Roughness"),
        ("0.10", "Thickness"), ("0.025", "Conductivity"), ("32", "Density"), ("1400", "Specific Heat"))
    obj("Material", ("PIR Insulation 140mm", "Name"), ("MediumRough", "Roughness"),
        ("0.14", "Thickness"), ("0.025", "Conductivity"), ("32", "Density"), ("1400", "Specific Heat"))
    obj("Material", ("Concrete 200mm", "Name"), ("MediumRough", "Roughness"), ("0.20", "Thickness"),
        ("1.95", "Conductivity"), ("2240", "Density"), ("900", "Specific Heat"))
    obj("Material", ("Gypsum 16mm", "Name"), ("Smooth", "Roughness"), ("0.016", "Thickness"),
        ("0.16", "Conductivity"), ("800", "Density"), ("1090", "Specific Heat"))
    obj("Construction", ("Ext Wall IMP", "Name"), ("Metal Panel Skin", "Outside Layer"),
        ("PIR Insulation 100mm", "Layer 2"), ("Metal Panel Skin", "Layer 3"))
    obj("Construction", ("Roof Insulated Deck", "Name"), ("Metal Panel Skin", "Outside Layer"),
        ("PIR Insulation 140mm", "Layer 2"), ("Concrete 200mm", "Layer 3"))
    obj("Construction", ("Slab", "Name"), ("Concrete 200mm", "Outside Layer"))
    obj("Construction", ("Interior Partition", "Name"), ("Gypsum 16mm", "Outside Layer"),
        ("Concrete 200mm", "Layer 2"), ("Gypsum 16mm", "Layer 3"))

    X, Y, H = HALL_X, HALL_Y, HALL_H
    for i, z in enumerate(HALLS):
        x0, x1 = i * X, (i + 1) * X
        obj("Zone", (z, "Name"), ("0", "Direction of Relative North"), ("0", "X Origin"),
            ("0", "Y Origin"), ("0", "Z Origin"), ("1", "Type"), ("1", "Multiplier"),
            (f"{H}", "Ceiling Height"), ("autocalculate", "Volume"))

        def surf(name, stype, cons, bc, bcobj, sun, wind, verts):
            f = [(name, "Name"), (stype, "Surface Type"), (cons, "Construction Name"),
                 (z, "Zone Name"), ("", "Space Name"), (bc, "Outside Boundary Condition"),
                 (bcobj, "Outside Boundary Condition Object"), (sun, "Sun Exposure"),
                 (wind, "Wind Exposure"), ("autocalculate", "View Factor to Ground"),
                 (str(len(verts)), "Number of Vertices")]
            for k, (a, b, c) in enumerate(verts):
                f.append((f"{a:g},{b:g},{c:g}", f"Vertex {k+1} X,Y,Z"))
            obj("BuildingSurface:Detailed", *f)
        ext = ("Outdoors", "", "SunExposed", "WindExposed")
        surf(f"{z} South Wall", "Wall", "Ext Wall IMP", *ext,
             [(x0, 0, H), (x0, 0, 0), (x1, 0, 0), (x1, 0, H)])
        surf(f"{z} North Wall", "Wall", "Ext Wall IMP", *ext,
             [(x1, Y, H), (x1, Y, 0), (x0, Y, 0), (x0, Y, H)])
        surf(f"{z} Roof", "Roof", "Roof Insulated Deck", *ext,
             [(x1, Y, H), (x0, Y, H), (x0, 0, H), (x1, 0, H)])
        surf(f"{z} Floor", "Floor", "Slab", "Adiabatic", "", "NoSun", "NoWind",
             [(x0, 0, 0), (x0, Y, 0), (x1, Y, 0), (x1, 0, 0)])
        west = [(x0, Y, H), (x0, Y, 0), (x0, 0, 0), (x0, 0, H)]
        east = [(x1, 0, H), (x1, 0, 0), (x1, Y, 0), (x1, Y, H)]
        if i == 0:
            surf(f"{z} West Wall", "Wall", "Ext Wall IMP", *ext, west)
            surf(f"{z} East Partition", "Wall", "Interior Partition", "Surface",
                 f"{HALLS[1]} West Partition", "NoSun", "NoWind", east)
        else:
            surf(f"{z} West Partition", "Wall", "Interior Partition", "Surface",
                 f"{HALLS[0]} East Partition", "NoSun", "NoWind", west)
            surf(f"{z} East Wall", "Wall", "Ext Wall IMP", *ext, east)


def internal_loads():
    section("IT equipment (ElectricEquipment:ITE:AirCooled) and lighting")
    obj("Curve:Biquadratic", ("ITE CPU Power fLoadTemp", "Name"),
        ("0.30", "Coefficient1 Constant"), ("0.70", "Coefficient2 x"), ("0", "Coefficient3 x**2"),
        ("0", "Coefficient4 y"), ("0", "Coefficient5 y**2"), ("0", "Coefficient6 x*y"),
        ("0", "Minimum Value of x"), ("1.0", "Maximum Value of x"),
        ("-10", "Minimum Value of y"), ("99", "Maximum Value of y"),
        ("0.0", "Minimum Curve Output"), ("1.0", "Maximum Curve Output"),
        ("Dimensionless", "Input Unit Type for X"), ("Temperature", "Input Unit Type for Y"),
        ("Dimensionless", "Output Unit Type"),
        comment="P_cpu/P_cpu,design = 0.30 + 0.70*u  (idle = 30% of peak; assumption)")
    obj("Curve:Biquadratic", ("ITE Airflow fLoadTemp", "Name"),
        ("0.60", "Coefficient1 Constant"), ("0.40", "Coefficient2 x"), ("0", "Coefficient3 x**2"),
        ("0", "Coefficient4 y"), ("0", "Coefficient5 y**2"), ("0", "Coefficient6 x*y"),
        ("0", "Minimum Value of x"), ("1.0", "Maximum Value of x"),
        ("-10", "Minimum Value of y"), ("99", "Maximum Value of y"),
        ("0.0", "Minimum Curve Output"), ("1.0", "Maximum Curve Output"),
        ("Dimensionless", "Input Unit Type for X"), ("Temperature", "Input Unit Type for Y"),
        ("Dimensionless", "Output Unit Type"),
        comment="Server airflow fraction = 0.60 + 0.40*u (assumption)")
    obj("Curve:Cubic", ("ITE Fan Power fFlow", "Name"), ("0", "Coefficient1 Constant"),
        ("0", "Coefficient2 x"), ("0", "Coefficient3 x**2"), ("1.0", "Coefficient4 x**3"),
        ("0", "Minimum Value of x"), ("1.5", "Maximum Value of x"),
        comment="Server fan affinity law (cube)")
    obj("Curve:Biquadratic", ("ITE Recirc fLoadTemp", "Name"),
        ("1.0", "Coefficient1 Constant"), ("0", "Coefficient2 x"), ("0", "Coefficient3 x**2"),
        ("0", "Coefficient4 y"), ("0", "Coefficient5 y**2"), ("0", "Coefficient6 x*y"),
        ("0", "Minimum Value of x"), ("1.5", "Maximum Value of x"),
        ("-10", "Minimum Value of y"), ("99", "Maximum Value of y"),
        ("0.0", "Minimum Curve Output"), ("1.0", "Maximum Curve Output"),
        ("Dimensionless", "Input Unit Type for X"), ("Temperature", "Input Unit Type for Y"),
        ("Dimensionless", "Output Unit Type"))
    obj("Curve:Quadratic", ("UPS Efficiency fPLR", "Name"), ("1.0", "Coefficient1 Constant"),
        ("0", "Coefficient2 x"), ("0", "Coefficient3 x**2"), ("0", "Minimum Value of x"),
        ("1.5", "Maximum Value of x"),
        comment="Flat UPS efficiency over the 0.75-1.0 load range seen here (assumption)")
    for z in HALLS:
        obj("ElectricEquipment:ITE:AirCooled", (f"{z} ITE", "Name"), (z, "Zone or Space Name"),
            ("FlowFromSystem", "Air Flow Calculation Method"),
            ("Watts/Area", "Design Power Input Calculation Method"),
            ("", "Watts per Unit"), ("", "Number of Units"),
            (f"{IT_W_PER_M2}", "Watts per Zone Floor Area"),
            ("ITE Installed Fraction", "Design Power Input Schedule Name"),
            ("ITE CPU Utilization", "CPU Loading  Schedule Name"),
            ("ITE CPU Power fLoadTemp", "CPU Power Input Function of Loading and Air Temperature Curve Name"),
            (f"{ITE_FAN_FRAC}", "Design Fan Power Input Fraction"),
            (f"{ITE_FLOW_PER_W}", "Design Fan Air Flow Rate per Power Input"),
            ("ITE Airflow fLoadTemp", "Air Flow Function of Loading and Air Temperature Curve Name"),
            ("ITE Fan Power fFlow", "Fan Power Input Function of Flow Curve Name"),
            (f"{T_SUPPLY}", "Design Entering Air Temperature"),
            ("A1", "Environmental Class"), ("AdjustedSupply", "Air Inlet Connection Type"),
            ("", "Air Inlet Room Air Model Node Name"), ("", "Air Outlet Room Air Model Node Name"),
            (f"{z} Supply Inlet Node", "Supply Air Node Name"),
            (f"{RECIRC}", "Design Recirculation Fraction"),
            ("ITE Recirc fLoadTemp", "Recirculation Function of Loading and Supply Temperature Curve Name"),
            (f"{UPS_EFF}", "Design Electric Power Supply Efficiency"),
            ("UPS Efficiency fPLR", "Electric Power Supply Efficiency Function of Part Load Ratio Curve Name"),
            ("1.0", "Fraction of Electric Power Supply Losses to Zone"),
            ("ITE-CPU", "CPU End-Use Subcategory"), ("ITE-Fans", "Fan End-Use Subcategory"),
            ("ITE-UPS", "Electric Power Supply End-Use Subcategory"))
        obj("Lights", (f"{z} Lights", "Name"), (z, "Zone or ZoneList or Space or SpaceList Name"),
            ("Lights Fraction", "Schedule Name"), ("Watts/Area", "Design Level Calculation Method"),
            ("", "Lighting Level"), ("5.0", "Watts per Zone Floor Area"), ("", "Watts per Person"),
            ("0", "Return Air Fraction"), ("0.4", "Fraction Radiant"), ("0.2", "Fraction Visible"),
            ("1.0", "Fraction Replaceable"), ("Lighting", "End-Use Subcategory"))


def air_side():
    section("Air side: one CRAH bank (AirLoopHVAC) per data hall, CHW coil + VAV fan, 100% recirculation")
    obj("ThermostatSetpoint:SingleCooling", ("Return Air Cooling SP", "Name"),
        ("Zone Cooling Setpoint", "Setpoint Temperature Schedule Name"))
    for z in HALLS:
        a = f"{z} CRAH"
        obj("Sizing:Zone", (z, "Zone or ZoneList Name"),
            ("SupplyAirTemperature", "Zone Cooling Design Supply Air Temperature Input Method"),
            (f"{T_SUPPLY}", "Zone Cooling Design Supply Air Temperature"),
            ("", "Zone Cooling Design Supply Air Temperature Difference"),
            ("SupplyAirTemperature", "Zone Heating Design Supply Air Temperature Input Method"),
            ("30", "Zone Heating Design Supply Air Temperature"),
            ("", "Zone Heating Design Supply Air Temperature Difference"),
            ("0.008", "Zone Cooling Design Supply Air Humidity Ratio"),
            ("0.008", "Zone Heating Design Supply Air Humidity Ratio"),
            ("", "Design Specification Outdoor Air Object Name"),
            ("1.0", "Zone Heating Sizing Factor"), ("1.0", "Zone Cooling Sizing Factor"),
            ("DesignDay", "Cooling Design Air Flow Method"))
        obj("ZoneControl:Thermostat", (f"{z} Thermostat", "Name"), (z, "Zone or ZoneList Name"),
            ("Zone Control Type", "Control Type Schedule Name"),
            ("ThermostatSetpoint:SingleCooling", "Control 1 Object Type"),
            ("Return Air Cooling SP", "Control 1 Name"))
        obj("ZoneHVAC:EquipmentConnections", (z, "Zone Name"), (f"{z} Equipment", "Zone Conditioning Equipment List Name"),
            (f"{z} Supply Inlet Node", "Zone Air Inlet Node or NodeList Name"), ("", "Zone Air Exhaust Node or NodeList Name"),
            (f"{z} Air Node", "Zone Air Node Name"), (f"{z} Return Outlet Node", "Zone Return Air Node or NodeList Name"))
        obj("ZoneHVAC:EquipmentList", (f"{z} Equipment", "Name"), ("SequentialLoad", "Load Distribution Scheme"),
            ("ZoneHVAC:AirDistributionUnit", "Zone Equipment 1 Object Type"), (f"{z} ADU", "Zone Equipment 1 Name"),
            ("1", "Zone Equipment 1 Cooling Sequence"), ("1", "Zone Equipment 1 Heating or No-Load Sequence"),
            ("", "Zone Equipment 1 Sequential Cooling Fraction Schedule Name"),
            ("", "Zone Equipment 1 Sequential Heating Fraction Schedule Name"))
        obj("ZoneHVAC:AirDistributionUnit", (f"{z} ADU", "Name"), (f"{z} Supply Inlet Node", "Air Distribution Unit Outlet Node Name"),
            ("AirTerminal:SingleDuct:VAV:NoReheat", "Air Terminal Object Type"), (f"{z} VAV", "Air Terminal Name"))
        obj("AirTerminal:SingleDuct:VAV:NoReheat", (f"{z} VAV", "Name"), ("Always On", "Availability Schedule Name"),
            (f"{z} Supply Inlet Node", "Air Outlet Node Name"), (f"{z} Terminal Inlet Node", "Air Inlet Node Name"),
            ("autosize", "Maximum Air Flow Rate"), ("Constant", "Zone Minimum Air Flow Input Method"),
            ("0.3", "Constant Minimum Air Flow Fraction"))
        obj("Sizing:System", (a, "AirLoop Name"), ("Sensible", "Type of Load to Size On"),
            ("0", "Design Outdoor Air Flow Rate"), ("1.0", "Central Heating Maximum System Air Flow Ratio"),
            ("7", "Preheat Design Temperature"), ("0.008", "Preheat Design Humidity Ratio"),
            ("12.8", "Precool Design Temperature"), ("0.008", "Precool Design Humidity Ratio"),
            (f"{T_COIL_OUT}", "Central Cooling Design Supply Air Temperature"),
            ("30", "Central Heating Design Supply Air Temperature"), ("NonCoincident", "Type of Zone Sum to Use"),
            ("No", "100% Outdoor Air in Cooling"), ("No", "100% Outdoor Air in Heating"),
            ("0.008", "Central Cooling Design Supply Air Humidity Ratio"),
            ("0.008", "Central Heating Design Supply Air Humidity Ratio"),
            ("DesignDay", "Cooling Supply Air Flow Rate Method"), ("", "Cooling Supply Air Flow Rate"),
            ("", "Cooling Supply Air Flow Rate Per Floor Area"), ("", "Cooling Fraction of Autosized Cooling Supply Air Flow Rate"),
            ("", "Cooling Supply Air Flow Rate Per Unit Cooling Capacity"),
            ("DesignDay", "Heating Supply Air Flow Rate Method"), ("", "Heating Supply Air Flow Rate"),
            ("", "Heating Supply Air Flow Rate Per Floor Area"), ("", "Heating Fraction of Autosized Heating Supply Air Flow Rate"),
            ("", "Heating Fraction of Autosized Cooling Supply Air Flow Rate"),
            ("", "Heating Supply Air Flow Rate Per Unit Heating Capacity"),
            ("ZoneSum", "System Outdoor Air Method"), ("1.0", "Zone Maximum Outdoor Air Fraction"),
            ("CoolingDesignCapacity", "Cooling Design Capacity Method"), ("autosize", "Cooling Design Capacity"),
            ("", "Cooling Design Capacity Per Floor Area"), ("", "Fraction of Autosized Cooling Design Capacity"),
            ("None", "Heating Design Capacity Method"), ("", "Heating Design Capacity"),
            ("", "Heating Design Capacity Per Floor Area"), ("", "Fraction of Autosized Heating Design Capacity"),
            ("OnOff", "Central Cooling Capacity Control Method"))
        obj("AirLoopHVAC", (a, "Name"), (f"{a} Controllers", "Controller List Name"),
            (f"{a} Avail List", "Availability Manager List Name"), ("autosize", "Design Supply Air Flow Rate"),
            (f"{a} Branches", "Branch List Name"), ("", "Connector List Name"),
            (f"{a} Supply Inlet Node", "Supply Side Inlet Node Name"),
            (f"{a} Demand Outlet Node", "Demand Side Outlet Node Name"),
            (f"{a} Demand Inlet Node", "Demand Side Inlet Node Names"),
            (f"{a} Supply Outlet Node", "Supply Side Outlet Node Names"))
        obj("AvailabilityManagerAssignmentList", (f"{a} Avail List", "Name"),
            ("AvailabilityManager:Scheduled", "Availability Manager 1 Object Type"),
            (f"{a} Avail", "Availability Manager 1 Name"))
        obj("AvailabilityManager:Scheduled", (f"{a} Avail", "Name"), ("Always On", "Schedule Name"))
        obj("AirLoopHVAC:ControllerList", (f"{a} Controllers", "Name"),
            ("Controller:WaterCoil", "Controller 1 Object Type"), (f"{a} Coil Controller", "Controller 1 Name"))
        obj("BranchList", (f"{a} Branches", "Name"), (f"{a} Main Branch", "Branch 1 Name"))
        obj("Branch", (f"{a} Main Branch", "Name"), ("", "Pressure Drop Curve Name"),
            ("Coil:Cooling:Water", "Component 1 Object Type"), (f"{a} CHW Coil", "Component 1 Name"),
            (f"{a} Supply Inlet Node", "Component 1 Inlet Node Name"), (f"{a} Coil Outlet Node", "Component 1 Outlet Node Name"),
            ("Fan:VariableVolume", "Component 2 Object Type"), (f"{a} Fan", "Component 2 Name"),
            (f"{a} Coil Outlet Node", "Component 2 Inlet Node Name"), (f"{a} Supply Outlet Node", "Component 2 Outlet Node Name"))
        obj("Coil:Cooling:Water", (f"{a} CHW Coil", "Name"), ("Always On", "Availability Schedule Name"),
            ("autosize", "Design Water Flow Rate"), ("autosize", "Design Air Flow Rate"),
            ("autosize", "Design Inlet Water Temperature"), ("autosize", "Design Inlet Air Temperature"),
            (f"{T_COIL_OUT}", "Design Outlet Air Temperature"), ("autosize", "Design Inlet Air Humidity Ratio"),
            ("autosize", "Design Outlet Air Humidity Ratio"),
            (f"{a} CHW Coil Water Inlet", "Water Inlet Node Name"), (f"{a} CHW Coil Water Outlet", "Water Outlet Node Name"),
            (f"{a} Supply Inlet Node", "Air Inlet Node Name"), (f"{a} Coil Outlet Node", "Air Outlet Node Name"),
            ("DetailedAnalysis", "Type of Analysis"), ("CounterFlow", "Heat Exchanger Configuration"),
            ("", "Condensate Collection Water Storage Tank Name"), (f"{DT_CHW}", "Design Water Temperature Difference"))
        obj("Controller:WaterCoil", (f"{a} Coil Controller", "Name"), ("Temperature", "Control Variable"),
            ("Reverse", "Action"), ("Flow", "Actuator Variable"), (f"{a} Coil Outlet Node", "Sensor Node Name"),
            (f"{a} CHW Coil Water Inlet", "Actuator Node Name"), ("0.01", "Controller Convergence Tolerance"),
            ("autosize", "Maximum Actuated Flow"), ("0.0", "Minimum Actuated Flow"))
        obj("Fan:VariableVolume", (f"{a} Fan", "Name"), ("Always On", "Availability Schedule Name"),
            (f"{CRAH_EFF}", "Fan Total Efficiency"), (f"{CRAH_DP}", "Pressure Rise"), ("autosize", "Maximum Flow Rate"),
            ("Fraction", "Fan Power Minimum Flow Rate Input Method"), ("0.2", "Fan Power Minimum Flow Fraction"),
            ("", "Fan Power Minimum Air Flow Rate"), ("0.93", "Motor Efficiency"), ("1.0", "Motor In Airstream Fraction"),
            ("0.040759894", "Fan Power Coefficient 1"), ("0.08804497", "Fan Power Coefficient 2"),
            ("-0.07292612", "Fan Power Coefficient 3"), ("0.943739823", "Fan Power Coefficient 4"),
            ("0", "Fan Power Coefficient 5"),
            (f"{a} Coil Outlet Node", "Air Inlet Node Name"), (f"{a} Supply Outlet Node", "Air Outlet Node Name"),
            ("CRAH Fans", "End-Use Subcategory"))
        obj("SetpointManager:Scheduled", (f"{a} Supply SPM", "Name"), ("Temperature", "Control Variable"),
            ("CRAH Supply Air Setpoint", "Schedule Name"), (f"{a} Supply Outlet Node", "Setpoint Node or NodeList Name"))
        obj("SetpointManager:MixedAir", (f"{a} Coil SPM", "Name"), ("Temperature", "Control Variable"),
            (f"{a} Supply Outlet Node", "Reference Setpoint Node Name"), (f"{a} Coil Outlet Node", "Fan Inlet Node Name"),
            (f"{a} Supply Outlet Node", "Fan Outlet Node Name"), (f"{a} Coil Outlet Node", "Setpoint Node or NodeList Name"))
        obj("AirLoopHVAC:SupplyPath", (f"{a} Supply Path", "Name"), (f"{a} Demand Inlet Node", "Supply Air Path Inlet Node Name"),
            ("AirLoopHVAC:ZoneSplitter", "Component 1 Object Type"), (f"{a} Zone Splitter", "Component 1 Name"))
        obj("AirLoopHVAC:ZoneSplitter", (f"{a} Zone Splitter", "Name"), (f"{a} Demand Inlet Node", "Inlet Node Name"),
            (f"{z} Terminal Inlet Node", "Outlet 1 Node Name"))
        obj("AirLoopHVAC:ReturnPath", (f"{a} Return Path", "Name"), (f"{a} Demand Outlet Node", "Return Air Path Outlet Node Name"),
            ("AirLoopHVAC:ZoneMixer", "Component 1 Object Type"), (f"{a} Zone Mixer", "Component 1 Name"))
        obj("AirLoopHVAC:ZoneMixer", (f"{a} Zone Mixer", "Name"), (f"{a} Demand Outlet Node", "Outlet Node Name"),
            (f"{z} Return Outlet Node", "Inlet 1 Node Name"))


# ---------------------------------------------------------------- plant helpers
def branch(name, comps):
    """comps: list of (type, name, inlet, outlet)."""
    f = [(name, "Name"), ("", "Pressure Drop Curve Name")]
    for k, (t, n, i, o) in enumerate(comps, 1):
        f += [(t, f"Component {k} Object Type"), (n, f"Component {k} Name"),
              (i, f"Component {k} Inlet Node Name"), (o, f"Component {k} Outlet Node Name")]
    obj("Branch", *f)


def pipe(name, i, o):
    obj("Pipe:Adiabatic", (name, "Name"), (i, "Inlet Node Name"), (o, "Outlet Node Name"))


def loop_side(prefix, inlet_branch, parallel, outlet_branch, side):
    """Write BranchList, splitter, mixer, connector list for one loop side.
    inlet_branch/outlet_branch/parallel are names of Branch objects already written."""
    names = [inlet_branch] + parallel + [outlet_branch]
    f = [(f"{prefix} {side} Branches", "Name")] + [(n, f"Branch {k+1} Name") for k, n in enumerate(names)]
    obj("BranchList", *f)
    f = [(f"{prefix} {side} Splitter", "Name"), (inlet_branch, "Inlet Branch Name")] + \
        [(n, f"Outlet Branch {k+1} Name") for k, n in enumerate(parallel)]
    obj("Connector:Splitter", *f)
    f = [(f"{prefix} {side} Mixer", "Name"), (outlet_branch, "Outlet Branch Name")] + \
        [(n, f"Inlet Branch {k+1} Name") for k, n in enumerate(parallel)]
    obj("Connector:Mixer", *f)
    obj("ConnectorList", (f"{prefix} {side} Connectors", "Name"),
        ("Connector:Splitter", "Connector 1 Object Type"), (f"{prefix} {side} Splitter", "Connector 1 Name"),
        ("Connector:Mixer", "Connector 2 Object Type"), (f"{prefix} {side} Mixer", "Connector 2 Name"))


def set_modern():
    """Equipment-informed plant (docs/EQUIPMENT_SPECS.md, recommendations 1-3, 6, 7)."""
    global MODERN, T_CHW, CW_MIN, TOWER_MIN_AFR, CELL_MIN_WFR, CELL_MAX_WFR
    MODERN = True
    T_CHW = 15.5            # FEMP >= 55 F; modern colocation/hyperscale 15-18 C
    CW_MIN = 15.5           # 60 F condenser floor (modern centrifugal / magnetic-bearing chillers)
    TOWER_MIN_AFR = 0.25    # gear-drive minimum motor speed
    CELL_MIN_WFR, CELL_MAX_WFR = 0.5, 1.2   # weir-dam / 50 % turndown; max flow per cell (assumption)


def sets_chiller_curves():
    """ASHRAE 90.1-2019 Addendum bd App. J Set S (SI, Table J-5). Valid CHWT 4-16 C, ECT 12.8-40 C."""
    n = SETS_CHILLER
    obj("Curve:Biquadratic", (n + " CAPFT", "Name"), ("0.971699", "Coefficient1 Constant"), ("0.036192", "Coefficient2 x"),
        ("-0.001858", "Coefficient3 x**2"), ("-0.005224", "Coefficient4 y"), ("-0.000134", "Coefficient5 y**2"),
        ("0.000709", "Coefficient6 x*y"), ("4.0", "Minimum Value of x"), ("16.0", "Maximum Value of x"),
        ("12.8", "Minimum Value of y"), ("40.0", "Maximum Value of y"), ("", "Minimum Curve Output"), ("", "Maximum Curve Output"),
        ("Temperature", "Input Unit Type for X"), ("Temperature", "Input Unit Type for Y"), ("Dimensionless", "Output Unit Type"),
        comment="ASHRAE 90.1-2019 Addendum bd, Appendix J, Set S (centrifugal 150-300 t, Path B), SI coefficients")
    obj("Curve:Biquadratic", (n + " EIRFT", "Name"), ("0.526475", "Coefficient1 Constant"), ("-0.030843", "Coefficient2 x"),
        ("0.000735", "Coefficient3 x**2"), ("0.035532", "Coefficient4 y"), ("-0.000510", "Coefficient5 y**2"),
        ("0.000216", "Coefficient6 x*y"), ("4.0", "Minimum Value of x"), ("16.0", "Maximum Value of x"),
        ("12.8", "Minimum Value of y"), ("40.0", "Maximum Value of y"), ("", "Minimum Curve Output"), ("", "Maximum Curve Output"),
        ("Temperature", "Input Unit Type for X"), ("Temperature", "Input Unit Type for Y"), ("Dimensionless", "Output Unit Type"))
    obj("Curve:Quadratic", (n + " EIRFPLR", "Name"), ("0.064979", "Coefficient1 Constant"), ("0.151829", "Coefficient2 x"),
        ("0.779131", "Coefficient3 x**2"), ("0.0", "Minimum Value of x"), ("1.0", "Maximum Value of x"),
        ("", "Minimum Curve Output"), ("", "Maximum Curve Output"), ("Dimensionless", "Input Unit Type for X"),
        ("Dimensionless", "Output Unit Type"))


def chiller_curves(name=CHILLER):
    import re
    t = open(os.path.join("/srv/data1/EnergyPlus-22-2-0/DataSets/Chillers.idf"), errors="ignore").read()
    out = []
    for suf in ("CAPFT", "EIRFT", "EIRFPLR"):
        m = re.search(r"\n(\s*Curve:\w+,\s*\n\s*" + re.escape(name + " " + suf) + r"\s*,.*?;[^\n]*)", t, re.S)
        if not m:
            raise SystemExit("curve not found: " + suf)
        out.append(m.group(1))
    return "\n\n".join(out)


def chw_loop(wse, hybrid=False):
    if hybrid:
        section("Chilled water loop: 3 x 50% water-cooled high-lift centrifugal chillers (N+1, ReformulatedEIR), variable primary")
    else:
        section("Chilled water loop: 3 x 50% water-cooled VSD centrifugal chillers (N+1), variable primary")
    ctype = "Chiller:Electric:ReformulatedEIR" if hybrid else "Chiller:Electric:EIR"
    p = "CHW"
    sup_branches = []
    inlet = [("Pump:VariableSpeed", f"{p} Primary Pump", f"{p} Supply Inlet Node", f"{p} Pump Outlet Node")]
    if wse:
        # integrated WSE: plate HX in series upstream of the chillers (pre-cools CHW return)
        inlet.append(("HeatExchanger:FluidToFluid", "WSE HX", f"{p} Pump Outlet Node", f"{p} WSE Outlet Node"))
    branch(f"{p} Supply Inlet Branch", inlet)
    for k in (1, 2, 3):
        n = f"{p} Chiller{k} Branch"
        branch(n, [(ctype, f"Chiller {k}", f"Chiller {k} CHW Inlet", f"Chiller {k} CHW Outlet")])
        sup_branches.append(n)
    branch(f"{p} Supply Bypass Branch", [("Pipe:Adiabatic", f"{p} Supply Bypass Pipe", f"{p} Supply Bypass Inlet", f"{p} Supply Bypass Outlet")])
    pipe(f"{p} Supply Bypass Pipe", f"{p} Supply Bypass Inlet", f"{p} Supply Bypass Outlet")
    sup_branches.append(f"{p} Supply Bypass Branch")
    branch(f"{p} Supply Outlet Branch", [("Pipe:Adiabatic", f"{p} Supply Outlet Pipe", f"{p} Supply Mixer Outlet", f"{p} Supply Outlet Node")])
    pipe(f"{p} Supply Outlet Pipe", f"{p} Supply Mixer Outlet", f"{p} Supply Outlet Node")
    loop_side(p, f"{p} Supply Inlet Branch", sup_branches, f"{p} Supply Outlet Branch", "Supply")

    # demand side
    branch(f"{p} Demand Inlet Branch", [("Pipe:Adiabatic", f"{p} Demand Inlet Pipe", f"{p} Demand Inlet Node", f"{p} Demand Inlet Pipe Outlet")])
    pipe(f"{p} Demand Inlet Pipe", f"{p} Demand Inlet Node", f"{p} Demand Inlet Pipe Outlet")
    dem = []
    for z in HALLS:
        a = f"{z} CRAH"
        n = f"{p} {z} Coil Branch"
        branch(n, [("Coil:Cooling:Water", f"{a} CHW Coil", f"{a} CHW Coil Water Inlet", f"{a} CHW Coil Water Outlet")])
        dem.append(n)
    branch(f"{p} Demand Bypass Branch", [("Pipe:Adiabatic", f"{p} Demand Bypass Pipe", f"{p} Demand Bypass Inlet", f"{p} Demand Bypass Outlet")])
    pipe(f"{p} Demand Bypass Pipe", f"{p} Demand Bypass Inlet", f"{p} Demand Bypass Outlet")
    dem.append(f"{p} Demand Bypass Branch")
    branch(f"{p} Demand Outlet Branch", [("Pipe:Adiabatic", f"{p} Demand Outlet Pipe", f"{p} Demand Outlet Pipe Inlet", f"{p} Demand Outlet Node")])
    pipe(f"{p} Demand Outlet Pipe", f"{p} Demand Outlet Pipe Inlet", f"{p} Demand Outlet Node")
    loop_side(p, f"{p} Demand Inlet Branch", dem, f"{p} Demand Outlet Branch", "Demand")

    obj("PlantLoop", (f"{p} Loop", "Name"), ("Water", "Fluid Type"), ("", "User Defined Fluid Type"),
        (f"{p} Operation Schemes", "Plant Equipment Operation Scheme Name"),
        (f"{p} Supply Outlet Node", "Loop Temperature Setpoint Node Name"),
        ("30", "Maximum Loop Temperature"), ("3", "Minimum Loop Temperature"),
        ("autosize", "Maximum Loop Flow Rate"), ("0", "Minimum Loop Flow Rate"), ("autocalculate", "Plant Loop Volume"),
        (f"{p} Supply Inlet Node", "Plant Side Inlet Node Name"), (f"{p} Supply Outlet Node", "Plant Side Outlet Node Name"),
        (f"{p} Supply Branches", "Plant Side Branch List Name"), (f"{p} Supply Connectors", "Plant Side Connector List Name"),
        (f"{p} Demand Inlet Node", "Demand Side Inlet Node Name"), (f"{p} Demand Outlet Node", "Demand Side Outlet Node Name"),
        (f"{p} Demand Branches", "Demand Side Branch List Name"), (f"{p} Demand Connectors", "Demand Side Connector List Name"),
        ("SequentialUniformPLR", "Load Distribution Scheme"), ("", "Availability Manager List Name"),
        ("SingleSetpoint", "Plant Loop Demand Calculation Scheme"), ("None", "Common Pipe Simulation"))
    obj("Sizing:Plant", (f"{p} Loop", "Plant or Condenser Loop Name"), ("Cooling", "Loop Type"),
        (f"{T_CHW}", "Design Loop Exit Temperature"), (f"{DT_CHW}", "Loop Design Temperature Difference"))
    obj("SetpointManager:Scheduled", (f"{p} Supply SPM", "Name"), ("Temperature", "Control Variable"),
        ("CHW Supply Setpoint", "Schedule Name"), (f"{p} Setpoint Nodes", "Setpoint Node or NodeList Name"))
    obj("NodeList", (f"{p} Setpoint Nodes", "Name"), (f"{p} Supply Outlet Node", "Node 1 Name"),
        *[(f"Chiller {k} CHW Outlet", f"Node {k+1} Name") for k in (1, 2, 3)],
        *([(f"{p} WSE Outlet Node", "Node 5 Name")] if wse else []))
    obj("Pump:VariableSpeed", (f"{p} Primary Pump", "Name"), (f"{p} Supply Inlet Node", "Inlet Node Name"),
        (f"{p} Pump Outlet Node", "Outlet Node Name"), ("autosize", "Design Maximum Flow Rate"),
        (f"{CHW_PUMP_HEAD:.0f}", "Design Pump Head"), ("autosize", "Design Power Consumption"),
        ("0.92", "Motor Efficiency"), ("0.0", "Fraction of Motor Inefficiencies to Fluid Stream"),
        ("0", "Coefficient 1 of the Part Load Performance Curve"), ("0.4", "Coefficient 2 of the Part Load Performance Curve"),
        ("0", "Coefficient 3 of the Part Load Performance Curve"), ("0.6", "Coefficient 4 of the Part Load Performance Curve"),
        ("0", "Design Minimum Flow Rate"), ("Intermittent", "Pump Control Type"),
        ("", "Pump Flow Rate Schedule Name"), ("", "Pump Curve Name"), ("", "Impeller Diameter"),
        ("", "VFD Control Type"), ("", "Pump RPM Schedule Name"), ("", "Minimum Pressure Schedule"),
        ("", "Maximum Pressure Schedule"), ("", "Minimum RPM Schedule"), ("", "Maximum RPM Schedule"),
        ("", "Zone Name"), ("", "Skin Loss Radiative Fraction"), ("PowerPerFlowPerPressure", "Design Power Sizing Method"),
        ("", "Design Electric Power per Unit Flow Rate"), ("1.282051282", "Design Shaft Power per Unit Flow Rate per Unit Head"),
        ("0.25", "Design Minimum Flow Rate Fraction"), ("CHW Pumps", "End-Use Subcategory"))

    obj("PlantEquipmentOperationSchemes", (f"{p} Operation Schemes", "Name"),
        ("PlantEquipmentOperation:CoolingLoad", "Control Scheme 1 Object Type"), (f"{p} Chiller Staging", "Control Scheme 1 Name"),
        ("Always On", "Control Scheme 1 Schedule Name"))
    obj("PlantEquipmentOperation:CoolingLoad", (f"{p} Chiller Staging", "Name"),
        ("0", "Load Range 1 Lower Limit"), ("100000000", "Load Range 1 Upper Limit"), (f"{p} Chillers", "Range 1 Equipment List Name"))
    obj("PlantEquipmentList", (f"{p} Chillers", "Name"),
        *sum([[(ctype, f"Equipment {k} Object Type"), (f"Chiller {k}", f"Equipment {k} Name")] for k in (1, 2, 3)], []))

    if hybrid:
        hybrid_chillers()
        return
    cn = SETS_CHILLER if MODERN else CHILLER
    for k in (1, 2, 3):
        obj("Chiller:Electric:EIR", (f"Chiller {k}", "Name"), ("autosize", "Reference Capacity"),
            ("5.54" if MODERN else "6.04", "Reference COP"),
            ("7.0" if MODERN else "6.67", "Reference Leaving Chilled Water Temperature"),
            ("30.0" if MODERN else "29.44", "Reference Entering Condenser Fluid Temperature"),
            ("autosize", "Reference Chilled Water Flow Rate"), ("autosize", "Reference Condenser Fluid Flow Rate"),
            (cn + " CAPFT", "Cooling Capacity Function of Temperature Curve Name"),
            (cn + " EIRFT", "Electric Input to Cooling Output Ratio Function of Temperature Curve Name"),
            (cn + " EIRFPLR", "Electric Input to Cooling Output Ratio Function of Part Load Ratio Curve Name"),
            ("0.25" if MODERN else "0.20", "Minimum Part Load Ratio"), ("1.03", "Maximum Part Load Ratio"),
            ("1.0", "Optimum Part Load Ratio"), ("0.25" if MODERN else "0.20", "Minimum Unloading Ratio"),
            (f"Chiller {k} CHW Inlet", "Chilled Water Inlet Node Name"), (f"Chiller {k} CHW Outlet", "Chilled Water Outlet Node Name"),
            (f"Chiller {k} CW Inlet", "Condenser Inlet Node Name"), (f"Chiller {k} CW Outlet", "Condenser Outlet Node Name"),
            ("WaterCooled", "Condenser Type"), ("", "Condenser Fan Power Ratio"),
            ("1.0", "Fraction of Compressor Electric Consumption Rejected by Condenser"),
            ("2.0", "Leaving Chilled Water Lower Temperature Limit"), ("LeavingSetpointModulated", "Chiller Flow Mode"),
            ("0", "Design Heat Recovery Water Flow Rate"), ("", "Heat Recovery Inlet Node Name"),
            ("", "Heat Recovery Outlet Node Name"), ("0.5", "Sizing Factor"), ("0", "Basin Heater Capacity"),
            ("2", "Basin Heater Setpoint Temperature"), ("", "Basin Heater Operating Schedule Name"),
            ("", "Condenser Heat Recovery Relative Capacity Fraction"),
            ("", "Heat Recovery Inlet High Temperature Limit Schedule Name"),
            ("", "Heat Recovery Leaving Temperature Setpoint Node Name"), ("Chillers", "End-Use Subcategory"))
    if MODERN:
        sets_chiller_curves()
        return
    raw("! Performance curves copied verbatim from EnergyPlus 22.2 DataSets/Chillers.idf (" + CHILLER + ")")
    raw(chiller_curves())


def hybrid_chillers():
    for k in (1, 2, 3):
        obj("Chiller:Electric:ReformulatedEIR", (f"Chiller {k}", "Name"), (f"{HYB_CHILLER_DESIGN_CAP:.0f}", "Reference Capacity"),
            (f"{HYB_CHILLER_COP}", "Reference COP"), (f"{HYB_CHILLER_TCHW_REF}", "Reference Leaving Chilled Water Temperature"),
            (f"{HYB_CHILLER_TCOND_REF:.2f}", "Reference Leaving Condenser Water Temperature"),
            ("autosize", "Reference Chilled Water Flow Rate"), (f"{hybrid_vw():.5f}", "Reference Condenser Water Flow Rate"),
            (HYB_CHILLER + " CAPFT", "Cooling Capacity Function of Temperature Curve Name"),
            (HYB_CHILLER + " EIRFT", "Electric Input to Cooling Output Ratio Function of Temperature Curve Name"),
            ("LeavingCondenserWaterTemperature", "Electric Input to Cooling Output Ratio Function of Part Load Ratio Curve Type"),
            (HYB_CHILLER + " EIRFPLR", "Electric Input to Cooling Output Ratio Function of Part Load Ratio Curve Name"),
            (HYB_CHILLER_PLR[0], "Minimum Part Load Ratio"), (HYB_CHILLER_PLR[1], "Maximum Part Load Ratio"),
            (HYB_CHILLER_PLR[2], "Optimum Part Load Ratio"), (HYB_CHILLER_PLR[3], "Minimum Unloading Ratio"),
            (f"Chiller {k} CHW Inlet", "Chilled Water Inlet Node Name"), (f"Chiller {k} CHW Outlet", "Chilled Water Outlet Node Name"),
            (f"Chiller {k} CW Inlet", "Condenser Inlet Node Name"), (f"Chiller {k} CW Outlet", "Condenser Outlet Node Name"),
            ("1.0", "Fraction of Compressor Electric Consumption Rejected by Condenser"),
            ("2.0", "Leaving Chilled Water Lower Temperature Limit"), ("LeavingSetpointModulated", "Chiller Flow Mode Type"),
            ("0", "Design Heat Recovery Water Flow Rate"), ("", "Heat Recovery Inlet Node Name"),
            ("", "Heat Recovery Outlet Node Name"), ("0.5", "Sizing Factor"),
            ("", "Condenser Heat Recovery Relative Capacity Fraction"),
            ("", "Heat Recovery Inlet High Temperature Limit Schedule Name"),
            ("", "Heat Recovery Leaving Temperature Setpoint Node Name"), ("Chillers", "End-Use Subcategory"),
            comment=(f"Curves: {HYB_CHILLER} (DataSets/Chillers.idf). Valid range of the curve set: leaving CHW\n"
                     "6.11-10.0 C, leaving condenser water 26.77-41.11 C, PLR 0.29-1.02. EnergyPlus clamps curve\n"
                     "inputs to these limits; models/summarize_dc_run.py counts the hours outside them.\n"
                     "Reference capacity hard-sized to the base model's autosized 552 kW (at the curve reference\n"
                     "6.11 C CHW / 34.8 C leaving condenser): E+ would autosize it as design load / CAPFT(design)\n"
                     "= 482 kW, and SequentialUniformPLR stages on reference capacity, so 2 x 482 kW < peak load\n"
                     "would start the standby chiller for ~2,500 h/yr. Condenser flow hard-sized = cooler flow.") if k == 1 else None)
    raw("! Performance curves copied verbatim from EnergyPlus 22.2 DataSets/Chillers.idf (" + HYB_CHILLER + ")")
    raw(chiller_curves(HYB_CHILLER))


def tower_curves():
    obj("Curve:Cubic", ("Merkel Fan Power fAirFlowRatio", "Name"), ("0.02", "Coefficient1 Constant"),
        ("0.0", "Coefficient2 x"), ("0.0", "Coefficient3 x**2"), ("0.98", "Coefficient4 x**3"),
        ("0.2", "Minimum Value of x"), ("1.0", "Maximum Value of x"), ("0.0", "Minimum Curve Output"),
        ("1.0", "Maximum Curve Output"), ("Dimensionless", "Input Unit Type for X"), ("Dimensionless", "Output Unit Type"),
        comment="Merkel tower curves from EnergyPlus 22.2 ExampleFiles/CoolingTower_MerkelVariableSpeed.idf")
    ua_afr = ("0.1174", "1.1082", "-0.2292") if MODERN else ("0.0", "1.3", "-0.3")    # modern: AFR^0.7 (fill data)
    ua_wfr = ("0.2473", "0.9169", "-0.1617") if MODERN else ("0.1082", "1.667", "-0.7713")  # modern: WFR^0.58
    obj("Curve:Quadratic", ("Merkel UA fAirFlowRatio", "Name"), (ua_afr[0], "Coefficient1 Constant"),
        (ua_afr[1], "Coefficient2 x"), (ua_afr[2], "Coefficient3 x**2"), ("0.2", "Minimum Value of x"),
        ("1.0", "Maximum Value of x"), ("0.0", "Minimum Curve Output"), ("1.0", "Maximum Curve Output"),
        ("Dimensionless", "Input Unit Type for X"), ("Dimensionless", "Output Unit Type"))
    obj("Curve:Linear", ("Merkel UA fWetbulbDifference", "Name"), ("1.0", "Coefficient1 Constant"),
        ("0.0081", "Coefficient2 x"), ("-10", "Minimum Value of x"), ("25.0", "Maximum Value of x"),
        ("0.85", "Minimum Curve Output"), ("1.3", "Maximum Curve Output"),
        ("Dimensionless", "Input Unit Type for X"), ("Dimensionless", "Output Unit Type"))
    obj("Curve:Quadratic", ("Merkel UA fWaterFlowRatio", "Name"), (ua_wfr[0], "Coefficient1 Constant"),
        (ua_wfr[1], "Coefficient2 x"), (ua_wfr[2], "Coefficient3 x**2"), ("0.3", "Minimum Value of x"),
        ("1.5" if MODERN else "1.0", "Maximum Value of x"), ("0.5", "Minimum Curve Output"),
        ("1.3" if MODERN else "1.1", "Maximum Curve Output"),
        ("Dimensionless", "Input Unit Type for X"), ("Dimensionless", "Output Unit Type"))


def merkel_tower(name, inlet, outlet, design_db, design_wb, cells=TOWER_CELLS, sizing_factor="1.0"):
    obj("CoolingTower:VariableSpeed:Merkel", (name, "Name"), (inlet, "Water Inlet Node Name"),
        (outlet, "Water Outlet Node Name"), ("NominalCapacity", "Performance Input Method"),
        ("1.25", "Heat Rejection Capacity and Nominal Capacity Sizing Ratio"), ("autosize", "Nominal Capacity"),
        ("autocalculate", "Free Convection Nominal Capacity"), ("0.1", "Free Convection Nominal Capacity Sizing Factor"),
        ("autocalculate", "Design Water Flow Rate"), ("5.382E-8", "Design Water Flow Rate per Unit of Nominal Capacity"),
        ("autocalculate", "Design Air Flow Rate"), ("", "Design Air Flow Rate Per Unit of Nominal Capacity"),
        (f"{TOWER_MIN_AFR}", "Minimum Air Flow Rate Ratio"), ("autocalculate", "Design Fan Power"),
        ("0.0105", "Design Fan Power Per Unit of Nominal Capacity"),
        ("Merkel Fan Power fAirFlowRatio", "Fan Power Modifier Function of Air Flow Rate Ratio Curve Name"),
        ("autocalculate", "Free Convection Regime Air Flow Rate"), ("0.1", "Free Convection Regime Air Flow Rate Sizing Factor"),
        ("", "Design Air Flow Rate U-Factor Times Area Value"), ("", "Free Convection Regime U-Factor Times Area Value"),
        ("", "Free Convection U-Factor Times Area Value Sizing Factor"),
        ("Merkel UA fAirFlowRatio", "U-Factor Times Area Modifier Function of Air Flow Ratio Curve Name"),
        ("Merkel UA fWetbulbDifference", "U-Factor Times Area Modifier Function of Wetbulb Temperature Difference Curve Name"),
        ("Merkel UA fWaterFlowRatio", "U-Factor Times Area Modifier Function of Water Flow Ratio Curve Name"),
        (f"{design_db}", "Design Inlet Air Dry-Bulb Temperature"), (f"{design_wb}", "Design Inlet Air Wet-Bulb Temperature"),
        (f"{APPROACH}", "Design Approach Temperature"), (f"{DT_CW}", "Design Range Temperature"),
        ("0", "Basin Heater Capacity"), ("2", "Basin Heater Setpoint Temperature"), ("", "Basin Heater Operating Schedule Name"),
        ("SaturatedExit", "Evaporation Loss Mode"), ("", "Evaporation Loss Factor"),
        (f"{DRIFT_PCT}", "Drift Loss Percent"), ("ConcentrationRatio", "Blowdown Calculation Mode"),
        (f"{COC}", "Blowdown Concentration Ratio"), ("", "Blowdown Makeup Water Usage Schedule Name"),
        ("", "Supply Water Storage Tank Name"), ("", "Outdoor Air Inlet Node Name"),
        (f"{cells}", "Number of Cells"), ("MaximalCell", "Cell Control"),
        (f"{CELL_MIN_WFR}", "Cell Minimum  Water Flow Rate Fraction"), (f"{CELL_MAX_WFR}", "Cell Maximum Water Flow Rate Fraction"),
        (sizing_factor, "Sizing Factor"), ("Towers", "End-Use Subcategory"))


def cw_loop(design_db, design_wb, wse=False, idle_tower=False):
    section("Condenser water loop: multi-cell CoolingTower:VariableSpeed:Merkel, variable-speed CW pump, WB reset")
    p = "CW"
    branch(f"{p} Supply Inlet Branch", [("Pump:VariableSpeed", f"{p} Pump", f"{p} Supply Inlet Node", f"{p} Pump Outlet Node")])
    sup = []
    towers = ["Tower 1"] + (["Tower 2 (idle test)"] if idle_tower else [])
    for k, tn in enumerate(towers, 1):
        n = f"{p} Tower{k} Branch"
        branch(n, [("CoolingTower:VariableSpeed:Merkel", tn, f"Tower {k} Water Inlet", f"Tower {k} Water Outlet")])
        sup.append(n)
    branch(f"{p} Supply Bypass Branch", [("Pipe:Adiabatic", f"{p} Supply Bypass Pipe", f"{p} Supply Bypass Inlet", f"{p} Supply Bypass Outlet")])
    pipe(f"{p} Supply Bypass Pipe", f"{p} Supply Bypass Inlet", f"{p} Supply Bypass Outlet")
    sup.append(f"{p} Supply Bypass Branch")
    branch(f"{p} Supply Outlet Branch", [("Pipe:Adiabatic", f"{p} Supply Outlet Pipe", f"{p} Supply Mixer Outlet", f"{p} Supply Outlet Node")])
    pipe(f"{p} Supply Outlet Pipe", f"{p} Supply Mixer Outlet", f"{p} Supply Outlet Node")
    loop_side(p, f"{p} Supply Inlet Branch", sup, f"{p} Supply Outlet Branch", "Supply")

    branch(f"{p} Demand Inlet Branch", [("Pipe:Adiabatic", f"{p} Demand Inlet Pipe", f"{p} Demand Inlet Node", f"{p} Demand Inlet Pipe Outlet")])
    pipe(f"{p} Demand Inlet Pipe", f"{p} Demand Inlet Node", f"{p} Demand Inlet Pipe Outlet")
    dem = []
    for k in (1, 2, 3):
        n = f"{p} Chiller{k} Branch"
        branch(n, [("Chiller:Electric:EIR", f"Chiller {k}", f"Chiller {k} CW Inlet", f"Chiller {k} CW Outlet")])
        dem.append(n)
    if wse:
        branch(f"{p} WSE HX Branch", [("HeatExchanger:FluidToFluid", "WSE HX", f"{p} WSE HX Inlet", f"{p} WSE HX Outlet")])
        dem.append(f"{p} WSE HX Branch")
    branch(f"{p} Demand Bypass Branch", [("Pipe:Adiabatic", f"{p} Demand Bypass Pipe", f"{p} Demand Bypass Inlet", f"{p} Demand Bypass Outlet")])
    pipe(f"{p} Demand Bypass Pipe", f"{p} Demand Bypass Inlet", f"{p} Demand Bypass Outlet")
    dem.append(f"{p} Demand Bypass Branch")
    branch(f"{p} Demand Outlet Branch", [("Pipe:Adiabatic", f"{p} Demand Outlet Pipe", f"{p} Demand Outlet Pipe Inlet", f"{p} Demand Outlet Node")])
    pipe(f"{p} Demand Outlet Pipe", f"{p} Demand Outlet Pipe Inlet", f"{p} Demand Outlet Node")
    loop_side(p, f"{p} Demand Inlet Branch", dem, f"{p} Demand Outlet Branch", "Demand")

    obj("CondenserLoop", (f"{p} Loop", "Name"), ("Water", "Fluid Type"), ("", "User Defined Fluid Type"),
        (f"{p} Operation Schemes", "Condenser Equipment Operation Scheme Name"),
        (f"{p} Supply Outlet Node", "Condenser Loop Temperature Setpoint Node Name"),
        ("80", "Maximum Loop Temperature"), ("5", "Minimum Loop Temperature"),
        ("autosize", "Maximum Loop Flow Rate"), ("0", "Minimum Loop Flow Rate"), ("autocalculate", "Condenser Loop Volume"),
        (f"{p} Supply Inlet Node", "Condenser Side Inlet Node Name"), (f"{p} Supply Outlet Node", "Condenser Side Outlet Node Name"),
        (f"{p} Supply Branches", "Condenser Side Branch List Name"), (f"{p} Supply Connectors", "Condenser Side Connector List Name"),
        (f"{p} Demand Inlet Node", "Demand Side Inlet Node Name"), (f"{p} Demand Outlet Node", "Demand Side Outlet Node Name"),
        (f"{p} Demand Branches", "Condenser Demand Side Branch List Name"), (f"{p} Demand Connectors", "Condenser Demand Side Connector List Name"),
        ("SequentialLoad", "Load Distribution Scheme"))
    obj("Sizing:Plant", (f"{p} Loop", "Plant or Condenser Loop Name"), ("Condenser", "Loop Type"),
        (f"{design_wb + APPROACH:.2f}", "Design Loop Exit Temperature"),
        (f"{DT_CW}", "Loop Design Temperature Difference"),
        comment="Design Loop Exit Temperature = design WB + approach (set by set_design_days.py)")
    obj("SetpointManager:FollowOutdoorAirTemperature", (f"{p} WB Reset SPM", "Name"), ("Temperature", "Control Variable"),
        ("OutdoorAirWetBulb", "Reference Temperature Type"), (f"{APPROACH}", "Offset Temperature Difference"),
        (f"{CW_MAX}", "Maximum Setpoint Temperature"), (f"{CW_MIN_WSE if wse else CW_MIN}", "Minimum Setpoint Temperature"),
        (f"{p} Supply Outlet Node", "Setpoint Node or NodeList Name"))
    obj("Pump:VariableSpeed", (f"{p} Pump", "Name"), (f"{p} Supply Inlet Node", "Inlet Node Name"),
        (f"{p} Pump Outlet Node", "Outlet Node Name"), ("autosize", "Design Maximum Flow Rate"),
        (f"{CW_PUMP_HEAD:.0f}", "Design Pump Head"), ("autosize", "Design Power Consumption"),
        ("0.92", "Motor Efficiency"), ("0.0", "Fraction of Motor Inefficiencies to Fluid Stream"),
        ("0", "Coefficient 1 of the Part Load Performance Curve"), ("1", "Coefficient 2 of the Part Load Performance Curve"),
        ("0", "Coefficient 3 of the Part Load Performance Curve"), ("0", "Coefficient 4 of the Part Load Performance Curve"),
        ("0", "Design Minimum Flow Rate"), ("Intermittent", "Pump Control Type"),
        ("", "Pump Flow Rate Schedule Name"), ("", "Pump Curve Name"), ("", "Impeller Diameter"),
        ("", "VFD Control Type"), ("", "Pump RPM Schedule Name"), ("", "Minimum Pressure Schedule"),
        ("", "Maximum Pressure Schedule"), ("", "Minimum RPM Schedule"), ("", "Maximum RPM Schedule"),
        ("", "Zone Name"), ("", "Skin Loss Radiative Fraction"), ("PowerPerFlowPerPressure", "Design Power Sizing Method"),
        ("", "Design Electric Power per Unit Flow Rate"), ("1.282051282", "Design Shaft Power per Unit Flow Rate per Unit Head"),
        ("0", "Design Minimum Flow Rate Fraction"), ("CW Pumps", "End-Use Subcategory"))
    obj("CondenserEquipmentOperationSchemes", (f"{p} Operation Schemes", "Name"),
        ("PlantEquipmentOperation:CoolingLoad", "Control Scheme 1 Object Type"), (f"{p} Tower Operation", "Control Scheme 1 Name"),
        ("Always On", "Control Scheme 1 Schedule Name"))
    if idle_tower:
        # DIAGNOSTIC ONLY. Tower 2 is plumbed in parallel. With threshold=None it is never in an
        # active load range (always off); otherwise it is switched on only above the threshold
        # (so it toggles between running and idle).
        thr = idle_tower if isinstance(idle_tower, float) else 1e8
        obj("PlantEquipmentOperation:CoolingLoad", (f"{p} Tower Operation", "Name"),
            ("0", "Load Range 1 Lower Limit"), (f"{thr:.0f}", "Load Range 1 Upper Limit"), (f"{p} Towers", "Range 1 Equipment List Name"),
            (f"{thr:.0f}", "Load Range 2 Lower Limit"), ("1000000000", "Load Range 2 Upper Limit"), (f"{p} Towers Both", "Range 2 Equipment List Name"))
        obj("CondenserEquipmentList", (f"{p} Towers", "Name"),
            ("CoolingTower:VariableSpeed:Merkel", "Equipment 1 Object Type"), ("Tower 1", "Equipment 1 Name"))
        obj("CondenserEquipmentList", (f"{p} Towers Both", "Name"),
            ("CoolingTower:VariableSpeed:Merkel", "Equipment 1 Object Type"), ("Tower 1", "Equipment 1 Name"),
            ("CoolingTower:VariableSpeed:Merkel", "Equipment 2 Object Type"), ("Tower 2 (idle test)", "Equipment 2 Name"))
    else:
        obj("PlantEquipmentOperation:CoolingLoad", (f"{p} Tower Operation", "Name"),
            ("0", "Load Range 1 Lower Limit"), ("100000000", "Load Range 1 Upper Limit"), (f"{p} Towers", "Range 1 Equipment List Name"))
        obj("CondenserEquipmentList", (f"{p} Towers", "Name"),
            ("CoolingTower:VariableSpeed:Merkel", "Equipment 1 Object Type"), ("Tower 1", "Equipment 1 Name"))
    tower_curves()
    for k, tn in enumerate(towers, 1):
        merkel_tower(tn, f"Tower {k} Water Inlet", f"Tower {k} Water Outlet", design_db, design_wb,
                     sizing_factor=f"{WSE_TOWER_SIZING_FACTOR:.4f}" if wse else "1.0")


def load_sdd():
    import importlib.util
    spec = importlib.util.spec_from_file_location("sdd", os.path.join(HERE, "set_design_days.py"))
    sdd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sdd)
    return sdd


def hybrid_q_nom():
    """Nominal (design) heat rejection per cooler [W] = condenser heat of one chiller at its
    reference COP; N_HYB = 3 coolers for 2 duty chillers gives N+1."""
    return HYB_CHILLER_DESIGN_CAP * (1.0 + 1.0 / HYB_CHILLER_COP)


def hybrid_vw():
    """Design water flow per cooler = reference condenser flow per chiller [m3/s] (hard-sized on both:
    EnergyPlus sizes the ReformulatedEIR condenser flow from the *reference* capacity, which is
    design capacity / CAPFT(design) = 0.87 x design here, i.e. a 6.4 K instead of 5.6 K range)."""
    return hybrid_q_nom() / (HYB_RHO_W * HYB_CP_W * HYB_RANGE)


def hybrid_cw_loop(info):
    section(f"Condenser water loop: {N_HYB} x FluidCooler:TwoSpeed (hybrid adiabatic dry coolers, N+1), "
            "variable-speed CW pump, dry-bulb reset")
    sdd = load_sdd()
    q = float(round(hybrid_q_nom()))          # values as written to the IDF (set_design_days.py reads them back)
    vw = round(hybrid_vw(), 5)
    d = sdd.hybrid_design(info, q, HYB_APPROACH, HYB_RANGE, HYB_AIR_DT, HYB_PAD_EFF, v_w=vw, low_ua_frac=HYB_LOW_UA_FRAC)
    for nt in d["notes"]:
        print(nt)
    p = "CW"
    branch(f"{p} Supply Inlet Branch", [("Pump:VariableSpeed", f"{p} Pump", f"{p} Supply Inlet Node", f"{p} Pump Outlet Node")])
    sup = []
    coolers = [f"Hybrid Cooler {k}" for k in range(1, N_HYB + 1)]
    for k, cn in enumerate(coolers, 1):
        n = f"{p} Hybrid Cooler{k} Branch"
        branch(n, [("FluidCooler:TwoSpeed", cn, f"{cn} Water Inlet", f"{cn} Water Outlet")])
        sup.append(n)
    branch(f"{p} Supply Bypass Branch", [("Pipe:Adiabatic", f"{p} Supply Bypass Pipe", f"{p} Supply Bypass Inlet", f"{p} Supply Bypass Outlet")])
    pipe(f"{p} Supply Bypass Pipe", f"{p} Supply Bypass Inlet", f"{p} Supply Bypass Outlet")
    sup.append(f"{p} Supply Bypass Branch")
    branch(f"{p} Supply Outlet Branch", [("Pipe:Adiabatic", f"{p} Supply Outlet Pipe", f"{p} Supply Mixer Outlet", f"{p} Supply Outlet Node")])
    pipe(f"{p} Supply Outlet Pipe", f"{p} Supply Mixer Outlet", f"{p} Supply Outlet Node")
    loop_side(p, f"{p} Supply Inlet Branch", sup, f"{p} Supply Outlet Branch", "Supply")

    branch(f"{p} Demand Inlet Branch", [("Pipe:Adiabatic", f"{p} Demand Inlet Pipe", f"{p} Demand Inlet Node", f"{p} Demand Inlet Pipe Outlet")])
    pipe(f"{p} Demand Inlet Pipe", f"{p} Demand Inlet Node", f"{p} Demand Inlet Pipe Outlet")
    dem = []
    for k in (1, 2, 3):
        n = f"{p} Chiller{k} Branch"
        branch(n, [("Chiller:Electric:ReformulatedEIR", f"Chiller {k}", f"Chiller {k} CW Inlet", f"Chiller {k} CW Outlet")])
        dem.append(n)
    branch(f"{p} Demand Bypass Branch", [("Pipe:Adiabatic", f"{p} Demand Bypass Pipe", f"{p} Demand Bypass Inlet", f"{p} Demand Bypass Outlet")])
    pipe(f"{p} Demand Bypass Pipe", f"{p} Demand Bypass Inlet", f"{p} Demand Bypass Outlet")
    dem.append(f"{p} Demand Bypass Branch")
    branch(f"{p} Demand Outlet Branch", [("Pipe:Adiabatic", f"{p} Demand Outlet Pipe", f"{p} Demand Outlet Pipe Inlet", f"{p} Demand Outlet Node")])
    pipe(f"{p} Demand Outlet Pipe", f"{p} Demand Outlet Pipe Inlet", f"{p} Demand Outlet Node")
    loop_side(p, f"{p} Demand Inlet Branch", dem, f"{p} Demand Outlet Branch", "Demand")

    obj("CondenserLoop", (f"{p} Loop", "Name"), ("Water", "Fluid Type"), ("", "User Defined Fluid Type"),
        (f"{p} Operation Schemes", "Condenser Equipment Operation Scheme Name"),
        (f"{p} Supply Outlet Node", "Condenser Loop Temperature Setpoint Node Name"),
        ("80", "Maximum Loop Temperature"), ("5", "Minimum Loop Temperature"),
        ("autosize", "Maximum Loop Flow Rate"), ("0", "Minimum Loop Flow Rate"), ("autocalculate", "Condenser Loop Volume"),
        (f"{p} Supply Inlet Node", "Condenser Side Inlet Node Name"), (f"{p} Supply Outlet Node", "Condenser Side Outlet Node Name"),
        (f"{p} Supply Branches", "Condenser Side Branch List Name"), (f"{p} Supply Connectors", "Condenser Side Connector List Name"),
        (f"{p} Demand Inlet Node", "Demand Side Inlet Node Name"), (f"{p} Demand Outlet Node", "Demand Side Outlet Node Name"),
        (f"{p} Demand Branches", "Condenser Demand Side Branch List Name"), (f"{p} Demand Connectors", "Condenser Demand Side Connector List Name"),
        ("UniformLoad", "Load Distribution Scheme"),
        comment="UniformLoad: all coolers of the N+1 bank run and share the flow (each ~2/3 of design with 2 chillers)")
    obj("Sizing:Plant", (f"{p} Loop", "Plant or Condenser Loop Name"), ("Condenser", "Loop Type"),
        (f"{d['exit']:.2f}", "Design Loop Exit Temperature"),
        (f"{DT_CW}", "Loop Design Temperature Difference"),
        comment="Design Loop Exit Temperature = cooler design entering (pad-cooled) air + approach (set by set_design_days.py)")
    obj("OutdoorAir:Node", (HYB_NODE, "Name"),
        comment="Shared air inlet of all hybrid coolers. A plugin/EMS program overrides its dry-bulb and wet-bulb\n"
                "(actuators 'Outdoor Air System Node' / 'Drybulb Temperature', 'Wetbulb Temperature') to model\n"
                "wetted-pad pre-cooling. Without that the node carries the site outdoor air state (dry operation).")
    obj("SetpointManager:FollowSystemNodeTemperature", (HYB_SPM, "Name"), ("Temperature", "Control Variable"),
        (HYB_NODE, "Reference Node Name"), ("NodeDryBulb", "Reference Temperature Type"),
        (f"{HYB_APPROACH}", "Offset Temperature Difference"), (f"{HYB_CW_MAX}", "Maximum Limit Setpoint Temperature"),
        (f"{HYB_CW_MIN}", "Minimum Limit Setpoint Temperature"), (f"{p} Supply Outlet Node", "Setpoint Node or NodeList Name"),
        comment="CW supply setpoint = cooler inlet air dry-bulb + design approach, limited to the chiller's range")
    obj("Pump:VariableSpeed", (f"{p} Pump", "Name"), (f"{p} Supply Inlet Node", "Inlet Node Name"),
        (f"{p} Pump Outlet Node", "Outlet Node Name"), ("autosize", "Design Maximum Flow Rate"),
        (f"{CW_PUMP_HEAD:.0f}", "Design Pump Head"), ("autosize", "Design Power Consumption"),
        ("0.92", "Motor Efficiency"), ("0.0", "Fraction of Motor Inefficiencies to Fluid Stream"),
        ("0", "Coefficient 1 of the Part Load Performance Curve"), ("1", "Coefficient 2 of the Part Load Performance Curve"),
        ("0", "Coefficient 3 of the Part Load Performance Curve"), ("0", "Coefficient 4 of the Part Load Performance Curve"),
        ("0", "Design Minimum Flow Rate"), ("Intermittent", "Pump Control Type"),
        ("", "Pump Flow Rate Schedule Name"), ("", "Pump Curve Name"), ("", "Impeller Diameter"),
        ("", "VFD Control Type"), ("", "Pump RPM Schedule Name"), ("", "Minimum Pressure Schedule"),
        ("", "Maximum Pressure Schedule"), ("", "Minimum RPM Schedule"), ("", "Maximum RPM Schedule"),
        ("", "Zone Name"), ("", "Skin Loss Radiative Fraction"), ("PowerPerFlowPerPressure", "Design Power Sizing Method"),
        ("", "Design Electric Power per Unit Flow Rate"), ("1.282051282", "Design Shaft Power per Unit Flow Rate per Unit Head"),
        ("0", "Design Minimum Flow Rate Fraction"), ("CW Pumps", "End-Use Subcategory"))
    obj("CondenserEquipmentOperationSchemes", (f"{p} Operation Schemes", "Name"),
        ("PlantEquipmentOperation:CoolingLoad", "Control Scheme 1 Object Type"), (f"{p} Cooler Operation", "Control Scheme 1 Name"),
        ("Always On", "Control Scheme 1 Schedule Name"))
    obj("PlantEquipmentOperation:CoolingLoad", (f"{p} Cooler Operation", "Name"),
        ("0", "Load Range 1 Lower Limit"), ("100000000", "Load Range 1 Upper Limit"), (f"{p} Coolers", "Range 1 Equipment List Name"))
    obj("CondenserEquipmentList", (f"{p} Coolers", "Name"),
        *sum([[("FluidCooler:TwoSpeed", f"Equipment {k} Object Type"), (cn, f"Equipment {k} Name")]
              for k, cn in enumerate(coolers, 1)], []))
    sdd_tag = sdd.hyb_tag({"approach": HYB_APPROACH, "range": HYB_RANGE, "air_dT": HYB_AIR_DT,
                           "low_UA_frac": HYB_LOW_UA_FRAC, "pad_eff": HYB_PAD_EFF})
    vair = float(f"{d['vair']:.3f}")       # as written, so that set_design_days.py reproduces the file
    for k, cn in enumerate(coolers, 1):
        cmt = None
        if k == 1:
            cmt = ("Hard-sized per cooler (EnergyPlus 22.2 autosizes High Fan Speed Air Flow Rate as\n"
                   "Q/(EWT-EAT)*4 'm3/s', ~1000x too large, and fan power as 0.0105 W/W):\n"
                   f"  nominal capacity = chiller design capacity {HYB_CHILLER_DESIGN_CAP/1e3:.0f} kW x (1 + 1/COP_ref {HYB_CHILLER_COP})\n"
                   f"  water flow = Q/(rho cp range), air flow = Q/(rho_air cp_air {HYB_AIR_DT:g} K), fan = {HYB_FAN_W_PER_W} W/W x Q\n"
                   f"  low speed: air {sdd.HYB_LOW_AIR_FRAC:g} x high, fan {HYB_LOW_FAN_FRAC} x high, capacity chosen so that E+ sizes\n"
                   f"  UA_low = {HYB_LOW_UA_FRAC} x UA_high\n"
                   "Design air state = pad-cooled 0.4% DB=>MWB condition (set_design_days.py updates it per site).\n"
                   "The next line is read by set_design_days.py; keep it directly above each cooler.\n")
        obj("FluidCooler:TwoSpeed", (cn, "Name"), (f"{cn} Water Inlet", "Water Inlet Node Name"),
            (f"{cn} Water Outlet", "Water Outlet Node Name"), ("NominalCapacity", "Performance Input Method"),
            ("", "High Fan Speed U-factor Times Area Value"), ("", "Low Fan Speed U-factor Times Area Value"),
            ("", "Low Fan Speed U-Factor Times Area Sizing Factor"),
            (f"{q:.0f}", "High Speed Nominal Capacity"), (f"{d['qlow']:.0f}", "Low Speed Nominal Capacity"),
            ("", "Low Speed Nominal Capacity Sizing Factor"),
            (f"{d['ewt']:.2f}", "Design Entering Water Temperature"), (f"{d['eat']:.2f}", "Design Entering Air Temperature"),
            (f"{d['eawb']:.2f}", "Design Entering Air Wet-bulb Temperature"),
            (f"{vw:.5f}", "Design Water Flow Rate"), (f"{vair:.3f}", "High Fan Speed Air Flow Rate"),
            (f"{HYB_FAN_W_PER_W * q:.0f}", "High Fan Speed Fan Power"),
            (f"{sdd.HYB_LOW_AIR_FRAC * vair:.3f}", "Low Fan Speed Air Flow Rate"),
            ("", "Low Fan Speed Air Flow Rate Sizing Factor"),
            (f"{HYB_LOW_FAN_FRAC * HYB_FAN_W_PER_W * q:.0f}", "Low Fan Speed Fan Power"),
            ("", "Low Fan Speed Fan Power Sizing Factor"), (HYB_NODE, "Outdoor Air Inlet Node Name"),
            comment=(cmt or "") + sdd_tag[2:])


def outputs(extra_towers=1, hybrid=False):
    section("Outputs")
    obj("Output:VariableDictionary", ("IDF", "Key Field"), ("Unsorted", "Sort Option"))
    obj("Output:Table:SummaryReports", ("AllSummary", "Report 1 Name"))
    obj("OutputControl:Table:Style", ("CommaAndHTML", "Column Separator"), ("JtoKWH", "Unit Conversion"))
    obj("Output:SQLite", ("SimpleAndTabular", "Option Type"))
    obj("Output:Diagnostics", ("DisplayAdvancedReportVariables", "Key 1"))
    for m in ["Electricity:Facility", "ITE-CPU:InteriorEquipment:Electricity", "ITE-Fans:InteriorEquipment:Electricity",
              "ITE-UPS:InteriorEquipment:Electricity", "InteriorLights:Electricity", "Cooling:Electricity",
              "Chillers:Cooling:Electricity", "HeatRejection:Electricity", "Pumps:Electricity", "Fans:Electricity"] + \
             ([] if hybrid else ["Water:Facility", "HeatRejection:Water", "MainsWater:Facility"]):
        obj("Output:Meter", (m, "Key Name"), ("Hourly", "Reporting Frequency"))
        obj("Output:Meter", (m, "Key Name"), ("RunPeriod", "Reporting Frequency"))
    v = [
        ("*", "Site Outdoor Air Drybulb Temperature"), ("*", "Site Outdoor Air Wetbulb Temperature"),
        ("*", "Site Outdoor Air Humidity Ratio"), ("*", "Site Outdoor Air Barometric Pressure"),
        ("*", "ITE Total Heat Gain to Zone Rate"), ("*", "ITE CPU Electricity Rate"), ("*", "ITE Fan Electricity Rate"),
        ("*", "ITE UPS Electricity Rate"), ("*", "ITE Air Inlet Dry-Bulb Temperature"),
        ("*", "ITE Air Inlet Operating Range Exceeded Time"), ("*", "ITE Standard Density Air Volume Flow Rate"),
        ("*", "Zone Air Temperature"), ("*", "Zone Air Relative Humidity"),
        ("*", "Fan Electricity Rate"), ("*", "Fan Air Mass Flow Rate"),
        ("*", "Cooling Coil Total Cooling Rate"),
        ("DataHall1 CRAH CHW Coil Water Outlet", "System Node Temperature"),
        ("DataHall1 CRAH CHW Coil Water Outlet", "System Node Mass Flow Rate"),
        ("*", "Chiller Electricity Rate"), ("*", "Chiller Evaporator Cooling Rate"), ("*", "Chiller Condenser Heat Transfer Rate"),
        ("*", "Chiller Part Load Ratio"), ("*", "Chiller COP"), ("*", "Chiller Evaporator Outlet Temperature"),
        ("*", "Chiller Evaporator Inlet Temperature"), ("*", "Chiller Condenser Inlet Temperature"),
        ("*", "Chiller Condenser Outlet Temperature"), ("*", "Chiller Evaporator Mass Flow Rate"),
        ("*", "Chiller Condenser Mass Flow Rate"), ("*", "Chiller Cycling Ratio"),
        ("*", "Pump Electricity Rate"), ("*", "Pump Mass Flow Rate"),
    ]
    hyb_ts = [   # hybrid: fluid coolers, their air node, condenser reset; also reported at Timestep
        ("*", "Cooling Tower Heat Transfer Rate"), ("*", "Cooling Tower Inlet Temperature"),
        ("*", "Cooling Tower Outlet Temperature"), ("*", "Cooling Tower Mass Flow Rate"),
        ("*", "Cooling Tower Fan Electricity Rate"), ("*", "Cooling Tower Fan Electricity Energy"),
        (HYB_NODE, "System Node Temperature"), (HYB_NODE, "System Node Wetbulb Temperature"),
        (HYB_NODE, "System Node Humidity Ratio"), (HYB_NODE, "System Node Pressure"),
        ("CW Supply Outlet Node", "System Node Temperature"), ("CW Supply Outlet Node", "System Node Setpoint Temperature"),
        ("CW Supply Inlet Node", "System Node Temperature"), ("CW Supply Outlet Node", "System Node Mass Flow Rate"),
        ("*", "Site Outdoor Air Drybulb Temperature"), ("*", "Site Outdoor Air Wetbulb Temperature"),
        ("*", "Site Outdoor Air Humidity Ratio"), ("*", "Site Outdoor Air Barometric Pressure"),
        ("*", "Chiller Electricity Rate"), ("*", "Chiller Part Load Ratio"),
        ("*", "Chiller Evaporator Outlet Temperature"), ("*", "Chiller Condenser Inlet Temperature"),
        ("*", "Chiller Condenser Outlet Temperature"),
    ]
    v += [] if hybrid else [
        ("*", "Cooling Tower Heat Transfer Rate"), ("*", "Cooling Tower Inlet Temperature"),
        ("*", "Cooling Tower Outlet Temperature"), ("*", "Cooling Tower Mass Flow Rate"),
        ("*", "Cooling Tower Fan Speed Ratio"), ("*", "Cooling Tower Operating Cells Count"),
        ("*", "Cooling Tower Fan Electricity Rate"), ("*", "Cooling Tower Fan Electricity Energy"),
        ("*", "Cooling Tower Make Up Water Volume Flow Rate"), ("*", "Cooling Tower Make Up Water Volume"),
        ("*", "Cooling Tower Water Evaporation Volume Flow Rate"), ("*", "Cooling Tower Water Drift Volume Flow Rate"),
        ("*", "Cooling Tower Water Blowdown Volume Flow Rate"), ("*", "Cooling Tower Make Up Mains Water Volume"),
        ("*", "Cooling Tower Water Evaporation Volume"), ("*", "Cooling Tower Water Drift Volume"),
        ("*", "Cooling Tower Water Blowdown Volume"),
    ]
    v += [
        ("CHW Supply Outlet Node", "System Node Temperature"), ("CHW Supply Inlet Node", "System Node Temperature"),
        ("CHW Supply Outlet Node", "System Node Setpoint Temperature"), ("CHW Supply Outlet Node", "System Node Mass Flow Rate"),
        ("CW Supply Outlet Node", "System Node Temperature"), ("CW Supply Inlet Node", "System Node Temperature"),
        ("CW Supply Outlet Node", "System Node Setpoint Temperature"), ("CW Supply Outlet Node", "System Node Mass Flow Rate"),
        ("*", "Plant Supply Side Unmet Demand Rate"),
        ("DataHall1 CRAH Supply Outlet Node", "System Node Temperature"),
        ("DataHall2 CRAH Supply Outlet Node", "System Node Temperature"),
    ]
    if hybrid:
        v = [x for x in v if x not in hyb_ts] + hyb_ts
    for k, n in v:
        obj("Output:Variable", (k, "Key Value"), (n, "Variable Name"), ("Hourly", "Reporting Frequency"))
    if hybrid:
        for k, n in hyb_ts:
            obj("Output:Variable", (k, "Key Value"), (n, "Variable Name"), ("Timestep", "Reporting Frequency"))


def build(args):
    OUT.clear()
    raw("! " + "=" * 77)
    hybrid = args.heat_rejection == "hybrid"
    if hybrid:
        raw("! datacenter_chiller_hybrid.idf  (EnergyPlus 22.2)")
        raw("! Representative ~1 MW-IT data center: 2 data halls, CRAH (CHW coil + VAV fan),")
        raw("! 3 x 50% water-cooled high-lift centrifugal chillers (N+1), variable-primary CHW at 10 C,")
        raw(f"! {N_HYB} x FluidCooler:TwoSpeed hybrid adiabatic dry coolers (N+1) on one OutdoorAir:Node")
        raw(f"! '{HYB_NODE}', condenser water dry-bulb reset '{HYB_SPM}'.")
        raw("! Without an EMS/plugin override of that node this is a plain DRY-cooler plant.")
    else:
        raw("! datacenter_chiller_tower" + ("_wse" if args.wse else "") + ".idf  (EnergyPlus 22.2)")
        raw("! Representative ~1 MW-IT water-cooled data center: 2 data halls, CRAH (CHW coil + VAV fan),")
        raw("! 3 x 50% water-cooled VSD centrifugal chillers (N+1), variable-primary CHW at 10 C,")
        raw("! 3-cell CoolingTower:VariableSpeed:Merkel, condenser water wet-bulb reset.")
    raw("! GENERATED by models/build_datacenter_idf.py -- edit the generator, not this file.")
    raw("! Design basis and sources: models/DATACENTER_MODEL.md")
    raw("! " + "=" * 77)
    simulation_control(args.timestep)
    info = location_and_design_days()
    schedules()
    envelope()
    internal_loads()
    air_side()
    chw_loop(args.wse, hybrid=hybrid)
    if hybrid:
        hybrid_cw_loop(info)
    else:
        cw_loop(info["wb_db"], info["wb_wb"], wse=args.wse,
                idle_tower=(args.tower2_threshold or True) if args.idle_tower_test else False)
    if args.wse:
        wse_objects()
    outputs(hybrid=hybrid)
    with open(args.out, "w") as f:
        f.write("\n".join(OUT))
    print("wrote", args.out)


def wse_objects():
    section("Integrated water-side economizer (plate HX, CHW return pre-cooling)")
    obj("HeatExchanger:FluidToFluid", ("WSE HX", "Name"), ("Always On", "Availability Schedule Name"),
        ("CW WSE HX Inlet", "Loop Demand Side Inlet Node Name"), ("CW WSE HX Outlet", "Loop Demand Side Outlet Node Name"),
        ("autosize", "Loop Demand Side Design Flow Rate"),
        ("CHW Pump Outlet Node", "Loop Supply Side Inlet Node Name"), ("CHW WSE Outlet Node", "Loop Supply Side Outlet Node Name"),
        ("autosize", "Loop Supply Side Design Flow Rate"), ("CounterFlow", "Heat Exchange Model Type"),
        (f"{WSE_UA:.0f}", "Heat Exchanger U-Factor Times Area Value"), ("CoolingSetpointModulated", "Control Type"),
        ("CHW WSE Outlet Node", "Heat Exchanger Setpoint Node Name"),
        (f"{WSE_DT_MIN}", "Minimum Temperature Difference to Activate Heat Exchanger"),
        ("FreeCooling", "Heat Transfer Metering End Use Type"), ("", "Component Override Loop Supply Side Inlet Node Name"),
        ("", "Component Override Loop Demand Side Inlet Node Name"), ("", "Component Override Cooling Control Temperature Mode"),
        ("1.0", "Sizing Factor"), ("2.0", "Operation Minimum Temperature Limit"), ("", "Operation Maximum Temperature Limit"))
    for v in ["Fluid Heat Exchanger Heat Transfer Rate", "Fluid Heat Exchanger Operation Status",
              "Fluid Heat Exchanger Loop Supply Side Inlet Temperature", "Fluid Heat Exchanger Loop Supply Side Outlet Temperature",
              "Fluid Heat Exchanger Loop Demand Side Inlet Temperature", "Fluid Heat Exchanger Loop Demand Side Mass Flow Rate"]:
        obj("Output:Variable", ("*", "Key Value"), (v, "Variable Name"), ("Hourly", "Reporting Frequency"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wse", action="store_true", help="integrated water-side economizer variant")
    ap.add_argument("--idle-tower-test", action="store_true", help="add a second, never-operated tower (diagnostic)")
    ap.add_argument("--tower2-threshold", type=float, help="with --idle-tower-test: switch tower 2 on above this condenser load [W]")
    ap.add_argument("--heat-rejection", choices=("tower", "hybrid"), default="tower",
                    help="tower: evaporative Merkel tower (default, unchanged); hybrid: hybrid adiabatic dry coolers")
    ap.add_argument("--timestep", type=int, default=6)
    ap.add_argument("--plant", choices=("base", "modern"), default="base",
                    help="modern: equipment-informed variant (15.5 C CHW and CW floor, 90.1 Set S chiller curves, "
                         "fill-data UA curves, tower min air 0.25, cell water 0.5-1.2); docs/EQUIPMENT_SPECS.md")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.plant == "modern":
        if a.heat_rejection != "tower" or a.wse:
            raise SystemExit("--plant modern is for the tower plant only")
        if not a.out:
            raise SystemExit("give --out for --plant modern (keep models/ for the base model)")
        set_modern()
    if a.wse:
        print("WARNING: --wse is EXPERIMENTAL and not validated (CHW unmet hours, coil/HX interaction); "
              "see models/DATACENTER_MODEL.md, 'Known limitations'.")
    if a.heat_rejection == "hybrid" and (a.wse or a.idle_tower_test):
        raise SystemExit("--wse / --idle-tower-test are tower-plant options; not available with --heat-rejection hybrid")
    if not a.out:
        if a.wse or a.idle_tower_test:
            raise SystemExit("give --out for diagnostic/experimental variants (keep models/ for the base model)")
        a.out = os.path.join(HERE, "datacenter_chiller_tower.idf" if a.heat_rejection == "tower"
                             else "datacenter_chiller_hybrid.idf")
    build(a)
