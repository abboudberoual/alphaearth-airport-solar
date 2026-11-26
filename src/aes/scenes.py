"""Section background views (Sentinel-2, 2025, April-September median) and the USPVDB farms inside each frame.
The images are exported from Earth Engine by scenes_ee(); scene_farms() counts farms from the local snapshot."""
import glob, gzip, json, math, os

SCENES = {  # name: (lon, lat) of frame centre; frame is 18 km x 8.4 km. True colour, 2025 median of the months given.
    "wide_desert_sunlight_ca": (-115.395, 33.825),      # Apr-Sep
    "wide_babcock_ranch_fl": (-81.73, 26.84),           # Jan-Apr
    "wide_boston_logan": (-71.005, 42.36),              # May-Aug
    "wide_garden_city_ks": (-100.80, 37.93),            # Jun-Aug
    "wide_green_mountains_vt_autumn": (-72.95, 44.33),  # 28 Sep-22 Oct 2025, Cloud Score+ mask >= 0.6
    "wide_boston_alphaearth": (-71.005, 42.36),         # AlphaEarth 2024, bands A01/A16/A09 as RGB, -0.3..0.3
}
HALF_W_KM, HALF_H_KM = 9.0, 4.2
MONTHS = {"wide_desert_sunlight_ca": (4, 9), "wide_babcock_ranch_fl": (1, 4), "wide_boston_logan": (5, 8), "wide_garden_city_ks": (6, 8)}


def frame(lon, lat):
    dlat = HALF_H_KM / 110.57; dlon = HALF_W_KM / (111.32 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def scenes_ee(year=2025, folder="aes_section_imagery"):
    """Run in Colab: exports each frame to Google Drive as an 8 m RGB GeoTIFF."""
    import ee
    out = {}
    for k, (lon, lat) in SCENES.items():
        if k not in MONTHS: continue  # the autumn and AlphaEarth views were made separately, see SCENES comments
        m0, m1 = MONTHS[k]
        r = ee.Geometry.Rectangle(list(frame(lon, lat)))
        img = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(r)
               .filterDate(f"{year}-01-01", f"{year}-12-31").filter(ee.Filter.calendarRange(m0, m1, "month"))
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10)).median()
               .select(["B4", "B3", "B2"]).visualize(min=200, max=2600, gamma=1.25))
        t = ee.batch.Export.image.toDrive(image=img, description=k, folder=folder, fileNamePrefix=k, region=r,
                                          scale=8, crs="EPSG:3857", fileFormat="GeoTIFF", maxPixels=1e9)
        t.start(); out[k] = t
    return out


def scene_farms(data_dir="data", out="results/followup/scene_farms.json"):
    import geopandas as gpd
    from shapely.geometry import box
    g = gpd.read_file(gzip.open(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1]))
    res = {}
    for k, (lon, lat) in SCENES.items():
        s = g[g.intersects(box(*frame(lon, lat)))]
        res[k] = {"n_farms": int(len(s)), "mw_ac": round(float(s.p_cap_ac.sum())), "names": sorted(s.p_name.tolist())}
    json.dump(res, open(out, "w"), indent=1)
    return res


if __name__ == "__main__":
    print(json.dumps({k: {a: b for a, b in v.items() if a != "names"} for k, v in scene_farms().items()}))
