"""Illustrative satellite images for the results page (Sentinel-2 true colour, embedding false colour,
model score overlays). Thumbnails only; nothing here feeds the experiment."""
import glob, json, os
import pandas as pd, requests
import ee
from . import config as C, labels, airports

FARMS = [404768, 406279, 403833]          # the three farms from the stage 1 access check (CO, AZ, NJ)
AIRPORTS = ["Washington Dulles International Airport", "Laurence G. Hanscom Field", "Teterboro Airport", "Centennial Airport"]
SCORE_PALETTE = ["fff3c4", "fdc24a", "ef7f1a", "b63a0b", "6b1203"]


def s2_rgb(year, region):
    col = (ee.ImageCollection(C.S2_ID).filterBounds(region).filterDate(f"{year}-05-01", f"{year}-10-01")
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20)))
    return col.median().visualize(bands=["B4", "B3", "B2"], min=200, max=2800, gamma=1.25)


def outline(geom, width=3, color="ffffff"):
    return ee.Image().byte().paint(ee.FeatureCollection([ee.Feature(geom)]), 1, width).visualize(palette=[color])


def save(img, region, path, dim=1024):
    url = img.getThumbURL({"region": region, "dimensions": dim, "format": "jpg"})
    r = requests.get(url, timeout=300); r.raise_for_status()
    open(path, "wb").write(r.content)
    print("saved", os.path.basename(path), len(r.content))


def run(data_dir, model_json, airports_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    farms, _ = labels.load_snapshot(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1])
    meta = []
    for cid in FARMS:
        f = farms[farms.case_id == cid].iloc[0]
        g = ee.Geometry(json.loads(json.dumps(f.geometry.__geo_interface__)))
        half = max(1500.0, (float(f.p_area) ** 0.5) * 0.9)
        region = g.centroid(1).buffer(half).bounds()
        y = int(f.p_year)
        for off in (-2, -1, 1):
            save(s2_rgb(y + off, region).blend(outline(g, 2)), region, os.path.join(out_dir, f"farm_{cid}_y{off:+d}.jpg"))
        for off in (-2, 1):
            emb = (ee.ImageCollection(C.EMB_ID).filterDate(f"{y + off}-01-01", f"{y + off + 1}-01-01").mosaic()
                   .visualize(bands=["A01", "A16", "A09"], min=-0.3, max=0.3))
            save(emb.blend(outline(g, 2)), region, os.path.join(out_dir, f"farm_{cid}_emb_y{off:+d}.jpg"))
        meta.append(dict(case_id=cid, name=f.p_name, state=f.p_state, county=f.p_county, p_year=y,
                         width_km=round(2 * half / 1000, 1)))
    model = json.load(open(model_json)); ap = pd.read_csv(airports_csv)
    score = airports.score_image(model)
    for name in AIRPORTS:
        r = ap[ap.name == name].iloc[0]
        pt = ee.Geometry.Point([float(r.lon), float(r.lat)]); circle = pt.buffer(C.AIRPORT_RADIUS_M)
        region = pt.buffer(5600).bounds()
        slug = name.lower().replace("/", " ").replace(".", "").replace(" ", "-")
        base = s2_rgb(C.AIRPORT_YEAR, region)
        save(base.blend(outline(circle, 3)), region, os.path.join(out_dir, f"airport_{slug}_rgb.jpg"))
        heat = score.updateMask(score.gte(0.5)).clip(circle).visualize(min=0.5, max=1.0, palette=SCORE_PALETTE, opacity=0.8)
        save(base.blend(heat).blend(outline(circle, 3)), region, os.path.join(out_dir, f"airport_{slug}_score.jpg"))
        meta.append(dict(airport=name, slug=slug, width_km=11.2, score_shown_from=0.5))
    json.dump(meta, open(os.path.join(out_dir, "imagery_meta.json"), "w"), indent=1)
    print("IMAGERY_META " + json.dumps(meta))


def run_wide(data_dir, out_dir, dim=2400):
    """Wide 16:9 views for page headers: one solar farm (operating) and one airport."""
    os.makedirs(out_dir, exist_ok=True)
    farms, _ = labels.load_snapshot(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1])
    f = farms[farms.case_id == 406279].iloc[0]
    c = f.geometry.centroid
    def box(lon, lat, half_w_km, half_h_km):
        import math
        dlat = half_h_km / 110.57; dlon = half_w_km / (111.32 * math.cos(math.radians(lat)))
        return ee.Geometry.Rectangle([lon - dlon, lat - dlat, lon + dlon, lat + dlat])
    r = box(c.x, c.y, 8.0, 4.5)
    save(s2_rgb(int(f.p_year) + 1, r), r, os.path.join(out_dir, "wide_solar_farm_az.jpg"), dim)
    r = box(-77.4578886, 38.9522483, 8.0, 4.5)
    save(s2_rgb(C.AIRPORT_YEAR, r), r, os.path.join(out_dir, "wide_airport_dulles.jpg"), dim)
    r = box(-104.8462922, 39.5795225, 8.0, 4.5)
    save(s2_rgb(C.AIRPORT_YEAR, r), r, os.path.join(out_dir, "wide_airport_centennial.jpg"), dim)
