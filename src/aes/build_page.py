"""Build the results page (docs/index.html) from results/. Every number in the page is filled in here.
Run from the repo root:  PYTHONPATH=src python -m aes.build_page"""
import json, os
import pandas as pd

REPO = "https://github.com/abboudberoual/alphaearth-airport-solar"
CSS = """
body{margin:0;background:#fff;color:#1b2430;font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:18px;line-height:1.65}
a{color:#1557b0}a:hover{color:#0b3a7a}
.pg{max-width:1040px;margin:0 auto;padding:64px 28px 80px}
.col{max-width:720px;margin-left:auto;margin-right:auto}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;color:#56616f;margin:0 0 20px}
h1{font-size:clamp(34px,5vw,52px);line-height:1.1;letter-spacing:-.02em;margin:0 0 22px;font-weight:600}
h2{font-size:30px;line-height:1.2;letter-spacing:-.015em;margin:0 0 16px;font-weight:600}
p{margin:0 0 16px}.lede{font-size:22px;line-height:1.5;color:#3a4553;margin:0}
section{margin-top:76px}
.bio{display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start;margin-top:8px}
.bio img{width:168px;height:168px;border-radius:50%;object-fit:cover;flex:0 0 auto}
.bio div{flex:1 1 380px}.fund{font-size:14.5px;color:#56616f;margin:0}
figure{margin:36px 0}figure img{width:100%;height:auto;display:block;border-radius:8px}
figcaption{font-size:15px;line-height:1.55;font-style:italic;color:#56616f;margin:12px auto 0;max-width:720px}
.box{background:#f6f8fb;border-radius:14px;padding:24px 28px;margin:26px 0 0}
.box h3{font-size:13px;font-family:'IBM Plex Mono',monospace;letter-spacing:.06em;text-transform:uppercase;color:#8a5a00;margin:0 0 10px;font-weight:500}
.box ol,.box ul,.col ul,.col ol{padding-left:1.2em;margin:0}.col li{margin-bottom:8px}
.so{border-left:0;font-weight:500}
footer{margin-top:76px;border-top:1px solid #d5dbe3;padding-top:22px;font-size:14.5px;color:#56616f}
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
<header class="col">
<p class="eyebrow">Independent student research &middot; Aboud Beroual, Concordia University</p>
<h1>Finding land for solar farms near airports, so hydrogen aviation can be truly clean</h1>
<p class="lede">Hydrogen aircraft are only as clean as the electricity used to make their fuel. I trained a model on satellite data to recognise the kind of land where solar farms get built, then pointed it at the land around 20 US airports.</p>
</header>

<section class="col">
<h2>Where this started</h2>
<div class="bio">
<img src="{img['me']}" alt="Aboud Beroual">
<div>
<p>In summer 2025 I held an NSERC Undergraduate Student Research Award to study the environmental impact of hydrogen aviation.</p>
<p class="fund">Background research funded by the Natural Sciences and Engineering Research Council of Canada (NSERC). This follow-up project is my own.</p>
</div>
</div>
<p style="margin-top:22px"><b>Why hydrogen?</b> Flying is one of the hardest things to clean up, because batteries are too heavy for most aircraft. Hydrogen stores far more energy for its weight and produces no carbon dioxide when used. That makes it one of the few realistic fuels for low-carbon flight.</p>
<p><b>The catch.</b> Making hydrogen takes a lot of electricity. If that electricity comes from coal or gas, the pollution just moves from the aircraft to the power plant. So my job was to gather reliable data on how electricity is produced in each region, which tells us how clean hydrogen made there would really be.</p>
<p><b>Why these airports.</b> Hydrogen aircraft are expected to arrive first as smaller regional planes. So we started with the 20 busiest general-aviation airports in the United States (general aviation means flights other than scheduled airlines, such as private, charter and training flights).</p>
</section>

<section class="col">
<h2>What I am trying to do now</h2>
<p>The earlier work asked how clean the local grid is. This project asks the next question: <b>could an airport make its own clean electricity nearby?</b> The goal is to find land around airports that is suitable for solar farms, so the hydrogen made there is truly clean.</p>
<p>Checking land by hand is slow. Instead, I taught a computer model what good solar land looks like, using {n['n_farms']} real US solar farms as examples. The model studies how each site looked from space <em>before</em> the farm was built, then searches for similar land near airports.</p>
<p>The satellite data comes from AlphaEarth, a system from Google DeepMind. It condenses a full year of satellite observations of every 10-metre square of land into 64 numbers, a kind of fingerprint that a computer can compare between places. I also tested ordinary satellite images, to see whether the fingerprint really helps.</p>
<div class="box"><h3>What this approach assumes</h3><ol>
<li>Good land for solar farms shares traits a satellite can see, such as being flat, open and unshaded.</li>
<li>Places where solar farms were built in the past are a fair guide to where they could be built in future.</li>
<li>Two years before a farm opens, the land still looks the way it did when it was chosen.</li>
<li>Land within 5 km of an airport is close enough to supply it.</li>
</ol></div>
</section>

<figure><img src="{img['fig2']}" alt="Three satellite images of the same site in Arizona in 2021, 2022 and 2024, showing open desert, then cleared ground, then solar panels">
<figcaption>Figure 1. One of the solar farms the model learned from (Yuma County, Arizona; opened 2023), seen by the Sentinel-2 satellite. White lines mark where the panels were later built. Two years before opening the land is untouched. One year before, the ground has already been cleared.</figcaption></figure>

<section class="col">
<h2>How I tested it</h2>
<p>For each solar farm, the model was also shown ordinary land 2 to 20 km away, {n['n_px']} sample points in all. Its task was to tell the two apart.</p>
<p>To keep the exam fair, the model was always tested on US states it had never seen. I also wrote down what would count as success and published it before training anything.</p>
<p>The score used below runs from 0.5 (no better than a coin flip) to 1.0 (every future solar site ranked above every piece of ordinary land).</p>
</section>

<figure><img src="{img['fig1']}" alt="Two line charts of score against number of training examples for AlphaEarth and ordinary Sentinel-2 imagery">
<figcaption>Figure 2. The score of each approach against the number of examples the model learned from. Error bars show the spread over 5 random draws. Left: land seen two years before the farm opened. Right: one year before.</figcaption></figure>

<section class="col">
<h2>What I found</h2>
<p><b>The fingerprint learns faster.</b> Given the same number of examples, AlphaEarth beat ordinary imagery at every size from 50 examples up. With only 100 examples it scored {n['ae100']}, about the same as ordinary imagery with 1,000 ({n['s21000']}); the small gap is within the noise. That matters because labelled examples are the expensive part of this kind of work.</p>
<p><b>Timing can fool the model.</b> Shown land one year before opening, every score jumps (up to {n['ae1000_y1']}). Figure 1 shows why: by then the ground is often already cleared, so the model is partly spotting construction, not good land. Seen two years ahead, the best score is {n['ae1000']}.</p>
<p><b>It is not ready to choose sites.</b> At the confidence a planner would want (95% of flagged land correct in testing), the model finds only {n['recall']}% of real solar land. It can narrow a search. It cannot yet make the decision.</p>
</section>

<figure><img src="{img['fig3']}" alt="Satellite image of Washington Dulles airport beside the same image with the model's score overlaid in orange">
<figcaption>Figure 3. Land within 5 km of Washington Dulles International Airport in 2025 (left) and the model's score for it (right). Darker orange means more similar to land where solar farms were later built. The circle looks slightly flattened because of the map projection.</figcaption></figure>

<section class="col">
<h2>What the model sees near an airport</h2>
<p>The model picks out flat, open, cleared ground. That is what solar land looks like from space, but here it includes the runways and taxiways themselves, along with car parks and building sites.</p>
<p>At the 95% confidence level, the largest area it flagged near any of the {n['n_air']} airports was {n['max_km2']} km&sup2; ({n['top_air']}). Before its map is useful, the model needs to know which land is actually available.</p>
</section>

<section class="col">
<h2>Limits</h2>
<ul>
<li>Looking like land that was built on is not the same as being buildable. Power-line access, zoning, ownership and price cannot be seen from space.</li>
<li>The test used equal numbers of solar and ordinary sites. Real land is almost all ordinary, so real-world accuracy would be lower.</li>
<li>These {n['n_air']} airports are busy and mostly surrounded by city.</li>
</ul>
</section>

<section class="col">
<h2>What comes next</h2>
<ul>
<li>Remove land that cannot be used (runways, buildings, water, existing solar farms) before scoring.</li>
<li>Add what satellites cannot see: distance to power lines, slope and protected areas.</li>
<li>Score every US general-aviation airport, not just {n['n_air']}.</li>
<li>Convert usable land into megawatts of solar power and kilograms of hydrogen per day.</li>
</ul>
</section>

<footer class="col">
<p><a href="{REPO}">Code, data and every number on this page</a> &middot; <a href="{REPO}/blob/main/HYPOTHESIS.md">The plan published before the experiment</a> &middot; <a href="{REPO}/tree/main/docs/fig">Figures as PDF</a></p>
<p>Data: AlphaEarth Foundations Satellite Embedding dataset (Google / Google DeepMind) via Google Earth Engine; USPVDB (U.S. Geological Survey and Lawrence Berkeley National Laboratory); contains modified Copernicus Sentinel data (2017&ndash;2025); ESA WorldCover. This is personal student work. It is not affiliated with or endorsed by any of these organisations or by NSERC.</p>
</footer>
</main>"""


def build(res="results", out="docs/index.html"):
    n = numbers(res)
    img = {"fig1": "fig/fig1_label_efficiency.png", "fig2": "fig/fig2_site_over_time.png", "fig3": "fig/fig3_airport_dulles.png", "me": "img/aboud.jpg"}
    html = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>Finding land for solar farms near airports, so hydrogen aviation can be truly clean</title>\n"
            f"{FONTS}\n<style>{CSS}</style>\n</head>\n<body>\n{fragment(n, img)}\n</body>\n</html>\n")
    open(out, "w").write(html)
    return n


if __name__ == "__main__":
    print(build())
