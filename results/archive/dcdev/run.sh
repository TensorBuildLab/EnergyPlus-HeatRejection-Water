#!/bin/bash
# usage: run.sh IDF EPW OUTDIR
set -e
E=/srv/data1/EnergyPlus-22-2-0
mkdir -p "$3"; cp "$1" "$3/in.idf"; cd "$3"
start=$(date +%s.%N)
$E/energyplus -r -d out -w "$2" in.idf > log.txt 2>&1 || true
end=$(date +%s.%N)
echo "wall: $(echo "$end - $start" | bc) s"; tail -1 out/eplusout.err
