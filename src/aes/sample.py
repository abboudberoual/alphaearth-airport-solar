"""Sample AlphaEarth embeddings and Sentinel-2 features at points. Samples pixels only; exports no images."""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
import ee
from . import config as C


def _fc(chunk):
    return ee.FeatureCollection([ee.Feature(ee.Geometry.Point([float(lo), float(la)]), {"pid": int(p)})
                                 for p, lo, la in zip(chunk.pid, chunk.lon, chunk.lat)])


def _fetch(img, fc, cols, scale=10):
    s = img.sampleRegions(collection=fc, properties=["pid"], scale=scale, geometries=False)
    return s.reduceColumns(ee.Reducer.toList(len(cols) + 1), ["pid"] + cols).get("list").getInfo()


def _retry(fn, tries=5):
    for a in range(tries):
        try: return fn()
        except Exception as e:
            if a == tries - 1: raise
            time.sleep(5 * (a + 1))


def emb_image(year):
    return ee.ImageCollection(C.EMB_ID).filterDate(f"{year}-01-01", f"{year + 1}-01-01").mosaic()


def s2_image(year, fc):
    """Four seasonal (quarterly) cloud-masked median composites, 10 bands each."""
    def mask(i):
        scl = i.select("SCL")
        ok = scl.remap(C.S2_BAD_SCL, [0] * len(C.S2_BAD_SCL), 1)
        return i.select(C.S2_BANDS).updateMask(ok)
    col = ee.ImageCollection(C.S2_ID).filterBounds(fc)
    out = []
    for q, (a, b) in enumerate(C.S2_QUARTERS):
        end = f"{year + 1}-{b}" if q == 3 else f"{year}-{b}"
        m = col.filterDate(f"{year}-{a}", end).map(mask).median()
        # an empty quarter gives an image with no bands; add fully masked bands so names stay fixed
        empty = ee.Image.constant([0] * len(C.S2_BANDS)).rename(C.S2_BANDS).updateMask(0)
        m = ee.Image(ee.Algorithms.If(m.bandNames().size().gt(0), m, empty))
        out.append(m.select(C.S2_BANDS, [f"{x}_q{q + 1}" for x in C.S2_BANDS]))
    return ee.Image.cat(out).unmask(-9999)


S2_COLS = [f"{b}_q{q}" for q in range(1, 5) for b in C.S2_BANDS]


def _run(jobs, workers, label):
    """jobs: list of (key, callable). Returns list of results; prints progress."""
    res, t0, done = [], time.time(), 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(_retry, fn): k for k, fn in jobs}
        for f in as_completed(futs):
            res.append((futs[f], f.result())); done += 1
            if done % max(1, len(jobs) // 10) == 0 or done == len(jobs):
                print(f"  {label}: {done}/{len(jobs)} requests, {time.time() - t0:.0f}s", flush=True)
    return res


def sample_embeddings(pts, year_col="year", chunk=500, workers=8):
    """pts needs pid, lon, lat and a year column. Returns DataFrame pid, year, A00..A63."""
    jobs = []
    for year, g in pts.groupby(year_col):
        g = g.sort_values(["lon", "lat"])
        for i in range(0, len(g), chunk):
            c = g.iloc[i:i + chunk]
            jobs.append(((int(year), i), (lambda c=c, year=int(year): _fetch(emb_image(year), _fc(c), C.EMB_BANDS))))
    rows = []
    for (year, _), lst in _run(jobs, workers, "embeddings"):
        for r in lst: rows.append([int(r[0]), year] + r[1:])
    return pd.DataFrame(rows, columns=["pid", "year"] + C.EMB_BANDS)


def sample_s2(pts, year_col="year", chunk=120, workers=8):
    """Returns DataFrame pid, year, 40 seasonal band medians (NaN where no clear view)."""
    jobs = []
    for year, g in pts.groupby(year_col):
        g = g.sort_values(["case_id", "label", "j"])      # keeps a farm and its negatives in one request
        for i in range(0, len(g), chunk):
            c = g.iloc[i:i + chunk]
            def fn(c=c, year=int(year)):
                fc = _fc(c); return _fetch(s2_image(year, fc), fc, S2_COLS)
            jobs.append(((int(year), i), fn))
    rows = []
    for (year, _), lst in _run(jobs, workers, "sentinel-2"):
        for r in lst: rows.append([int(r[0]), year] + r[1:])
    df = pd.DataFrame(rows, columns=["pid", "year"] + S2_COLS)
    df[S2_COLS] = df[S2_COLS].where(df[S2_COLS] > -9000)
    return df


def sample_worldcover(pts, chunk=2000, workers=8):
    img = ee.ImageCollection(C.WORLDCOVER_ID).first().select("Map")
    g = pts.sort_values(["lon", "lat"])
    jobs = [(i, (lambda c=g.iloc[i:i + chunk]: _fetch(img, _fc(c), ["Map"]))) for i in range(0, len(g), chunk)]
    rows = [r for _, lst in _run(jobs, workers, "land cover") for r in lst]
    return pd.DataFrame(rows, columns=["pid", "worldcover"]).astype(int)


def s2_features(df):
    """Fill a missing season with the mean of that point's other seasons, then add NDVI per season.
    NDVI = (near-infrared - red) / (near-infrared + red), a standard greenness index."""
    out = df[["pid", "year"]].copy()
    X = df[S2_COLS].copy()
    for b in C.S2_BANDS:
        cols = [f"{b}_q{q}" for q in range(1, 5)]
        m = X[cols].mean(axis=1)
        for c in cols: X[c] = X[c].fillna(m)
    for q in range(1, 5):
        nir, red = X[f"B8_q{q}"], X[f"B4_q{q}"]
        X[f"NDVI_q{q}"] = (nir - red) / (nir + red).replace(0, np.nan)
    out["n_clear_quarters"] = df[[f"B4_q{q}" for q in range(1, 5)]].notna().sum(axis=1).values
    return pd.concat([out, X], axis=1)
