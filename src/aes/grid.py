"""D. Grid access, and overlay images for the interactive map."""
import glob, json, math, os, time
import numpy as np, pandas as pd, requests
from . import config as C

LINES_FS = "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Electric_Power_Transmission_Lines/FeatureServer/0"
BOX_KM = 12.0


def bbox(lon, lat, km=BOX_KM):
    dlat = km / 110.57; dlon = km / (111.32 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def fetch_lines(airports_csv, out_geojson):
    ap = pd.read_csv(airports_csv); feats, seen = [], set()
    for _, r in ap.iterrows():
        x0, y0, x1, y1 = bbox(r.lon, r.lat)
        off = 0
        while True:
            j = requests.get(LINES_FS + "/query", timeout=120, params={
                "where": "1=1", "geometry": f"{x0},{y0},{x1},{y1}", "geometryType": "esriGeometryEnvelope",
                "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "ID,STATUS,VOLTAGE,VOLT_CLASS,OWNER,TYPE",
                "outSR": 4326, "f": "geojson", "resultOffset": off, "resultRecordCount": 1000, "geometryPrecision": 5}).json()
            got = j.get("features", [])
            for f in got:
                k = f["properties"].get("ID")
                if k not in seen:
                    seen.add(k); feats.append(f)
            off += len(got)
            if len(got) < 1000: break
        print(r.faa_id, "lines so far", len(feats), flush=True)
    gj = {"type": "FeatureCollection", "source": LINES_FS, "retrieved": time.strftime("%Y-%m-%d"), "features": feats}
    json.dump(gj, open(out_geojson, "w"))
    return gj


def grid_areas(airports_csv, model_json, data_dir, runways_csv, lines_geojson, out_csv, overlay_dir, scale=10, only=None):
    import ee
    from . import airports as A, labels, followup as F
    ap = pd.read_csv(airports_csv); m = json.load(open(model_json))
    if only: ap = ap[ap.faa_id.isin(only)]
    rl = F.runway_lines(pd.read_csv(runways_csv, low_memory=False), ap.faa_id.tolist())
    farms, _ = labels.load_snapshot(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1])
    import geopandas as gpd
    from shapely.geometry import box as sbox, Point
    lines = json.load(open(lines_geojson))["features"]
    # Keep a line unless its status says it is not operating. "NOT AVAILABLE" means the status was not recorded.
    NOT_OPERATING = {"NOT IN SERVICE", "OUT OF SERVICE", "INACTIVE", "PROPOSED", "UNDER CONSTRUCTION", "RETIRED", "DECOMMISSIONED"}
    lines = [f for f in lines if str(f["properties"].get("STATUS", "")).upper() not in NOT_OPERATING and f.get("geometry")]
    lg = gpd.GeoDataFrame.from_features(lines, crs=4326); lg["i"] = range(len(lg)); lg_m = lg.to_crs(C.EQUAL_AREA_CRS)
    wc = ee.ImageCollection(C.WORLDCOVER_ID).first().select("Map")
    openland = wc.remap(F.OPEN_LAND, [1] * len(F.OPEN_LAND), 0).eq(1)
    slope = ee.Terrain.slope(ee.Image("USGS/3DEP/10m"))
    score = A.score_image(m); area = ee.Image.pixelArea()
    os.makedirs(overlay_dir, exist_ok=True); rows = []
    for _, r in ap.iterrows():
        x0, y0, x1, y1 = bbox(r.lon, r.lat)
        box = ee.Geometry.Rectangle([x0, y0, x1, y1])
        idx = lg[lg.intersects(sbox(x0, y0, x1, y1))].i.tolist()
        near = [lines[i] for i in idx]
        lfc = ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"])) for f in near]) if near else None
        dist = lfc.distance(searchRadius=20000, maxError=10) if near else ee.Image.constant(1e9)
        circ = ee.Geometry.Point([float(r.lon), float(r.lat)]).buffer(C.AIRPORT_RADIUS_M)
        nf = farms.cx[x0:x1, y0:y1]
        ffc = ee.FeatureCollection([ee.Feature(ee.Geometry(json.loads(json.dumps(g.__geo_interface__)))) for g in nf.geometry])
        not_farm = ee.Image(1).byte().paint(ffc, 0) if len(nf) else ee.Image(1).byte()
        geom, nrw = rl[r.faa_id]
        not_rwy = ee.Image(1).byte().paint(ee.FeatureCollection([ee.Feature(geom.buffer(500))]), 0) if geom else ee.Image(1).byte()
        avail = openland.And(slope.lte(5)).And(not_farm).And(not_rwy)
        bands = {"avail": avail}
        for km in (1, 2, 5):
            bands[f"grid{km}"] = avail.And(dist.lte(km * 1000))
        kw = dict(geometry=circ, scale=scale, crs=C.EQUAL_AREA_CRS, maxPixels=1e9)
        req = ee.Dictionary({k: area.updateMask(v).reduceRegion(ee.Reducer.sum(), **kw).get("area") for k, v in bands.items()})
        for t in range(5):
            try: v = req.getInfo(); break
            except Exception:
                if t == 4: raise
                time.sleep(10 * (t + 1))
        pt_m = gpd.GeoSeries([Point(float(r.lon), float(r.lat))], crs=4326).to_crs(C.EQUAL_AREA_CRS).iloc[0]
        dm = lg_m[lg_m.i.isin(idx)].distance(pt_m)
        kv5 = lg_m[lg_m.distance(pt_m) <= 5000].VOLTAGE.tolist()
        kv5 = [x for x in kv5 if x is not None and x > 0]
        rows.append(dict(faa_id=r.faa_id, lines_in_box=len(near), available_km2_check=(v.get("avail") or 0) / 1e6,
                         grid1_km2=(v.get("grid1") or 0) / 1e6, grid2_km2=(v.get("grid2") or 0) / 1e6, grid5_km2=(v.get("grid5") or 0) / 1e6,
                         airport_to_line_km=float(dm.min() / 1000) if len(dm) else None,
                         max_kv_within_5km=max(kv5) if kv5 else None))
        print(r.faa_id, rows[-1], flush=True)
        # overlays: transparent PNGs over the 12 km box, for the interactive map
        vis = {"avail": avail.selfMask().visualize(palette=["8ec5ff"], opacity=0.55),
               "grid": bands["grid2"].selfMask().visualize(palette=["1f6fd1"], opacity=0.85),
               "score": score.updateMask(avail.And(score.gte(0.5))).visualize(min=0.5, max=1.0, palette=["fff3c4", "fdc24a", "ef7f1a", "b63a0b", "6b1203"], opacity=0.85)}
        for k, img in vis.items():
            url = img.clip(box).getThumbURL({"region": box, "dimensions": 900, "format": "png", "crs": "EPSG:3857"})
            for t in range(5):
                try:
                    c = requests.get(url, timeout=300); c.raise_for_status(); break
                except Exception:
                    if t == 4: raise
                    time.sleep(8 * (t + 1))
            open(os.path.join(overlay_dir, f"{r.faa_id}_{k}.png"), "wb").write(c.content)
    out = pd.DataFrame(rows); out.to_csv(out_csv, index=False)
    return out


def _coords(g):
    t = g["type"]; c = g["coordinates"]
    if t == "LineString": return c
    if t == "MultiLineString": return [p for line in c for p in line]
    return []


def _intersects(g, b):
    x0, y0, x1, y1 = b
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in _coords(g))


def _near_point(g, lon, lat, km):
    kx = 111.32 * math.cos(math.radians(lat)); ky = 110.57
    return any(math.hypot((x - lon) * kx, (y - lat) * ky) <= km for x, y in _coords(g))
