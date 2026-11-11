/* Telehealth Access Explorer: a static, offline-capable PWA. Data: docs/data/app.json (built by run_all.py). */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const S = { data: null, atlas: null, q: 0, geo: "CA", a: "CA", b: "US", tab: "map", desc: true, sheetGeo: null };
  const RACE_SHORT = { "American Indian/Alaska Native": "AI/AN", "Asian/Pacific Islander": "Asian/PI",
    "Black/African American": "Black", "Hispanic": "Hispanic", "Non-Hispanic White": "White" };
  const AGE_LABEL = { "0-64": "Under 65", "65-74": "65–74", "75-84": "75–84", "85 and over": "85+" };

  const fmt = (v, d = 1) => (v == null ? "n/a" : (v * 100).toFixed(d) + "%");
  const fmtPP = (v) => (v == null ? "n/a" : (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(1) + " pts");
  const cls = (v) => (v == null ? "" : v >= 0 ? "up" : "down");
  const geo = (c) => S.data.geos.find((g) => g.code === c);
  const ser = (c) => S.data.series[c];
  const period = (i = S.q) => S.data.periods[i];
  const states = () => S.data.geos.filter((g) => g.type === "state");
  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

  function rank(code, qi = S.q) {
    const v = ser(code).all[qi];
    if (v == null || geo(code).type !== "state") return null;
    return 1 + states().filter((g) => (ser(g.code).all[qi] ?? -1) > v).length;
  }
  const sameQLastYear = (qi) => (qi >= 4 ? qi - 4 : null);
  const peak2020 = (code) => { const a = ser(code).all.slice(0, 4).filter((v) => v != null); return a.length ? Math.max(...a) : null; };

  /* ---------- routing: #tab/arg1/arg2?q=2026-Q1 ---------- */
  function readHash() {
    const [path, qs] = location.hash.replace(/^#/, "").split("?");
    const [tab, x, y] = (path || "map").split("/");
    const qp = new URLSearchParams(qs || "").get("q");
    const qi = S.data.periods.indexOf(qp);
    if (qi >= 0) S.q = qi;
    if (tab === "state" && x && ser(x)) S.geo = x;
    if (tab === "compare" && x && ser(x)) { S.a = x; if (y && ser(y)) S.b = y; }
    S.tab = ["map", "state", "compare", "insights", "about"].includes(tab) ? tab : "map";
  }
  function writeHash() {
    const p = S.tab === "state" ? `state/${S.geo}` : S.tab === "compare" ? `compare/${S.a}/${S.b}` : S.tab;
    const h = `#${p}?q=${period()}`;
    if (location.hash !== h) history.replaceState(null, "", h);
  }
  function go(tab) { S.tab = tab; closeSheet(); render(); window.scrollTo(0, 0); }

  /* ---------- quarter selector ---------- */
  function initQuarter() {
    const sel = $("#quarter");
    sel.innerHTML = S.data.periods.map((p, i) => `<option value="${i}">${p.replace("-", " ")}${i === S.data.periods.length - 1 ? " (latest)" : ""}</option>`).join("");
    sel.addEventListener("change", () => { S.q = +sel.value; render(); });
    $("#qPrev").addEventListener("click", () => { if (S.q > 0) { S.q--; render(); } });
    $("#qNext").addEventListener("click", () => { if (S.q < S.data.periods.length - 1) { S.q++; render(); } });
  }

  function geoOptions(includeNational) {
    const g = S.data.geos.filter((x) => includeNational || x.type !== "national");
    const grp = (t, label) => `<optgroup label="${label}">` + g.filter((x) => x.type === t)
      .map((x) => `<option value="${x.code}">${esc(x.name)}</option>`).join("") + "</optgroup>";
    return (includeNational ? grp("national", "United States") : "") + grp("state", "States + DC") + grp("territory", "Territories");
  }

  /* ---------- map ---------- */
  let mapPaths = null;
  function colorScale() {
    const vals = states().map((g) => ser(g.code).all[S.q]).filter((v) => v != null);
    return d3.scaleSequential(d3.interpolateYlGnBu).domain([d3.min(vals) * 0.9, d3.max(vals)]);
  }
  function drawMap() {
    const feats = topojson.feature(S.atlas, S.atlas.objects.states).features;
    const byFips = Object.fromEntries(states().map((g) => [g.fips, g.code]));
    const svg = d3.select("#map").append("svg").attr("viewBox", "0 0 975 610").attr("aria-hidden", "true");
    const path = d3.geoPath();
    mapPaths = svg.append("g").selectAll("path").data(feats).join("path")
      .attr("class", "state").attr("d", path)
      .attr("data-code", (d) => byFips[d.id]).attr("data-name", (d) => d.properties.name)
      .on("click", (ev, d) => openSheet(byFips[d.id]));
    svg.append("path").datum(topojson.mesh(S.atlas, S.atlas.objects.states, (a, b) => a !== b))
      .attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 0.6).attr("pointer-events", "none");
  }
  function renderMap() {
    const c = colorScale();
    mapPaths.attr("fill", function () { const v = ser(this.dataset.code).all[S.q]; return v == null ? "#d9dfe2" : c(v); })
      .classed("sel", function () { return this.dataset.code === S.sheetGeo; });
    mapPaths.filter(function () { return this.dataset.code === S.sheetGeo; }).raise();
    const [lo, hi] = c.domain(), us = ser("US").all[S.q];
    const stops = d3.range(0, 1.01, 0.1).map((t) => c(lo + t * (hi - lo))).join(",");
    const pos = Math.max(0, Math.min(100, ((us - lo) / (hi - lo)) * 100));
    $("#legend").className = "legend legend-wrap";
    $("#legend").innerHTML = `<span>${fmt(lo / 0.9, 0)}</span><div class="ramp" style="background:linear-gradient(90deg,${stops})">
      <div class="tick" style="left:${pos}%"></div><div class="ticklbl" style="left:${pos}%">US ${fmt(us)}</div></div><span>${fmt(hi, 0)}</span>`;
    $("#mapCaption").textContent = `${period().replace("-", " ")} · darker = higher use · national ${fmt(us)}`;
    const rows = states().map((g) => ({ g, v: ser(g.code).all[S.q] })).filter((r) => r.v != null)
      .sort((x, y) => (S.desc ? y.v - x.v : x.v - y.v));
    const max = d3.max(rows, (r) => r.v);
    const usRow = `<li class="us" data-code="US"><span class="rk">US</span><span class="nm">National<span class="bar" style="width:${(us / max) * 100}%;background:#0b3c49"></span></span><span class="val">${fmt(us)}</span></li>`;
    $("#rankList").innerHTML = rows.map((r) => `<li data-code="${r.g.code}"><span class="rk">${rank(r.g.code)}</span><span class="nm">${esc(r.g.name)}<span class="bar" style="width:${(r.v / max) * 100}%;background:${c(r.v)}"></span></span><span class="val">${fmt(r.v)}</span></li>`).join("");
    const lis = $("#rankList").children; const at = Math.min(S.desc ? rows.findIndex((r) => r.v < us) : rows.findIndex((r) => r.v > us), lis.length);
    if (at >= 0) lis[at].insertAdjacentHTML("beforebegin", usRow);
    $("#rankOrder").textContent = S.desc ? "Highest first" : "Lowest first";
  }

  /* ---------- bottom sheet ---------- */
  function kpiCards(code) {
    const s = ser(code), v = s.all[S.q], us = ser("US").all[S.q], ly = sameQLastYear(S.q), pk = peak2020(code), r = rank(code);
    const cards = [
      ["Telehealth use", fmt(v), `${s.users[S.q]?.toLocaleString() ?? "n/a"} of ${s.eligible[S.q]?.toLocaleString() ?? "n/a"} people`],
      code === "US" ? ["States above national", `${states().filter((g) => (ser(g.code).all[S.q] ?? 0) > us).length} of 51`, "incl. DC"]
        : ["Rank", r ? `#${r} of 51` : "n/a", r ? "50 states + DC, 1 = highest" : "territory, not ranked"],
      code === "US" ? ["2020 peak", fmt(pk), v != null && pk ? `now ${Math.round((v / pk) * 100)}% of peak` : ""]
        : ["vs national", `<span class="${cls(v - us)}">${fmtPP(v - us)}</span>`, `US ${fmt(us)}`],
      ["vs a year earlier", ly == null ? "n/a" : `<span class="${cls(v - s.all[ly])}">${fmtPP(v - s.all[ly])}</span>`, ly == null ? "no earlier data" : `${period(ly).replace("-", " ")}: ${fmt(s.all[ly])}`],
    ];
    return cards.map(([l, n, c]) => `<div class="kpi"><div class="lbl">${l}</div><div class="num">${n}</div><div class="ctx">${c}</div></div>`).join("");
  }
  function openSheet(code) {
    if (!code) return;
    S.sheetGeo = code;
    $("#sheetTitle").textContent = geo(code).name;
    $("#sheetBody").innerHTML = `<p class="muted small">${period().replace("-", " ")} · share of telehealth-eligible Medicare FFS users who had a telehealth service</p>
      <div class="kpis">${kpiCards(code)}</div><div id="sheetSpark" class="chart"></div>`;
    $("#sheet").hidden = false; $("#sheetBackdrop").hidden = false; $("#sheet").classList.remove("closing");
    lineChart("#sheetSpark", [{ code, color: "#12806f" }, { code: "US", color: "#9aa8ae" }], { height: 120, readout: null });
    renderMap();
  }
  function closeSheet() {
    if ($("#sheet").hidden) return;
    S.sheetGeo = null; $("#sheet").hidden = true; $("#sheetBackdrop").hidden = true;
    if (mapPaths) renderMap();
  }
  function initSheet() {
    $("#sheetClose").addEventListener("click", closeSheet);
    $("#sheetBackdrop").addEventListener("click", closeSheet);
    $("#sheetDetail").addEventListener("click", () => { S.geo = S.sheetGeo; go("state"); });
    $("#sheetCompare").addEventListener("click", () => { S.a = S.sheetGeo; S.b = S.a === "US" ? "CA" : "US"; go("compare"); });
    let y0 = null; const sh = $("#sheet");
    sh.addEventListener("pointerdown", (e) => { if (e.target.closest("button,.chart")) return; y0 = e.clientY; });
    sh.addEventListener("pointermove", (e) => { if (y0 != null && e.clientY - y0 > 0) sh.style.transform = `translateY(${e.clientY - y0}px)`; });
    const end = (e) => { if (y0 == null) return; const dy = e.clientY - y0; y0 = null; sh.style.transform = ""; if (dy > 80) closeSheet(); };
    sh.addEventListener("pointerup", end); sh.addEventListener("pointercancel", end);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSheet(); });
  }

  /* ---------- charts ---------- */
  function lineChart(sel, lines, { height = 210, readout = null } = {}) {
    const el = $(sel); el.innerHTML = "";
    const W = Math.max(280, el.clientWidth || 340), H = height, m = { t: 10, r: 18, b: 22, l: 36 };
    const P = S.data.periods, x = d3.scaleLinear().domain([0, P.length - 1]).range([m.l, W - m.r]);
    const all = lines.flatMap((l) => ser(l.code).all).filter((v) => v != null);
    const y = d3.scaleLinear().domain([0, d3.max(all) * 1.08]).nice().range([H - m.b, m.t]);
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("height", H);
    svg.append("g").attr("class", "grid").selectAll("line").data(y.ticks(4)).join("line")
      .attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y);
    svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).tickValues(P.map((p, i) => i).filter((i) => P[i].endsWith("Q1"))).tickFormat((i) => P[i].slice(0, 4)).tickSizeOuter(0));
    svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat((v) => Math.round(v * 100) + "%")).call((g) => g.select(".domain").remove());
    svg.append("line").attr("class", "marker").attr("x1", x(S.q)).attr("x2", x(S.q)).attr("y1", m.t).attr("y2", H - m.b);
    const line = d3.line().defined((d) => d != null).x((d, i) => x(i)).y((d) => y(d));
    lines.slice().reverse().forEach((l) => {
      svg.append("path").datum(ser(l.code).all).attr("fill", "none").attr("stroke", l.color).attr("stroke-width", l.code === lines[0].code ? 2.6 : 2).attr("d", line);
      const v = ser(l.code).all[S.q];
      if (v != null) svg.append("circle").attr("cx", x(S.q)).attr("cy", y(v)).attr("r", 4).attr("fill", l.color).attr("stroke", "#fff").attr("stroke-width", 1.5);
    });
    if (!readout) return;
    const cur = svg.append("line").attr("class", "cursor").attr("y1", m.t).attr("y2", H - m.b).style("display", "none");
    const show = (ev) => {
      const [px] = d3.pointer(ev, svg.node()); const i = Math.max(0, Math.min(P.length - 1, Math.round(x.invert(px))));
      cur.style("display", null).attr("x1", x(i)).attr("x2", x(i));
      $(readout).innerHTML = `<b>${P[i].replace("-", " ")}</b> · ` + lines.map((l) => `<span style="color:${l.color};font-weight:600">${esc(geo(l.code).code === "US" ? "US" : geo(l.code).name)} ${fmt(ser(l.code).all[i])}</span>`).join(" · ");
    };
    svg.on("pointerdown pointermove", show);
  }
  function barRows(items, max) {
    return items.map((it) => `<div class="bar-row"><span class="lab">${esc(it.label)}</span><span class="track">${it.v == null ? "" : `<span class="fill" style="width:${(it.v / max) * 100}%;background:${it.color || "var(--accent)"}"></span>`}${it.ref == null ? "" : `<span class="ref" style="left:calc(${(it.ref / max) * 100}% - 1px)" title="National ${fmt(it.ref)}"></span>`}</span><span class="v">${fmt(it.v)}</span></div>`).join("");
  }

  /* ---------- state view ---------- */
  function segItems(code, dim, labeler = (s) => s) {
    return S.data.segments[dim].map((sg) => ({ label: labeler(sg), v: ser(code)[dim][sg][S.q], ref: code === "US" ? null : ser("US")[dim][sg][S.q] }));
  }
  function renderState() {
    const code = S.geo; $("#statePick").value = code;
    $("#stateKpis").innerHTML = kpiCards(code);
    lineChart("#stateTrend", [{ code, color: "#12806f" }, ...(code === "US" ? [] : [{ code: "US", color: "#9aa8ae" }])], { readout: "#trendReadout" });
    $("#trendReadout").innerHTML = `<span style="color:#12806f;font-weight:600">● ${esc(geo(code).name)}</span>${code === "US" ? "" : ' <span style="color:#9aa8ae;font-weight:600">● National</span>'} · dashed line = selected quarter`;
    const ru = segItems(code, "rurality"), age = segItems(code, "age", (s) => AGE_LABEL[s]);
    const ds = segItems(code, "dual_status", (s) => (s === "Medicare & Medicaid" ? "Dual-eligible" : "Medicare only"));
    const race = segItems(code, "race", (s) => RACE_SHORT[s]);
    const mx = (a) => Math.max(0.05, d3.max(a.flatMap((i) => [i.v, i.ref]).filter((v) => v != null)) * 1.1);
    const gap = ru[1].v != null && ru[0].v != null ? ru[1].v - ru[0].v : null;
    $("#stateRural").innerHTML = barRows(ru, mx(ru)) + `<p class="muted small">${gap == null ? "Rural or urban figure not reported for this geography." : gap > 0 ? `Urban residents use telehealth <b>${fmtPP(gap).replace("+", "")}</b> more than rural residents.` : `Rural residents use telehealth <b>${fmtPP(-gap).replace("+", "")}</b> more than urban residents.`}</p>`;
    $("#stateAge").innerHTML = barRows(age, mx(age)) + `<p class="muted small">Under-65 beneficiaries qualify for Medicare through disability or end-stage renal disease.</p>`;
    const eq = [...ds, ...race];
    $("#stateEquity").innerHTML = `<div class="grp">Dual status</div>${barRows(ds, mx(eq))}<div class="grp">Race / ethnicity</div>${barRows(race, mx(eq))}<p class="muted small">n/a = suppressed by CMS for small numbers. Tick = national.</p>`;
  }

  /* ---------- compare view ---------- */
  function renderCompare() {
    $("#cmpA").value = S.a; $("#cmpB").value = S.b;
    lineChart("#cmpTrend", [{ code: S.a, color: "#12806f" }, { code: S.b, color: "#e07a1f" }], { readout: "#cmpReadout" });
    $("#cmpReadout").innerHTML = `<span style="color:#12806f;font-weight:600">● ${esc(geo(S.a).name)}</span> <span style="color:#e07a1f;font-weight:600">● ${esc(geo(S.b).name)}</span> · touch to read a quarter`;
    const ly = sameQLastYear(S.q);
    const rows = [
      ["Telehealth use", (c) => ser(c).all[S.q]],
      ["Rank (of 51)", (c) => rank(c), "rank"],
      ["Change vs year earlier", (c) => (ly == null ? null : ser(c).all[S.q] - ser(c).all[ly]), "pp"],
      ["2020 peak", (c) => peak2020(c)],
      ["Rural", (c) => ser(c).rurality.Rural[S.q]],
      ["Urban", (c) => ser(c).rurality.Urban[S.q]],
      ["Under 65", (c) => ser(c).age["0-64"][S.q]],
      ["85+", (c) => ser(c).age["85 and over"][S.q]],
      ["Dual-eligible", (c) => ser(c).dual_status["Medicare & Medicaid"][S.q]],
      ["Medicare only", (c) => ser(c).dual_status["Medicare Only"][S.q]],
    ];
    const cell = (v, kind) => (v == null ? "n/a" : kind === "rank" ? `#${v}` : kind === "pp" ? `<span class="${cls(v)}">${fmtPP(v)}</span>` : fmt(v));
    const diff = (a, b, kind) => (a == null || b == null ? "–" : kind === "rank" ? `${a - b > 0 ? "+" : ""}${a - b}` : `<span class="${cls(a - b)}">${fmtPP(a - b)}</span>`);
    const short = (c) => (c === "US" ? "US" : c);
    $("#cmpTable").innerHTML = `<thead><tr><th></th><th class="a">${short(S.a)}</th><th class="b">${short(S.b)}</th><th>Diff</th></tr></thead><tbody>` +
      rows.map(([l, f, k]) => `<tr><td>${l}</td><td>${cell(f(S.a), k)}</td><td>${cell(f(S.b), k)}</td><td>${diff(f(S.a), f(S.b), k)}</td></tr>`).join("") + "</tbody>";
    $("#cmpCaption").textContent = `${period().replace("-", " ")} · Diff = ${geo(S.a).name} minus ${geo(S.b).name}`;
  }

  /* ---------- insights + about ---------- */
  const INSIGHT_LINK = { plateau: ["state", "US"], geography: ["map"], rural: ["state", "MN"], age: ["state", "US"], equity: ["state", "US"] };
  function renderInsights() {
    $("#insightList").innerHTML = S.data.findings.map((f, i) => `<article class="card insight">
      <div class="stat">${esc(f.stat)}</div><div class="statlbl">${esc(f.stat_label)}</div>
      <h3>${i + 1}. ${esc(f.title)}</h3><p>${esc(f.text)}</p>
      <div class="sowhat"><b>So what:</b> ${esc(f.so_what)}</div>
      <button class="chip go" data-id="${f.id}">See it in the data ›</button></article>`).join("");
  }
  function renderAbout() {
    $("#coverage").textContent = S.data.meta.coverage.replaceAll("-", " ");
    const w = S.data.meta.dq_warnings;
    $("#dqNote").textContent = w.length ? `Data-quality flag: ${w.join(" ")}` : "No data-quality warnings in this release.";
  }

  /* ---------- render ---------- */
  function render() {
    $("#quarter").value = S.q; $("#qPrev").disabled = S.q === 0; $("#qNext").disabled = S.q === S.data.periods.length - 1;
    document.querySelectorAll(".view").forEach((v) => (v.hidden = v.dataset.tab !== S.tab));
    document.querySelectorAll(".tabbar button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === S.tab)));
    if (S.tab === "map") renderMap();
    if (S.tab === "state") renderState();
    if (S.tab === "compare") renderCompare();
    if (S.sheetGeo) openSheet(S.sheetGeo);
    writeHash();
  }

  function initEvents() {
    document.querySelectorAll(".tabbar button").forEach((b) => b.addEventListener("click", () => go(b.dataset.tab)));
    $("#rankList").addEventListener("click", (e) => { const li = e.target.closest("li"); if (li) openSheet(li.dataset.code); });
    $("#rankOrder").addEventListener("click", () => { S.desc = !S.desc; renderMap(); });
    $("#statePick").innerHTML = geoOptions(true); $("#cmpA").innerHTML = geoOptions(true); $("#cmpB").innerHTML = geoOptions(true);
    $("#statePick").addEventListener("change", (e) => { S.geo = e.target.value; render(); });
    $("#cmpA").addEventListener("change", (e) => { S.a = e.target.value; render(); });
    $("#cmpB").addEventListener("change", (e) => { S.b = e.target.value; render(); });
    $("#cmpSwap").addEventListener("click", () => { [S.a, S.b] = [S.b, S.a]; render(); });
    $("#insightList").addEventListener("click", (e) => {
      const b = e.target.closest("[data-id]"); if (!b) return; const [tab, g] = INSIGHT_LINK[b.dataset.id] || ["map"];
      if (g) S.geo = g; S.q = S.data.periods.length - 1; go(tab);
    });
    window.addEventListener("hashchange", () => { readHash(); render(); });
    let rw; window.addEventListener("resize", () => { clearTimeout(rw); rw = setTimeout(render, 150); });
  }

  function initInstall() {
    const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    if (ios && !standalone && !localStorage.getItem("hintDismissed")) $("#installHint").hidden = false;
    $("#hintClose").addEventListener("click", () => { $("#installHint").hidden = true; localStorage.setItem("hintDismissed", "1"); });
    let deferred = null;
    window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; $("#installBtn").hidden = false; });
    $("#installBtn").addEventListener("click", async () => { if (!deferred) return; deferred.prompt(); await deferred.userChoice; deferred = null; $("#installBtn").hidden = true; });
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch((err) => console.warn("SW registration failed", err));
  }

  async function boot() {
    const [data, atlas] = await Promise.all([fetch("data/app.json").then((r) => r.json()), fetch("data/states-albers-10m.json").then((r) => r.json())]);
    S.data = data; S.atlas = atlas; S.q = data.periods.length - 1;
    readHash(); initQuarter(); initEvents(); initSheet(); drawMap(); renderInsights(); renderAbout(); initInstall(); render();
    document.body.dataset.ready = "1";
  }
  window.addEventListener("DOMContentLoaded", () => boot().catch((err) => {
    console.error(err); $("#app").insertAdjacentHTML("afterbegin", `<div class="card">Could not load data. ${esc(err.message)}</div>`);
  }));
})();
