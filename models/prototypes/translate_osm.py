#!/usr/bin/env python3
"""Translate an OpenStudio model (.osm) to EnergyPlus input with the OpenStudio Python bindings.

Runs in a separate environment (pip install openstudio==3.7.0; EnergyPlus 23.2 input):
  /srv/data1/liangzhang/envs/ostudio/bin/python models/prototypes/translate_osm.py IN.osm OUT.idf
build_prototypes.py then converts OUT.idf to EnergyPlus 22.2.
"""
import sys

import openstudio

src, dst = sys.argv[1], sys.argv[2]
m = openstudio.osversion.VersionTranslator().loadModel(src)
if not m.is_initialized():
    raise SystemExit("could not load " + src)
ft = openstudio.energyplus.ForwardTranslator()
ws = ft.translateModel(m.get())
for e in ft.errors():
    print("ERROR", e.logMessage())
print(len(ft.warnings()), "translation warnings")
ws.save(dst, True)
