import json
import re
import sqlite3

import pandas as pd

import build_db
from paths import APP_JSON, CLEAN_FILE, DB_FILE, DOCS, REPORTS


def test_data_quality_has_no_errors():
    dq = json.loads((REPORTS / "data_quality.json").read_text())
    assert dq and not [c for c in dq if c["severity"] == "error"]


def test_clean_table_is_tidy_and_valid():
    t = pd.read_csv(CLEAN_FILE)
    assert not t.duplicated(["geo_code", "period", "dimension", "segment"]).any()
    assert t.pct_telehealth.dropna().between(0, 1).all()
    assert (t.geo_type == "state").groupby(t.geo_code).any().sum() == 51  # 50 states + DC
    assert set(t.dimension) == {"all", "rurality", "age", "race", "dual_status", "sex", "entitlement"}


def test_rate_equals_users_over_eligible():
    t = pd.read_csv(CLEAN_FILE).dropna(subset=["pct_telehealth"])
    assert ((t.telehealth_users / t.eligible_users - t.pct_telehealth).abs() <= 1e-4).all()


def test_state_ranking_query():
    rk = build_db.query("01_state_rankings")
    assert len(rk) == 51 and rk.rank_high_to_low.iloc[0] == 1
    assert rk.pct_telehealth.is_monotonic_decreasing


def test_every_sql_file_runs():
    for name in build_db.analysis_queries():
        assert len(build_db.query(name)) > 0, name


def test_findings_match_database(pipeline):
    m = pipeline["metrics"]
    con = sqlite3.connect(DB_FILE)
    nat = con.execute("SELECT pct_telehealth FROM quarterly_all WHERE geo_code='US' ORDER BY period_idx DESC LIMIT 1").fetchone()[0]
    con.close()
    assert abs(m["plateau"]["latest"] - nat) < 1e-9
    assert m["geography"]["top"] > m["plateau"]["latest"] > m["geography"]["bottom"]
    assert len(pipeline["findings"]) == 5
    for f in pipeline["findings"]:  # every percentage quoted in the text appears in the data's precision
        assert re.search(r"\d", f["text"]) and f["so_what"]


def test_app_json_aligns_with_map():
    app = json.loads(APP_JSON.read_text())
    n = len(app["periods"])
    assert app["periods"][0] == "2020-Q1" and app["meta"]["latest"] == app["periods"][-1]
    atlas = json.loads((DOCS / "data" / "states-albers-10m.json").read_text())
    ids = {g["id"] for g in atlas["objects"]["states"]["geometries"]}
    states = [g for g in app["geos"] if g["type"] == "state"]
    assert len(states) == 51 and {g["fips"] for g in states} == ids
    for s in app["series"].values():
        assert len(s["all"]) == n and all(len(v) == n for v in s["rurality"].values())


def test_pwa_files_are_installable_and_relative():
    man = json.loads((DOCS / "manifest.json").read_text())
    assert man["display"] == "standalone" and man["start_url"].startswith("./") and man["scope"] == "./"
    assert {"192x192", "512x512"} <= {i["sizes"] for i in man["icons"]}
    assert any(i.get("purpose") == "maskable" for i in man["icons"])
    for i in man["icons"]:
        assert (DOCS / i["src"]).exists()
    html = (DOCS / "index.html").read_text()
    for tag in ['rel="apple-touch-icon"', 'name="apple-mobile-web-app-capable"', 'rel="manifest"', "viewport-fit=cover"]:
        assert tag in html
    assert not re.search(r'(src|href)="/(?!/)', html), "absolute paths break GitHub Pages project sites"
    sw = (DOCS / "sw.js").read_text()
    for asset in re.findall(r'"([^"]+\.(?:html|css|js|json|png))"', sw):
        assert (DOCS / asset).exists(), asset
