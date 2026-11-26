"""Follow-up analyses A-C, as fixed in FOLLOWUP.md."""
import glob, io, json, os, re, time, zipfile
import numpy as np, pandas as pd, requests
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from . import config as C, train

OPEN_LAND = [20, 30, 40, 60]          # WorldCover shrubland, grassland, cropland, bare/sparse


# ---------- A. harder comparison (no Earth Engine) ----------
def harder(data_dir, out_dir, offset=-2, open_only=True, tag="followupA"):
    os.makedirs(out_dir, exist_ok=True)
    df, s2_cols, _ = train.load(data_dir, offset)
    keep = ((df.label == 1) | df.worldcover.isin(OPEN_LAND)) if open_only else (df.label >= 0)
    dropped = int((~keep).sum()); df = df[keep].reset_index(drop=True)
    fold_of = train.assign_folds(df); df["fold"] = df.p_state.map(fold_of)
    feats = {"alphaearth": C.EMB_BANDS, "sentinel2": s2_cols}
    rows = []
    for k in range(C.N_FOLDS):
        tr, te = df[df.fold != k], df[df.fold == k]; yte = te.label.values
        for n in C.LABEL_SIZES:
            for seed in C.SEEDS:
                rng = np.random.default_rng(100000 * k + 10 * n + seed)
                idx = train.draw_training_rows(tr, n, rng); ytr = df.loc[idx, "label"].values
                for f, cols in feats.items():
                    m = train.models(seed)["logreg"].fit(df.loc[idx, cols].values, ytr)
                    p = m.predict_proba(te[cols].values)[:, 1]
                    rows.append(dict(offset=offset, features=f, model="logreg", n_labels=n, fold=k, seed=seed,
                                     ap=average_precision_score(yte, p), auc=roc_auc_score(yte, p), f1=f1_score(yte, p >= 0.5),
                                     n_test=len(yte), test_pos_share=float(yte.mean())))
    res = pd.DataFrame(rows); res.to_csv(os.path.join(out_dir, f"{tag}_runs.csv"), index=False)
    summ = train.summarise(res)
    ps = res.groupby(["offset", "features", "model", "n_labels", "seed"]).auc.mean().reset_index()
    a = ps.groupby(["offset", "features", "model", "n_labels"]).auc.agg(["mean", "std"]).reset_index()
    summ["auc_mean"], summ["auc_sd"] = a["mean"].values, a["std"].values
    summ.to_csv(os.path.join(out_dir, f"{tag}_summary.csv"), index=False)
    hyp = train.hypothesis_test(res, offset=offset)
    meta = {"negatives_dropped": dropped, "n_pos": int((df.label == 1).sum()), "n_neg": int((df.label == 0).sum()),
            "test_positive_share": float(df.label.mean()), "open_land_classes": OPEN_LAND if open_only else None,
            "hypothesis": hyp}
    json.dump(meta, open(os.path.join(out_dir, f"{tag}_result.json"), "w"), indent=1)
    return summ, meta


# ---------- B. forward check on 2025 farms (Earth Engine) ----------
def forward(data_dir, model_json, out_dir):
    from . import labels, sample
    import ee
    os.makedirs(out_dir, exist_ok=True)
    farms, snap = labels.load_snapshot(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1])
    old = (C.ONLINE_YEARS, C.OFFSETS)
    C.ONLINE_YEARS = (2025, 2025)
    try:
        pts = labels.make_points(farms)
    finally:
        C.ONLINE_YEARS = old[0]
    wc = sample.sample_worldcover(pts); pts = pts.merge(wc, on="pid", how="left")
    bad = (pts.label == 0) & (pts.worldcover.isna() | (pts.worldcover == 80))
    pts = pts[~bad]
    neg = pts[pts.label == 0].sort_values(["case_id", "j"]).groupby("case_id").head(C.POINTS_PER_FARM)
    pts = pd.concat([pts[pts.label == 1], neg]).reset_index(drop=True)
    pts = pts.assign(year=2023)
    emb = sample.sample_embeddings(pts)
    d = pts.merge(emb, on=["pid", "year"])
    m = json.load(open(model_json))
    z = d[m["bands"]].values @ np.array(m["weights"]) + m["bias"]
    d["score"] = 1 / (1 + np.exp(-z))
    d[["pid", "case_id", "p_state", "p_type", "label", "worldcover", "score"]].to_csv(os.path.join(out_dir, "followupB_scores.csv"), index=False)
    ap = average_precision_score(d.label, d.score)
    ap_open = average_precision_score(d.label[(d.label == 1) | d.worldcover.isin(OPEN_LAND)],
                                      d.score[(d.label == 1) | d.worldcover.isin(OPEN_LAND)])
    res = {"snapshot_date": snap, "n_farms": int(d.case_id.nunique()), "n_pos": int((d.label == 1).sum()),
           "n_neg": int((d.label == 0).sum()), "neg_dropped_water_or_nodata": int(bad.sum()),
           "embedding_year": 2023, "ap_2025": float(ap), "ap_2025_open_land_negatives": float(ap_open),
           "oof_ap_reference": m["oof_ap"]}
    json.dump(res, open(os.path.join(out_dir, "followupB_result.json"), "w"), indent=1)
    print("FOLLOWUP_B " + json.dumps(res))
    return res


# ---------- C. airport supply (Earth Engine part + PVWatts) ----------
def faa_runways(out_csv):
    """Runway end coordinates from the FAA's current 28-day NASR subscription (CSV edition)."""
    base = "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/"
    html = requests.get(base, timeout=60).text
    links = re.findall(r'href="(https?://[^"]+_CSV\.zip)"', html)
    if not links:
        cur = re.findall(r'href="([^"]*NASR_Subscription/\d{4}-\d{2}-\d{2})"', html)
        page = requests.get(requests.compat.urljoin(base, cur[0]), timeout=60).text
        links = re.findall(r'href="(https?://[^"]+_CSV\.zip)"', page)
    url = links[0]; print("FAA NASR:", url)
    z = zipfile.ZipFile(io.BytesIO(requests.get(url, timeout=300).content))
    name = [n for n in z.namelist() if n.upper().endswith("APT_RWY_END.CSV")][0]
    rw = pd.read_csv(z.open(name), low_memory=False)
    rw.to_csv(out_csv, index=False)
    return rw, url


def runway_lines(rw, ids):
    import ee
    cols = {c.upper(): c for c in rw.columns}
    a, r, lat, lon = cols["ARPT_ID"], cols["RWY_ID"], cols["LAT_DECIMAL"], cols["LONG_DECIMAL"]
    out = {}
    for i in ids:
        g = rw[(rw[a] == i) & rw[lat].notna() & rw[lon].notna()]
        lines = []
        for _, e in g.groupby(r):
            if len(e) >= 2:
                lines.append(ee.Geometry.LineString([[float(e[lon].iloc[0]), float(e[lat].iloc[0])],
                                                     [float(e[lon].iloc[1]), float(e[lat].iloc[1])]]))
        out[i] = (ee.Geometry.MultiLineString([l.coordinates() for l in lines]) if lines else None, len(lines))
    return out


def supply_areas(airports_csv, model_json, data_dir, runways_csv, out_csv, scale=10):
    import ee
    from . import airports as A, labels
    ap = pd.read_csv(airports_csv); m = json.load(open(model_json))
    rw = pd.read_csv(runways_csv, low_memory=False)
    rl = runway_lines(rw, ap.faa_id.tolist())
    farms, _ = labels.load_snapshot(sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))[-1])
    wc = ee.ImageCollection(C.WORLDCOVER_ID).first().select("Map")
    openland = wc.remap(OPEN_LAND, [1] * len(OPEN_LAND), 0).eq(1)
    slope = ee.Terrain.slope(ee.Image("USGS/3DEP/10m"))
    score = A.score_image(m)
    area = ee.Image.pixelArea()
    rows = []
    for _, r in ap.iterrows():
        pt = ee.Geometry.Point([float(r.lon), float(r.lat)]); circ = pt.buffer(C.AIRPORT_RADIUS_M)
        near = farms.cx[r.lon - 0.1:r.lon + 0.1, r.lat - 0.1:r.lat + 0.1]
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry(json.loads(json.dumps(g.__geo_interface__)))) for g in near.geometry])
        not_farm = ee.Image(1).byte().paint(fc, 0) if len(near) else ee.Image(1).byte()
        geom, nrw = rl[r.faa_id]
        not_rwy = ee.Image(1).byte().paint(ee.FeatureCollection([ee.Feature(geom.buffer(500))]), 0) if geom else ee.Image(1).byte()
        avail = openland.And(slope.lte(5)).And(not_farm).And(not_rwy)
        img = ee.Image.cat([area.rename("land"), area.updateMask(openland).rename("open"),
                            area.updateMask(avail).rename("avail"),
                            area.updateMask(avail.And(score.gte(0.5))).rename("avail_solarlike"),
                            score.updateMask(avail).rename("score")])
        kw = dict(geometry=circ, scale=scale, crs=C.EQUAL_AREA_CRS, maxPixels=1e9)
        req = ee.Dictionary({k: img.select(k).reduceRegion(ee.Reducer.sum(), **kw).get(k) for k in ("land", "open", "avail", "avail_solarlike")}
                            ).set("score_mean", img.select("score").reduceRegion(ee.Reducer.mean(), **kw).get("score"))
        for t in range(5):
            try: v = req.getInfo(); break
            except Exception:
                if t == 4: raise
                time.sleep(10 * (t + 1))
        rows.append(dict(name=r["name"], faa_id=r.faa_id, state=r.state, lon=r.lon, lat=r.lat, emm_region=r.emm_region,
                         runways_masked=nrw, circle_km2=(v["land"] or 0) / 1e6, open_km2=(v["open"] or 0) / 1e6,
                         available_km2=(v["avail"] or 0) / 1e6, available_solarlike_km2=(v["avail_solarlike"] or 0) / 1e6,
                         mean_score_available=v["score_mean"]))
        print(r.faa_id, rows[-1]["available_km2"], flush=True)
    out = pd.DataFrame(rows); out.to_csv(out_csv, index=False)
    return out


def pvwatts(airports_csv, out_csv, api_key="DEMO_KEY"):
    ap = pd.read_csv(airports_csv); rows = []
    for _, r in ap.iterrows():
        q = dict(api_key=api_key, lat=r.lat, lon=r.lon, system_capacity=1, module_type=0, losses=14,
                 array_type=2, tilt=0, azimuth=180, timeframe="monthly")
        j = requests.get("https://developer.nlr.gov/api/pvwatts/v8.json", params=q, timeout=60).json()
        if j.get("errors"): raise RuntimeError(j["errors"])
        rows.append(dict(faa_id=r.faa_id, kwh_per_kw_year=j["outputs"]["ac_annual"],
                         capacity_factor_pct=j["outputs"]["capacity_factor"], pvwatts_version=j.get("version")))
        time.sleep(1.5)
    out = pd.DataFrame(rows); out.to_csv(out_csv, index=False)
    return out
