"""Build the results page (docs/index.html) from results/. Every number in the page is filled in here.
Run from the repo root:  PYTHONPATH=src python -m aes.build_page"""
import json, os
import pandas as pd

REPO = "https://github.com/abboudberoual/alphaearth-airport-solar"
CSS = """
body{margin:0;background:#fff;color:#1b2430;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:17px;line-height:1.6}
a{color:#1557b0}a:hover{color:#0b3a7a}
.pg{max-width:1040px;margin:0 auto;padding:56px 28px 72px}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;color:#56616f;margin:0 0 18px}
h1{font-size:clamp(34px,5.2vw,54px);line-height:1.08;letter-spacing:-.02em;margin:0 0 22px;font-weight:600;max-width:17em}
h2{font-size:28px;line-height:1.2;letter-spacing:-.01em;margin:0 0 14px;font-weight:600}
h3{font-size:18px;margin:0 0 6px;font-weight:600}
p{margin:0 0 14px}.lede{font-size:20px;color:#3a4553;max-width:40em}
section{margin-top:72px}.num{font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:#1557b0;letter-spacing:.06em;margin:0 0 8px}
.answer{margin-top:30px;border:1px solid #d5dbe3;border-radius:14px;padding:22px 26px;display:flex;gap:22px;flex-wrap:wrap;align-items:baseline;background:#f6f8fb}
.answer b{font-family:'IBM Plex Mono',monospace;font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;color:#8a5a00;flex:0 0 auto}
.answer p{margin:0;font-size:19px;flex:1 1 420px}
.three{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;margin-top:22px}
.card{border-top:3px solid #1b2430;padding-top:14px}.card p{font-size:16px;color:#3a4553;margin:0}
figure{margin:26px 0 0}figure img{width:100%;height:auto;display:block;border-radius:6px}
figcaption{font-size:14.5px;color:#56616f;margin-top:10px;max-width:60em}figcaption b{color:#1b2430}
.steps{margin:22px 0 0;padding-left:1.25em;max-width:44em}.steps li{margin-bottom:8px}
.find{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:22px;margin-top:30px}
.find div{background:#f6f8fb;border-radius:12px;padding:20px 22px}.find p{font-size:16px;margin:0 0 10px}
.big{font-size:34px;font-weight:600;letter-spacing:-.02em;line-height:1.1;margin:0 0 8px}
.so{font-size:15px;color:#1b2430;border-top:1px solid #d5dbe3;padding-top:10px;margin:0}.so b{color:#8a5a00}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:36px;margin-top:8px}
.two li{margin-bottom:8px}.two ul{padding-left:1.15em;margin:0}
footer{margin-top:72px;border-top:1px solid #d5dbe3;padding-top:22px;font-size:14.5px;color:#56616f}
"""
FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">'


def numbers(res="results"):
    J = lambda n: json.load(open(os.path.join(res, n)))
    s = pd.read_csv(os.path.join(res, "label_efficiency_summary.csv")); s = s[s.model == "logreg"]
    g = lambda off, f, n: float(s[(s.offset == off) & (s.features == f) & (s.n_labels == n)].ap_mean.iloc[0])
    hr, fm, rep = J("hypothesis_result.json"), J("final_model.json"), J("stage2_report.json")
    h, c = hr["hypothesis"], hr["hypothesis_one_year_before"]
    ap = pd.read_csv(os.path.join(res, "airports.csv")); top = ap.sort_values("solar_like_km2").iloc[-1]
    return dict(
        n_farms=f"{rep['n_farms']:,}", n_px=f"{rep['n_pos'] + rep['n_neg']:,}",
        ae100=f"{h['ae_mean']:.2f}", s21000=f"{h['s2_mean']:.2f}", diff=f"{h['diff_mean']:+.3f}",
        lo=f"{h['diff_ci95'][0]:+.3f}", hi=f"{h['diff_ci95'][1]:+.3f}",
        ae1000=f"{g(-2, 'alphaearth', 1000):.2f}", ae1000_y1=f"{g(-1, 'alphaearth', 1000):.2f}",
        c_ae=f"{c['ae_mean']:.2f}", c_s2=f"{c['s2_mean']:.2f}",
        recall=f"{fm['recall_at_threshold'] * 100:.1f}", max_km2=f"{top.solar_like_km2:.2f}", n_air=len(ap),
        top_air=top["name"].replace(" International Airport", ""))


def fragment(n, img):
    """img maps a figure name to its URL. Returns the page body."""
    return f"""<main class="pg">
<header>
<p class="eyebrow">Independent student research &middot; Aboud Beroual, Concordia University</p>
<h1>Can an AI map of the Earth spot land for solar farms from only 100 examples?</h1>
<p class="lede">Hydrogen-powered aircraft will need large amounts of clean electricity at airports, and solar farms next door are one way to supply it. I tested whether AlphaEarth, Google's new AI summary of satellite data, can find land that looks like the places where solar farms get built, without thousands of hand-labelled examples.</p>
<div class="answer"><b>Short answer</b><p>Partly. AlphaEarth learned as much from 100 examples as ordinary satellite imagery did from 1,000. But neither is accurate enough yet to choose sites near airports.</p></div>
</header>

<section>
<p class="num">01 &middot; WHY IT MATTERS</p>
<h2>Screening land by hand does not scale</h2>
<div class="three">
<div class="card"><h3>The need</h3><p>My earlier research looked at supplying hydrogen to the busiest general-aviation airports. Making hydrogen cleanly takes a lot of electricity, ideally generated close by.</p></div>
<div class="card"><h3>The bottleneck</h3><p>Training a computer to recognise suitable land normally takes thousands of labelled examples, which are slow and costly to collect for every new region or question.</p></div>
<div class="card"><h3>The idea</h3><p>AlphaEarth compresses a year of satellite observations of each 10 m square of land into 64 numbers. Google DeepMind says this lets simple models learn from very few examples. I tested that claim on a task they did not publish.</p></div>
</div>
</section>

<section>
<p class="num">02 &middot; THE TEST</p>
<h2>Show the model land before the solar farm existed</h2>
<p style="max-width:44em">If a model studies photos of finished solar farms, it only learns to recognise panels. To learn what kind of <em>land</em> gets chosen, it has to see each site before anything was built.</p>
<figure><img src="{img['fig2']}" alt="Three satellite images of the same site in Arizona in 2021, 2022 and 2024, showing open desert, then cleared ground, then solar panels">
<figcaption><b>Figure 1.</b> One of the {n['n_farms']} solar farms in the study (Yuma County, Arizona; opened 2023), in Sentinel-2 satellite images. White lines mark where the panels were later built. Two years before opening the land is untouched; one year before, the ground has already been cleared.</figcaption></figure>
<ol class="steps">
<li><b>Examples.</b> Every US solar farm of 1 MW or more that opened from 2019 to 2024 ({n['n_farms']} farms, from the USGS / Berkeley Lab database), plus ordinary land 2 to 20 km from each one: {n['n_px']} sample points in total.</li>
<li><b>Two descriptions of each point.</b> AlphaEarth's 64 numbers, and for comparison ordinary Sentinel-2 satellite imagery (seasonal colour measurements).</li>
<li><b>A deliberately simple model</b> (logistic regression), trained on 10, 50, 100, 500 or 1,000 examples and repeated 5 times with different random draws.</li>
<li><b>A fair exam.</b> The model is always tested on US states it never saw in training. The hypothesis and the pass/fail rule were published before any model was trained.</li>
</ol>
</section>

<section>
<p class="num">03 &middot; RESULTS</p>
<h2>Ten times fewer examples for the same accuracy, with a catch</h2>
<figure><img src="{img['fig1']}" alt="Two line charts of average precision against number of training examples for AlphaEarth and Sentinel-2">
<figcaption><b>Figure 2.</b> How well each approach ranks future solar sites above ordinary land (average precision: 0.5 is a coin flip, 1.0 is perfect), against the number of training examples. Error bars show the spread over 5 random draws. Circles mark the two points the hypothesis compares: AlphaEarth with 100 examples and Sentinel-2 with 1,000 (dashed line).</figcaption></figure>
<div class="find">
<div><p class="big">100 &asymp; 1,000</p><p>With land seen two years ahead, AlphaEarth with 100 examples scored {n['ae100']}; ordinary imagery needed 1,000 to reach {n['s21000']}. The gap ({n['diff']}, 95% interval {n['lo']} to {n['hi']}) is within the noise, so this is a tie, not a win.</p><p class="so"><b>So what:</b> a small team could get the same result with a tenth of the labelling work.</p></div>
<div><p class="big">Timing can fool you</p><p>One year ahead, every score jumps (AlphaEarth with 1,000 examples: {n['ae1000_y1']} against {n['ae1000']}), because the ground is often already being cleared. There, imagery with 1,000 examples ({n['c_s2']}) beats AlphaEarth with 100 ({n['c_ae']}).</p><p class="so"><b>So what:</b> a model shown the year before construction is partly detecting bulldozers, not good land.</p></div>
<div><p class="big">Not a siting tool yet</p><p>The best honest score is {n['ae1000']}. At the confidence a planner would want (95% of flagged land correct in testing), the model finds only {n['recall']}% of real solar land.</p><p class="so"><b>So what:</b> useful as a first filter to narrow a search; not enough to choose a site.</p></div>
</div>
</section>

<section>
<p class="num">04 &middot; NEAR AN AIRPORT</p>
<h2>What the model highlights around Washington Dulles</h2>
<figure><img src="{img['fig3']}" alt="Satellite image of Washington Dulles airport beside the same image with the model's score overlaid in orange">
<figcaption><b>Figure 3.</b> Land within 5 km of Washington Dulles International Airport in 2025, and the model's score for it (the 5 km circle looks slightly flattened because of the map projection). Darker orange means more similar to land where solar farms were later built.</figcaption></figure>
<p style="max-width:44em;margin-top:20px">The model picks out flat, open, cleared ground, which is what solar-farm land looks like from orbit. But here that includes the runways and taxiways themselves, plus car parks and building sites. At the 95% confidence level, the largest area flagged near any of the {n['n_air']} airports studied was {n['max_km2']} km&sup2; ({n['top_air']}). The model needs to know what land is actually available before its map is useful.</p>
</section>

<section>
<div class="two">
<div><p class="num">05 &middot; LIMITS</p><h2>What this does not show</h2><ul>
<li>&ldquo;Looks like land that got built on&rdquo; is not &ldquo;can be built on&rdquo;. Power-line access, zoning, ownership and price are invisible from space.</li>
<li>The exam used equal numbers of solar and ordinary sites. Real land is almost all ordinary, so real-world accuracy would be lower.</li>
<li>The {n['n_air']} airports are busy and mostly urban. They are not typical small airports.</li>
</ul></div>
<div><p class="num">06 &middot; NEXT</p><h2>Making it actionable</h2><ul>
<li>Remove land that cannot be used (runways, buildings, water, existing solar farms) before scoring.</li>
<li>Add what satellites cannot see: distance to power lines, slope, protected areas.</li>
<li>Score every US general-aviation airport, not {n['n_air']}.</li>
<li>Convert usable area into megawatts of solar and kilograms of hydrogen per day.</li>
</ul></div>
</div>
</section>

<footer>
<p><a href="{REPO}">Code, data and every number on this page</a> &middot; <a href="{REPO}/blob/main/HYPOTHESIS.md">The plan published before the experiment</a> &middot; <a href="{REPO}/tree/main/docs/fig">Figures as PDF</a></p>
<p>Data: AlphaEarth Foundations Satellite Embedding dataset (Google / Google DeepMind) via Google Earth Engine; USPVDB (U.S. Geological Survey and Lawrence Berkeley National Laboratory); contains modified Copernicus Sentinel data (2017&ndash;2025); ESA WorldCover. This is personal student work and is not affiliated with or endorsed by any of these organisations.</p>
</footer>
</main>"""


def build(res="results", out="docs/index.html"):
    n = numbers(res)
    img = {"fig1": "fig/fig1_label_efficiency.png", "fig2": "fig/fig2_site_over_time.png", "fig3": "fig/fig3_airport_dulles.png"}
    html = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>Can an AI map of the Earth spot land for solar farms from 100 examples?</title>\n"
            f"{FONTS}\n<style>{CSS}</style>\n</head>\n<body>\n{fragment(n, img)}\n</body>\n</html>\n")
    open(out, "w").write(html)
    return n


if __name__ == "__main__":
    print(build())
