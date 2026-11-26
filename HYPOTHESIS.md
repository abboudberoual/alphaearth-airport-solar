# Pre-registration: what I will test, fixed before any model is trained

Written and committed on 26 November 2026, **before** running any classifier. The git history shows this
file and `src/aes/train.py` were committed before the first results file. Nothing below is changed after
seeing results; any later deviation is listed at the bottom with the reason.

## Question
Can Google's AlphaEarth satellite embeddings (64 numbers that summarise a year of satellite observations
for each 10 m pixel) find land near airports that resembles land where US solar farms were later built,
using only a handful of labelled examples? The longer-term motivation is on-site solar power for hydrogen
production at airports; that conversion is a later step and is not tested here.

## Hypothesis
With **100** labelled examples, a logistic regression (a straight-line classifier, often called a
"linear probe" when it sits on top of a pretrained model) on AlphaEarth embeddings reaches an average
precision **at least as high** as the same classifier trained on **1,000** examples of Sentinel-2
seasonal-composite features. A clear failure is an equally valid result and will be reported as-is.

## Design (fixed)
- **Labels:** USPVDB (USGS / Berkeley Lab), a dated snapshot of the public feature service saved in `data/`.
  Every facility that began operating 2019-2024 is used; no filtering by site type.
- **Positives:** 3 random pixels inside each facility's array footprint.
- **Main test uses the satellite year TWO years before the facility began operating**, so the model sees
  untouched land rather than panels or a construction site. **One year before** is run as a robustness check.
- **Negatives:** for each facility, 3 random land pixels 2-20 km from its centre, at least 500 m from any
  facility in the database (any year), not permanent water, taken from the **same satellite year** as that
  facility's positives (so the year cannot give the answer away).
- **Features compared on identical pixels:**
  - AlphaEarth: the 64 embedding values.
  - Sentinel-2 baseline: cloud-masked median reflectance of 10 bands in each of the 4 quarters of the year,
    plus a greenness index (NDVI) per quarter = 44 values. A quarter with no clear view is filled with the
    mean of that pixel's other quarters. This is a deliberately stronger baseline than one annual median.
- **Split:** spatial cross-validation. US states are divided into 5 groups; each group is held out once and
  the model is trained only on the other four, so nearby pixels can never be in both training and test.
- **Training sizes:** 10, 50, 100, 500, 1,000 labels (half solar, half not; one pixel per facility
  neighbourhood), 5 random seeds each. Both feature sets get exactly the same training pixels.
- **Classifiers:** logistic regression (standardised inputs, C = 1, no tuning) is the primary model. A random
  forest (300 trees, defaults) is reported alongside so the baseline also gets a non-linear learner.
  No hyperparameter is tuned on test data, or at all.
- **Metrics:** average precision (primary) and F1 at a 0.5 threshold, on the held-out states.

## Decision rule
Compute, for each of the 5 held-out folds, mean average precision of AlphaEarth at 100 labels minus
Sentinel-2 at 1,000 labels (logistic regression, two-years-before).
- Mean difference >= 0: hypothesis **supported**. If the 95% interval across folds includes 0, I say
  "matches", not "beats".
- Mean difference < 0: hypothesis **not supported**.

## Airport step (fixed)
The final model is a logistic regression on all usable two-years-before AlphaEarth samples, applied to the
2025 embeddings within 5 km of each airport. A pixel counts as "solar-like" if its score is above the
lowest threshold at which precision on held-out states reaches 95%. Areas are computed in an equal-area
projection (EPSG:5070). Permanent water is excluded.

## Known limits, stated in advance
- "Looks like land that was built on" is not "can be built on": grid connections, zoning, ownership and
  price are invisible from space.
- The test set is balanced 50/50. Real land is overwhelmingly not solar, so real-world precision will be
  far lower than test precision, and the airport areas are an upper-end screening estimate.
- Negatives near a state border can lie in a neighbouring state.
- AlphaEarth embeddings already summarise optical, radar and other sources; the baseline uses optical only.

## Differences from my original brief
1. Two-years-before is the main test and one-year-before the check (the reverse of the brief), because the
   stage 1 access check showed a site whose embedding had already changed a year before it opened.
2. Negatives come from a 2-20 km ring around each facility instead of "the same county" (same idea, no
   county boundaries needed).
3. The baseline is seasonal composites rather than one annual median, to make it a fairer opponent.

## Deviations and additions after results
The sections above are unchanged from the pre-registration commit. Added or found afterwards:
1. **Analyses added after seeing results (exploratory, not pre-registered):** the formal 100-vs-1,000 test at
   one year before; the year-to-year embedding similarity ("drift") comparison; the mean score per airport.
2. **The label snapshot file is not in `data/` yet**, contrary to the Labels line above. It was saved in the
   Colab session of the run (26 November 2026) and is too large to copy out by the route used. Until it is
   added, a re-run downloads a fresh snapshot.
3. **Implementation details not spelled out above:** positives are drawn at least 10 m inside the footprint
   where its shape allows; the 500 m rule is applied to each farm's bounding box, which is slightly stricter
   than stated; four negative candidates are drawn per farm and those on water or with no land-cover value
   are dropped, so some farms have fewer than three negatives (10,232 in total for 3,472 farms); positive and
   negative training pixels are drawn independently, so one farm neighbourhood can supply one of each.
4. **"Never" was too strong.** Folds follow the farm's state. Two farms either side of a state border, or a
   negative that falls across the border, can be close together in different folds.
5. **Not pre-registered and not done:** existing solar farms are not masked out of the airport areas; the
   baseline uses single pixels while the embeddings also carry some spatial context; Alaska and Hawaii farms
   are included although the equal-area projection is designed for the lower 48 states.
6. **Timing.** The pre-registration commit was made at about 14:00 and the Colab run that produced the
   results ran from about 14:10 to 14:50 (Toronto time) on the same day.
