"""Stage 5: apply the final embedding model to land within 5 km of each airport."""
import glob, io, json, os, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests
import ee
from . import config as C, labels

OURAIRPORTS_URL = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"


def score_image(model, year=C.AIRPORT_YEAR):
    """Per-pixel score from the logistic regression, computed on Earth Engine's servers."""
    emb = (ee.ImageCollection(C.EMB_ID).filterDate(f"{year}-01-01", f"{year + 1}-01-01").mosaic()
           .select(model["bands"]))
    logit = emb.multiply(ee.Image.constant(model["weights"])).reduce(ee.Reducer.sum()).add(model["bias"])
    return logit.multiply(-1).exp().add(1).pow(-1).rename("score")


def _one(row, model, scale):
    geom = ee.Geometry.Point([float(row.lon), float(row.lat)]).buffer(C.AIRPORT_RADIUS_M)
    p = score_image(model)
    land = ee.ImageCollection(C.WORLDCOVER_ID).first().select("Map").neq(80)
    area = ee.Image.pixelArea()
    img = ee.Image.cat([area.updateMask(land.And(p.mask())).rename("land_m2"),
                        area.updateMask(land.And(p.gte(model["threshold"]))).rename("solar_m2"),
                        p.updateMask(land).rename("mean_score")])
    kw = dict(geometry=geom, scale=scale, crs=C.EQUAL_AREA_CRS, maxPixels=1e9)
    req = ee.Dictionary({
        "land_m2": img.select("land_m2").reduceRegion(ee.Reducer.sum(), **kw).get("land_m2"),
        "solar_m2": img.select("solar_m2").reduceRegion(ee.Reducer.sum(), **kw).get("solar_m2"),
        "mean_score": img.select("mean_score").reduceRegion(ee.Reducer.mean(), **kw).get("mean_score")})
    for a in range(5):
        try:
            v = req.getInfo(); break
        except Exception:
            if a == 4: raise
            time.sleep(5 * (a + 1))
    land_m2, solar_m2, mean = v.get("land_m2") or 0.0, v.get("solar_m2") or 0.0, v.get("mean_score")
    return dict(name=row["name"], state=row.state, lon=float(row.lon), lat=float(row.lat),
                land_km2=land_m2 / 1e6, solar_like_km2=solar_m2 / 1e6,
                solar_like_frac=(solar_m2 / land_m2) if land_m2 else None, mean_score=mean)


def existing_farms(airports, data_dir):
    import geopandas as gpd
    snaps = sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))
    farms, _ = labels.load_snapshot(snaps[-1]); farms = farms.to_crs(C.EQUAL_AREA_CRS)
    pts = gpd.GeoSeries(gpd.points_from_xy(airports.lon, airports.lat), crs=4326).to_crs(C.EQUAL_AREA_CRS)
    return [int(farms.intersects(p.buffer(C.AIRPORT_RADIUS_M)).sum()) for p in pts]


def run(airports_csv, model_json, data_dir, out_csv, scale=10, workers=8):
    ap = pd.read_csv(airports_csv); model = json.load(open(model_json))
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(lambda r: _one(r, model, scale), [r for _, r in ap.iterrows()]))
    out = pd.DataFrame(rows); out["existing_farms_5km"] = existing_farms(out, data_dir)
    out = out.sort_values("solar_like_km2", ascending=False)
    out.to_csv(out_csv, index=False)
    print(f"{len(out)} airports scored at {scale} m in {time.time() - t0:.0f}s")
    return out


def ourairports_us(types=("medium_airport", "large_airport")):
    df = pd.read_csv(io.StringIO(requests.get(OURAIRPORTS_URL, timeout=120).text))
    df = df[(df.iso_country == "US") & df.type.isin(types) & df.iso_region.str.startswith("US-")]
    df = df[~df.iso_region.isin(["US-AK", "US-HI"])]            # the equal-area projection used here covers the lower 48
    return pd.DataFrame(dict(name=df.name, state=df.iso_region.str[3:], lon=df.longitude_deg, lat=df.latitude_deg,
                             ident=df.ident, type=df.type)).reset_index(drop=True)
