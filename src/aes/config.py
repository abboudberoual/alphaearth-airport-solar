"""Fixed settings. Nothing here is tuned after seeing results."""
import os

PROJECT = os.environ.get("EE_PROJECT", "airport-solar-hydrogen-rating")
EMB_ID = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
S2_ID = "COPERNICUS/S2_SR_HARMONIZED"
WORLDCOVER_ID = "ESA/WorldCover/v200"
USPVDB_FS = "https://energy.usgs.gov/arcgis/rest/services/Hosted/uspvdbDyn/FeatureServer/0"

ONLINE_YEARS = (2019, 2024)      # solar farms that began operating in these years
OFFSETS = (-2, -1)               # satellite year relative to the year online; -2 is the main test
DRIFT_OFFSETS = (0, 1)           # extra embedding years for the "does the embedding see construction" figure
POINTS_PER_FARM = 3
NEG_CANDIDATES_PER_FARM = 4      # one spare, because some land in water and are dropped
NEG_RING_KM = (2.0, 20.0)        # negatives are drawn this far from the farm centre
NEG_MIN_DIST_M = 500.0           # and at least this far from ANY solar farm in the database
EQUAL_AREA_CRS = "EPSG:5070"     # US Albers equal-area, so areas and random points are not distorted

EMB_BANDS = [f"A{i:02d}" for i in range(64)]
S2_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
S2_QUARTERS = [("01-01", "04-01"), ("04-01", "07-01"), ("07-01", "10-01"), ("10-01", "01-01")]
S2_BAD_SCL = [0, 1, 3, 8, 9, 10]  # no data, saturated, cloud shadow, cloud (medium/high), cirrus

LABEL_SIZES = (10, 50, 100, 500, 1000)
SEEDS = (0, 1, 2, 3, 4)
N_FOLDS = 5
AIRPORT_RADIUS_M = 5000
AIRPORT_YEAR = 2025
TARGET_PRECISION = 0.95
