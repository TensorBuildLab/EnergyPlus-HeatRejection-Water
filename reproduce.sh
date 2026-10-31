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
