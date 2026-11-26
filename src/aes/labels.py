"""Download a dated USPVDB snapshot and draw positive / negative sample points."""
import datetime, gzip, json, time
import numpy as np, pandas as pd, requests
import geopandas as gpd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from . import config as C


def fetch_uspvdb(out_path, page=200):
    """All facilities with polygons, straight from the public USGS feature service."""
    feats, offset = [], 0
    while True:
        for attempt in range(5):
            try:
                r = requests.get(C.USPVDB_FS + "/query", timeout=120, params={
                    "where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
                    "orderByFields": "case_id", "resultOffset": offset, "resultRecordCount": page,
                    "geometryPrecision": 6})
                r.raise_for_status(); js = r.json(); break
            except Exception as e:  # network hiccup: wait and retry
                if attempt == 4: raise
                time.sleep(3 * (attempt + 1))
        got = js.get("features", [])
        feats += got; offset += len(got)
        if len(got) < page: break
    snap = {"type": "FeatureCollection", "snapshot_date": datetime.date.today().isoformat(),
            "source": C.USPVDB_FS, "features": feats}
    with gzip.open(out_path, "wt") as f: json.dump(snap, f)
    return snap


def load_snapshot(path):
    with gzip.open(path, "rt") as f: snap = json.load(f)
    rows = [dict(f["properties"], geometry=shape(f["geometry"])) for f in snap["features"] if f.get("geometry")]
    g = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    g = g.drop_duplicates("case_id").reset_index(drop=True)
    return g, snap["snapshot_date"]


def _points_in_polygon(poly, n, rng):
    inner = poly.buffer(-10)                     # stay 10 m inside the edge where the shape allows
    if inner.is_empty: inner = poly
    minx, miny, maxx, maxy = inner.bounds
    out = []
    for _ in range(20000):
        p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if inner.contains(p):
            out.append(p)
            if len(out) == n: break
    return out


def make_points(farms_all):
    """Returns one row per sample point. Coordinates are drawn in an equal-area projection."""
    g = farms_all.to_crs(C.EQUAL_AREA_CRS)
    g["geometry"] = g.geometry.buffer(0)
    tree = STRtree(list(g.geometry.values))
    sel = g[(g.p_year >= C.ONLINE_YEARS[0]) & (g.p_year <= C.ONLINE_YEARS[1])]
    r1, r2 = C.NEG_RING_KM[0] * 1000, C.NEG_RING_KM[1] * 1000
    rows = []
    for _, f in sel.iterrows():
        rng = np.random.default_rng(int(f.case_id))
        base = dict(case_id=int(f.case_id), p_year=int(f.p_year), p_state=f.p_state,
                    p_type=f.p_type, p_area=float(f.p_area or 0))
        for j, p in enumerate(_points_in_polygon(f.geometry, C.POINTS_PER_FARM, rng)):
            rows.append(dict(base, label=1, j=j, x=p.x, y=p.y))
        c = f.geometry.centroid; j = 0
        for _ in range(200):
            if j == C.NEG_CANDIDATES_PER_FARM: break
            r = np.sqrt(rng.uniform(r1 ** 2, r2 ** 2)); a = rng.uniform(0, 2 * np.pi)
            p = Point(c.x + r * np.cos(a), c.y + r * np.sin(a))
            near = tree.query(p.buffer(C.NEG_MIN_DIST_M))
            if len(near) == 0:
                rows.append(dict(base, label=0, j=j, x=p.x, y=p.y)); j += 1
    df = pd.DataFrame(rows)
    ll = gpd.GeoSeries(gpd.points_from_xy(df.x, df.y), crs=C.EQUAL_AREA_CRS).to_crs(4326)
    df["lon"], df["lat"] = ll.x.values, ll.y.values
    df["pid"] = np.arange(len(df))
    return df
