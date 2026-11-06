# Cover letter

Liang Zhang
University of Arizona, Tucson, AZ, USA
liangzhang1@arizona.edu

November 2026

To the Editors, *Energy and Buildings*

Dear Editors,

I am pleased to submit the manuscript "Evaluating cooling tower evaporation models for data center water use in building energy simulation" for consideration as a Research Paper in *Energy and Buildings*.

Cooling towers dominate the direct water use of data centers, and water availability is becoming a design constraint, for example in Arizona, where Colorado River shortages and groundwater limits now affect new development. Building energy simulation is the tool designers use to estimate this water use, yet the evaporation models it offers are simplified relations whose errors under real operation have not been quantified. The manuscript addresses this gap.

The study compares eight evaporation models, from rules of thumb and saturated-exit energy balances to the Poppe model, by evaluating all of them at the same simulated operating point in every timestep, with fan-cycling towers resolved into their fan-on and free-convection states. The models are implemented as an open-source EnergyPlus Python plugin, verified against an independent solution and 126 measured fill tests, and applied in 14 climates to the LBNL/DOE large data center prototype (published in this journal by Sun et al., 2021), a data center with a variable-speed tower and the DOE large office prototype.

The main findings are:

- The error of simplified models follows the state of the exhaust air. Saturated-exit models overpredict where hot, dry air leaves the tower unsaturated and underpredict where cold air leaves it supersaturated; the tower's air-to-water ratio, set by its part-load control, decides which regime dominates.
- The EnergyPlus default differs from Poppe by -9 to +38 % in annual evaporation, depending on climate, tower control and building. For the fan-cycling tower of the data center prototype, up to 22 percentage points come from how EnergyPlus averages fan cycling over a timestep.
- Empirical rules deviate by up to 65 %, and the local makeup-water chemistry changes makeup by -16 to +44 %, an effect of the same order as the evaporation model.

The manuscript gives practical recommendations on which model to use for data center water estimates, including for the choice between air-cooled and evaporative heat rejection. Because the plugin works with existing EnergyPlus models, including the prototype buildings used in code development and building-stock studies, the results can be used directly by the building simulation community this journal serves. The code, a tutorial, the models and the scripts that reproduce every figure and table are openly available.

I confirm that this manuscript is original, has not been published elsewhere and is not under consideration by another journal. I am the sole author and have approved the submission. I have no competing interests to declare. The use of generative AI tools in the preparation of the manuscript is declared in the manuscript, as required by Elsevier's policy. This work was supported by the U.S. National Science Foundation under Award No. 2623038.

Thank you for considering this manuscript.

Sincerely,

Liang Zhang
University of Arizona, Tucson, AZ, USA
National Laboratory of the Rockies, Golden, CO, USA
