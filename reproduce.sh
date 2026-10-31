#!/usr/bin/env bash
# Reproduce every number and figure in the paper from scratch (~15 min on a 16+ core machine).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python3}    # Python 3.8+ with numpy scipy pandas matplotlib psychrolib pypandoc_binary (see pyproject.toml [analysis])
EPLUS=${EPLUS:-/srv/data1/EnergyPlus-22-2-0/energyplus}   # EnergyPlus 22.2.0 (c249759bad); scripts take --eplus

echo "== 1. Unit tests and code verification"
$PY -m unittest discover -s tests
$PY tools/verify_poppe.py

echo "== 2. Climate-general method map (standalone)"
$PY tools/method_map.py --out results/method_map
$PY tools/fig_method_map.py

echo "== 3. Data center, 14 climates (EnergyPlus 22.2 + plugin)"
$PY tools/run_climates.py --idf models/datacenter_chiller_tower.idf --out runs/dc --ddy-sizing --jobs 16 \
    --sites $(ls -d weather/*/ | grep -v "weather/phx/")

echo "== 4. Tables and figures"
$PY tools/study_report.py runs/dc

echo "== 4b. Validation against measured fill tests (Kloppers 2003)"
$PY tools/validate_kloppers.py

echo "== 4c. Plant sensitivity: 4 sites for the round-1 variants, 14 sites for the equipment-informed plant"
SENS_SITES="weather/phoenix_tmyx weather/singapore weather/frankfurt weather/stockholm"
for v in duty_sized cw_floor_15 duty_sized_cw_floor_15; do
    $PY tools/run_climates.py --idf models/sensitivity/$v.idf --out runs/sens_$v --ddy-sizing --jobs 16 --sites $SENS_SITES
done
$PY models/build_datacenter_idf.py --plant modern --out models/sensitivity/modern_plant.idf
$PY tools/run_climates.py --idf models/sensitivity/modern_plant.idf --out runs/sens_modern_plant --ddy-sizing --jobs 16 \
    --sites $(ls -d weather/*/ | grep -v "weather/phx/")

echo "== 4d. Review analyses (mist, consistency, fill-exponent sweep, ordinary-fill tower), site water quality, LaTeX tables"
$PY tools/review_analyses.py runs/dc
$PY tools/review_analyses.py runs/dc --fill-exp-sweep 0.5 0.6 0.78
$PY tools/realistic_fill_check.py runs/dc --lg 1.0 1.2 1.4
$PY tools/water_quality_study.py runs/dc
$PY tools/review_tables.py

echo "== 5. Hybrid adiabatic dry cooler: 14 climates x 7 control strategies"
$PY models/build_datacenter_idf.py --heat-rejection hybrid
$PY tools/run_hybrid_study.py --idf models/datacenter_chiller_hybrid.idf --out runs/hyb --jobs 48 \
    --t-on 16 20 24 28 32 --sites $(ls -d weather/*/ | grep -v "weather/phx/")
$PY tools/hybrid_report.py runs/hyb

echo "== 6. EnergyPlus water-accounting reproductions"
$PY bugreports/check_eplus_water_accounting.py

echo "== 7. Word versions"
$PY tools/make_docx.py
echo "Done: results/figures, results/study, paper/manuscript.tex/.docx, docs/METHODS.docx"
