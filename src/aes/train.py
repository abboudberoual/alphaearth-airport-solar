"""Stages 3-4: label-efficiency experiment with whole states held out. Pure pandas / scikit-learn."""
import json, os
import numpy as np, pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from . import config as C


def load(data_dir, offset):
    """Rows usable by BOTH feature sets at this offset, so the two are compared on identical examples."""
    pts = pd.read_parquet(os.path.join(data_dir, "points.parquet"))
    emb = pd.read_parquet(os.path.join(data_dir, "emb.parquet"))
    s2 = pd.read_parquet(os.path.join(data_dir, "s2.parquet"))
    e = emb[emb.offset == offset].drop(columns=["year", "offset"])
    s = s2[s2.offset == offset].drop(columns=["year", "offset"])
    s2_cols = [c for c in s.columns if c not in ("pid", "n_clear_quarters")]
    df = pts.merge(e, on="pid").merge(s, on="pid")
    n_before = len(df)
    df = df[(df.n_clear_quarters >= 1) & np.isfinite(df[C.EMB_BANDS]).all(axis=1)].copy()
    df[s2_cols] = df[s2_cols].fillna(0.0)          # only NDVI can still be missing (zero reflectance sum)
    return df.reset_index(drop=True), s2_cols, {"merged": n_before, "usable": len(df)}


def assign_folds(pts):
    """Whole states go to one fold. Largest states first, each to the fold with the fewest farms so far."""
    counts = pts.drop_duplicates("case_id").groupby("p_state").size().sort_values(ascending=False, kind="stable")
    load_, fold = [0] * C.N_FOLDS, {}
    for st in sorted(counts.index, key=lambda s: (-counts[s], s)):
        k = int(np.argmin(load_)); fold[st] = k; load_[k] += int(counts[st])
    return fold


def models(seed):
    return {
        "logreg": make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000)),
        "rf": RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1),
    }


def draw_training_rows(train, n, rng):
    """n labels = n/2 solar + n/2 non-solar, each from a different farm neighbourhood (one pixel per farm)."""
    idx = []
    for lab in (1, 0):
        pool = train[train.label == lab]
        farms = rng.choice(pool.case_id.unique(), size=n // 2, replace=False)
        sub = pool[pool.case_id.isin(farms)]
        idx += list(sub.groupby("case_id").sample(1, random_state=int(rng.integers(1 << 31))).index)
    return idx


def label_efficiency(data_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows, meta = [], {}
    for offset in C.OFFSETS:
        df, s2_cols, counts = load(data_dir, offset)
        fold_of = assign_folds(df); df["fold"] = df.p_state.map(fold_of)
        meta[f"offset{offset}"] = dict(counts, n_farms=int(df.case_id.nunique()),
                                       n_pos=int((df.label == 1).sum()), n_neg=int((df.label == 0).sum()))
        meta["folds"] = {k: int(v) for k, v in fold_of.items()}
        feats = {"alphaearth": C.EMB_BANDS, "sentinel2": s2_cols}
        for k in range(C.N_FOLDS):
            train, test = df[df.fold != k], df[df.fold == k]
            yte = test.label.values
            for n in C.LABEL_SIZES:
                for seed in C.SEEDS:
                    rng = np.random.default_rng(100000 * k + 10 * n + seed)
                    idx = draw_training_rows(train, n, rng)       # the SAME rows for both feature sets
                    ytr = df.loc[idx, "label"].values
                    for fname, cols in feats.items():
                        for mname, m in models(seed).items():
                            m.fit(df.loc[idx, cols].values, ytr)
                            p = m.predict_proba(test[cols].values)[:, 1]
                            rows.append(dict(offset=offset, features=fname, model=mname, n_labels=n, fold=k, seed=seed,
                                             ap=average_precision_score(yte, p), f1=f1_score(yte, p >= 0.5),
                                             n_test=len(yte), test_pos_share=float(yte.mean())))
            print(f"offset {offset} fold {k} done", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(out_dir, "label_efficiency_runs.csv"), index=False)
    json.dump(meta, open(os.path.join(out_dir, "train_meta.json"), "w"), indent=1)
    return res


def summarise(res):
    """Mean over folds and seeds; the spread reported is the standard deviation across the 5 seeds
    (each seed's value being its mean over the 5 folds)."""
    per_seed = res.groupby(["offset", "features", "model", "n_labels", "seed"])[["ap", "f1"]].mean().reset_index()
    g = per_seed.groupby(["offset", "features", "model", "n_labels"])
    out = g.agg(ap_mean=("ap", "mean"), ap_sd=("ap", "std"), f1_mean=("f1", "mean"), f1_sd=("f1", "std")).reset_index()
    out["n_runs"] = res.groupby(["offset", "features", "model", "n_labels"]).size().values
    return out


def hypothesis_test(res, offset=-2, model="logreg", ae_n=100, s2_n=1000):
    """Decision rule fixed in HYPOTHESIS.md: difference in mean average precision, AlphaEarth@100 minus
    Sentinel-2@1000, with a 95% t-interval across the 5 held-out folds."""
    r = res[(res.offset == offset) & (res.model == model)]
    a = r[(r.features == "alphaearth") & (r.n_labels == ae_n)].groupby("fold").ap.mean()
    b = r[(r.features == "sentinel2") & (r.n_labels == s2_n)].groupby("fold").ap.mean()
    d = (a - b).values
    half = stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))
    return {"supported": bool(d.mean() >= 0), "metric": "average precision", "ae_n": ae_n, "s2_n": s2_n,
            "ae_mean": float(a.mean()), "s2_mean": float(b.mean()), "diff_mean": float(d.mean()),
            "diff_ci95": [float(d.mean() - half), float(d.mean() + half)], "per_fold_diff": [float(x) for x in d]}


def final_model(data_dir, out_dir, offset=-2):
    """Logistic regression on all usable AlphaEarth rows. The airport threshold is the lowest score at which
    out-of-fold (held-out-state) precision reaches TARGET_PRECISION on the balanced test data."""
    df, _, _ = load(data_dir, offset)
    fold_of = assign_folds(df); df["fold"] = df.p_state.map(fold_of)
    X, y = df[C.EMB_BANDS].values, df.label.values
    oof = np.zeros(len(df))
    for k in range(C.N_FOLDS):
        tr, te = (df.fold != k).values, (df.fold == k).values
        oof[te] = models(0)["logreg"].fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    prec, rec, thr = precision_recall_curve(y, oof)
    ok = np.where(prec[:-1] >= C.TARGET_PRECISION)[0]
    t = float(thr[ok[0]]) if len(ok) else None
    m = models(0)["logreg"].fit(X, y)
    sc, lr = m.named_steps["standardscaler"], m.named_steps["logisticregression"]
    w = lr.coef_[0] / sc.scale_; b = float(lr.intercept_[0] - (sc.mean_ * w).sum())
    out = {"offset": offset, "bands": C.EMB_BANDS, "weights": [float(v) for v in w], "bias": b, "threshold": t,
           "target_precision": C.TARGET_PRECISION, "oof_ap": float(average_precision_score(y, oof)),
           "recall_at_threshold": float(rec[ok[0]]) if len(ok) else None, "n_train": int(len(df))}
    json.dump(out, open(os.path.join(out_dir, "final_model.json"), "w"), indent=1)
    return out


def drift(data_dir, out_dir):
    """How much a site's embedding changes between years (cosine similarity; 1 = unchanged)."""
    pts = pd.read_parquet(os.path.join(data_dir, "points.parquet"))[["pid", "label"]]
    emb = pd.read_parquet(os.path.join(data_dir, "emb.parquet")).merge(pts, on="pid")
    E = {o: g.set_index("pid") for o, g in emb.groupby("offset")}
    names = {-2: "Y-2", -1: "Y-1", 0: "Y0", 1: "Y+1"}
    rows = []
    for a, b in [(-2, -1), (-1, 0), (-1, 1)]:
        for lab, gname in [(1, "solar"), (0, "control")]:
            A, B = E[a][E[a].label == lab], E[b][E[b].label == lab]
            common = A.index.intersection(B.index)
            if len(common) == 0: continue
            x, z = A.loc[common, C.EMB_BANDS].values, B.loc[common, C.EMB_BANDS].values
            cs = (x * z).sum(1) / (np.linalg.norm(x, axis=1) * np.linalg.norm(z, axis=1))
            rows.append(dict(pair=f"{names[a]} vs {names[b]}", group=gname, median=float(np.median(cs)),
                             q25=float(np.quantile(cs, .25)), q75=float(np.quantile(cs, .75)), n=int(len(cs))))
    json.dump(rows, open(os.path.join(out_dir, "drift.json"), "w"), indent=1)
    return rows


def run(data_dir, out_dir):
    res = label_efficiency(data_dir, out_dir)
    summ = summarise(res); summ.to_csv(os.path.join(out_dir, "label_efficiency_summary.csv"), index=False)
    hyp = hypothesis_test(res)
    rob = {"main_offset": -2, "check_offset": -1, "n_labels": 100}
    for key, off in (("main", -2), ("check", -1)):
        for f, short in (("alphaearth", "ae"), ("sentinel2", "s2")):
            v = summ[(summ.offset == off) & (summ.features == f) & (summ.model == "logreg") & (summ.n_labels == 100)]
            rob[f"{short}_mean_{key}"] = float(v.ap_mean.iloc[0])
    hyp_check = hypothesis_test(res, offset=-1)
    fm = final_model(data_dir, out_dir); dr = drift(data_dir, out_dir)
    json.dump({"hypothesis": hyp, "hypothesis_one_year_before": hyp_check, "robustness": rob},
              open(os.path.join(out_dir, "hypothesis_result.json"), "w"), indent=1)
    print("SUMMARY\n" + summ.round(4).to_string(index=False))
    print("HYPOTHESIS " + json.dumps(hyp)); print("HYP_CHECK " + json.dumps(hyp_check))
    print("FINAL " + json.dumps({k: v for k, v in fm.items() if k not in ("weights", "bands")}))
    print("DRIFT " + json.dumps(dr))
