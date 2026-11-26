"""Static figures for the results page and write-up, drawn with matplotlib from results/ and docs/img/.
Run from the repo root:  PYTHONPATH=src python -m aes.figures"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd

BLUE, ORANGE, INK, GREY = "#1f6fd1", "#d9650a", "#1b2430", "#6b7785"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#9aa4b1", "axes.labelcolor": INK,
                     "xtick.color": GREY, "ytick.color": GREY, "text.color": INK, "savefig.dpi": 170,
                     "savefig.bbox": "tight", "figure.facecolor": "white"})


def _save(fig, out, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"))
    plt.close(fig)


def fig_label_efficiency(res="results", out="docs/fig"):
    s = pd.read_csv(os.path.join(res, "label_efficiency_summary.csv")); s = s[s.model == "logreg"]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1), sharey=True)
    titles = {-2: "(a) Land seen two years before the farm opened  [main test]",
              -1: "(b) Land seen one year before  [robustness check]"}
    for ax, off in zip(axes, (-2, -1)):
        for feat, col, mk, lab in (("alphaearth", BLUE, "o", "AlphaEarth embeddings"),
                                   ("sentinel2", ORANGE, "s", "Sentinel-2 imagery (baseline)")):
            d = s[(s.offset == off) & (s.features == feat)].sort_values("n_labels")
            ax.errorbar(d.n_labels, d.ap_mean, yerr=d.ap_sd, color=col, marker=mk, ms=6, lw=2, capsize=3,
                        label=lab, markeredgecolor="white", markeredgewidth=1)
        ref = s[(s.offset == off) & (s.features == "sentinel2") & (s.n_labels == 1000)].ap_mean.iloc[0]
        ae = s[(s.offset == off) & (s.features == "alphaearth") & (s.n_labels == 100)].ap_mean.iloc[0]
        ax.axhline(ref, color=ORANGE, lw=1, ls=(0, (4, 3)), alpha=.8)
        ax.scatter([100], [ae], s=210, facecolors="none", edgecolors=INK, lw=1.4, zorder=5)
        ax.scatter([1000], [ref], s=210, facecolors="none", edgecolors=INK, lw=1.4, zorder=5)
        ax.axhline(0.5, color=GREY, lw=1, ls=":"); ax.text(10, 0.505, "coin flip", fontsize=8.5, color=GREY, va="bottom")
        ax.set_xscale("log"); ax.set_xticks([10, 50, 100, 500, 1000]); ax.set_xticklabels(["10", "50", "100", "500", "1,000"])
        ax.minorticks_off(); ax.set_ylim(0.45, 0.92); ax.grid(axis="y", color="#e6eaef", lw=.8); ax.set_axisbelow(True)
        ax.set_title(titles[off], fontsize=10.5, loc="left", pad=10)
        ax.set_xlabel("Number of labelled examples used for training (log scale)")
    axes[0].set_ylabel("Average precision on held-out states\n(1.0 = perfect ranking)")
    axes[0].legend(frameon=False, loc="upper left", fontsize=9.5)
    fig.tight_layout(w_pad=2.5)
    _save(fig, out, "fig1_label_efficiency")


def _panel(ax, path, title):
    ax.imshow(mpimg.imread(path)); ax.set_title(title, fontsize=10.5, loc="left", pad=6)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)


def _scalebar(ax, img_width_px, width_km, km):
    L = img_width_px * km / width_km; h = ax.get_ylim()[0]
    import matplotlib.patheffects as pe
    fx = [pe.withStroke(linewidth=3, foreground="#1b2430")]
    ax.plot([30, 30 + L], [h - 34, h - 34], color="white", lw=3, solid_capstyle="butt", path_effects=[pe.withStroke(linewidth=5, foreground="#1b2430")])
    ax.text(30 + L / 2, h - 62, f"{km} km", color="white", ha="center", va="bottom", fontsize=9, fontweight="bold", path_effects=fx)


def fig_site_over_time(res="results", img="docs/img", out="docs/fig", cid=406279):
    meta = {m.get("case_id"): m for m in json.load(open(os.path.join(res, "imagery_meta.json")))}[cid]
    y = meta["p_year"]
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.25))
    for ax, off, note in zip(axes, (-2, -1, 1), ("two years before opening", "one year before (ground cleared)", "operating")):
        _panel(ax, os.path.join(img, f"farm_{cid}_y{off:+d}.jpg"), f"{y + off}  |  {note}")
    _scalebar(axes[0], 1024, meta["width_km"], 1)
    fig.tight_layout(w_pad=1.0)
    _save(fig, out, "fig2_site_over_time")


def fig_airport(res="results", img="docs/img", out="docs/fig", slug="washington-dulles-international-airport"):
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.25))
    _panel(axes[0], os.path.join(img, f"airport_{slug}_rgb.jpg"), "(a) Satellite view, 2025 (circle = 5 km radius)")
    _panel(axes[1], os.path.join(img, f"airport_{slug}_score.jpg"), "(b) Model score: how much the land resembles solar-farm land")
    _scalebar(axes[0], 1024, 11.2, 2)
    cmap = LinearSegmentedColormap.from_list("score", ["#fff3c4", "#fdc24a", "#ef7f1a", "#b63a0b", "#6b1203"])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0.5, 1.0))
    cb = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.045, pad=0.04, aspect=45)
    cb.set_label("Model score (areas below 0.5 not coloured)", fontsize=9.5); cb.outline.set_visible(False)
    _save(fig, out, "fig3_airport_dulles")


def fig_harder(res="results/followup", out="docs/fig"):
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1), sharey=True)
    for ax, tag, title in zip(axes, ("followupA_control_all_negatives", "followupA"),
                              ("(a) Solar sites vs all nearby land", "(b) Solar sites vs nearby OPEN land only")):
        s = pd.read_csv(os.path.join(res, f"{tag}_summary.csv"))
        for feat, col, mk, lab in (("alphaearth", BLUE, "o", "AlphaEarth embeddings"),
                                   ("sentinel2", ORANGE, "s", "Sentinel-2 imagery (baseline)")):
            d = s[s.features == feat].sort_values("n_labels")
            ax.errorbar(d.n_labels, d.auc_mean, yerr=d.auc_sd, color=col, marker=mk, ms=6, lw=2, capsize=3,
                        label=lab, markeredgecolor="white", markeredgewidth=1)
        ax.axhline(0.5, color=GREY, lw=1, ls=":"); ax.text(10, 0.505, "coin flip", fontsize=8.5, color=GREY, va="bottom")
        ax.set_xscale("log"); ax.set_xticks([10, 50, 100, 500, 1000]); ax.set_xticklabels(["10", "50", "100", "500", "1,000"])
        ax.minorticks_off(); ax.set_ylim(0.45, 0.85); ax.grid(axis="y", color="#e6eaef", lw=.8); ax.set_axisbelow(True)
        ax.set_title(title, fontsize=10.5, loc="left", pad=10)
        ax.set_xlabel("Number of labelled examples used for training (log scale)")
    axes[0].set_ylabel("ROC AUC on held-out states\n(0.5 = chance, 1.0 = perfect)")
    axes[0].legend(frameon=False, loc="upper left", fontsize=9.5)
    fig.tight_layout(w_pad=2.5)
    _save(fig, out, "fig4_harder_comparison")


def fig_supply(res="results/followup", out="docs/fig"):
    a = pd.read_csv(os.path.join(res, "airport_supply.csv")).sort_values("available_km2").reset_index(drop=True)
    lab = [f"{n.replace(' International Airport','').replace(' Airport','').replace(' Municipal','')} ({i})" for n, i in zip(a.name, a.faa_id)]
    y = range(len(a))
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 6.8), sharey=True, gridspec_kw={"width_ratios": [1.45, 1]})
    ax = axes[0]
    gpath = os.path.join(res, "grid_areas.csv")
    if os.path.exists(gpath):
        a = a.merge(pd.read_csv(gpath)[["faa_id", "grid2_km2"]], on="faa_id", how="left")
        a["grid2_h2"] = a.grid2_km2 * a.h2_t_per_day_per_km2
        ax.barh(y, a.available_km2, color="#c9d8ee", height=.72, label="Usable open land (after masks)")
        ax.barh(y, a.grid2_km2, color=BLUE, height=.72, label="...of which within 2 km of a power line")
        for yi, km, t in zip(y, a.available_km2, a.grid2_h2):
            ax.text(km + .4, yi, f"{t:.0f} t H2/day", va="center", fontsize=8.6, color=INK)
    else:
        ax.barh(y, a.available_km2, color="#c9d8ee", height=.72, label="Usable open land (after masks)")
        ax.barh(y, a.available_solarlike_km2, color=BLUE, height=.72, label="...of which the model scores as solar-like")
        for yi, km, t in zip(y, a.available_km2, a.available_h2_t_per_day):
            ax.text(km + .4, yi, f"{t:.0f} t H2/day", va="center", fontsize=8.6, color=INK)
    ax.set_yticks(list(y)); ax.set_yticklabels(lab, fontsize=9)
    ax.set_xlabel("Land within 5 km of the airport (km²)"); ax.set_xlim(0, a.available_km2.max() * 1.32)
    ax.grid(axis="x", color="#e6eaef", lw=.8); ax.set_axisbelow(True)
    ax.set_title("(a) Usable land and the hydrogen it could make", fontsize=10.5, loc="left", pad=34)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8.8, handlelength=1.2, columnspacing=1.2)
    ax = axes[1]
    lo, hi = a.solar_h2_kgco2_per_kg_low.iloc[0], a.solar_h2_kgco2_per_kg_high.iloc[0]
    ax.axvspan(lo, hi, color="#f6c9a4", alpha=.7, lw=0)
    ax.text(hi + .4, len(a) - .2, "solar-powered", ha="left", va="bottom", fontsize=9, color=INK)
    ax.scatter(a.grid_h2_kgco2_per_kg, list(y), color="#5b6675", s=34, zorder=3, edgecolor="white", lw=.8)
    ax.text(a.grid_h2_kgco2_per_kg.max(), len(a) - .2, "local grid", ha="right", va="bottom", fontsize=9, color=INK)
    ax.set_xlim(0, a.grid_h2_kgco2_per_kg.max() * 1.12); ax.set_ylim(-.7, len(a) + .6)
    ax.set_xlabel("kg CO₂ per kg of hydrogen")
    ax.grid(axis="x", color="#e6eaef", lw=.8); ax.set_axisbelow(True)
    ax.set_title("(b) Carbon per kg of hydrogen", fontsize=10.5, loc="left", pad=34)
    fig.tight_layout(w_pad=1.5)
    _save(fig, out, "fig5_airport_supply")


if __name__ == "__main__":
    os.makedirs("docs/fig", exist_ok=True)
    fig_label_efficiency(); fig_site_over_time(); fig_airport(); fig_harder(); fig_supply()
    print("figures written to docs/fig")
