"""Data files for docs/map.html, built from results/ and data/."""
import glob, json, os
import pandas as pd
from . import labels, grid as G


def build(res="results/followup", data_dir="data", out="docs/data/map"):
    os.makedirs(out, exist_ok=True)
    sup = pd.read_csv(os.path.join(res, "airport_supply.csv")); g = pd.read_csv(os.path.join(res, "grid_areas.csv"))
    a = sup.merge(g, on="faa_id")
    a["grid2_h2"] = a.grid2_km2 * a.h2_t_per_day_per_km2
    a["available_h2"] = a.available_h2_t_per_day
    rows = []
    for _, r in a.iterrows():
        rows.append(dict(faa_id=r.faa_id, name=r["name"], state=r.state, lon=r.lon, lat=r.lat, box=list(G.bbox(r.lon, r.lat)),
                         available_km2=r.available_km2, grid1_km2=r.grid1_km2, grid2_km2=r.grid2_km2, grid5_km2=r.grid5_km2,
                         airport_to_line_km=None if pd.isna(r.airport_to_line_km) else r.airport_to_line_km,
                         max_kv_within_5km=None if pd.isna(r.max_kv_within_5km) else r.max_kv_within_5km,
                         grid2_h2=r.grid2_h2, available_h2=r.available_h2))
    json.dump(rows, open(os.path.join(out, "airports.json"), "w"), indent=1)
    farms, _ = labels.load_snapshot(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1])
    keep = []
    for r in rows:
        x0, y0, x1, y1 = r["box"]; keep.append(farms.cx[x0:x1, y0:y1])
    f = pd.concat(keep).drop_duplicates("case_id")[["case_id", "p_name", "p_year", "p_cap_ac", "geometry"]]
    import geopandas as gpd
    gpd.GeoDataFrame(f, crs=4326).to_file(os.path.join(out, "solar_farms.geojson"), driver="GeoJSON")
    return a
