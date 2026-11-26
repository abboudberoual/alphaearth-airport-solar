/* Airport solar label-efficiency test: page logic.
   Every result shown on the page is read at runtime from data/*.json.
   Nothing here contains a result value. */
(function () {
  'use strict';

  var COLORS = { alphaearth: '#257de0', sentinel2: '#f47230' };
  var INK = '#101623', INK2 = '#454e5f', INK3 = '#667085', GRID = '#e3e7ee', AXIS = '#c9d0db', RING = '#d18f00';
  var SERIES = [
    { key: 'alphaearth', label: 'AlphaEarth', shape: 'circle' },
    { key: 'sentinel2', label: 'Sentinel-2', shape: 'square' }
  ];
  var MODEL_LABELS = { logreg: 'Logistic regression', rf: 'Random forest' };
  var MODEL_PLAIN = {
    logreg: 'linear probe (logistic regression)',
    rf: 'random forest'
  };
  var METRICS = {
    ap: { label: 'Average precision', short: 'average precision', mean: 'ap_mean', sd: 'ap_sd', chance: 0.5 },
    f1: { label: 'F1', short: 'F1', mean: 'f1_mean', sd: 'f1_sd', chance: null }
  };
  var PAGE_SIZE = 25;
  var NA = 'n/a';

  /* ---------- helpers ---------- */
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  var fmt = {
    int: function (v) { return isNum(v) ? Math.round(v).toLocaleString('en-US') : NA; },
    score: function (v) { return isNum(v) ? v.toFixed(3) : NA; },
    signed: function (v) { return isNum(v) ? (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(3) : NA; },
    km2: function (v) { return isNum(v) ? v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : NA; },
    pct: function (v) { return isNum(v) ? (v * 100).toFixed(1) + '%' : NA; },
    tick: function (v) { return isNum(v) ? v.toFixed(2) : NA; },
    range: function (a) { return Array.isArray(a) && a.length === 2 ? a[0] + '–' + a[1] : NA; },
    date: function (s) {
      if (typeof s !== 'string' || !s) return NA;
      var d = new Date(s.length <= 10 ? s + 'T00:00:00Z' : s);
      if (isNaN(d)) return s;
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
    },
    pm: function (m, sd) { return fmt.score(m) + (isNum(sd) ? ' ± ' + sd.toFixed(3) : ''); }
  };
  var NUMBER_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six'];
  function offsetWords(o) {
    if (!isNum(o)) return NA;
    var n = Math.abs(o), w = NUMBER_WORDS[n] || String(n);
    if (o === 0) return 'the same year as';
    return w + (n === 1 ? ' year ' : ' years ') + (o < 0 ? 'before' : 'after');
  }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function listWords(arr) {
    if (!arr.length) return NA;
    if (arr.length === 1) return arr[0];
    return arr.slice(0, -1).join(', ') + ' and ' + arr[arr.length - 1];
  }

  function el(tag, attrs) {
    var node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else node.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null) continue;
      node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    }
    return node;
  }
  function $(sel) { return document.querySelector(sel); }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function getJSON(path, optional) {
    return fetch(path, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(path + ' returned ' + r.status);
      return r.json();
    }).catch(function (err) {
      if (optional) return null;
      throw new Error('Could not load ' + path + ' (' + err.message + ')');
    });
  }

  function onResize(node, fn) {
    var last = 0, raf = 0;
    function run() {
      raf = 0;
      var w = node.clientWidth;
      if (w && Math.abs(w - last) >= 1) { last = w; fn(w); }
    }
    if (window.ResizeObserver) new ResizeObserver(function () { if (!raf) raf = requestAnimationFrame(run); }).observe(node);
    else window.addEventListener('resize', run);
    run();
  }

  /* ---------- tooltip ---------- */
  var tip = $('#tooltip');
  function showTip(content, cx, cy) {
    clear(tip); tip.appendChild(content); tip.hidden = false;
    var r = tip.getBoundingClientRect(), vw = document.documentElement.clientWidth, vh = window.innerHeight;
    var x = cx + 16, y = cy - r.height - 12;
    if (x + r.width > vw - 8) x = cx - r.width - 16;
    if (x < 8) x = Math.max(8, Math.min(vw - r.width - 8, cx - r.width / 2));
    if (y < 8) y = Math.min(vh - r.height - 8, cy + 18);
    tip.style.left = Math.round(x) + 'px'; tip.style.top = Math.round(y) + 'px';
  }
  function hideTip() { tip.hidden = true; }
  window.addEventListener('scroll', hideTip, { passive: true });
  function ttRow(name, value, sub, color) {
    var nameEl = el('span', { class: 'tt-name' });
    if (color) { var k = el('span', { class: 'tt-line' }); k.style.borderTopColor = color; nameEl.appendChild(k); }
    nameEl.appendChild(document.createTextNode(name));
    var val = el('strong', { text: value });
    if (sub) val.appendChild(el('span', { class: 'tt-sub', text: ' ' + sub }));
    return el('div', { class: 'tt-row' }, nameEl, val);
  }

  /* ---------- small SVG marker helpers ---------- */
  function drawMarker(g, shape, x, y, size, fill, opts) {
    opts = opts || {};
    var node;
    if (shape === 'square') node = g.append('rect').attr('x', x - size).attr('y', y - size).attr('width', size * 2).attr('height', size * 2).attr('rx', 1.5);
    else if (shape === 'diamond') node = g.append('path').attr('d', 'M' + x + ',' + (y - size * 1.3) + 'L' + (x + size * 1.3) + ',' + y + 'L' + x + ',' + (y + size * 1.3) + 'L' + (x - size * 1.3) + ',' + y + 'Z');
    else node = g.append('circle').attr('cx', x).attr('cy', y).attr('r', size * 1.1);
    node.attr('fill', opts.hollow ? '#fff' : fill).attr('stroke', opts.hollow ? fill : '#fff').attr('stroke-width', 2);
    return node;
  }
  function legendItem(parent, draw, text) {
    var item = el('span', { class: 'legend-item' });
    var svg = d3.select(item).append('svg').attr('width', 28).attr('height', 14);
    draw(svg);
    item.appendChild(document.createTextNode(text));
    parent.appendChild(item);
  }

  /* ---------- text bindings ---------- */
  function bind(values) {
    document.querySelectorAll('[data-f]').forEach(function (n) {
      var k = n.getAttribute('data-f');
      n.textContent = values[k] != null ? values[k] : NA;
    });
  }

  function renderSummary(S, airports, le) {
    var h = S.hypothesis || {}, r = S.robustness || {};
    var sizes = Array.from(new Set((le || []).map(function (d) { return d.n_labels; }))).filter(isNum).sort(d3.ascending);
    bind({
      ae_n: fmt.int(h.ae_n), s2_n: fmt.int(h.s2_n),
      ae_mean: fmt.score(h.ae_mean), s2_mean: fmt.score(h.s2_mean),
      diff: fmt.signed(h.diff_mean),
      ci_lo: fmt.signed((h.diff_ci95 || [])[0]), ci_hi: fmt.signed((h.diff_ci95 || [])[1]),
      metric: h.metric || NA,
      n_seeds: fmt.int(S.n_seeds), n_folds: fmt.int(S.n_folds), n_states: fmt.int(S.n_states),
      sizes: listWords(sizes.map(fmt.int)),
      main_offset_words: offsetWords(r.main_offset), check_offset_words: offsetWords(r.check_offset),
      online_range: fmt.range(S.online_years).replace('–', ' and '),
      snapshot: fmt.date(S.uspvdb_snapshot_date),
      total: fmt.int(S.uspvdb_total), farms: fmt.int(S.n_farms),
      generated: fmt.date(S.generated),
      threshold: isNum(S.airport_threshold) ? S.airport_threshold.toFixed(3) : NA,
      n_airports: fmt.int(airports.length),
      rob_n: fmt.int(r.n_labels)
    });

    // placeholder banner
    $('#placeholder-banner').hidden = S.placeholder !== true;

    // verdict chip
    var chip = $('#verdict-chip'), supported = h.supported === true;
    chip.classList.add(S.verdict_mixed === true ? 'is-mixed' : (supported ? 'is-yes' : 'is-no'));
    $('#verdict-text').textContent = typeof h.supported === 'boolean'
      ? (typeof S.verdict_text === 'string' ? S.verdict_text : (supported ? 'Hypothesis supported' : 'Hypothesis not supported')) : 'Result unavailable';
    var fbox = document.getElementById('findings-list');
    if (fbox && Array.isArray(S.findings) && S.findings.length) {
      S.findings.forEach(function (t) { var li = document.createElement('li'); li.textContent = t; fbox.appendChild(li); });
      document.getElementById('findings').hidden = false;
    }

    // repository links
    var url = typeof S.repo_url === 'string' && /^https?:\/\//i.test(S.repo_url) ? S.repo_url : null;
    document.querySelectorAll('[data-repo]').forEach(function (a) {
      if (url) { a.href = url; a.rel = 'noopener'; a.hidden = false; }
    });

    $('#threshold-note').textContent = S.airport_threshold_note || '';

    // key numbers
    var stats = [
      [fmt.int(S.uspvdb_total), 'solar farms listed in the USPVDB snapshot'],
      [fmt.int(S.n_farms), 'farms used, opened ' + fmt.range(S.online_years)],
      [fmt.int(S.n_positive_points), 'solar-site pixels (positives)'],
      [fmt.int(S.n_negative_points), 'ordinary-land pixels (negatives)'],
      [fmt.int(S.n_states), 'states and districts with sites (incl. DC)'],
      [fmt.int(S.n_folds) + ' × ' + fmt.int(S.n_seeds), 'held-out splits × random seeds'],
      [fmt.range(S.embedding_years), 'satellite years used'],
      [fmt.int(airports.length), 'airports scored']
    ];
    var dl = $('#stats'); clear(dl);
    stats.forEach(function (s) {
      dl.appendChild(el('div', { class: 'stat' }, el('dt', { text: s[1] }), el('dd', { text: s[0] })));
    });
    $('#stats-note').textContent = 'USPVDB snapshot dated ' + fmt.date(S.uspvdb_snapshot_date) + '.';
  }

  /* ---------- label-efficiency chart ---------- */
  function initLabelEfficiency(data, S) {
    var h = S.hypothesis || {}, rob = S.robustness || {};
    var offsets = Array.from(new Set(data.map(function (d) { return d.offset; }))).filter(isNum);
    var mainOffset = offsets.indexOf(rob.main_offset) >= 0 ? rob.main_offset : d3.min(offsets);
    offsets.sort(function (a, b) { return (b === mainOffset) - (a === mainOffset) || a - b; });
    var models = Array.from(new Set(data.map(function (d) { return d.model; })));
    models.sort(function (a, b) { return (b === 'logreg') - (a === 'logreg') || d3.ascending(a, b); });
    var defaults = { metric: 'ap', model: models.indexOf('logreg') >= 0 ? 'logreg' : models[0], offset: mainOffset };
    var state = { metric: defaults.metric, model: defaults.model, offset: defaults.offset };
    var chartEl = $('#le-chart'), width = 0;

    function seg(name, legend, options) {
      var fs = el('fieldset', { class: 'seg' }, el('legend', { text: legend }));
      var row = el('div', { class: 'seg-row' });
      options.forEach(function (o) {
        var input = el('input', { type: 'radio', name: 'le-' + name, value: String(o.value), checked: String(state[name]) === String(o.value) });
        input.checked = String(state[name]) === String(o.value);
        input.addEventListener('change', function () { state[name] = o.value; draw(); });
        row.appendChild(el('label', null, input, el('span', { text: o.label })));
      });
      fs.appendChild(row);
      return fs;
    }
    var controls = $('#le-controls'); clear(controls);
    controls.appendChild(seg('metric', 'Metric', Object.keys(METRICS).map(function (k) { return { value: k, label: METRICS[k].label }; })));
    if (models.length) controls.appendChild(seg('model', 'Classifier', models.map(function (m) { return { value: m, label: MODEL_LABELS[m] || m }; })));
    if (offsets.length) controls.appendChild(seg('offset', 'Land seen', offsets.map(function (o) { return { value: o, label: cap(offsetWords(o)) }; })));

    // legend (static)
    var legend = $('#le-legend'); clear(legend);
    SERIES.forEach(function (s) {
      legendItem(legend, function (svg) {
        svg.append('line').attr('x1', 0).attr('x2', 28).attr('y1', 7).attr('y2', 7).attr('stroke', COLORS[s.key]).attr('stroke-width', 2);
        drawMarker(svg, s.shape, 14, 7, 4, COLORS[s.key]);
      }, s.label + ' (' + (s.shape === 'circle' ? 'circles' : 'squares') + ')');
    });
    legendItem(legend, function (svg) {
      svg.append('line').attr('x1', 0).attr('x2', 28).attr('y1', 7).attr('y2', 7).attr('stroke', INK3).attr('stroke-width', 1.5).attr('stroke-dasharray', '5 4');
    }, 'Sentinel-2 at ' + fmt.int(h.s2_n) + ' labels');
    legendItem(legend, function (svg) {
      svg.append('circle').attr('cx', 14).attr('cy', 7).attr('r', 6).attr('fill', 'none').attr('stroke', RING).attr('stroke-width', 2);
    }, 'points the hypothesis compares');

    function rowsFor(features) {
      return data.filter(function (d) {
        return d.features === features && d.model === state.model && d.offset === state.offset && isNum(d.n_labels) && d.n_labels > 0 && isNum(d[METRICS[state.metric].mean]);
      }).sort(function (a, b) { return a.n_labels - b.n_labels; });
    }

    function draw() {
      if (!width) return;
      var M = METRICS[state.metric];
      var series = SERIES.map(function (s) { return { s: s, rows: rowsFor(s.key) }; });
      var all = series[0].rows.concat(series[1].rows);
      clear(chartEl); hideTip();
      renderCaption(M, all);
      renderTable(M, series);
      if (!all.length) {
        chartEl.appendChild(el('p', { class: 'fine', text: 'No results are available for this combination.' }));
        return;
      }
      var narrow = width < 560;
      var m = { t: 34, r: narrow ? 16 : 116, b: 48, l: narrow ? 40 : 54 };
      var H = Math.round(Math.max(330, Math.min(460, width * 0.56)));
      var ns = Array.from(new Set(all.map(function (d) { return d.n_labels; }))).sort(d3.ascending);
      var x = d3.scaleLog().domain([ns[0] / 1.35, ns[ns.length - 1] * 1.35]).range([m.l, width - m.r]);
      var refRow = series[1].rows.filter(function (d) { return d.n_labels === h.s2_n; })[0];
      var ref = refRow ? refRow[M.mean] : null;
      var vals = [];
      all.forEach(function (d) { var sd = isNum(d[M.sd]) ? d[M.sd] : 0; vals.push(d[M.mean] - sd, d[M.mean] + sd); });
      if (isNum(M.chance)) vals.push(M.chance);
      var lo = Math.max(0, Math.floor((d3.min(vals) - 0.02) * 20) / 20);
      var hi = Math.min(1, Math.ceil((d3.max(vals) + 0.02) * 20) / 20);
      if (hi - lo < 0.1) { lo = Math.max(0, lo - 0.05); hi = Math.min(1, hi + 0.05); }
      var y = d3.scaleLinear().domain([lo, hi]).range([H - m.b, m.t]);

      var svg = d3.select(chartEl).append('svg').attr('width', width).attr('height', H)
        .attr('role', 'img')
        .attr('aria-label', M.label + ' against number of training labels for AlphaEarth embeddings and Sentinel-2 features. The exact values are in the table below the chart.');

      // grid + y axis
      var yTicks = y.ticks(narrow ? 5 : 6);
      var gy = svg.append('g');
      yTicks.forEach(function (t) {
        gy.append('line').attr('x1', m.l).attr('x2', width - m.r).attr('y1', y(t)).attr('y2', y(t)).attr('stroke', GRID).attr('stroke-width', 1).attr('shape-rendering', 'crispEdges');
        gy.append('text').attr('x', m.l - 8).attr('y', y(t)).attr('dy', '0.32em').attr('text-anchor', 'end').attr('font-size', 12).attr('fill', INK3).text(fmt.tick(t));
      });
      svg.append('text').attr('x', 0).attr('y', 10).attr('font-size', 12).attr('fill', INK2).attr('font-weight', 600).text(M.label);

      // x axis
      var gx = svg.append('g');
      gx.append('line').attr('x1', m.l).attr('x2', width - m.r).attr('y1', H - m.b).attr('y2', H - m.b).attr('stroke', AXIS).attr('shape-rendering', 'crispEdges');
      var lastTickX = -Infinity;
      ns.forEach(function (n) {
        gx.append('line').attr('x1', x(n)).attr('x2', x(n)).attr('y1', H - m.b).attr('y2', H - m.b + 5).attr('stroke', AXIS);
        var label = fmt.int(n), w = label.length * 6.6 + 6;
        if (x(n) - w / 2 < lastTickX) return;
        lastTickX = x(n) + w / 2;
        gx.append('text').attr('x', x(n)).attr('y', H - m.b + 19).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', INK3).text(label);
      });
      svg.append('text').attr('x', (m.l + width - m.r) / 2).attr('y', H - 6).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', INK2)
        .text('Number of labelled training examples (log scale)');

      var xpos = function (d, i) { return x(d.n_labels) + (i === 0 ? -3 : 3); };
      // pixel geometry helpers used to keep labels off the data
      function lineYAt(se, i, px) {
        var r = se.rows;
        for (var j = 0; j < r.length - 1; j++) {
          var xa = xpos(r[j], i), xb = xpos(r[j + 1], i);
          if (px >= xa && px <= xb) return y(r[j][M.mean]) + (y(r[j + 1][M.mean]) - y(r[j][M.mean])) * (px - xa) / (xb - xa || 1);
        }
        return null;
      }
      function boxHits(x0, x1, y0, y1) {
        var hits = 0;
        series.forEach(function (se, i) {
          for (var k = 0; k <= 10; k++) { var ly = lineYAt(se, i, x0 + (x1 - x0) * k / 10); if (ly != null && ly > y0 - 3 && ly < y1 + 3) hits++; }
          se.rows.forEach(function (d) {
            var px = xpos(d, i), sd = isNum(d[M.sd]) ? d[M.sd] : 0;
            if (px > x0 - 6 && px < x1 + 6 && y(d[M.mean] + sd) - 5 < y1 && y(d[M.mean] - sd) + 5 > y0) hits += 3;
          });
        });
        return hits;
      }

      // chance level
      if (isNum(M.chance) && M.chance >= lo && M.chance <= hi) {
        svg.append('line').attr('x1', m.l).attr('x2', width - m.r).attr('y1', y(M.chance)).attr('y2', y(M.chance)).attr('stroke', INK3).attr('stroke-width', 1).attr('stroke-dasharray', '1.5 3.5');
        var ch = svg.append('text').attr('font-size', 12).attr('fill', INK3).text('chance level');
        if (narrow) ch.attr('x', m.l + 6).attr('y', y(M.chance) - 6).attr('paint-order', 'stroke').attr('stroke', '#fff').attr('stroke-width', 4);
        else ch.attr('x', width - m.r + 8).attr('y', y(M.chance)).attr('dy', '0.32em');
      }

      // reference: Sentinel-2 at the hypothesis label count
      if (isNum(ref)) {
        svg.append('line').attr('x1', m.l).attr('x2', width - m.r).attr('y1', y(ref)).attr('y2', y(ref)).attr('stroke', INK3).attr('stroke-width', 1.5).attr('stroke-dasharray', '5 4');
        var refText = 'Sentinel-2 at ' + fmt.int(h.s2_n) + ' labels' + (narrow ? '' : ': ' + fmt.score(ref));
        var tw = refText.length * 6.3, yr = y(ref), xr = width - m.r;
        // try a few spots along the line and keep the one that covers the least data
        var spots = [];
        [m.l + 6, (m.l + xr - tw) / 2, xr - tw - 18].forEach(function (x0) {
          [[yr - 20, yr - 4], [yr + 4, yr + 20]].forEach(function (b, bi) {
            if (b[1] > H - m.b - 2 || b[0] < m.t - 14) return;
            spots.push({ x: x0, y: bi === 0 ? yr - 7 : yr + 15, hits: boxHits(x0 - 4, x0 + tw + 4, b[0], b[1]) });
          });
        });
        spots.sort(function (a, b) { return a.hits - b.hits; });
        if (spots.length && !(narrow && spots[0].hits > 0)) svg.append('text').attr('x', spots[0].x).attr('y', spots[0].y).attr('font-size', 12).attr('fill', INK2)
          .attr('paint-order', 'stroke').attr('stroke', '#fff').attr('stroke-width', 4).attr('stroke-linejoin', 'round').text(refText);
      }

      // series
      var ends = [];
      series.forEach(function (se, i) {
        var c = COLORS[se.s.key], g = svg.append('g');
        if (!se.rows.length) return;
        se.rows.forEach(function (d) {
          if (!isNum(d[M.sd])) return;
          var px = xpos(d, i), y0 = y(Math.max(lo, d[M.mean] - d[M.sd])), y1 = y(Math.min(hi, d[M.mean] + d[M.sd]));
          g.append('line').attr('x1', px).attr('x2', px).attr('y1', y0).attr('y2', y1).attr('stroke', c).attr('stroke-width', 1.25).attr('stroke-opacity', 0.75);
          [y0, y1].forEach(function (yy) { g.append('line').attr('x1', px - 3.5).attr('x2', px + 3.5).attr('y1', yy).attr('y2', yy).attr('stroke', c).attr('stroke-width', 1.25).attr('stroke-opacity', 0.75); });
        });
        g.append('path').attr('fill', 'none').attr('stroke', c).attr('stroke-width', 2).attr('stroke-linejoin', 'round').attr('stroke-linecap', 'round')
          .attr('d', d3.line().x(function (d) { return xpos(d, i); }).y(function (d) { return y(d[M.mean]); })(se.rows));
        se.rows.forEach(function (d) {
          var isHyp = (se.s.key === 'alphaearth' && d.n_labels === h.ae_n) || (se.s.key === 'sentinel2' && d.n_labels === h.s2_n);
          if (isHyp) g.append('circle').attr('cx', xpos(d, i)).attr('cy', y(d[M.mean])).attr('r', 10).attr('fill', 'none').attr('stroke', RING).attr('stroke-width', 2);
          drawMarker(g, se.s.shape, xpos(d, i), y(d[M.mean]), 4, c).attr('data-n', d.n_labels).attr('class', 'pt');
        });
        var last = se.rows[se.rows.length - 1];
        ends.push({ label: se.s.label, x: xpos(last, i), y: y(last[M.mean]), se: se, i: i });
      });
      // direct labels at line ends, nudged apart if they would collide
      var halo = function (t) { return t.attr('paint-order', 'stroke').attr('stroke', '#fff').attr('stroke-width', 4).attr('stroke-linejoin', 'round'); };
      if (narrow) {
        // no room beside the plot: the upper line is labelled above its end, the lower one below
        var topIdx = ends.length === 2 && ends[1].y < ends[0].y ? 1 : 0;
        ends.forEach(function (e, i) {
          var above = i === topIdx, tw = e.label.length * 6.9, x1 = e.x + 8, x0 = x1 - tw, se = e.se, ty;
          // clear the series' own line and error bars across the label's width
          var ys = [];
          se.rows.forEach(function (d) {
            var px = xpos(d, e.i), sd = isNum(d[M.sd]) ? d[M.sd] : 0;
            if (px > x0 - 6) ys.push(above ? y(Math.min(hi, d[M.mean] + sd)) : y(Math.max(lo, d[M.mean] - sd)));
          });
          var edge = lineYAt(se, e.i, x0); if (edge != null) ys.push(edge);
          if (above) ty = Math.max(11, d3.min(ys) - 14);
          else ty = Math.min(H - m.b - 6, d3.max(ys) + 22);
          halo(svg.append('text').attr('x', x1).attr('y', ty).attr('text-anchor', 'end')
            .attr('font-size', 12).attr('font-weight', 650).attr('fill', INK)).text(e.label);
        });
      } else {
        if (ends.length === 2 && Math.abs(ends[0].y - ends[1].y) < 16) {
          var mid = (ends[0].y + ends[1].y) / 2, up = ends[0].y <= ends[1].y ? 0 : 1;
          ends[up].y = mid - 8; ends[1 - up].y = mid + 8;
        }
        ends.forEach(function (e) {
          halo(svg.append('text').attr('x', e.x + 19).attr('y', e.y).attr('dy', '0.32em').attr('font-size', 13).attr('font-weight', 650).attr('fill', INK)).text(e.label);
        });
      }

      // hover layer: crosshair snaps to the nearest label count
      var hair = svg.append('line').attr('y1', m.t).attr('y2', H - m.b).attr('stroke', INK3).attr('stroke-width', 1).attr('visibility', 'hidden');
      svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', Math.max(0, width - m.r - m.l)).attr('height', H - m.b - m.t).attr('fill', 'transparent')
        .on('pointermove pointerdown', function (ev) {
          var px = d3.pointer(ev, svg.node())[0];
          var n = ns.reduce(function (best, v) { return Math.abs(x(v) - px) < Math.abs(x(best) - px) ? v : best; }, ns[0]);
          hair.attr('x1', x(n)).attr('x2', x(n)).attr('visibility', 'visible');
          var box = el('div', null, el('div', { class: 'tt-title', text: fmt.int(n) + ' labels' }));
          var runs = [];
          series.forEach(function (se) {
            var d = se.rows.filter(function (r) { return r.n_labels === n; })[0];
            box.appendChild(ttRow(se.s.label, d ? fmt.score(d[M.mean]) : NA, d && isNum(d[M.sd]) ? '± ' + d[M.sd].toFixed(3) : '', COLORS[se.s.key]));
            if (d && isNum(d.n_runs)) runs.push(d.n_runs);
          });
          if (runs.length) box.appendChild(el('div', { class: 'tt-foot', text: M.short + ', mean of ' + fmt.int(d3.max(runs)) + ' runs ± sd across seeds' }));
          showTip(box, ev.clientX, ev.clientY);
        })
        .on('pointerleave', function () { hair.attr('visibility', 'hidden'); hideTip(); });
    }

    function renderCaption(M, all) {
      var isPre = state.metric === defaults.metric && state.model === defaults.model && state.offset === defaults.offset;
      var runs = d3.max(all, function (d) { return d.n_runs; });
      var t = cap(M.short) + ' on held-out states, ' + (MODEL_PLAIN[state.model] || state.model) + ', land seen ' + offsetWords(state.offset) + ' each farm opened. ' +
        'Points are means' + (isNum(runs) ? ' over ' + fmt.int(runs) + ' runs' : '') + '; vertical bars show plus or minus one standard deviation across random seeds. ' +
        'The dashed line marks Sentinel-2 at ' + fmt.int(h.s2_n) + ' labels' + (isNum(M.chance) ? ', and the dotted line marks chance level' : '') + '. ' +
        (isPre ? 'This is the pre-registered view.' : 'This is an additional view, not the pre-registered comparison.');
      $('#le-caption').textContent = t;
    }

    function renderTable(M, series) {
      var host = $('#le-table'); clear(host);
      var ns = Array.from(new Set(series[0].rows.concat(series[1].rows).map(function (d) { return d.n_labels; }))).sort(d3.ascending);
      var table = el('table', null,
        el('caption', { text: M.label + ' (mean ± standard deviation across random seeds), ' + (MODEL_LABELS[state.model] || state.model).toLowerCase() + ', ' + offsetWords(state.offset) + ' opening' }),
        el('thead', null, el('tr', null,
          el('th', { scope: 'col', class: 'left', text: 'Labels' }),
          el('th', { scope: 'col', text: 'AlphaEarth' }),
          el('th', { scope: 'col', text: 'Sentinel-2' }),
          el('th', { scope: 'col', text: 'Runs' }))));
      var tb = el('tbody');
      ns.forEach(function (n) {
        var a = series[0].rows.filter(function (d) { return d.n_labels === n; })[0];
        var b = series[1].rows.filter(function (d) { return d.n_labels === n; })[0];
        tb.appendChild(el('tr', null,
          el('th', { scope: 'row', class: 'left', text: fmt.int(n) }),
          el('td', { text: a ? fmt.pm(a[M.mean], a[M.sd]) : NA }),
          el('td', { text: b ? fmt.pm(b[M.mean], b[M.sd]) : NA }),
          el('td', { text: fmt.int((a || b || {}).n_runs) })));
      });
      table.appendChild(tb); host.appendChild(table);
    }

    onResize(chartEl, function (w) { width = w; draw(); });
  }

  /* ---------- robustness ---------- */
  function renderRobustness(S) {
    var r = S.robustness;
    if (!r) { $('#robustness').hidden = true; return; }
    var mainW = offsetWords(r.main_offset), checkW = offsetWords(r.check_offset);
    var rows = [
      { label: 'AlphaEarth', cls: 'key key-ae', a: r.ae_mean_main, b: r.ae_mean_check },
      { label: 'Sentinel-2', cls: 'key key-s2', a: r.s2_mean_main, b: r.s2_mean_check }
    ];
    var host = $('#rob-table'); clear(host);
    var tb = el('tbody');
    rows.forEach(function (row) {
      var d = isNum(row.a) && isNum(row.b) ? row.b - row.a : null;
      row.d = d;
      var name = el('th', { scope: 'row', class: 'left' }, el('span', { class: row.cls, 'aria-hidden': 'true' }), ' ' + row.label);
      tb.appendChild(el('tr', null, name,
        el('td', { text: fmt.score(row.a) }), el('td', { text: fmt.score(row.b) }),
        el('td', { class: 'delta', text: fmt.signed(d) })));
    });
    host.appendChild(el('table', null,
      el('thead', null, el('tr', null,
        el('th', { scope: 'col', class: 'left', text: 'Features' }),
        el('th', { scope: 'col', text: cap(mainW) + ' (main)' }),
        el('th', { scope: 'col', text: cap(checkW) + ' (check)' }),
        el('th', { scope: 'col', text: 'Change' }))), tb));
    if (rows.every(function (x) { return isNum(x.d); })) {
      $('#rob-sentence').textContent = 'Moving from ' + mainW + ' to ' + checkW + ' opening changed the AlphaEarth score by ' +
        fmt.signed(rows[0].d) + ' and the Sentinel-2 score by ' + fmt.signed(rows[1].d) + '.';
    }
  }

  /* ---------- drift ---------- */
  function initDrift(data) {
    var section = $('#drift');
    var rows = Array.isArray(data) ? data.filter(function (d) { return d && isNum(d.median); }) : [];
    if (!rows.length) return;
    section.hidden = false;
    document.querySelector('[data-nav="drift"]').hidden = false;
    var ORDER = ['Y-2 vs Y-1', 'Y-1 vs Y0', 'Y-1 vs Y+1'];
    var pairs = Array.from(new Set(rows.map(function (d) { return d.pair; })));
    pairs.sort(function (a, b) {
      var ia = ORDER.indexOf(a), ib = ORDER.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
    var GROUPS = [
      { key: 'solar', label: 'Solar sites', shape: 'diamond', color: INK, hollow: false },
      { key: 'control', label: 'Control land', shape: 'circle', color: INK3, hollow: true }
    ];
    function pretty(p) { return String(p).replace(/-/g, '−').replace(/\bvs\b/, 'compared with'); }

    var legend = $('#drift-legend'); clear(legend);
    GROUPS.forEach(function (g) {
      legendItem(legend, function (svg) {
        svg.append('line').attr('x1', 1).attr('x2', 27).attr('y1', 7).attr('y2', 7).attr('stroke', g.color).attr('stroke-width', 3).attr('stroke-linecap', 'round').attr('stroke-opacity', g.hollow ? 0.6 : 0.35);
        drawMarker(svg, g.shape, 14, 7, 4, g.color, { hollow: g.hollow });
      }, g.label + (g.key === 'solar' ? ' (land that became a solar farm)' : ' (nearby land that did not)'));
    });

    // table
    var host = $('#drift-table'); clear(host);
    var tb = el('tbody');
    pairs.forEach(function (p) {
      GROUPS.forEach(function (g) {
        var d = rows.filter(function (r) { return r.pair === p && r.group === g.key; })[0];
        if (!d) return;
        tb.appendChild(el('tr', null, el('th', { scope: 'row', class: 'left', text: pretty(p) }), el('td', { class: 'left', text: g.label }),
          el('td', { text: fmt.score(d.median) }), el('td', { text: fmt.score(d.q25) }), el('td', { text: fmt.score(d.q75) }), el('td', { text: fmt.int(d.n) })));
      });
    });
    host.appendChild(el('table', null, el('thead', null, el('tr', null,
      el('th', { scope: 'col', class: 'left', text: 'Years compared' }), el('th', { scope: 'col', class: 'left', text: 'Group' }),
      el('th', { scope: 'col', text: 'Median' }), el('th', { scope: 'col', text: 'Lower quartile' }), el('th', { scope: 'col', text: 'Upper quartile' }), el('th', { scope: 'col', text: 'Sites' }))), tb));

    var chartEl = $('#drift-chart');
    onResize(chartEl, function (width) {
      clear(chartEl);
      var m = { t: 6, r: 58, b: 44, l: 96 }, rowH = 24, blockH = 28 + rowH * GROUPS.length + 12;
      var H = m.t + blockH * pairs.length + m.b;
      var vals = []; rows.forEach(function (d) { vals.push(d.median); if (isNum(d.q25)) vals.push(d.q25); if (isNum(d.q75)) vals.push(d.q75); });
      var lo = Math.max(-1, Math.floor((d3.min(vals) - 0.03) * 10) / 10), hi = Math.min(1, Math.ceil((d3.max(vals) + 0.005) * 10) / 10);
      if (hi <= lo) hi = lo + 0.1;
      var x = d3.scaleLinear().domain([lo, hi]).range([m.l, width - m.r]);
      var svg = d3.select(chartEl).append('svg').attr('width', width).attr('height', H).attr('role', 'img')
        .attr('aria-label', 'Median cosine similarity between years for solar sites and control land. The exact values are in the table below the chart.');
      x.ticks(width < 560 ? 4 : 6).forEach(function (t) {
        svg.append('line').attr('x1', x(t)).attr('x2', x(t)).attr('y1', m.t).attr('y2', H - m.b).attr('stroke', GRID).attr('shape-rendering', 'crispEdges');
        svg.append('text').attr('x', x(t)).attr('y', H - m.b + 16).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', INK3).text(fmt.tick(t));
      });
      svg.append('text').attr('x', (m.l + width - m.r) / 2).attr('y', H - 6).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', INK2).text('Cosine similarity between the two years');
      pairs.forEach(function (p, pi) {
        var top = m.t + pi * blockH;
        svg.append('text').attr('x', 0).attr('y', top + 18).attr('font-size', 13).attr('font-weight', 650).attr('fill', INK)
          .attr('paint-order', 'stroke').attr('stroke', '#fff').attr('stroke-width', 4).text(pretty(p));
        GROUPS.forEach(function (g, gi) {
          var d = rows.filter(function (r) { return r.pair === p && r.group === g.key; })[0];
          if (!d) return;
          var cy = top + 28 + gi * rowH + rowH / 2;
          svg.append('text').attr('x', m.l - 10).attr('y', cy).attr('dy', '0.32em').attr('text-anchor', 'end').attr('font-size', 12.5).attr('fill', INK2).text(g.label);
          var right = x(d.median);
          if (isNum(d.q25) && isNum(d.q75)) {
            svg.append('line').attr('x1', x(d.q25)).attr('x2', x(d.q75)).attr('y1', cy).attr('y2', cy).attr('stroke', g.color).attr('stroke-width', 4).attr('stroke-linecap', 'round').attr('stroke-opacity', g.hollow ? 0.6 : 0.35);
            right = x(Math.max(d.q75, d.median));
          }
          drawMarker(svg, g.shape, x(d.median), cy, 4.5, g.color, { hollow: g.hollow });
          svg.append('text').attr('x', right + 12).attr('y', cy).attr('dy', '0.32em').attr('font-size', 12.5).attr('font-weight', 650).attr('fill', INK).text(fmt.score(d.median));
          svg.append('rect').attr('x', m.l).attr('y', cy - rowH / 2).attr('width', Math.max(0, width - m.l)).attr('height', rowH).attr('fill', 'transparent')
            .on('pointermove pointerdown', function (ev) {
              var box = el('div', null, el('div', { class: 'tt-title', text: g.label + ', ' + pretty(p) }),
                ttRow('Median', fmt.score(d.median)), ttRow('Middle half of sites', fmt.score(d.q25) + ' to ' + fmt.score(d.q75)), ttRow('Sites', fmt.int(d.n)));
              showTip(box, ev.clientX, ev.clientY);
            }).on('pointerleave', hideTip);
        });
      });
    });
  }

  /* ---------- airports: map + table ---------- */
  function initAirports(airports, us) {
    var rows = airports.filter(function (d) { return d && typeof d.name === 'string'; });
    var ranked = rows.slice().sort(function (a, b) { return (isNum(b.solar_like_km2) ? b.solar_like_km2 : -1) - (isNum(a.solar_like_km2) ? a.solar_like_km2 : -1); });
    ranked.forEach(function (d, i) { d._rank = i + 1; d._id = i; });
    var maxV = d3.max(ranked, function (d) { return d.solar_like_km2; }) || 0;
    var ramp = d3.interpolateRgbBasis(['#fde9a9', '#f6bd2c', '#dd8a00', '#a85a00', '#6b3600']);
    var color = d3.scaleSequential(ramp).domain([0, maxV || 1]);
    var hot = null, mapApi = null, tableApi = null;

    function setHot(id, from) {
      if (hot === id) return;
      hot = id;
      if (mapApi) mapApi.highlight(id);
      if (tableApi) tableApi.highlight(id, from);
    }
    function tipFor(d) {
      return el('div', null,
        el('div', { class: 'tt-title', text: d.name + (d.state ? ', ' + d.state : '') }),
        ttRow('Solar-like land', fmt.km2(d.solar_like_km2), 'km²'),
        ttRow('Share of nearby land', fmt.pct(d.solar_like_frac)),
        ttRow('Mean score', fmt.score(d.mean_score)),
        ttRow('Existing solar farms nearby', fmt.int(d.existing_farms_5km)),
        el('div', { class: 'tt-foot', text: 'Rank ' + fmt.int(d._rank) + ' of ' + fmt.int(ranked.length) + ' by solar-like land' }));
    }

    /* map */
    var mapEl = $('#map');
    if (us && us.objects && us.objects.states && window.topojson) {
      var VW = 975, VH = 610;
      var proj = d3.geoAlbersUsa().scale(1300).translate([VW / 2, VH / 2]);
      var pts = [];
      ranked.forEach(function (d) {
        if (!isNum(d.lon) || !isNum(d.lat)) return;
        var p = proj([d.lon, d.lat]);
        if (p) pts.push({ d: d, x: p[0], y: p[1] });
      });
      var off = ranked.length - pts.length;
      if (off > 0) $('#map-caption').appendChild(document.createTextNode(' ' + fmt.int(off) + (off === 1 ? ' airport lies' : ' airports lie') + ' outside the area this map can show and ' + (off === 1 ? 'appears' : 'appear') + ' only in the table.'));
      var delaunay = pts.length ? d3.Delaunay.from(pts, function (p) { return p.x; }, function (p) { return p.y; }) : null;
      var path = d3.geoPath();
      var states = topojson.feature(us, us.objects.states).features;
      var nation = us.objects.nation ? topojson.feature(us, us.objects.nation) : null;

      onResize(mapEl, function (width) {
        clear(mapEl);
        var k = width / VW, narrow = width < 560, n = pts.length;
        var rmax = (n <= 30 ? 16 : n <= 200 ? 11 : 7.5) * (narrow ? 0.55 : 1), rmin = n <= 30 ? 3  : n <= 200 ? 2.5 : 1.8;
        var rpx = d3.scaleSqrt().domain([0, maxV || 1]).range([rmin, rmax]);
        var r = function (d) { return rpx(isNum(d.solar_like_km2) ? d.solar_like_km2 : 0) / k; };
        var svg = d3.select(mapEl).append('svg').attr('viewBox', '0 0 ' + VW + ' ' + VH).attr('role', 'img')
          .attr('aria-label', 'Map of the United States with one circle per airport, sized and shaded by the area of solar-like land nearby. The same values are in the table below.');
        svg.append('g').selectAll('path').data(states).join('path').attr('class', 'state').attr('d', path).attr('stroke-width', 1 / k);
        if (nation) svg.append('path').attr('class', 'nation').attr('d', path(nation)).attr('stroke-width', 1 / k);
        var circles = svg.append('g').selectAll('circle').data(pts).join('circle').attr('class', 'apt')
          .attr('cx', function (p) { return p.x; }).attr('cy', function (p) { return p.y; })
          .attr('r', function (p) { return r(p.d); })
          .attr('fill', function (p) { return isNum(p.d.solar_like_km2) ? color(p.d.solar_like_km2) : '#fff'; })
          .attr('fill-opacity', n > 200 ? 0.82 : 0.92)
          .attr('stroke-width', (n > 200 ? 0.5 : 0.8) / k);
        // direct labels for the top few, only when there is room
        if (!narrow) {
          var placed = [];
          pts.slice(0, 3).forEach(function (p) {
            var fs = 12.5 / k, left = p.x > VW * 0.72, tx = p.x + (left ? -1 : 1) * (r(p.d) + 5 / k);
            var w = p.d.name.length * fs * 0.56, box = { x0: left ? tx - w : tx, x1: left ? tx : tx + w, y0: p.y - fs, y1: p.y + fs };
            if (box.x0 < 0 || box.x1 > VW) return;
            if (placed.some(function (b) { return box.x0 < b.x1 && box.x1 > b.x0 && box.y0 < b.y1 && box.y1 > b.y0; })) return;
            placed.push(box);
            svg.append('text').attr('class', 'apt-label').attr('x', tx).attr('y', p.y).attr('dy', '0.32em').attr('text-anchor', left ? 'end' : 'start')
              .attr('font-size', fs).attr('stroke-width', 3.5 / k).text(p.d.name);
          });
        }
        var ring = svg.append('circle').attr('fill', 'none').attr('stroke', INK).attr('stroke-width', 2 / k).attr('visibility', 'hidden').attr('pointer-events', 'none');
        mapApi = {
          highlight: function (id) {
            var p = pts.filter(function (q) { return q.d._id === id; })[0];
            if (!p) { ring.attr('visibility', 'hidden'); return; }
            ring.attr('cx', p.x).attr('cy', p.y).attr('r', r(p.d) + 2.5 / k).attr('visibility', 'visible');
          }
        };
        if (hot != null) mapApi.highlight(hot);
        svg.on('pointermove pointerdown', function (ev) {
          if (!delaunay) return;
          var rect = svg.node().getBoundingClientRect();
          var mx = (ev.clientX - rect.left) / k, my = (ev.clientY - rect.top) / k;
          var i = delaunay.find(mx, my), p = pts[i];
          if (!p || Math.hypot(p.x - mx, p.y - my) > Math.max(r(p.d) + 4 / k, 16 / k)) { setHot(null); hideTip(); return; }
          setHot(p.d._id, 'map');
          showTip(tipFor(p.d), ev.clientX, ev.clientY);
        }).on('pointerleave', function () { setHot(null); hideTip(); });

        // legend
        var lg = $('#map-legend'); clear(lg);
        var stops = d3.range(0, 1.01, 0.1).map(function (t) { return ramp(t); }).join(',');
        var bar = el('span', { class: 'ramp-bar' }); bar.style.background = 'linear-gradient(90deg,' + stops + ')';
        lg.appendChild(el('span', { class: 'ramp' }, el('span', { class: 'ramp-title', text: 'Solar-like land nearby' }), el('span', { text: fmt.km2(0) }), bar, el('span', { text: fmt.km2(maxV) + ' km²' })));
        var sizes = el('span', { class: 'sizes' });
        [maxV / 4, maxV].forEach(function (v) {
          var rr = rpx(v), s = d3.select(sizes).append('svg').attr('width', rr * 2 + 2).attr('height', rr * 2 + 2);
          s.append('circle').attr('cx', rr + 1).attr('cy', rr + 1).attr('r', rr).attr('fill', color(v)).attr('stroke', '#4a2c00').attr('stroke-opacity', 0.55).attr('stroke-width', 0.8);
          sizes.appendChild(el('span', { text: fmt.km2(v) + ' km²' }));
        });
        if (maxV > 0) lg.appendChild(sizes);
      });
    } else {
      mapEl.appendChild(el('p', { class: 'fine', text: 'The map outline could not be loaded, so only the table is shown.' }));
    }

    /* table */
    var COLS = [
      { key: '_rank', label: 'Rank', num: true, f: fmt.int },
      { key: 'name', label: 'Airport', num: false },
      { key: 'state', label: 'State', num: false },
      { key: 'solar_like_km2', label: 'Solar-like land (km²)', num: true, f: fmt.km2, bar: true },
      { key: 'solar_like_frac', label: 'Share of nearby land', num: true, f: fmt.pct },
      { key: 'mean_score', label: 'Mean score', num: true, f: fmt.score },
      { key: 'existing_farms_5km', label: 'Existing solar farms nearby', num: true, f: fmt.int },
      { key: 'land_km2', label: 'Land scored (km²)', num: true, f: fmt.km2 }
    ];
    var sort = { key: '_rank', dir: 1 }, query = '', expanded = false;
    var host = $('#air-table'), moreBtn = $('#air-more'), count = $('#air-count');
    var thead = el('thead'), tbody = el('tbody'), headRow = el('tr');
    COLS.forEach(function (c) {
      var btn = el('button', { type: 'button', class: 'sort-btn' }, el('span', { text: c.label }), el('span', { class: 'arrow', 'aria-hidden': 'true' }));
      btn.addEventListener('click', function () {
        if (sort.key === c.key) sort.dir = -sort.dir;
        else sort = { key: c.key, dir: c.num && c.key !== '_rank' ? -1 : 1 };
        render();
      });
      c.th = el('th', { scope: 'col', class: c.num ? null : 'left' }, btn);
      headRow.appendChild(c.th);
    });
    thead.appendChild(headRow);
    clear(host);
    host.appendChild(el('table', null, el('caption', { class: 'visually-hidden', text: 'Airports ranked by solar-like land nearby. Column headers sort the table.' }), thead, tbody));

    function render() {
      var q = query.trim().toLowerCase();
      var list = ranked.filter(function (d) { return !q || d.name.toLowerCase().indexOf(q) >= 0 || String(d.state || '').toLowerCase().indexOf(q) >= 0; });
      var col = COLS.filter(function (c) { return c.key === sort.key; })[0];
      list.sort(function (a, b) {
        var va = a[sort.key], vb = b[sort.key], r;
        if (col.num) { var na = isNum(va), nb = isNum(vb); if (!na || !nb) return (nb ? 1 : 0) - (na ? 1 : 0) || a._rank - b._rank; r = va - vb; }
        else r = String(va || '').localeCompare(String(vb || ''));
        return r * sort.dir || a._rank - b._rank;
      });
      COLS.forEach(function (c) {
        var active = c.key === sort.key;
        if (active) c.th.setAttribute('aria-sort', sort.dir > 0 ? 'ascending' : 'descending'); else c.th.removeAttribute('aria-sort');
        c.th.querySelector('.arrow').textContent = active ? (sort.dir > 0 ? '▲' : '▼') : '▼';
      });
      var shown = expanded || q ? list : list.slice(0, PAGE_SIZE);
      clear(tbody);
      shown.forEach(function (d) {
        var tr = el('tr', { 'data-id': d._id });
        COLS.forEach(function (c) {
          var txt = c.f ? c.f(d[c.key]) : (d[c.key] != null ? String(d[c.key]) : NA), td;
          if (c.key === 'name') td = el('th', { scope: 'row', class: 'left wrap-ok', text: txt });
          else if (c.bar) {
            var bar = el('i'); bar.style.width = (maxV > 0 && isNum(d[c.key]) ? Math.max(0, d[c.key] / maxV) * 100 : 0) + '%';
            td = el('td', null, el('span', { class: 'bar-cell' }, el('span', { text: txt }), el('span', { class: 'bar-track', 'aria-hidden': 'true' }, bar)));
          } else td = el('td', { class: c.num ? null : 'left', text: txt });
          tr.appendChild(td);
        });
        tr.addEventListener('pointerenter', function () { setHot(d._id, 'table'); });
        tr.addEventListener('pointerleave', function () { setHot(null, 'table'); });
        tbody.appendChild(tr);
      });
      if (!shown.length) tbody.appendChild(el('tr', null, el('td', { class: 'left', colspan: COLS.length, text: 'No airports match.' })));
      count.textContent = 'Showing ' + fmt.int(shown.length) + ' of ' + fmt.int(ranked.length) + ' airports';
      var canToggle = !q && list.length > PAGE_SIZE;
      moreBtn.hidden = !canToggle;
      moreBtn.textContent = expanded ? 'Show fewer' : 'Show all ' + fmt.int(list.length) + ' airports';
      if (hot != null) tableApi.highlight(hot);
    }
    tableApi = {
      highlight: function (id) {
        tbody.querySelectorAll('tr.is-hot').forEach(function (tr) { tr.classList.remove('is-hot'); });
        if (id == null) return;
        var tr = tbody.querySelector('tr[data-id="' + id + '"]');
        if (tr) tr.classList.add('is-hot');
      }
    };
    $('#air-filter').addEventListener('input', function (e) { query = e.target.value; render(); });
    moreBtn.addEventListener('click', function () { expanded = !expanded; render(); });
    render();
  }

  /* ---------- gallery ---------- */
  function initGallery(items) {
    var list = Array.isArray(items) ? items.filter(function (g) { return g && typeof g.slug === 'string' && /^[A-Za-z0-9._-]+$/.test(g.slug); }) : [];
    if (!list.length) return;
    var grid = $('#gallery-grid'); clear(grid);
    var section = $('#gallery'), nav = document.querySelector('[data-nav="gallery"]'), alive = list.length;
    list.forEach(function (g) {
      var img = el('img', { src: 'img/airports/' + g.slug + '.png', alt: 'Satellite tile around ' + (g.name || g.slug) + ' with solar-like land highlighted', loading: 'lazy', decoding: 'async' });
      var fig = el('figure', null, img, el('figcaption', null, el('strong', { text: g.name || g.slug }), g.caption ? String(g.caption) : null));
      img.addEventListener('error', function () {
        fig.remove(); alive -= 1;
        if (alive <= 0) { section.hidden = true; nav.hidden = true; }
      });
      grid.appendChild(fig);
    });
    section.hidden = false; nav.hidden = false;
  }

  /* ---------- boot ---------- */
  function fail(err) {
    var box = $('#load-error');
    box.hidden = false;
    box.querySelector('.error-box').textContent = 'The results could not be loaded. ' + (err && err.message ? err.message + '. ' : '') +
      (location.protocol === 'file:' ? 'Browsers block data loading from file:// pages; serve this folder with a local web server instead.' : '');
    $('#verdict-text').textContent = 'Result unavailable';
    if (window.console) console.error(err);
  }

  Promise.all([
    getJSON('data/summary.json'),
    getJSON('data/label_efficiency.json'),
    getJSON('data/airports.json'),
    getJSON('data/drift.json', true),
    getJSON('data/gallery.json', true),
    getJSON('vendor/states-albers-10m.json', true)
  ]).then(function (res) {
    var S = res[0] || {}, le = Array.isArray(res[1]) ? res[1] : [], airports = Array.isArray(res[2]) ? res[2] : [];
    var steps = [
      function () { renderSummary(S, airports, le); },
      function () { initLabelEfficiency(le, S); },
      function () { renderRobustness(S); },
      function () { initDrift(res[3]); },
      function () { initAirports(airports, res[5]); },
      function () { initGallery(res[4]); }
    ];
    steps.forEach(function (step) { try { step(); } catch (e) { if (window.console) console.error(e); } });
  }).catch(fail);
})();
