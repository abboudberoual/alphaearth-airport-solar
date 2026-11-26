"""Stage 2: snapshot the labels, draw points, sample features. Run inside an authenticated Earth Engine session."""
import glob, json, os, time
import numpy as np, pandas as pd
from . import config as C, labels, sample


def run(data_dir, limit=None, s2_workers=8):
    os.makedirs(data_dir, exist_ok=True)
    snaps = sorted(glob.glob(os.path.join(data_dir, "uspvdb_snapshot_*.geojson.gz")))
    if not snaps:
        import datetime
        p = os.path.join(data_dir, f"uspvdb_snapshot_{datetime.date.today():%Y%m%d}.geojson.gz")
        labels.fetch_uspvdb(p); snaps = [p]
    farms, snap_date = labels.load_snapshot(snaps[-1])
    print(f"USPVDB snapshot {snap_date}: {len(farms)} facilities with polygons")

    pts = labels.make_points(farms)
    if limit:                                    # small timing run only
        keep = pd.Series(pts.case_id.unique()).sample(limit, random_state=0)
        pts = pts[pts.case_id.isin(keep)]
    print(f"candidate points: {int((pts.label == 1).sum())} positive, {int((pts.label == 0).sum())} negative, "
          f"{pts.case_id.nunique()} farms")

    wc = sample.sample_worldcover(pts)
    pts = pts.merge(wc, on="pid", how="left")
    neg = pts[(pts.label == 0)]
    bad = neg[neg.worldcover.isna() | (neg.worldcover == 80)]     # 80 = permanent water; NaN = no land-cover data
    pts = pts.drop(bad.index)
    neg = pts[pts.label == 0].sort_values(["case_id", "j"]).groupby("case_id").head(C.POINTS_PER_FARM)
    pts = pd.concat([pts[pts.label == 1], neg]).reset_index(drop=True)
    print(f"negatives dropped for water / no data: {len(bad)}; kept points: "
          f"{int((pts.label == 1).sum())} positive, {int((pts.label == 0).sum())} negative")
    pts.to_parquet(os.path.join(data_dir, "points.parquet"))

    t0 = time.time()
    frames = []
    for off in list(C.OFFSETS) + list(C.DRIFT_OFFSETS):
        p = pts if off in C.OFFSETS else pts[pts.label == 1]
        frames.append(p.assign(year=p.p_year + off, offset=off))
    allp = pd.concat(frames)
    emb = sample.sample_embeddings(allp).merge(allp[["pid", "year", "offset"]], on=["pid", "year"])
    emb[C.EMB_BANDS] = emb[C.EMB_BANDS].astype("float32")
    emb.to_parquet(os.path.join(data_dir, "emb.parquet"))
    print(f"embeddings: {len(emb)} of {len(allp)} samples returned, {time.time() - t0:.0f}s")

    t0 = time.time()
    s2p = allp[allp.offset.isin(C.OFFSETS)]
    raw = sample.sample_s2(s2p, workers=s2_workers).merge(s2p[["pid", "year", "offset"]], on=["pid", "year"])
    s2 = sample.s2_features(raw).merge(raw[["pid", "year", "offset"]], on=["pid", "year"])
    fcols = [c for c in s2.columns if c not in ("pid", "year", "offset", "n_clear_quarters")]
    s2[fcols] = s2[fcols].astype("float32")
    s2.to_parquet(os.path.join(data_dir, "s2.parquet"))
    print(f"sentinel-2: {len(s2)} of {len(s2p)} samples returned, {time.time() - t0:.0f}s")

    rep = {"snapshot_date": snap_date, "uspvdb_total": int(len(farms)), "n_farms": int(pts.case_id.nunique()),
           "n_pos": int((pts.label == 1).sum()), "n_neg": int((pts.label == 0).sum()),
           "neg_dropped_water_or_nodata": int(len(bad))}
    for off in C.OFFSETS:
        e = emb[emb.offset == off]; s = s2[s2.offset == off]
        rep[f"offset{off}"] = {
            "emb_returned": int(len(e)), "s2_returned": int(len(s)),
            "s2_clear_quarters_counts": {int(k): int(v) for k, v in s.n_clear_quarters.value_counts().sort_index().items()},
            "s2_zero_clear_by_year": {int(k): int(v) for k, v in s[s.n_clear_quarters == 0].groupby("year").size().items()},
            "samples_by_year": {int(k): int(v) for k, v in s.groupby("year").size().items()}}
    json.dump(rep, open(os.path.join(data_dir, "stage2_report.json"), "w"), indent=1)
    print("STAGE2_REPORT " + json.dumps(rep))
    return rep
