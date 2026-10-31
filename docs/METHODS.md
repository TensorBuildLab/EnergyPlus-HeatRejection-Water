# Technical Reference: Cooling Tower Water Consumption Methods

*tower_water v0.2 · EnergyPlus 22.2 Python Plugin · Liang Zhang, University of Arizona*

This document records every equation the tool implements, the assumptions behind it, where it is coded,
and the literature it comes from. Section numbers match the comments in `src/tower_water/*.py`.
References are listed in §9; DOIs and the check of every reference and claim are in `docs/REFERENCES_CHECK.md`,
and BibTeX in `paper/references.bib`.

---

## 1. Concept: one operating point, many water models

EnergyPlus solves the condenser loop with its own tower model and gives, every system timestep,
an **operating point**:

| Symbol | Meaning | EnergyPlus source |
|---|---|---|
| $T_{w,i}$, $T_{w,o}$ | water temperature entering / leaving the tower | `Cooling Tower Inlet/Outlet Temperature` |
| $\dot m_{w,i}$ | water mass flow entering | `Cooling Tower Mass Flow Rate` |
| $\dot Q$ | heat rejected, $\dot m_{w,i} c_{pw}(T_{w,i}-T_{w,o})$ | `Cooling Tower Heat Transfer Rate` |
| $\dot m_a$ | dry-air mass flow | §4, from air-flow ratio, sizing, and fan regime |
| $T_{db}$, $T_{wb}$, $\omega_i$, $p$ | inlet air state | `Site Outdoor Air *` |

The plugin evaluates **every** evaporation method (§3) at the same operating point, then a water
balance (§5–6). Differences between methods therefore come from the physics of evaporation alone, not from
different thermal solutions. This is "accounting mode": the plugin does not feed back into EnergyPlus.
Rating mode (§3.8, standalone only) instead predicts $T_{w,o}$ from a fill characteristic, which allows the
thermal predictions of the methods to be compared as well.

Implemented in `methods.py` (registry), `eplus_plugin.py` (EnergyPlus glue), `evaporation.py` (physics).

---

## 2. Properties (`psychro.py`)

Units: SI, temperatures in °C unless noted, enthalpy in J/kg dry air.

**Saturation pressure** (Hyland & Wexler 1983; ASHRAE Fundamentals Ch. 1, Eqs. 5–6), $T$ in K:

$$\ln p_{ws} = \frac{C_8}{T} + C_9 + C_{10}T + C_{11}T^2 + C_{12}T^3 + C_{13}\ln T \quad (0 \le t \le 200\,^\circ\mathrm{C})$$

with $C_8=-5.8002206\times10^{3}$, $C_9=1.3914993$, $C_{10}=-4.8640239\times10^{-2}$,
$C_{11}=4.1764768\times10^{-5}$, $C_{12}=-1.4452093\times10^{-8}$, $C_{13}=6.5459673$; over ice the
$C_1$–$C_7$ set. The enhancement factor (≈1.004) is neglected, as in EnergyPlus.

**Humidity ratio**, **enthalpy**, **wet-bulb** (ASHRAE Fundamentals Ch. 1):

$$\omega_s = 0.621945\,\frac{p_{ws}}{p-p_{ws}},\qquad
i_{ma} = c_{pa}t + \omega\,(i_{fg0} + c_{pv}t),\qquad
\omega = \frac{(2501-2.326t^*)\,\omega_s^* - 1.006\,(t-t^*)}{2501+1.86t-4.186t^*}$$

with $c_{pa}=1006$, $c_{pv}=1860$, $c_{pw}=4186$ J/kg·K and $i_{fg0}=2.501\times10^6$ J/kg (the constant
property set used by Kloppers & Kröger 2005a). Wet-bulb from $\omega$ is found by bisection.

**Latent heat** (Henderson-Sellers 1984), $T$ in K:
$i_{fg}(T) = 1.91846\times10^{6}\,[T/(T-33.91)]^2$ J/kg (stated validity 273–323 K; within 0.3 % of IAPWS-95, 0–40 °C).

**Liquid water density** (Kell 1975), **moist-air density** $\rho = p/[287\,T(1+1.6077687\,\omega)]$ (EnergyPlus form).

*Verification:* `tests/test_methods.py::AgainstPsychroLib` checks $p_{ws}$, $\omega_s$, $i_{ma}$ and $T_{wb}$
against PsychroLib (Meyer & Thevenard 2019), an implementation of the ASHRAE Handbook equations; agreement
is within 0.05 % ($p_{ws}$), 0.1 % ($\omega_s$), 0.2 % ($i$) and 0.02 K ($T_{wb}$).

---

## 3. Evaporation methods (`evaporation.py`, `methods.py`)

| ID | Method | Physics level | Needs air flow | Section |
|---|---|---|---|---|
| `LAT` | Latent-only, $E=\dot Q/i_{fg}$ | bound | no | 3.1 |
| `ROT` | Rule of thumb, 0.153 %/K | empirical | no | 3.2 |
| `LF` | EnergyPlus LossFactor, $k$ %/K | empirical | no | 3.3 |
| `EPSAT` | EnergyPlus SaturatedExit (replica) | Merkel, saturated exit | yes | 3.4 |
| `MSAT` | Merkel energy balance, saturated exit, dry-air basis | Merkel | yes | 3.4 |
| `BRAUN` | Braun et al. (1989) effectiveness model, unsaturated exit | e-NTU, $Le_f=1$ | yes | 3.5 |
| `POPPE` | Poppe, Bošnjaković Lewis factor | full heat and mass transfer | yes | 3.6 |
| `POPPE1` | Poppe, $Le_f=1$ | full, Lewis effect removed | yes | 3.6 |

`POPPE` is the reference method. A method that cannot solve an operating point (status `NO_AIRFLOW` or
`INFEASIBLE`) is assigned the `MSAT` value for that timestep, so totals stay complete. The status is reported,
and the fallback share is a reported metric.

### 3.1 Latent-only bound (`LAT`)

$$E = \frac{\dot Q}{i_{fg}(\bar T_w)}, \qquad \bar T_w = \tfrac12(T_{w,i}+T_{w,o})$$

Assumes all heat leaves as latent heat. This is common in water-footprint screening. It is **not** an
upper bound in hot, dry air: when $T_{db} > T_w$, sensible heat flows from the air *into* the water and
$E > \dot Q/i_{fg}$ (tested in `test_hot_dry_air_evaporates_more_than_latent_bound`).

### 3.2 Rule of thumb (`ROT`)

$$E = 0.00085 \times 1.8 \times (T_{w,i}-T_{w,o})\,[\mathrm K] \times \dot m_w$$

This is the widely quoted "0.00085 × flow × range(°F)" rule, about 1 % of circulating flow per 10 °F of range
(cooling-tower practice; see Perry's handbook in §9). Equivalent to a loss factor of 0.153 %/K.

### 3.3 Loss factor (`LF`, EnergyPlus `LossFactor`)

$$\dot V_E = \frac{k}{100}\,(T_{w,i}-T_{w,o})\,\frac{\dot m_w}{\rho_w(\bar T_w)}$$

$k$ in %/K. The EnergyPlus default is 0.2; the EnergyPlus I/O Reference and IDD give 0.15–0.27 as a typical range
without a source. Configurable (`--loss-factor`). **Note:** EnergyPlus itself applies the input without dividing by 100,
so its own `LossFactor` mode evaporates 100× the documented rate (§8, issue 4). `LF` here implements the documented intent.

### 3.4 Saturated exit air (`EPSAT`, `MSAT`)

Merkel's (1925) model assumes the exit air is saturated. With the air-side energy balance

$$i_{ma,o} = i_{ma,i} + \dot Q/\dot m_a,\qquad T_{a,o} = T_{sat}(i_{ma,o}),\qquad E = \dot m_a\,[\omega_s(T_{a,o}) - \omega_i]$$

`MSAT` uses dry-air mass flow and humidity ratios. `EPSAT` reproduces `CoolingTower::calculateWaterUsage`
(EnergyPlus v22.2, also present in later versions) line by line. Its differences from `MSAT`:
(i) inlet enthalpy taken as saturated air at $T_{wb}$; (ii) moist-air mass flow $\dot m_{air}=r\,\dot V_{des}\rho_{moist}\,N_{on}/N$;
(iii) differences in *specific humidity* $\omega/(1+\omega)$; (iv) water density at the mean air temperature
($\ge 4$ °C); (v) EnergyPlus psychrometric constants ($c_{pa}=1004.84$, $i_{fg0}=2.50094\times10^6$, $c_{pv}=1858.95$).
*Verification:* `EPSAT` reproduces the EnergyPlus `Cooling Tower Water Evaporation Volume Flow Rate` within
0.4 % on every loaded timestep in all tested climates. This confirms the plugin reads the operating point
EnergyPlus uses.

### 3.5 Braun–Klein–Mitchell effectiveness model (`BRAUN`)

Braun et al. (1989) linearise the saturated-air enthalpy over the water temperature range,
$c_s = [i_{s}(T_{w,i}) - i_s(T_{w,o})]/(T_{w,i}-T_{w,o})$, and treat the tower as a counterflow exchanger with
capacity ratio $m^* = \dot m_a c_s/(\dot m_w c_{pw})$ and air-side effectiveness

$$\varepsilon_a = \frac{i_{ma,o}-i_{ma,i}}{i_s(T_{w,i})-i_{ma,i}} = \frac{1-\exp[-NTU(1-m^*)]}{1-m^*\exp[-NTU(1-m^*)]}.$$

In accounting mode, $\varepsilon_a$ is known from the operating point, and $NTU$ is obtained in closed form,

$$NTU = \frac{1}{1-m^*}\ln\frac{1-\varepsilon_a m^*}{1-\varepsilon_a}\quad(m^*\neq1),\qquad NTU=\frac{\varepsilon_a}{1-\varepsilon_a}\quad(m^*=1).$$

Exit humidity follows the effective-saturation-state relations of Braun et al. (1989):

$$i_{s,w,e} = i_{ma,i} + \frac{i_{ma,o}-i_{ma,i}}{1-e^{-NTU}},\qquad
\omega_o = \omega_{s,w,e} + (\omega_i-\omega_{s,w,e})\,e^{-NTU},\qquad E=\dot m_a(\omega_o-\omega_i)$$

with $\omega_{s,w,e}$ the saturation humidity at the temperature where $i_s = i_{s,w,e}$. If $\omega_o$ exceeds
saturation at the exit state (a fog the model cannot represent), the exit is limited to saturation (status `CLIPPED`).
The EnergyPlus `CoolingTower:VariableSpeed:Merkel` thermal model is of this effectiveness type with
$UA$ curves (EnergyPlus Engineering Reference), so `BRAUN` is the water model consistent with that tower's thermal model.

### 3.6 Poppe method (`POPPE`, `POPPE1`)

Poppe & Rögener (1991) keep the terms Merkel drops: the Lewis factor $Le_f = h/(c_{pma}h_d) \neq 1$,
water lost by evaporation, and the real exit-air state (unsaturated or supersaturated). We use the form of
Kloppers & Kröger (2005a), with water temperature as the independent variable.

**Unsaturated air** ($\omega \le \omega_s(T_a)$):

$$\frac{d\omega}{dT_w} = \frac{c_{pw}\,(\dot m_w/\dot m_a)\,(\omega_{sw}-\omega)}{D},\qquad
\frac{di_{ma}}{dT_w} = \frac{\dot m_w c_{pw}}{\dot m_a}\left[1 + \frac{c_{pw}T_w(\omega_{sw}-\omega)}{D}\right],\qquad
\frac{dMe_P}{dT_w} = \frac{c_{pw}}{D}$$

$$D = (i_{masw}-i_{ma}) + (Le_f-1)\,[\,i_{masw}-i_{ma}-(\omega_{sw}-\omega)\,i_v\,] - (\omega_{sw}-\omega)\,c_{pw}T_w,\qquad i_v = i_{fg0}+c_{pv}T_w$$

**Supersaturated air** ($\omega > \omega_{sa}$, mist present; $i_{ss} = c_{pa}T_a + \omega_{sa}(i_{fg0}+c_{pv}T_a) + (\omega-\omega_{sa})c_{pw}T_a$):

$$D_{ss} = (i_{masw}-i_{ss}) + (Le_f-1)\,[\,i_{masw}-i_{ss}-(\omega_{sw}-\omega_{sa})i_v + (\omega-\omega_{sa})c_{pw}T_w\,] + (\omega-\omega_{sw})\,c_{pw}T_w$$

and the same three equations with $(\omega_{sw}-\omega)\to(\omega_{sw}-\omega_{sa})$ and $D\to D_{ss}$.
$T_a$ of supersaturated air is solved from $i_{ss}$ by bisection.

**Water flow** along the fill: $\dot m_w/\dot m_a = \dot m_{w,i}/\dot m_a - (\omega_o-\omega)$; $\omega_o$ is unknown,
so the integration is repeated (fixed point, ≤ 6 passes, $|\Delta\omega_o|<10^{-8}$).

**Lewis factor** (Bošnjaković 1965; used by Kloppers & Kröger 2005b; equations checked term by term against Kloppers & Kröger 2004):

$$Le_f = 0.865^{2/3}\,\frac{x-1}{\ln x},\qquad x = \frac{\omega_{sw}+0.622}{\omega+0.622}$$

(with $\omega_{sa}$ in place of $\omega$ for supersaturated air). `POPPE1` sets $Le_f=1$ to isolate this effect.

**Integration:** classical RK4 from the bottom ($T_{w,o}$, inlet air) to the top ($T_{w,i}$), $n=10$ steps
(converged to $10^{-4}$ relative; `test_step_convergence`). Because both water temperatures are known, the Merkel
number $Me_P$ is an *output*, so no fill data is needed. If $D \le 0$ anywhere, the driving force has vanished:
the operating point is not physical for the given air flow, and status is `INFEASIBLE`.

**Operating points beyond the thermodynamic limit (status `ADJUSTED`).** EnergyPlus' Merkel tower linearises
$i_s(T)$ (Braun's $c_s$) and runs at the lowest fan speed meeting the setpoint; an oversized tower at part load is then
driven to within a fraction of a percent of $i_s(T_{w,i})$ at the exit. Poppe ($Le_f<1$, evaporated-water enthalpy)
can find $D\le0$ near the top of the fill. `methods.evaluate` then re-solves with the smallest air-flow factor in
{1.01, 1.02, 1.03, 1.05, 1.08, 1.12, 1.2, 1.35, 1.5} that is feasible and reports it (`AirScale`). Near the pinch evaporation is
insensitive to air flow (Dublin test point: +2 % air → <0.1 %, +20 % → 1.4 %; `tests/test_methods.py::NearPinch`). In the
14-climate study the mean factor was 1.01–1.03 and no timestep needed the MSAT fallback.
**Common air flow (since review round 1):** when POPPE is adjusted, MSAT, BRAUN and POPPE1 are evaluated at the same
adjusted air flow (`methods.COMMON_AIR`, `cfg['common_air']`, default on), so all physical models share one operating point;
EPSAT always keeps EnergyPlus' air flow. A fixed-fill rating check (`tools/review_analyses.py`) bounds the effect of
EnergyPlus' near-pinch operating points on evaporation per unit heat to ≤ 0.15 % (paper §6.3).

**Vapour and mist:** in supersaturated exhaust Poppe's ω includes liquid mist. `tools/review_analyses.py` splits
E into vapour, ṁ_a(ω_s(T_a,o) − ω_i), and mist, ṁ_a(ω_o − ω_s(T_a,o)); vapour-only is a lower bound of consumption
(mist may be captured by drift eliminators), total an upper bound.

**Note on $Me_P$:** this rearranged form defines $Me_P$ on the *local* water flow, $Me_P=\int h_d a_{fi}A_{fr}\,dz/\dot m_w(z)$,
which is larger than $h_da_{fi}A_{fr}L/\dot m_{w,i}$ by about half the evaporated fraction (≈0.5–0.7 % here).
Compare fill correlations on the same definition.

**Verification against an independent formulation** (`tools/verify_poppe.py`): the original height-wise
conservation equations ($d\dot m_w = K(\omega_{sw}-\omega)dz$; $\dot m_a\,di = K[Le_f c_{pma}(T_w-T_a)+(\omega_{sw}-\omega)i_v]dz$;
$d(\dot m_wc_{pw}T_w)=\dot m_a\,di$), with prescribed $K$, solved as a boundary-value problem (shooting, SciPy LSODA,
rtol $10^{-10}$). Five cases from hot-dry to hot-humid; maximum difference in evaporation and $Me_P$ is $<10^{-4}$ %:

| case | $T_{w,o}$ [°C] | $Me_P$ ref / code | $E$ ref / code [g/s] |
|---|---|---|---|
| temperate design (25 °C, 50 %) | 26.215 | 1.2081 / 1.2081 | 133.114 / 133.114 |
| hot-dry (42 °C, 12 %) | 26.332 | 1.2081 / 1.2081 | 144.884 / 144.884 |
| hot-humid (31 °C, 75 %) | 30.181 | 1.4068 / 1.4068 | 92.314 / 92.314 |
| mild, high L/G | 26.610 | 0.8027 / 0.8027 | 75.825 / 75.825 |
| cool, low L/G | 19.860 | 1.0054 / 1.0054 | 104.435 / 104.435 |

### 3.7 Merkel number from Merkel's method

$$Me_M = \int_{T_{w,o}}^{T_{w,i}} \frac{c_{pw}\,dT_w}{i_{masw}-i_{ma}},\qquad i_{ma}(T_w) = i_{ma,i} + \frac{\dot m_w c_{pw}}{\dot m_a}(T_w - T_{w,o})$$

Evaluated by four-point Chebyshev quadrature at $T_{w,o}+\{0.1,0.4,0.6,0.9\}\,(T_{w,i}-T_{w,o})$ (CTI ATC-105 practice; node
values confirmed only from secondary sources;
reported as `MeMerkel`) and by Simpson's rule (rating mode). The two agree within 1 % in tests.

### 3.8 Rating mode (standalone)

Given a fill Merkel number, find $T_{w,o}$ such that the method's required $Me(T_{w,o})$ equals it (bisection):
`outlet_temperature_merkel`, `outlet_temperature_poppe` (any Lewis option), and `outlet_temperature_entu`
(Braun, $NTU = Me\,\dot m_w/\dot m_a$, with $c_s$ by fixed point). This is for validation against manufacturer
performance data, where thermal and water predictions must be tested together.

---

## 4. Air flow from EnergyPlus (`eplus_plugin.air_volume_flow`)

Physical evaporation methods need the actual air flow. What EnergyPlus reports depends on the tower type:

| Regime | `CoolingTower:VariableSpeed` (YorkCalc/CoolTools) | `CoolingTower:VariableSpeed:Merkel` |
|---|---|---|
| fan modulating | $r\,\dot V_{des}$ ($r$ = `Air Flow Rate Ratio`) | $r\,\dot V_{des}$ ($r$ = `Fan Speed Ratio`) |
| fan cycling / free convection | EnergyPlus sets $r = PLR\,r_{min} + (1-PLR)\,f_{fc}$, where $f_{fc}$ is the free-convection **capacity** fraction | $r = 0$ although $\dot Q>0$ |
| used by this tool | $PLR\,r_{min}\dot V_{des} + (1-PLR)\dot V_{fc}$ | $\dot V_{fc}$ from sizing (`Free Convection Regime Air Flow Rate`) |

$\dot V_{fc}$ comes from the `.eio` sizing report. Cell staging is applied as $N_{on}/N$. For the empirical
VariableSpeed models, the air-flow ratio is a control variable of a regression, not a measured flow, so physical
methods can find some operating points infeasible. **The Merkel tower is recommended** because its air flow is
tied to a $UA$ model.

---

## 5. Blowdown and water chemistry (`chemistry.py`)

### 5.1 Mass balance

With cycles of concentration $N$ (ratio of concentration in the basin to makeup), evaporation $E$, drift $D$,
blowdown $B$:

$$M = E + D + B,\qquad N = \frac{M}{D+B}\;\Rightarrow\; B = \frac{E}{N-1} - D \;(\ge 0).$$

Drift: $D = \dot V_{w,des}\,f_d\,\min(1,\dot V_a/\dot V_{a,des})$ while rejecting heat, with $f_d$ from the IDF
(EnergyPlus scales drift with air-flow ratio in the same way).

### 5.2 Constituent limits

$$N_i = \frac{c_{i,\max}}{c_{i,\mathrm{makeup}}},\qquad N_{ij} = \sqrt{\frac{K_{ij}}{c_ic_j}}\ \text{(product limits)},\qquad
N = \mathrm{clip}\!\left(\min_k N_k,\ N_{\min},\ N_{\max}\right).$$

### 5.3 Calcium carbonate: Langelier and Ryznar indices

$$pH_s = (9.3 + A + B) - (C + D),\quad A = \frac{\log_{10}TDS - 1}{10},\quad B = -13.12\log_{10}(t+273.15) + 34.55,$$
$$C = \log_{10}[\mathrm{Ca^{2+}\ as\ CaCO_3}] - 0.4,\quad D = \log_{10}[\text{alkalinity as CaCO}_3],\qquad LSI = pH - pH_s,\quad RSI = 2pH_s - pH$$

(index: Langelier 1936; Ryznar 1944). The empirical A–D form is the one commonly attributed to Carrier (1965);
it is an approximation of the equilibrium calculation in *Standard Methods* 2330, which uses activity-corrected constants.
**Source of the A–D constants still to be confirmed** (see `docs/REFERENCES_CHECK.md`). TDS, calcium and alkalinity all scale with $N$, so
$pH_s(N) = pH_s(1) - 1.9\log_{10}N$, and the LSI limit is closed-form:

$$N_{LSI} = 10^{\,(LSI_{\max} - pH + pH_s(1))/1.9}$$

evaluated at the hot-water temperature $T_{w,i}$ (worst case for scaling). The recirculating pH is an input
(acid-feed setpoint); predicting pH from alkalinity is not attempted.

### 5.4 Silica

Amorphous-silica solubility (Fournier 1977, geothermometer form; application at 15–40 °C is an extrapolation to be checked):
$\log_{10} S\,[\mathrm{mg/kg}] = 4.52 - 731/T$ (K), evaluated at
the cold-water temperature $T_{w,o}$ (lowest solubility). $N_{SiO_2} = f\,S(T_{w,o})/c_{SiO_2}$ with $f$ the allowable
multiple of solubility under the treatment program.

### 5.5 Modes

`fixed` ($N$ given, EnergyPlus `ConcentrationRatio`), `constituent` (5.2 only, constant), `dynamic` (5.2–5.4 each
timestep: an idealised conductivity controller always running at the allowable $N$).

### 5.6 Water-quality data

- `data/water_sources_sourced.json` holds **sourced makeup water for all 14 study sites** (utility reports, or USGS
  source-water records where reports give no mineral data). It also holds **five sourced treatment limit sets**:
  - EVAPCO galvanized inhibitor;
  - EVAPCO 316 stainless;
  - BAC galvanized;
  - an ICC GEW174-14 modern-stabiliser program;
  - an acid-fed program at pH 7.5.

  Every value has its URL, year, conversion and confidence rating in `docs/WATER_QUALITY_SOURCES.md`. A JSON `null` means
  the value was not reported, and that constraint is skipped.
- `tools/water_quality_study.py` pairs each site with its own water and evaluates every limit set, writing
  `results/study/water_quality_*` and `fig_dc_water_quality`.
- `data/water_sources.json` keeps the original illustrative sources (soft surface, hard groundwater, reclaimed) for
  generic scenarios. Those values are **not** from any utility.
- Assumptions and limits:
  - recirculating pH 8.5 for programs without acid (assumption);
  - the LSI limit scales alkalinity with $N$ even under acid feed (conservative);
  - corrosion limits for soft, aggressive waters are not modelled;
  - the cycle cap is 10.

---

## 6. Water balance outputs and metrics

Per tower, each timestep: `E_<ID>` for every method (m³/s, converted from kg/s at $\rho_w(20\,^\circ\mathrm{C})$;
`EPSAT` is exactly the EnergyPlus volume), and for the reference method: `Drift`, `Blowdown`, `Makeup`, `MakeupVol`,
`Cycles`, `CycLimit` (code of the limiting constraint), `AirMass`, `AirOutT`, `AirOutW`, `Fog`, `MePoppe`, `MeMerkel`,
`NTU`, `Status`.

**Fog**: the reference method flags supersaturated exit air (`Fog`). Annual "fog hours" in `tools/analyze.py` count
timesteps whose exit air carries more than 0.1 g/kg of liquid (`FOG_LIQUID_GKG`), evaluated at site pressure, so that traces of
mist at the pinch are not counted. The threshold is a reporting choice, not a visibility criterion.

Facility metric: **Water Usage Effectiveness** (The Green Grid 2011),
$WUE = \text{annual site water [L]} / \text{IT energy [kWh]}$, using tower makeup as site water.
Specific water use per heat rejected (L/kWh$_{th}$) is reported as well, since it is independent of the PUE.

---

## 6b. Hybrid adiabatic dry cooler (`hybrid.py`, `eplus_hybrid.py`)

A bank of `FluidCooler:TwoSpeed` objects (dry coils, EnergyPlus thermal model) shares one `OutdoorAir:Node`.
Wetted media pads (or sprays) upstream of the coils pre-cool the air in wet mode. Unlike §1–5 (accounting mode),
this plugin **changes the EnergyPlus solution**: at the start of each zone timestep it overrides the node's dry-bulb
and wet-bulb with EMS actuators (`Outdoor Air System Node` / `Drybulb Temperature`, `Wetbulb Temperature`).
EnergyPlus recomputes the node humidity ratio from both (`OutAirNodeManager::SetOutAirNodes`), the coolers read the
node state (`FluidCoolerspecs::initialize`), and any `SetpointManager:FollowSystemNodeTemperature` on that node lowers the
condenser setpoint, so the chillers see the benefit.

### 6.1 Pad pre-cooling

$$T_{pre} = T_{db} - \varepsilon\,(T_{db}-T_{wb}),\qquad
i(T_{db},\omega_i) + (\omega_{pre}-\omega_i)\,c_{pw}T_{wb} = i(T_{pre},\omega_{pre})$$

i.e. adiabatic saturation along a constant wet-bulb line, solved exactly for $\omega_{pre}$ with the §2 property set.
*Check:* at $\varepsilon=1$ the state reaches the ASHRAE wet-bulb saturation state within 0.2 %; for $\varepsilon<1$ the wet-bulb
of the pad-leaving air equals the inlet wet-bulb within 0.03 K (`tests/test_hybrid.py`).

Velocity dependence (standalone library): with $h\propto V^{n}$, the pad NTU scales as $V^{n-1}$:
$NTU_d=-\ln(1-\varepsilon_d)$, $\varepsilon(V)=1-\exp[-NTU_d (V/V_d)^{n-1}]$, $n=0.8$ (forced-convection analogy; assumption).
**In the EnergyPlus plugin a constant $\varepsilon_d$ is used** for both the imposed air state and the water booked, so heat and
mass stay consistent (air speed is only known after EnergyPlus has simulated the timestep).
Default $\varepsilon_d = 0.85$ (assumption, typical of 150–200 mm rigid cellulose media at design face velocity; replace with
manufacturer data).

### 6.2 Water

Pad evaporation $E=\sum_k f_k\,\dot m_{a,k}(\omega_{pre}-\omega_i)$ over the fan states $k$ of the timestep (§6.4).
- **Media (recirculating):** bleed $B=E/(N-1)$, $N$ from the chemistry model (§5) with the same water source; makeup $E+B$.
- **Spray (once-through):** applied water $E/\eta_s$, runoff $E(1/\eta_s-1)$; $\eta_s=0.6$ default (assumption).
Pads are wetted only when the fan runs; drying-out and pad flushing are not modelled.

### 6.3 Fan penalty

$\Delta p(V)=\Delta p_d (V/V_d)^{1.8}$, $P_{pad}=\Delta p\,\dot V/\eta_{fan}$, reported (`HC_FanPenalty`) but **not** added to EnergyPlus fan power;
the study adds it to facility electricity in post-processing. Default $\Delta p_d=0$ (off).

### 6.4 Air flow from fan power

`FluidCoolerspecs::calcTwoSpeed` (v22.2) sets fan power to $f P_{low}$ when low speed suffices, else to
$f P_{high}+(1-f)P_{low}$. Inverting: $P\le P_{low}\Rightarrow[(P/P_{low},\dot V_{low})]$; otherwise
$f=(P-P_{low})/(P_{high}-P_{low})$, states $[(f,\dot V_{high}),(1-f,\dot V_{low})]$.
**Cooler air flows must be hard-sized**: EnergyPlus autosizes fluid-cooler air flow as
$Q_{nom}/(T_{w,in}-T_{a,in})\times4$ with $Q$ in W (`FluidCoolers.cc`, v22.2), about three orders of magnitude too large (§8, issue 5).

### 6.5 Wet/dry control

| strategy | rule |
|---|---|
| `dry` | never wet (baseline, same hardware) |
| `wet` | wet whenever $T_{db}\ge T_{freeze}$ (5 °C) |
| `threshold` | wet when $T_{db}\ge T_{on}$; stays wet until $T_{db}<T_{on}-\Delta$ ($\Delta=2$ K) |

All strategies are inhibited below $T_{freeze}$ and, optionally, when $T_{db}-T_{wb}$ is below a minimum depression. The decision
uses the current timestep's weather (perfect knowledge of ambient, no knowledge of the plant response). Sweeping $T_{on}$
traces the water–energy trade-off.

---

## 7. Numerical and software verification

| Check | Where | Result |
|---|---|---|
| Psychrometrics vs PsychroLib (ASHRAE) | `tests/test_methods.py` | < 0.2 % / 0.02 K |
| Latent heat vs IAPWS-95 | `tests/test_methods.py` | < 0.3 % |
| Poppe energy balance closure | `tests/test_physics.py` | < 0.1 % |
| Poppe step convergence (10 vs 80 RK4 steps) | `tests/test_physics.py` | < 0.01 % |
| Poppe vs independent height-wise BVP, 7 cases incl. supersaturated near-pinch | `tools/verify_poppe.py` | evaporation 0.008 % (10 steps); $Me_P$ 0.003 % (40 steps) |
| Poppe energy/mass closure in supersaturated air | `tests/test_physics.py` | < 0.1 % |
| Braun NTU inversion round trip | `tests/test_methods.py` | < 1 % |
| Rating mode: Merkel vs Poppe vs e-NTU outlet temperature, same fill | `tests/test_methods.py` | < 0.5 K |
| `EPSAT` replica vs EnergyPlus output | `tools/analyze.py`, all runs | < 0.4 % |
| Limit behaviour (saturated exit at high NTU, fog in cold humid air, hot-dry $E>\dot Q/i_{fg}$) | tests | pass |

| Poppe vs 126 measured counterflow fill tests (Kloppers 2003, App. R–T: trickle, splash, film) | `tools/validate_kloppers.py` | $Me_P$ vs Kloppers' own Poppe analysis +1.0 % mean (95th pct 2.0 %); outlet-air T vs measured: bias −0.20 K, rms 0.84 K (Kloppers 0.85 K) |
| Fill law $Me\propto(L/G)^{-n}$, single-point $n=0.6$, rating mode on the same tests | `tools/validate_kloppers.py` | $T_{w,o}$ rms 0.17–0.83 K; evaporation mean error ±4.4 %, max 11.5 % (film) |

The fill tests measure outlet-air temperature but not evaporation. They validate the air-side balance, not water use
directly. Not yet done: metered makeup and blowdown of an operating tower. Data: `data/equipment/kloppers2003_fill_tests.csv`;
extraction: `data/equipment/extraction/`.

---

## 8. EnergyPlus water-accounting issues found (v22.2; same code in `develop` as of 2026-10)

1. **Idle towers report water.** `CoolingTower::simulate` calls `calculateWaterUsage()` before `report()`.
   When the tower is not running (`RunFlag` false), `report()` zeroes heat and air flow, but evaporation, drift and
   blowdown were already computed from the stale `airFlowRateRatio`. In the stock example `CoolingTower_VariableSpeed.idf`,
   the idle second tower books 4.5–12 m³/yr with zero heat rejected.
2. **Merkel tower books no water in free convection.** In `calculateMerkelVariableSpeedTower`, the free-convection branch
   sets `airFlowRateRatio = 0` while `Qactual > 0`, so the `SaturatedExit` air mass flow is zero and evaporation is zero.
3. **VariableSpeed tower uses a capacity fraction as an air-flow ratio** in the fan-off and cycling regimes (§4).
4. **`LossFactor` is applied as a fraction, not a percent.** The IDD gives the field in percent/K (default 0.2, typical 0.15–0.27),
   but `UserEvapLossFactor = NumArray(...)` is used without `/100` (drift percent, read the same way, is divided by 100).
   A run of the stock `CoolingTower_VariableSpeed.idf` with `LossFactor` 0.2 gives an implied factor of 0.2001 per K (20 %/K),
   evaporating up to 24 % of the circulating water.
5. **Fluid-cooler air flow autosizing is about three orders of magnitude too large.** `FluidCoolerspecs::size()` sets
   `HighSpeedAirFlowRate = NominalCapacity / (DesignEnteringWaterTemp - DesignEnteringAirTemp) * 4.0` with capacity in W and the
   result in m³/s (stock `FluidCoolerTwoSpeed.idf`: 58.6 kW → 14,061 m³/s). Thermal results depend on the UA sized with this flow,
   but any air-side quantity (fan power scaling, pad water in §6) is unphysical. To be checked against the I/O Reference.

Minimal reproductions: `bugreports/` (to be filed upstream after confirmation).

---

## 9. References

- ASHRAE (2021). *ASHRAE Handbook—Fundamentals*, Chapter 1: Psychrometrics. ASHRAE, Atlanta.
- Bošnjaković, F. (1965). *Technical Thermodynamics* (transl. P.L. Blackshear). Holt, Rinehart and Winston, New York.
- Carrier Air Conditioning Company (1965). *Handbook of Air Conditioning System Design*. McGraw-Hill, New York. (A–D LSI form; to be confirmed.)
- Braun, J.E., Klein, S.A., Mitchell, J.W. (1989). Effectiveness models for cooling towers and cooling coils. *ASHRAE Transactions* 95(2), 164–174.
- Cooling Technology Institute (2019). *ATC-105: Acceptance Test Code for Water Cooling Towers*. CTI, Houston.
- EnergyPlus (2022). *Engineering Reference* and *Input Output Reference*, version 22.2. U.S. Department of Energy.
- Fournier, R.O. (1977). Chemical geothermometers and mixing models for geothermal systems. *Geothermics* 5, 41–50.
- Henderson-Sellers, B. (1984). A new formula for latent heat of vaporization of water as a function of temperature. *Quarterly Journal of the Royal Meteorological Society* 110, 1186–1190.
- Hyland, R.W., Wexler, A. (1983). Formulations for the thermodynamic properties of the saturated phases of H₂O from 173.15 K to 473.15 K. *ASHRAE Transactions* 89(2A), 500–513 (pages to confirm).
- Jaber, H., Webb, R.L. (1989). Design of cooling towers by the effectiveness-NTU method. *Journal of Heat Transfer* 111(4), 837–843.
- Kell, G.S. (1975). Density, thermal expansivity, and compressibility of liquid water from 0° to 150 °C: correlations and tables for atmospheric pressure and saturation reviewed and expressed on 1968 temperature scale. *Journal of Chemical and Engineering Data* 20(1), 97–105.
- Kloppers, J.C., Kröger, D.G. (2005a). A critical investigation into the heat and mass transfer analysis of counterflow wet-cooling towers. *International Journal of Heat and Mass Transfer* 48, 765–777.
- Kloppers, J.C., Kröger, D.G. (2005b). The Lewis factor and its influence on the performance prediction of wet-cooling towers. *International Journal of Thermal Sciences* 44, 879–884.
- Kloppers, J.C., Kröger, D.G. (2005c). Cooling tower performance evaluation: Merkel, Poppe, and e-NTU methods of analysis. *Journal of Engineering for Gas Turbines and Power* 127, 1–7.
- Kloppers, J.C., Kröger, D.G. (2004). Cooling tower performance: a critical evaluation of the Merkel assumptions. *R&D Journal* (SAIMechE) 20(1) — open-access source used to check the Poppe equations; see `paper/references.bib`.
- Kröger, D.G. (2004). *Air-Cooled Heat Exchangers and Cooling Towers: Thermal-Flow Performance Evaluation and Design*, Vol. 1. PennWell, Tulsa.
- Langelier, W.F. (1936). The analytical control of anti-corrosion water treatment. *Journal AWWA* 28(10), 1500–1521.
- Merkel, F. (1925). Verdunstungskühlung. *VDI-Forschungsarbeiten* 275, Berlin.
- Meyer, D., Thevenard, D. (2019). PsychroLib: a library of psychrometric functions to calculate thermodynamic properties of air. *Journal of Open Source Software* 4(33), 1137.
- Mytton, D. (2021). Data centre water consumption. *npj Clean Water* 4, 11.
- Perry, R.H., Green, D.W. (eds.). *Perry's Chemical Engineers' Handbook*, Section 12, Eq. (12-14c) ("0.00085 evaporation constant is a good rule-of-thumb value"; edition to confirm). McGraw-Hill.
- Poppe, M., Rögener, H. (1991). Berechnung von Rückkühlwerken. *VDI-Wärmeatlas*, Mi 1–Mi 15. VDI-Verlag, Düsseldorf.
- Ryznar, J.W. (1944). A new index for determining amount of calcium carbonate scale formed by a water. *Journal AWWA* 36(4), 472–483.
- Shehabi, A., et al. (2016). *United States Data Center Energy Usage Report*. LBNL-1005775, Lawrence Berkeley National Laboratory.
- The Green Grid (2011). *Water Usage Effectiveness (WUE): A Green Grid Data Center Sustainability Metric*. White Paper #35.
- Wagner, W., Pruß, A. (2002). The IAPWS formulation 1995 for the thermodynamic properties of ordinary water substance for general and scientific use. *Journal of Physical and Chemical Reference Data* 31(2), 387–535.
