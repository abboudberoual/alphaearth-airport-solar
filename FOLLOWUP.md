# Follow-up plan, fixed before running (26 November 2026, about 16:20 Toronto time)

The main study (HYPOTHESIS.md) is finished and unchanged. This file sets out three follow-up analyses and
their rules **before** any of them is run. Anything changed afterwards is listed at the bottom.

## A. Harder comparison: does the model know more than "open ground"?
- Same data, folds, seeds, training sizes and logistic regression as the main test, land seen two years
  before opening.
- **Only change:** negatives are restricted to open land, ESA WorldCover 2021 classes shrubland (20),
  grassland (30), cropland (40) and bare/sparse (60). Tree cover, built-up, water and wetland negatives are
  dropped. Positives are unchanged.
- Report average precision for AlphaEarth and Sentinel-2 at every size, and apply the main study's decision
  rule (AlphaEarth at 100 labels vs Sentinel-2 at 1,000).
- Reading: if AlphaEarth at 1,000 labels stays at or above 0.60, the model distinguishes solar land from
  other open land; below that, much of the main-test signal was "open versus not open".

## B. Forward check: farms the model never saw
- Facilities in the saved USPVDB snapshot (26 Nov 2026) that began operating in **2025**. Points drawn with
  exactly the same rules as the main study (3 inside each footprint, 3 negatives 2-20 km away, not water).
- AlphaEarth embeddings from **2023** (two years before opening).
- Score them with the **published final model** (`results/final_model.json`, trained only on 2019-2024 farms),
  with no retraining.
- Reading: if average precision on 2025 farms is within 0.05 of the final model's out-of-fold average
  precision (0.789), the model holds up on future farms.

## C. What the land near each of the 20 airports could supply
Within 5 km of each airport, computed in an equal-area projection (EPSG:5070) at 10 m:
1. **Available land** = ESA WorldCover 2021 open land (classes 20, 30, 40, 60), with slope of 5 degrees or less
   (USGS 3DEP 10 m elevation), minus existing USPVDB solar footprints, minus a 500 m band around every runway
   (FAA runway-end coordinates).
2. **Solar-like available land** = available land where the final model's 2025 score is 0.5 or higher.
3. **Capacity** = area x packing density, where packing density is the median of `p_cap_dc / p_area`
   (MW DC per km² of array footprint) over the 3,472 USPVDB facilities used in the main study.
4. **Electricity** = capacity x yearly output per kW from NREL PVWatts v8 at the airport's coordinates
   (single-axis tracking, 14% losses, default module).
5. **Hydrogen** = electricity / 55 kWh per kg (DOE PEM electrolyser system, 2022 status); 51 kWh/kg
   (DOE 2026 target) reported as a sensitivity.
6. **Carbon per kg of hydrogen**: from the local grid = 55 kWh x the EIA Annual Energy Outlook 2025 reference
   case, 2025, CO2 g/kWh for the airport's electricity region (data from my NSERC project); from solar =
   55 kWh x 10-36 g CO2e/kWh (NREL 2024 life-cycle assessment of US utility-scale PV).
   The grid figure counts power-plant emissions only, so the comparison favours the grid.

All quantities are screening-level upper bounds: they ignore grid connection, ownership, zoning and cost.

## Deviations after running
1. **A, metric.** Dropping non-open negatives left the test sets about 68% solar, so average precision no
   longer has 0.5 as its chance level (chance is about 0.68) and the pre-set reading (AP >= 0.60) cannot tell
   anything apart. I added ROC AUC, whose chance level is 0.5 whatever the class balance, and ran the same code
   on all negatives as a control so the two can be compared. Average precision is still reported.
2. **B, outcome outside the band, upwards.** Average precision on 2025 farms (0.855) was 0.066 above the
   out-of-fold value, outside the pre-set +/-0.05 band. It is reported as "did better", not "held up".
3. **C, data sources.** NREL is now the National Laboratory of the Rockies; its API moved from developer.nrel.gov
   to developer.nlr.gov (old domain retired 29 May 2026). PVWatts returned version 8.5.0. The FAA runway file is
   the 28-day NASR subscription cycle linked from the FAA page on the day of the run (file name in the results).
4. **C, Palm Beach runways not masked.** The FAA runway-end file used had no rows for PBI, so no runway band was
   removed there and its available land is overstated. Not re-run, because of the Earth Engine quota.
5. **B, per-point scores not saved to the repo.** The summary values were copied from the notebook output; the
   per-point score file stayed in the Colab session. Re-running `followup.forward()` regenerates it.

## Results (copied from results/followup/)
- A: ROC AUC at 1,000 labels, AlphaEarth 0.726 and Sentinel-2 0.587 on open-land negatives (0.795 and 0.684 on
  all negatives). Decision rule with ROC AUC: AlphaEarth at 100 labels 0.617 vs Sentinel-2 at 1,000 labels 0.587,
  difference +0.030, 95% interval -0.005 to +0.064 ("matches").
- B: average precision 0.855 on 217 farms that opened in 2025 (out-of-fold reference 0.789).
- C: see results/followup/airport_supply.csv.

