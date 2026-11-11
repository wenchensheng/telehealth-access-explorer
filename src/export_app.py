"""Export a compact JSON file that the phone app (docs/) reads.

Shape: periods[] + per-geography arrays aligned to periods, so the app needs no server.
"""
from __future__ import annotations

import json

import pandas as pd

from paths import APP_JSON, ATLAS, CLEAN_FILE, CMS_PAGE, CMS_URL, REPORTS, ROOT

SEGMENT_ORDER = {
    "rurality": ["Rural", "Urban"],
    "age": ["0-64", "65-74", "75-84", "85 and over"],
    "race": ["American Indian/Alaska Native", "Asian/Pacific Islander", "Black/African American", "Hispanic",
             "Non-Hispanic White"],
    "dual_status": ["Medicare & Medicaid", "Medicare Only"],
    "sex": ["Female", "Male"],
    "entitlement": ["Aged", "Disabled", "ESRD"],
}


def _r(v, nd=4):
    return None if pd.isna(v) else round(float(v), nd)


def build_payload(findings: dict | None = None) -> dict:
    t = pd.read_csv(CLEAN_FILE)
    t = t[(t.period_type == "quarter") & (t.geo_type != "missing")]
    periods = t.sort_values("period_idx").period.drop_duplicates().tolist()
    atlas = json.loads(ATLAS.read_text())
    fips = {g["properties"]["name"]: g["id"] for g in atlas["objects"]["states"]["geometries"]}

    geos, series = [], {}
    for (code, name, gtype), g in t.groupby(["geo_code", "geo", "geo_type"]):
        geos.append({"code": code, "name": name, "type": gtype, "fips": fips.get(name)})
        a = g[g.dimension == "all"].set_index("period").reindex(periods)
        s = {"all": [_r(v) for v in a.pct_telehealth],
             "eligible": [None if pd.isna(v) else int(v) for v in a.eligible_users],
             "users": [None if pd.isna(v) else int(v) for v in a.telehealth_users]}
        for dim, segs in SEGMENT_ORDER.items():
            d = g[g.dimension == dim]
            s[dim] = {seg: [_r(v) for v in d[d.segment == seg].set_index("period").reindex(periods).pct_telehealth]
                      for seg in segs}
        series[code] = s
    order = {"national": 0, "state": 1, "territory": 2}
    geos.sort(key=lambda x: (order[x["type"]], x["name"]))
    dq = json.loads((REPORTS / "data_quality.json").read_text())
    return {
        "meta": {"title": "Medicare Telehealth Trends", "publisher": "Centers for Medicare & Medicaid Services",
                 "latest": periods[-1], "coverage": f"{periods[0]} to {periods[-1]}",
                 "dq_warnings": [c["detail"] for c in dq if c["severity"] == "warning"]},
        "periods": periods,
        "segments": SEGMENT_ORDER,
        "geos": geos,
        "series": series,
        "findings": (findings or {}).get("findings", []),
    }


def main(findings: dict | None = None) -> dict:
    payload = build_payload(findings)
    APP_JSON.parent.mkdir(parents=True, exist_ok=True)
    APP_JSON.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"[export] {len(payload['geos'])} geographies x {len(payload['periods'])} quarters -> "
          f"{APP_JSON.relative_to(ROOT)} ({APP_JSON.stat().st_size / 1024:.0f} KB)")
    return payload


if __name__ == "__main__":
    import findings as fnd
    main(fnd.main())
