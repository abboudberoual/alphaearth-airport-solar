# Solar-like land near airports: a label-efficiency test of AlphaEarth embeddings

**Results page:** https://abboudberoual.github.io/alphaearth-airport-solar/

Can Google's AlphaEarth satellite embeddings find land near airports that resembles land where US solar
farms were later built, using only a handful of labelled examples? This is an independent student project
(Aboud Beroual, aerospace engineering, Concordia University). It follows from my NSERC research on hydrogen
for general-aviation airports: the long-term question is whether land around an airport could host the
solar power needed to make hydrogen on site. It is not affiliated with Google, USGS or any data provider.

## Result in one paragraph
The hypothesis, design and decision rule were committed in [HYPOTHESIS.md](HYPOTHESIS.md) before any model
was trained. On the main test (land as it looked two years before a solar farm opened, whole US states held
out), a logistic regression on AlphaEarth embeddings with 100 labels reached an average precision of 0.677,
against 0.666 for the same classifier on Sentinel-2 seasonal features with 1,000 labels. The difference is
+0.011 with a 95% interval of -0.032 to +0.055 across the five held-out folds, so the honest reading is
"matches" (the two cannot be told apart), not "beats". The robustness check (one year before opening) did **not** agree: there the
hypothesis fails (0.779 against 0.817). Scores are much higher one year before than two years before for
both kinds of feature, which suggests site preparation is often already visible a year ahead. Near the 20
airports, the pre-registered high-confidence threshold flags almost no land. All numbers are in `results/`.

## What is here
| Path | What it is |
|---|---|
| `HYPOTHESIS.md` | Pre-registration: question, design, decision rule, known limits |
| `src/aes/` | All code: label snapshot and sampling (`labels.py`, `sample.py`, `stage2.py`), experiment (`train.py`), airports (`airports.py`), page data (`site_data.py`) |
| `notebooks/reproduce.ipynb` | Runs everything top to bottom in Google Colab |
| `results/` | Outputs of the published run (see the note below) |
| `docs/` | The results page (GitHub Pages) |
| `data/airports_top20.csv` | The 20 airports from my earlier hydrogen study (the busiest for general-aviation traffic; several are also large airline airports) |

## Method in plain language
1. **Labels.** USPVDB, the USGS / Berkeley Lab database of US solar farms of 1 MW or more. All 3,472
   facilities that began operating 2019-2024 are used (snapshot of 26 November 2026, 6,611 facilities).
2. **Positives.** Three random pixels inside each farm's footprint, read from the satellite year two years
   before the farm opened, so the model sees the land and not the panels.
3. **Negatives.** Three random land pixels 2-20 km from each farm, same satellite year.
4. **Features.** AlphaEarth: 64 numbers per 10 m pixel per year (an "embedding", a compact summary learned
   by a large pretrained model). Baseline: Sentinel-2 cloud-masked seasonal medians of 10 bands plus a
   greenness index, 44 numbers.
5. **Spatial cross-validation.** States are split into 5 groups; each is held out once, so nearby pixels
   never sit on both sides of the train/test line.
6. **Label efficiency.** Train on 10, 50, 100, 500 and 1,000 labels, 5 random seeds, both feature sets on
   identical pixels; score average precision and F1 on the held-out states.
7. **Airports.** Apply the final embedding model to 2025 embeddings within 5 km of each airport, in an
   equal-area projection.

## Limits
- "Looks like land that got built on" is not "can be built on": grid connections, zoning and ownership are
  invisible from space.
- The test data are balanced 50/50; real land is overwhelmingly not solar, so real-world precision would be
  far lower.
- The 20 airports are busy and mostly urban; they are a poor sample of "small airports".
- Turning solar area into megawatts and kilograms of hydrogen is not done yet; it needs cited capacity
  factors and electrolyser efficiencies.

## Reproduce
Open `notebooks/reproduce.ipynb` in Colab, set your Earth Engine project (free non-commercial tier is
enough; only sample pixels are read, nothing is exported) and run all cells. It takes about an hour.

**Note on `results/`.** The published run happened in Colab. The files here are the run's summary outputs.
The per-run score table, the sampled feature tables and the USPVDB snapshot file are large and are not in
the repo yet. The summary files were copied out of Colab by hand at 6 decimal places; `final_model.json` holds
the model weights at 6 significant figures, and `train_meta.json` has an added `test_sets` entry with the size of
each held-out test set. Re-running the
notebook regenerates everything; a fresh USPVDB download can differ slightly from the 26 November snapshot.

## Data credits
AlphaEarth Foundations Satellite Embedding dataset (Google / Google DeepMind) via Google Earth Engine;
USPVDB (U.S. Geological Survey and Lawrence Berkeley National Laboratory); Copernicus Sentinel-2 (ESA);
ESA WorldCover. Code: MIT licence.
