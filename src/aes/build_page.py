"""Build the results page (docs/index.html) from results/. Every number in the page is filled in here.
Run from the repo root:  PYTHONPATH=src python -m aes.build_page"""
import json, os
import pandas as pd

REPO = "https://github.com/abboudberoual/alphaearth-airport-solar"
CSS = """
body{margin:0;background:#fff;color:#1b2430;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:18px;line-height:1.6}
a{color:#1557b0}a:hover{color:#0b3a7a}
img{max-width:100%;display:block}
.hero{min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 28px;background-size:cover;background-position:center;position:relative}
.hero::before{content:"";position:absolute;inset:0;background:rgba(14,18,26,.46)}
.hero h1{position:relative;color:#fff;font-size:clamp(34px,5.4vw,68px);line-height:1.08;letter-spacing:-.02em;font-weight:600;max-width:15em;margin:0;text-shadow:0 2px 28px rgba(0,0,0,.35)}
.wrap{max-width:1080px;margin:0 auto;padding:0 28px}
.sec{padding:104px 0 0}
.kick{font-family:'IBM Plex Mono',monospace;font-size:12.5px;letter-spacing:.08em;text-transform:uppercase;color:#56616f;margin:0 0 14px}
h2{font-size:clamp(28px,3.4vw,40px);line-height:1.15;letter-spacing:-.02em;font-weight:600;margin:0 0 18px;max-width:18em}
p{margin:0 0 14px;max-width:34em}.dim{color:#56616f;font-size:15px}
.shot{border-radius:14px;box-shadow:0 1px 2px rgba(16,24,40,.06),0 22px 48px -22px rgba(16,24,40,.32);width:100%;height:auto}
.cap{font-size:14.5px;font-style:italic;color:#56616f;margin:14px 0 0;max-width:46em}
.bio{display:flex;gap:44px;flex-wrap:wrap;align-items:center}
.bio>img{width:230px;height:230px;border-radius:50%;object-fit:cover;box-shadow:0 22px 48px -22px rgba(16,24,40,.4)}
.bio>div{flex:1 1 420px}
.marks{display:flex;gap:30px;align-items:center;flex-wrap:wrap;margin-top:22px}.marks img{height:38px;width:auto}
.split{display:flex;gap:48px;flex-wrap:wrap;align-items:center}.split>*{flex:1 1 360px;min-width:0}
.path{position:relative;margin-top:56px;padding-left:64px;border-left:2px dotted #aeb8c5;margin-left:18px}
.step{position:relative;padding:0 0 84px}.step:last-child{padding-bottom:8px}
.dot{position:absolute;left:-84px;top:-2px;width:38px;height:38px;border-radius:50%;background:#fff;border:2px solid #1b2430;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:14px}
.step h3{font-size:24px;letter-spacing:-.01em;font-weight:600;margin:0 0 8px}
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-top:22px}
.pair figure{margin:0}.pair figcaption{font-size:13.5px;color:#56616f;margin-top:8px;font-family:'IBM Plex Mono',monospace}
.finds{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:40px;margin-top:40px}
.finds b{display:block;font-size:44px;line-height:1;letter-spacing:-.03em;font-weight:600;margin-bottom:12px}
.finds p{font-size:16.5px;margin:0}
.band{background:#f5f7fa;margin-top:104px;padding:80px 0}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:48px}
.cols h3{font-size:20px;margin:0 0 12px;font-weight:600}.cols ul,.cols ol{margin:0;padding-left:1.15em;font-size:16.5px}.cols li{margin-bottom:8px}
.tools{display:flex;gap:44px 56px;flex-wrap:wrap;align-items:center;margin-top:34px}.tools img{height:46px;width:auto}.tools span{font-weight:600;font-size:19px}
.next{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:0;margin-top:44px;border-top:2px dotted #aeb8c5}
.next div{position:relative;padding:34px 26px 0 0}.next span{position:absolute;top:-20px;left:0;width:38px;height:38px;border-radius:50%;background:#fff;border:2px solid #1b2430;display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-size:14px}
.next b{display:block;font-size:19px;margin-bottom:6px}.next p{font-size:16px;color:#3a4553;margin:0}
.wheel{perspective:2200px;height:360px;display:flex;align-items:center;justify-content:center;margin-top:28px;overflow-x:clip}
.ring{--z:260px;position:relative;width:250px;height:220px;transform-style:preserve-3d;animation:spin 42s linear infinite}
.ring:hover{animation-play-state:paused}
.ring>div{position:absolute;inset:0;background:#fff;border:1px solid #e3e7ee;border-radius:16px;box-shadow:0 22px 48px -24px rgba(16,24,40,.35);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:22px;text-align:center;backface-visibility:hidden}
.ring>div:nth-child(1){transform:rotateY(0deg) translateZ(var(--z))}.ring>div:nth-child(2){transform:rotateY(60deg) translateZ(var(--z))}.ring>div:nth-child(3){transform:rotateY(120deg) translateZ(var(--z))}
.ring>div:nth-child(4){transform:rotateY(180deg) translateZ(var(--z))}.ring>div:nth-child(5){transform:rotateY(240deg) translateZ(var(--z))}.ring>div:nth-child(6){transform:rotateY(300deg) translateZ(var(--z))}
.ring img{max-height:58px;max-width:180px;width:auto}.ring b{font-size:17px}.ring small{font-size:14px;color:#56616f;line-height:1.4}.ring .txt{font-size:22px;font-weight:600;letter-spacing:-.01em}
@keyframes spin{to{transform:rotateY(-360deg)}}
@media (max-width:640px){.ring{--z:175px;width:190px;height:200px}.ring>div{padding:14px}.ring img{max-width:140px;max-height:44px}.ring .txt{font-size:18px}.wheel{height:300px}}
@media (prefers-reduced-motion:reduce){.ring{animation:none}}
.mapframe{margin-top:22px;border-radius:16px;overflow:hidden;box-shadow:0 1px 2px rgba(16,24,40,.06),0 24px 56px -26px rgba(16,24,40,.38);border:1px solid #e3e7ee;height:min(660px,78vh);min-height:460px;background:#e9edf2}
.mapframe iframe{width:100%;height:100%;border:0;display:block}
.scene{position:relative;margin-top:104px;min-height:min(80vh,760px);background-size:cover;background-position:center;display:flex;align-items:flex-end;color:#fff}
.scene::before{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,14,22,0) 35%,rgba(10,14,22,.72) 100%)}
.scene .wrap{position:relative;width:100%;box-sizing:border-box;padding-bottom:52px}
.scene .big{font-size:clamp(24px,3.2vw,38px);font-weight:600;line-height:1.18;letter-spacing:-.015em;max-width:19em;margin:0 0 10px;text-shadow:0 2px 22px rgba(0,0,0,.4)}
.scene small{display:block;font-family:'IBM Plex Mono',monospace;font-size:13px;letter-spacing:.02em;opacity:.88}
@media (min-width:900px) and (hover:hover){.scene{background-attachment:fixed}}
.band.sat{position:relative;background-size:cover;background-position:center;color:#fff;padding:120px 0}
.band.sat::before{content:"";position:absolute;inset:0;background:rgba(11,16,24,.8)}
.band.sat .wrap{position:relative}.band.sat li{color:#e8edf3}
.cap a{padding:9px 2px}footer p:first-child a{display:inline-block;padding:9px 0}.full{display:inline-block;padding:10px 0}
@supports (min-height:100svh){.hero{min-height:100svh}}
@media (max-width:640px){.next{border-top:0;border-left:2px dotted #aeb8c5;margin-left:18px;gap:0}.next div{padding:0 0 30px 40px}.next span{top:-6px;left:-20px}.scene{min-height:62svh;margin-top:80px}.scene .wrap{padding-bottom:36px}.sec{padding-top:80px}.band.sat{padding:84px 0}.mapframe{min-height:520px;height:72svh}}
@media (max-width:420px){.ring{--z:130px;width:156px;height:196px}.ring>div{padding:10px;gap:8px}.ring b{font-size:15px}.ring small{font-size:12.5px}.ring img{max-width:118px;max-height:38px}.ring .txt{font-size:16px}.wheel{height:280px;perspective:1400px}}
footer{padding:64px 0 80px;font-size:14.5px;color:#56616f}footer p{max-width:60em}
"""
FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">'


IMG = {"fig1": "fig/fig1_label_efficiency.png", "fig3": "fig/fig3_airport_dulles.png", "me": "img/aboud.jpg",
       "hero": "img/wide_solar_farm_az.jpg", "centennial": "img/wide_airport_centennial.jpg", "s_ds": "img/wide_desert_sunlight_ca.jpg", "s_fl": "img/wide_babcock_ranch_fl.jpg", "s_bos": "img/wide_boston_logan.jpg", "s_ae": "img/wide_boston_alphaearth.jpg", "s_ks": "img/wide_garden_city_ks.jpg", "s_vt": "img/wide_green_mountains_vt_autumn.jpg", "dulles": "img/wide_airport_dulles.jpg",
       "f_m2": "img/farm_406279_y-2.jpg", "f_m1": "img/farm_406279_y-1.jpg", "f_p1": "img/farm_406279_y+1.jpg",
       "f_emb": "img/farm_406279_emb_y-2.jpg", "nserc": "img/logos/nserc.png", "concordia": "img/logos/concordia.png",
       "colab": "img/logos/colab.png", "ee": "img/logos/earth-engine.png", "s2logo": "img/logos/sentinel2.png",
       "usgs": "img/logos/usgs.png", "colabshot": "img/colab_cell.jpg", "s2sat": "img/sentinel2_satellite_esa.jpg", "hy4": "img/hy4_dlr_cc-by-3.0-de.jpg", "fig4": "fig/fig4_harder_comparison.png", "fig5": "fig/fig5_airport_supply.png"}


def numbers(res="results"):
    J = lambda n: json.load(open(os.path.join(res, n)))
    s = pd.read_csv(os.path.join(res, "label_efficiency_summary.csv")); s = s[s.model == "logreg"]
    g = lambda off, f, n: float(s[(s.offset == off) & (s.features == f) & (s.n_labels == n)].ap_mean.iloc[0])
    hr, fm, rep = J("hypothesis_result.json"), J("final_model.json"), J("stage2_report.json")
    h, c = hr["hypothesis"], hr["hypothesis_one_year_before"]
    ap = pd.read_csv(os.path.join(res, "airports.csv")); top = ap.sort_values("solar_like_km2").iloc[-1]
    fa = J("followup/followupA_result.json"); fc = J("followup/followupA_control_all_negatives_result.json")
    sa = pd.read_csv(os.path.join(res, "followup/followupA_summary.csv")); sc = pd.read_csv(os.path.join(res, "followup/followupA_control_all_negatives_summary.csv"))
    au = lambda d, f: float(d[(d.features == f) & (d.n_labels == 1000)].auc_mean.iloc[0])
    fb = J("followup/followupB_result.json")
    sup = pd.read_csv(os.path.join(res, "followup/airport_supply.csv"))
    gr = pd.read_csv(os.path.join(res, "followup/grid_areas.csv")); sg = sup.merge(gr, on="faa_id")
    sg["g2h2"] = sg.grid2_km2 * sg.h2_t_per_day_per_km2
    ratio_lo = sup.grid_h2_kgco2_per_kg.min() / sup.solar_h2_kgco2_per_kg_high.iloc[0]
    ratio_hi = sup.grid_h2_kgco2_per_kg.max() / sup.solar_h2_kgco2_per_kg_low.iloc[0]
    extra = dict(
        a_ae_all=f"{au(sc, 'alphaearth'):.2f}", a_s2_all=f"{au(sc, 'sentinel2'):.2f}",
        a_ae_open=f"{au(sa, 'alphaearth'):.2f}", a_s2_open=f"{au(sa, 'sentinel2'):.2f}",
        b_farms=f"{fb['n_farms']:,}", b_ap=f"{fb['ap_2025']:.2f}", b_ref=f"{fb['oof_ap_reference']:.2f}",
        land_total=f"{sup.available_km2.sum():.0f}", land_min=f"{sup.available_km2.min():.1f}", land_max=f"{sup.available_km2.max():.1f}",
        h2_km2_lo=f"{sup.h2_t_per_day_per_km2.min():.0f}", h2_km2_hi=f"{sup.h2_t_per_day_per_km2.max():.0f}",
        h2_min=f"{sup.available_h2_t_per_day.min():.0f}", h2_max=f"{sup.available_h2_t_per_day.max():.0f}",
        h2sl_min=f"{sup.available_solarlike_h2_t_per_day.min():.0f}", h2sl_max=f"{sup.available_solarlike_h2_t_per_day.max():.0f}",
        grid_lo=f"{sup.grid_h2_kgco2_per_kg.min():.1f}", grid_hi=f"{sup.grid_h2_kgco2_per_kg.max():.1f}",
        sol_lo=f"{sup.solar_h2_kgco2_per_kg_low.iloc[0]:.2f}", sol_hi=f"{sup.solar_h2_kgco2_per_kg_high.iloc[0]:.2f}",
        ratio_lo=f"{ratio_lo:.0f}", ratio_hi=f"{ratio_hi:.0f}",
        grid_total=f"{sg.grid2_km2.sum():.0f}", grid_share=f"{100 * sg.grid2_km2.sum() / sg.available_km2.sum():.0f}",
        g2h2_max=f"{sg.g2h2.max():.0f}", g2h2_top=", ".join(sg.sort_values("g2h2", ascending=False).name.head(2).str.replace(" Airport", "")),
        grid_poor=", ".join(sg[sg.grid2_km2 < 0.5].name.str.replace(" Airport", "").str.replace(" County", "")),
        dens=f"{J('followup/supply_constants.json')['packing_density']['median_mw_per_km2']:.0f}")
    return dict(**extra, scenes=J("followup/scene_farms.json"),
        n_farms=f"{rep['n_farms']:,}", n_px=f"{rep['n_pos'] + rep['n_neg']:,}",
        ae100=f"{h['ae_mean']:.2f}", s21000=f"{h['s2_mean']:.2f}", diff=f"{h['diff_mean']:+.3f}",
        lo=f"{h['diff_ci95'][0]:+.3f}", hi=f"{h['diff_ci95'][1]:+.3f}",
        ae1000=f"{g(-2, 'alphaearth', 1000):.2f}", ae1000_y1=f"{g(-1, 'alphaearth', 1000):.2f}",
        c_ae=f"{c['ae_mean']:.2f}", c_s2=f"{c['s2_mean']:.2f}",
        recall=f"{fm['recall_at_threshold'] * 100:.1f}", max_km2=f"{top.solar_like_km2:.2f}", n_air=len(ap),
        top_air=top["name"].replace(" International Airport", ""))


def fragment(n, img):
    """img maps a figure name to its URL. Returns the page body."""
    sc = n["scenes"]
    return f"""<main>
<header class="hero" style="background-image:url({img['hero']})"><h1>Finding suitable solar farm land for clean hydrogen aviation</h1></header>

<section class="sec"><div class="wrap bio">
<img src="{img['me']}" alt="Aboud Beroual">
<div>
<p class="kick">Where this started</p>
<h2>A summer studying how clean hydrogen flight could really be</h2>
<p>I'm Aboud, an aerospace engineering student at Concordia. In 2025 I held an NSERC undergraduate research award on the environmental impact of hydrogen aviation.</p>
<p>Hydrogen emits no carbon dioxide in flight, but making it takes a lot of electricity. So I built a dataset of how electricity is produced around the 20 busiest US general-aviation airports, using the US Energy Information Administration's 2025 outlook.</p>
<div class="marks"><img src="{img['nserc']}" alt="NSERC"><img src="{img['concordia']}" alt="Concordia University"></div>
</div>
</div>
<div class="wrap"><figure style="margin:64px 0 0"><img class="shot" src="{img['hy4']}" alt="A white twin-fuselage aircraft flying against a blue sky">
<figcaption class="cap">HY4, an aircraft powered by a hydrogen fuel cell, over Stuttgart Airport on its first flight in 2016. Photo: DLR, Felix Oprean, <a href="https://creativecommons.org/licenses/by/3.0/de/deed.en">CC BY 3.0 DE</a>, via <a href="https://commons.wikimedia.org/wiki/File:HY4_2016-09-29_ueber_Flughafen_Stuttgart.jpg">Wikimedia Commons</a>.</figcaption></figure></div>
</section>

<section class="sec"><div class="wrap split">
<div>
<p class="kick">The question now</p>
<h2>Could an airport make its own clean power next door?</h2>
<p>If the local grid is not clean, the hydrogen is not clean either. A solar farm near the airport would fix that, if there is suitable land.</p>
<p>This project teaches a computer to recognise that kind of land from space.</p>
</div>
<figure style="margin:0"><img class="shot" src="{img['dulles']}" alt="Satellite view of Washington Dulles airport and the land around it">
<figcaption class="cap">Washington Dulles International Airport from space, 2025. Sentinel-2 image.</figcaption></figure>
</div></section>

<section class="scene" style="background-image:url({img['s_ae']});background-position:center"><div class="wrap"><p class="big">AlphaEarth turns every 10 m square of land into 64 numbers. Here are three of them, shown as colour.</p><small>Boston Logan International Airport &middot; AlphaEarth Foundations embedding, 2024, bands A01, A16, A09</small></div></section>

<section class="sec"><div class="wrap">
<p class="kick">How it works</p>
<h2>Four steps, from past solar farms to land near airports</h2>
<div class="path">

<div class="step"><span class="dot">1</span>
<h3>Learn from real solar farms, before they were built</h3>
<p>{n['n_farms']} US solar farms opened between 2019 and 2024. The model studies each site as it looked two years earlier, when it was still bare land.</p>
<div class="pair">
<figure><img class="shot" src="{img['f_m2']}" alt="Satellite image of desert in 2021"><figcaption>2021 &middot; untouched</figcaption></figure>
<figure><img class="shot" src="{img['f_m1']}" alt="Same site in 2022 with ground cleared"><figcaption>2022 &middot; ground cleared</figcaption></figure>
<figure><img class="shot" src="{img['f_p1']}" alt="Same site in 2024 covered in solar panels"><figcaption>2024 &middot; operating</figcaption></figure>
</div>
<p class="cap">One site in Yuma County, Arizona. White lines mark where the panels were later built.</p>
</div>

<div class="step"><span class="dot">2</span>
<h3>Turn each patch of land into a fingerprint</h3>
<p>AlphaEarth, from Google DeepMind, condenses a year of satellite observations of every 10-metre square into 64 numbers. Similar land gets similar numbers.</p>
<div class="pair">
<figure><img class="shot" src="{img['f_m2']}" alt="Ordinary satellite image"><figcaption>What a camera sees</figcaption></figure>
<figure><img class="shot" src="{img['f_emb']}" alt="False-colour image of three of the 64 AlphaEarth numbers"><figcaption>What the model sees (3 of 64 numbers as colours)</figcaption></figure>
</div>
</div>

<div class="step"><span class="dot">3</span>
<h3>Test it fairly</h3>
<p>The model had to tell future solar sites from ordinary land nearby, in US states it had never seen. I compared AlphaEarth with ordinary satellite imagery, and published the pass mark before running anything.</p>
<img class="shot" style="margin-top:22px;box-shadow:none;border:1px solid #e3e7ee" src="{img['fig1']}" alt="Line charts of score against number of training examples for AlphaEarth and Sentinel-2">
<p class="cap">Score (0.5 is a coin flip, 1.0 is perfect) against the number of examples the model learned from. Left: land seen two years before opening. Right: one year before.</p>
</div>

<div class="step"><span class="dot">4</span>
<h3>Point it at the land around airports</h3>
<p>The trained model scored every 10-metre square within 5 km of each airport.</p>
<img class="shot" style="margin-top:22px;box-shadow:none;border:1px solid #e3e7ee" src="{img['fig3']}" alt="Washington Dulles airport with the model score overlaid in orange">
<p class="cap">Darker orange means more similar to land where solar farms were later built. The circle looks flattened because of the map projection.</p>
</div>

</div>
</div></section>

<section class="scene" style="background-image:url({img['s_ds']});background-position:60% center"><div class="wrap"><p class="big">Flat, open, unshaded: the kind of land solar farms are built on.</p><small>Desert Sunlight and Desert Harvest, California &middot; {sc['wide_desert_sunlight_ca']['n_farms']} solar farms, {sc['wide_desert_sunlight_ca']['mw_ac']:,} MW &middot; Sentinel-2, 2025</small></div></section>

<section class="sec"><div class="wrap">
<p class="kick">What I found</p>
<h2>It learns fast, but it is not ready to choose sites</h2>
<div class="finds">
<div><b>10&times;</b><p>fewer examples needed. AlphaEarth with 100 examples scored {n['ae100']}, about the same as ordinary imagery with 1,000 ({n['s21000']}).</p></div>
<div><b>{n['ae1000']} &rarr; {n['ae1000_y1']}</b><p>The score jumps when the model sees land one year ahead, not two. By then the ground is often cleared, so it is spotting construction, not good land.</p></div>
<div><b>{n['recall']}%</b><p>of real solar land found at the confidence a planner would need. Near airports, much of what it highlights is runways and car parks.</p></div>
</div>
</div></section>

<section class="sec"><div class="wrap">
<p class="kick">Two harder tests</p>
<h2>Does it know more than "open ground", and does it work on future farms?</h2>
<div class="split" style="align-items:flex-start;margin-top:8px">
<div><p><b>Against open land only.</b> I removed forests, towns and water from the comparison, leaving fields, grassland and bare ground. AlphaEarth still separated future solar sites ({n['a_ae_open']}, where 0.5 is chance); ordinary imagery fell to {n['a_s2_open']}.</p></div>
<div><p><b>On farms it never saw.</b> On {n['b_farms']} solar farms that opened in 2025, the finished model scored {n['b_ap']}, better than in testing ({n['b_ref']}).</p></div>
</div>
<img class="shot" style="margin-top:26px;box-shadow:none;border:1px solid #e3e7ee" src="{img['fig4']}" alt="Line charts comparing AlphaEarth and Sentinel-2 against all land and against open land only">
<p class="cap">Score (ROC AUC: 0.5 is chance, 1.0 is perfect) against the number of training examples. Right: the same test with only open land as the comparison.</p>
</div></section>

<section class="scene" style="background-image:url({img['s_fl']});background-position:30% center"><div class="wrap"><p class="big">Solar farms are not only a desert thing.</p><small>Near Babcock Ranch, Florida &middot; {sc['wide_babcock_ranch_fl']['n_farms']} solar farms, {sc['wide_babcock_ranch_fl']['mw_ac']:,} MW, beside wetlands &middot; Sentinel-2, 2025</small></div></section>

<section class="sec"><div class="wrap">
<p class="kick">What the land could supply</p>
<h2>Up to {n['g2h2_max']} tonnes of clean hydrogen a day per airport, on paper</h2>
<p>I removed land that cannot be used (buildings, roads, water, forest, slopes over 5&deg;, existing solar farms and a 500 m band around runways), kept what lies within 2 km of a transmission line, then converted it into solar power and hydrogen.</p>
<div class="finds">
<div><b>{n['grid_total']} km&sup2;</b><p>of the {n['land_total']} km&sup2; of usable land ({n['grid_share']}%) lies within 2 km of a transmission line. {n['grid_poor']} have almost none.</p></div>
<div><b>{n['h2_km2_lo']}&ndash;{n['h2_km2_hi']} t</b><p>of hydrogen a day per km&sup2; of solar, depending on how sunny the airport is.</p></div>
<div><b>{n['ratio_lo']}&ndash;{n['ratio_hi']}&times;</b><p>less CO&#8322; per kg than hydrogen made from the local grid ({n['sol_lo']}&ndash;{n['sol_hi']} kg against {n['grid_lo']}&ndash;{n['grid_hi']} kg).</p></div>
</div>
<img class="shot" style="margin-top:36px;box-shadow:none;border:1px solid #e3e7ee" src="{img['fig5']}" alt="Bar chart of usable land and hydrogen per airport, and dot chart of carbon per kg of hydrogen from grid versus solar">
<p class="cap">Upper bounds: they ignore grid connection, ownership, zoning and cost. Solar output from NLR PVWatts; {n['dens']} MW per km&sup2; is the median of the {n['n_farms']} real farms; 55 kWh per kg of hydrogen is the DOE electrolyser figure; grid carbon from the EIA 2025 outlook used in my NSERC work (power plants only). Labels show hydrogen from grid-ready land. Palm Beach's runways could not be masked, so its land is overstated. Power lines: HIFLD via GeoPlatform ArcGIS Online (2023).</p>
</div></section>

<section class="scene" style="background-image:url({img['s_bos']});background-position:40% center"><div class="wrap"><p class="big">Many busy airports sit between city and sea, with little open land to spare.</p><small>Boston Logan International Airport &middot; Sentinel-2, 2025</small></div></section>

<section class="sec"><div class="wrap">
<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap">
<div><p class="kick">Interactive map</p><h2 style="margin-bottom:6px">Explore every airport</h2>
<p style="margin:0">Pick an airport, then switch layers: usable land, land near the grid, the model's score, power lines and existing solar farms.</p></div>
<a class="full" href="map.html" style="color:#1557b0;text-decoration:none;font-weight:500;white-space:nowrap">Open full screen &rarr;</a></div>
<div class="mapframe"><iframe src="map.html?embed=1" title="Interactive map of usable land, power lines and solar farms around 20 US airports" loading="lazy" allow="fullscreen"></iframe></div>
</div></section>

<section class="band sat" style="background-image:url({img['centennial']})"><div class="wrap cols">
<div><h3>What this assumes</h3><ol>
<li>Good solar land shares traits a satellite can see: flat, open, unshaded.</li>
<li>Where farms were built before is a fair guide to where they could be built.</li>
<li>Two years before opening, the land still looks as it did when chosen.</li>
<li>Land within 5 km is close enough to supply the airport.</li>
<li>Solar farms near airports pack as densely as the median US farm.</li>
</ol></div>
<div><h3>What it cannot see</h3><ul>
<li>Power lines, zoning, ownership and price.</li>
<li>Real land is almost all ordinary, so real-world accuracy would be lower than in the test.</li>
<li>These {n['n_air']} airports are mostly surrounded by city.</li>
</ul></div>
</div></section>

<section class="scene" style="background-image:url({img['s_ks']});background-position:75% center"><div class="wrap"><p class="big">Airports far from big cities have more open land around them: the next places to test.</p><small>Garden City Regional Airport, Kansas, among irrigated crop circles &middot; Sentinel-2, 2025</small></div></section>

<section class="sec"><div class="wrap">
<p class="kick">Next steps</p>
<h2>Making the map useful</h2>
<div class="next">
<div><span>1</span><b>Check grid capacity</b><p>Whether nearby lines and substations can take new solar.</p></div>
<div><span>2</span><b>Add the rules</b><p>Protected land, wetlands and airport safety zones.</p></div>
<div><span>3</span><b>Cover every airport</b><p>All US general-aviation airports, not {n['n_air']}.</p></div>
<div><span>4</span><b>Match supply to demand</b><p>Compare with what hydrogen aircraft at each airport would need.</p></div>
</div>
</div></section>

<section class="scene" style="background-image:url({img['s_vt']});background-position:center"><div class="wrap"><p class="big">The same satellites revisit every few days, through every season.</p><small>Green Mountains, Vermont, October 2025 &middot; Sentinel-2</small></div></section>

<section class="sec"><div class="wrap">
<p class="kick">Tools and data</p>
<h2>Built with open data and free tools</h2>
<div class="wheel"><div class="ring">
<div><img src="{img['colab']}" alt="Google Colab"><b>Google Colab</b><small>Runs the code in the cloud</small></div>
<div><img src="{img['ee']}" alt="Google Earth Engine"><b>Earth Engine</b><small>Serves the satellite data</small></div>
<div><span class="txt">AlphaEarth Foundations</span><small>Google DeepMind's 64-number fingerprint of every 10 m square</small></div>
<div><img src="{img['s2logo']}" alt="Copernicus Sentinel-2" style="max-height:84px"><b>Sentinel-2</b><small>The comparison imagery</small></div>
<div><img src="{img['usgs']}" alt="USGS"><b>USPVDB</b><small>Where US solar farms are</small></div>
<div><span class="txt">Python</span><small>scikit-learn for the model, matplotlib for the figures</small></div>
</div></div>
<div class="split" style="margin-top:44px">
<figure style="margin:0"><img class="shot" src="{img['colabshot']}" alt="Three lines of Python in Google Colab that run the whole pipeline">
<figcaption class="cap">The whole study runs from three calls in a Colab notebook.</figcaption></figure>
<figure style="margin:0"><img class="shot" src="{img['s2sat']}" alt="Illustration of the Sentinel-2 satellite imaging the Earth in several colour bands">
<figcaption class="cap">Sentinel-2 photographs the same ground every five days in 13 colour bands. Illustration: ESA.</figcaption></figure>
</div>
</div></section>

<footer><div class="wrap">
<p><a href="{REPO}">Code, data and every number on this page</a> &middot; <a href="{REPO}/blob/main/HYPOTHESIS.md">The plan published before the experiment</a> &middot; <a href="{REPO}/tree/main/docs/fig">Figures as PDF</a></p>
<p>Data: AlphaEarth Foundations Satellite Embedding dataset (Google / Google DeepMind) via Google Earth Engine; USPVDB (U.S. Geological Survey and Lawrence Berkeley National Laboratory); contains modified Copernicus Sentinel data (2017&ndash;2025); ESA WorldCover; U.S. EIA Annual Energy Outlook 2025. Logos belong to their owners and are shown only to credit the tools and funders. This is personal student work, not affiliated with or endorsed by any of these organisations.</p>
</div></footer>
</main>"""


def build(res="results", out="docs/index.html"):
    n = numbers(res)
    img = IMG
    html = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>Finding suitable solar farm land for clean hydrogen aviation</title>\n"
            f"{FONTS}\n<style>{CSS}</style>\n</head>\n<body>\n{fragment(n, img)}\n</body>\n</html>\n")
    open(out, "w").write(html)
    return n


if __name__ == "__main__":
    print(build())
