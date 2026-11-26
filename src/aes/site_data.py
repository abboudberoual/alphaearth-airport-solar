"""Build the JSON files the results page reads. Every number on the page comes from results/ via this file."""
import datetime, json, os, shutil
import pandas as pd
from . import config as C

REPO_URL = "https://github.com/abboudberoual/alphaearth-airport-solar"


def build(results_dir="results", site_dir="docs/data"):
    os.makedirs(site_dir, exist_ok=True)
    J = lambda n: json.load(open(os.path.join(results_dir, n)))
    summ = pd.read_csv(os.path.join(results_dir, "label_efficiency_summary.csv"))
    s2rep, meta, fm = J("stage2_report.json"), J("train_meta.json"), J("final_model.json")
    hr = J("hypothesis_result.json"); hyp, rob = hr["hypothesis"], hr["robustness"]
    m = meta["offset-2"]
    summary = {
        "placeholder": False, "generated": datetime.date.today().isoformat(),
        "uspvdb_snapshot_date": s2rep["snapshot_date"], "uspvdb_total": s2rep["uspvdb_total"],
        "n_farms": m["n_farms"], "n_positive_points": m["n_pos"], "n_negative_points": m["n_neg"],
        "n_states": len(meta["folds"]), "online_years": list(C.ONLINE_YEARS), "embedding_years": [2017, 2025],
        "n_folds": C.N_FOLDS, "n_seeds": len(C.SEEDS),
        "hypothesis": {k: hyp[k] for k in ("supported", "metric", "ae_n", "s2_n", "ae_mean", "s2_mean", "diff_mean", "diff_ci95")},
        "robustness": rob, "airport_threshold": fm["threshold"],
        "airport_threshold_note": (f"Lowest score at which precision on held-out states reaches "
                                   f"{int(C.TARGET_PRECISION * 100)}% (balanced test data); "
                                   f"it recovers only {fm['recall_at_threshold']:.1%} of solar pixels there, so the threshold itself rests on few pixels and is a rough estimate."),
        "repo_url": REPO_URL}
    chk = hr["hypothesis_one_year_before"]
    lo, hi = hyp["diff_ci95"]
    if hyp["supported"]:
        summary["verdict_text"] = ("Main test: matches, not clearly better" if lo < 0 else "Main test: beats")
        summary["verdict_mixed"] = bool(lo < 0 or not chk["supported"])
        if not chk["supported"]: summary["verdict_text"] += ". Robustness check: fails"
    else:
        summary["verdict_text"] = "Not supported"
    g = lambda off, f, n, col="ap_mean": float(summ[(summ.offset == off) & (summ.features == f) & (summ.model == "logreg") & (summ.n_labels == n)][col].iloc[0])
    ap_air = pd.read_csv(os.path.join(results_dir, "airports.csv"))
    dr = {(d["pair"], d["group"]): d for d in J("drift.json")}
    summary["findings"] = [
        f"Main test (land seen two years before opening): AlphaEarth with {hyp['ae_n']} labels scored {hyp['ae_mean']:.3f}, "
        f"Sentinel-2 with {hyp['s2_n']:,} labels scored {hyp['s2_mean']:.3f}. The difference is {hyp['diff_mean']:+.3f}, and its 95% "
        f"interval across the five held-out groups of states runs from {lo:+.3f} to {hi:+.3f}, which includes zero. By the rule "
        f"written down in advance that is \"matches\", not \"beats\"; strictly, the two cannot be told apart, and AlphaEarth could be "
        f"slightly worse.",
        f"At equal label counts AlphaEarth is ahead at every size from 50 labels up: {g(-2, 'alphaearth', 1000):.3f} against "
        f"{g(-2, 'sentinel2', 1000):.3f} at 1,000 labels. At 10 labels the two are indistinguishable "
        f"({g(-2, 'alphaearth', 10):.3f} and {g(-2, 'sentinel2', 10):.3f}; chance is about 0.5).",
        f"The robustness check did not agree with the main test. Seen one year before opening, AlphaEarth with {chk['ae_n']} labels "
        f"scored {chk['ae_mean']:.3f} and Sentinel-2 with {chk['s2_n']:,} labels scored {chk['s2_mean']:.3f} "
        f"(difference {chk['diff_mean']:+.3f}, interval {chk['diff_ci95'][0]:+.3f} to {chk['diff_ci95'][1]:+.3f}): the hypothesis fails there.",
        f"Every score is much higher one year before opening than two years before (AlphaEarth at 1,000 labels: "
        f"{g(-1, 'alphaearth', 1000):.3f} against {g(-2, 'alphaearth', 1000):.3f}). Site preparation is often already visible a year "
        f"ahead, so one-year-before scores probably measure in part \"construction has started\", not \"this land suits solar\". "
        f"The embeddings are consistent with this: a solar site's embedding typically changes more between those two years "
        f"(median similarity {dr[('Y-2 vs Y-1', 'solar')]['median']:.3f}) than nearby ordinary land does "
        f"({dr[('Y-2 vs Y-1', 'control')]['median']:.3f}). Some sites may be disturbed even earlier; that was not checked, so the "
        f"main-test scores may also contain some construction signal.",
        f"The task is hard. Even with 1,000 labels the best two-years-before score is {g(-2, 'alphaearth', 1000):.3f}: "
        f"where solar farms get built depends heavily on things a satellite cannot see.",
        f"Around the airports, the pre-registered high-confidence threshold ({fm['threshold']:.3f}) flags almost nothing: it only "
        f"recovers {fm['recall_at_threshold'] * 100:.1f}% of solar pixels in testing, and the largest flagged area near any of the "
        f"{len(ap_air)} airports is {ap_air.solar_like_km2.max():.2f} km\u00b2 ({ap_air.sort_values('solar_like_km2').name.iloc[-1]}). "
        f"The model is not confident enough for site screening at that bar. Existing solar farms were not masked out, so some "
        f"flagged pixels may be panels that are already there. The mean score column is shown for context only; "
        f"it was not part of the pre-registered plan."]
    json.dump(summary, open(os.path.join(site_dir, "summary.json"), "w"), indent=1)
    summ.to_json(os.path.join(site_dir, "label_efficiency.json"), orient="records", indent=1)
    ap = pd.read_csv(os.path.join(results_dir, "airports.csv"))
    ap[["name", "state", "lon", "lat", "solar_like_km2", "solar_like_frac", "mean_score", "existing_farms_5km", "land_km2"]] \
        .to_json(os.path.join(site_dir, "airports.json"), orient="records", indent=1)
    if os.path.exists(os.path.join(results_dir, "drift.json")):
        shutil.copy(os.path.join(results_dir, "drift.json"), os.path.join(site_dir, "drift.json"))
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
