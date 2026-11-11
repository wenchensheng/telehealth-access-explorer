"""Clean the raw CMS file into one tidy table and write a data-quality report.

Output: data/processed/telehealth_clean.csv with one row per
geography x period x (dimension, segment). Only rows that break the population down by
ONE characteristic at a time are kept (e.g. rural/urban OR age), which is the grain CMS
publishes for every state. Report: reports/data_quality.md and reports/data_quality.json.
"""
from __future__ import annotations

import json

import pandas as pd

from paths import CLEAN_FILE, RAW_FILE, REPORTS, ROOT

EXPECTED_COLUMNS = ["Year", "quarter", "Bene_Geo_Desc", "Bene_Mdcd_Mdcr_Enrl_Stus", "Bene_Race_Desc",
                    "Bene_Sex_Desc", "Bene_Mdcr_Entlmt_Stus", "Bene_Age_Desc", "Bene_RUCA_Desc",
                    "Total_Bene_TH_Elig", "Total_PartB_Enrl", "Total_Bene_Telehealth", "Pct_Telehealth"]

# raw column -> tidy dimension name
DIMENSIONS = {"Bene_RUCA_Desc": "rurality", "Bene_Age_Desc": "age", "Bene_Race_Desc": "race",
              "Bene_Mdcd_Mdcr_Enrl_Stus": "dual_status", "Bene_Sex_Desc": "sex",
              "Bene_Mdcr_Entlmt_Stus": "entitlement"}

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District Of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}
TERRITORIES = {"Puerto Rico": "PR", "Virgin Islands": "VI", "Territories": "TERR"}
OTHER = {"National": "US", "Missing Data": "MISSING"}


def geo_type(name: str) -> str:
    if name in STATES:
        return "state"  # 50 states + DC
    if name in TERRITORIES:
        return "territory"
    return {"National": "national"}.get(name, "missing")


def check(results: list, name: str, passed: bool, detail: str, severity: str = "error") -> None:
    results.append({"check": name, "passed": bool(passed), "severity": severity if not passed else "ok",
                    "detail": detail})


def run() -> pd.DataFrame:
    raw = pd.read_csv(RAW_FILE, dtype={"quarter": str})
    dq: list[dict] = []

    # 1. schema
    check(dq, "schema", list(raw.columns) == EXPECTED_COLUMNS, f"{len(raw.columns)} columns: {list(raw.columns)}")
    # 2. geographies
    expected_geos = set(STATES) | set(TERRITORIES) | set(OTHER)
    found = set(raw.Bene_Geo_Desc.unique())
    check(dq, "geographies", found == expected_geos,
          f"{len(found)} geographies (50 states + DC, PR, VI, other territories, National, Missing Data); "
          f"unexpected={sorted(found - expected_geos)} absent={sorted(expected_geos - found)}")
    # 3. unique key
    key = ["Year", "quarter", "Bene_Geo_Desc", *DIMENSIONS]
    dups = int(raw.duplicated(key).sum())
    check(dq, "unique key", dups == 0, f"{dups} duplicate rows on {key}")
    # 4. every geography has every period
    periods = raw.groupby("Bene_Geo_Desc")[["Year", "quarter"]].apply(lambda g: len(g.drop_duplicates()))
    check(dq, "period coverage", periods.nunique() == 1,
          f"each geography has {sorted(int(x) for x in periods.unique())} distinct periods "
          f"({raw.Year.min()}-{raw.Year.max()}, quarters 1-4 plus annual 'Overall')")

    d = raw.copy()
    d["n_split"] = (d[list(DIMENSIONS)] != "All").sum(axis=1)
    # 5. suppressed / missing values
    miss = d[d.Pct_Telehealth.isna()]
    by = miss.assign(seg=miss.Bene_RUCA_Desc.where(miss.Bene_RUCA_Desc != "All", miss.Bene_Race_Desc)) \
             .seg.value_counts().to_dict()
    check(dq, "suppressed cells", True,
          f"{len(miss):,} of {len(d):,} rows have no rate (suppressed or not applicable). "
          f"Mostly 'Unknown' rural/urban and 'Other/Unknown' race: {by}", "info")
    v = d.dropna(subset=["Pct_Telehealth"])
    # 6. rate range
    check(dq, "rate within 0-1", v.Pct_Telehealth.between(0, 1).all(),
          f"min={v.Pct_Telehealth.min():.4f} max={v.Pct_Telehealth.max():.4f}")
    # 7. users <= eligible
    bad = v[v.Total_Bene_Telehealth > v.Total_Bene_TH_Elig]
    check(dq, "users <= eligible", bad.empty, f"{len(bad)} rows where telehealth users exceed eligible users")
    # 8. published rate matches users / eligible
    err = (v.Total_Bene_Telehealth / v.Total_Bene_TH_Elig - v.Pct_Telehealth).abs()
    check(dq, "rate = users / eligible", err.max() <= 0.0001,
          f"max absolute difference {err.max():.6f} (CMS rounds to 4 decimals)")
    # 9. states add up to national
    allrows = d[d.n_split == 0]
    nat = allrows[allrows.Bene_Geo_Desc == "National"].set_index(["Year", "quarter"]).Total_Bene_TH_Elig
    sub = allrows[allrows.Bene_Geo_Desc != "National"].groupby(["Year", "quarter"]).Total_Bene_TH_Elig.sum()
    ratio = (sub / nat).dropna()
    check(dq, "states sum to national", ratio.between(0.99, 1.01).all(),
          f"sum of geographies / national eligible users ranges {ratio.min():.4f}-{ratio.max():.4f}")
    # 10. denominator jumps (warning only): eligible users changing >20% vs prior quarter
    q = allrows[(allrows.quarter != "Overall") & allrows.Bene_Geo_Desc.isin(STATES)].copy()
    q["idx"] = q.Year * 10 + q.quarter.astype(int)
    q = q.sort_values(["Bene_Geo_Desc", "idx"])
    q["chg"] = q.groupby("Bene_Geo_Desc").Total_Bene_TH_Elig.pct_change()
    jumps = q[q.chg.abs() > 0.20]
    jump_list = [f"{r.Bene_Geo_Desc} {r.Year}-Q{r.quarter} ({r.chg:+.0%})" for r in jumps.itertuples()]
    check(dq, "eligible-user jumps >20% q/q", jumps.empty,
          f"{len(jumps)} state-quarters: {jump_list}. Kept as published; treat with care.", "warning")

    # tidy: keep the one-characteristic-at-a-time grain
    t = d[d.n_split <= 1].copy()
    t["dimension"], t["segment"] = "all", "All"
    for col, dim in DIMENSIONS.items():
        m = t[col] != "All"
        t.loc[m, "dimension"], t.loc[m, "segment"] = dim, t.loc[m, col]
    t["geo"] = t.Bene_Geo_Desc.replace({"District Of Columbia": "District of Columbia"})
    t["geo_code"] = t.Bene_Geo_Desc.map({**STATES, **TERRITORIES, **OTHER})
    t["geo_type"] = t.Bene_Geo_Desc.map(geo_type)
    t["period_type"] = t.quarter.map(lambda s: "annual" if s == "Overall" else "quarter")
    t["quarter_num"] = pd.to_numeric(t.quarter, errors="coerce").fillna(0).astype(int)
    t["period"] = t.apply(lambda r: f"{r.Year}" if r.quarter_num == 0 else f"{r.Year}-Q{r.quarter_num}", axis=1)
    t["period_idx"] = t.Year * 10 + t.quarter_num
    t = t.rename(columns={"Year": "year", "Total_Bene_TH_Elig": "eligible_users",
                          "Total_Bene_Telehealth": "telehealth_users", "Total_PartB_Enrl": "partb_enrollees",
                          "Pct_Telehealth": "pct_telehealth"})
    cols = ["geo", "geo_code", "geo_type", "year", "quarter_num", "period", "period_idx", "period_type",
            "dimension", "segment", "eligible_users", "telehealth_users", "partb_enrollees", "pct_telehealth"]
    t = t[cols].sort_values(["geo_code", "period_idx", "dimension", "segment"]).reset_index(drop=True)
    check(dq, "tidy key unique", not t.duplicated(["geo_code", "period", "dimension", "segment"]).any(),
          f"{len(t):,} tidy rows, {t.geo_code.nunique()} geographies, {t.period.nunique()} periods")
    dropped = int((d.n_split > 1).sum())
    check(dq, "cross-tab rows excluded", True,
          f"{dropped:,} national-only rows that cross two characteristics (e.g. dual status x age) are not "
          f"used, because states are only published one characteristic at a time", "info")

    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(CLEAN_FILE, index=False)
    write_report(dq, raw, t)
    errors = [c for c in dq if c["severity"] == "error"]
    print(f"[clean] {len(t):,} tidy rows -> {CLEAN_FILE.relative_to(ROOT)}; "
          f"{sum(c['passed'] for c in dq)}/{len(dq)} checks passed, {len(errors)} errors")
    if errors:
        raise SystemExit(f"[clean] data-quality errors: {errors}")
    return t


def write_report(dq: list[dict], raw: pd.DataFrame, t: pd.DataFrame) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "data_quality.json").write_text(json.dumps(dq, indent=2))
    icon = {"ok": "PASS", "info": "INFO", "warning": "WARN", "error": "FAIL"}
    lines = ["# Data-quality report", "",
             f"Source file: `{RAW_FILE.name}` ({len(raw):,} rows x {len(raw.columns)} columns). "
             f"Clean output: {len(t):,} rows.", "",
             "| Result | Check | Detail |", "|---|---|---|"]
    lines += [f"| {icon[c['severity']]} | {c['check']} | {c['detail']} |" for c in dq]
    (REPORTS / "data_quality.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    run()
