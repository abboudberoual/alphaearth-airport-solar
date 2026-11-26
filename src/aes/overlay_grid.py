"""Redraw the 'usable and within 2 km of a line' overlay images from the usable-land overlay and the line file.
Illustration only: the reported areas come from Earth Engine (grid.grid_areas)."""
import json, os
import numpy as np, pandas as pd, geopandas as gpd
from PIL import Image, ImageDraw
from shapely.geometry import box
from shapely.ops import transform as stransform
from pyproj import Transformer
from . import grid as G, config as C

NOT_OPERATING = {"NOT IN SERVICE", "OUT OF SERVICE", "INACTIVE", "PROPOSED", "UNDER CONSTRUCTION", "RETIRED", "DECOMMISSIONED"}


def redraw(airports_csv, lines_geojson, overlay_dir, km=2.0):
    ap = pd.read_csv(airports_csv)
    lines = gpd.read_file(lines_geojson)
    lines = lines[~lines.STATUS.fillna("").str.upper().isin(NOT_OPERATING)]
    to3857 = Transformer.from_crs(C.EQUAL_AREA_CRS, 3857, always_xy=True).transform
    t4 = Transformer.from_crs(4326, 3857, always_xy=True).transform
    for _, r in ap.iterrows():
        x0, y0, x1, y1 = G.bbox(r.lon, r.lat)
        av = Image.open(os.path.join(overlay_dir, f"{r.faa_id}_avail.png")).convert("RGBA")
        W, H = av.size
        X0, Y0 = t4(x0, y0); X1, Y1 = t4(x1, y1)
        near = lines[lines.intersects(box(x0, y0, x1, y1).buffer(0.05))].to_crs(C.EQUAL_AREA_CRS)
        mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
        if len(near):
            buf = stransform(to3857, near.buffer(km * 1000).union_all())
            polys = [buf] if buf.geom_type == "Polygon" else list(buf.geoms)
            px = lambda c: [((x - X0) / (X1 - X0) * W, (Y1 - y) / (Y1 - Y0) * H) for x, y in c]
            for p in polys:
                d.polygon(px(p.exterior.coords), fill=255)
                for h in p.interiors: d.polygon(px(h.coords), fill=0)
        a = np.array(av); m = np.array(mask) > 0
        out = np.zeros_like(a); keep = (a[..., 3] > 0) & m
        out[keep] = [31, 111, 209, 217]
        Image.fromarray(out, "RGBA").save(os.path.join(overlay_dir, f"{r.faa_id}_grid.png"), optimize=True)
        print(r.faa_id, int(keep.sum()), "px")
