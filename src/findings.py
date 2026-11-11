"""Compute the headline findings from the SQLite database.

Every number in the README, the notebook and the app's Insights tab comes from here,
so the text can never drift from the data. Output: reports/findings.json and .md.
"""
from __future__ import annotations

import json
import sqlite3

import pandas as pd

from paths import DB_FILE, REPORTS, ROOT


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def pp(x: float) -> str:
    return f"{x * 100:+.1f} pts"


def load(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM telehealth WHERE period_type = 'quarter'", con)


def compute(db=DB_FILE) -> dict:
    con = sqlite3.connect(db)
    t = load(con)
    con.close()
    latest_idx = int(t.period_idx.max())
    latest = t.loc[t.period_idx == latest_idx, "period"].iloc[0]
    same24 = f"2024-Q{latest_idx % 10}"
    allq = t[t.dimension == "all"]
    nat = allq[allq.geo_code == "US"].set_index("period").pct_telehealth
    nat_idx = allq[allq.geo_code == "US"].set_index("period").period_idx

    def seg(geo, dim, period=latest):
        s = t[(t.geo_code == geo) & (t.dimension == dim) & (t.period == period)]
        return s.set_index("segment").pct_telehealth

    # F1 national plateau
    peak_period = nat.idxmax()
    recent = nat[nat_idx >= 20231]
    since = nat[nat_idx > 20201]
    low_period = since.idxmin()
    f1 = dict(peak_period=peak_period, peak=nat[peak_period], latest=nat[latest], same_qtr_2024=nat[same24],
              retained=nat[latest] / nat[peak_period], recent_min=recent.min(), recent_max=recent.max(),
              recent_min_period=recent.idxmin(), low_period=low_period, low=since.min(),
              users_latest=float(allq[(allq.geo_code == "US") & (allq.period == latest)].telehealth_users.iloc[0]))

    # F2 geography
    st = allq[(allq.geo_type == "state") & (allq.period == latest)].sort_values("pct_telehealth", ascending=False)
    top, bot = st.iloc[0], st.iloc[-1]
    f2 = dict(top_state=top.geo, top=top.pct_telehealth, bottom_state=bot.geo, bottom=bot.pct_telehealth,
              ratio=top.pct_telehealth / bot.pct_telehealth, n_states=len(st),
              n_above_national=int((st.pct_telehealth > nat[latest]).sum()),
              top5=st.head(5).geo.tolist(), bottom5=st.tail(5).geo.tolist()[::-1])

    # F3 rural-urban
    ru = t[(t.dimension == "rurality") & (t.period == latest) & (t.geo_type == "state")] \
        .pivot(index="geo", columns="segment", values="pct_telehealth").dropna(subset=["Rural", "Urban"])
    ru["gap"] = ru.Urban - ru.Rural
    nru = seg("US", "rurality")
    f3 = dict(rural=nru["Rural"], urban=nru["Urban"], gap=nru["Urban"] - nru["Rural"],
              ratio=nru["Urban"] / nru["Rural"], n_states=len(ru), n_rural_lower=int((ru.gap > 0).sum()),
              largest_gap_state=ru.gap.idxmax(), largest_gap=ru.gap.max(),
              largest_gap_rural=ru.loc[ru.gap.idxmax(), "Rural"], largest_gap_urban=ru.loc[ru.gap.idxmax(), "Urban"])

    # F4 age / disability
    age, ent = seg("US", "age"), seg("US", "entitlement")
    f4 = dict(under65=age["0-64"], a65_74=age["65-74"], a75_84=age["75-84"], a85=age["85 and over"],
              ratio=age["0-64"] / age["65-74"], disabled=ent["Disabled"], aged=ent["Aged"], esrd=ent["ESRD"])

    # F5 equity: dual status and race/ethnicity
    ds, race = seg("US", "dual_status"), seg("US", "race").dropna()
    ds_st = t[(t.dimension == "dual_status") & (t.period == latest) & (t.geo_type == "state")] \
        .pivot(index="geo", columns="segment", values="pct_telehealth").dropna()
    race24 = seg("US", "race", same24).dropna()
    f5 = dict(dual=ds["Medicare & Medicaid"], medicare_only=ds["Medicare Only"],
              ratio=ds["Medicare & Medicaid"] / ds["Medicare Only"], n_states=len(ds_st),
              n_dual_higher=int((ds_st["Medicare & Medicaid"] > ds_st["Medicare Only"]).sum()),
              race_high=race.idxmax(), race_high_pct=race.max(), race_low=race.idxmin(), race_low_pct=race.min(),
              white=race["Non-Hispanic White"], race=race.round(4).to_dict(),
              race_change_vs_2024={k: round(race[k] - race24[k], 4) for k in race.index if k in race24})

    findings = [
        dict(id="plateau", title="Telehealth settled at a steady base, it did not disappear",
             stat=pct(f1["latest"]), stat_label=f"of eligible Medicare FFS users, {latest}",
             text=(f"National use peaked at {pct(f1['peak'])} in {f1['peak_period']}. Since 2023 it has held between "
                   f"{pct(f1['recent_min'])} and {pct(f1['recent_max'])} a quarter, and was {pct(f1['latest'])} in "
                   f"{latest} ({pp(f1['latest'] - f1['same_qtr_2024'])} vs {same24}), about "
                   f"{f1['users_latest'] / 1e6:.1f} million people. The low point since 2020 was {pct(f1['low'])} "
                   f"in {f1['low_period']}."),
             so_what=("Plan virtual capacity as a permanent, steady share of visits rather than a pandemic surge "
                      "that is still unwinding.")),
        dict(id="geography", title=f"Where a patient lives changes telehealth use by more than {int(f2['ratio'])}x",
             stat=f"{f2['ratio']:.1f}x", stat_label=f"{f2['top_state']} vs {f2['bottom_state']}",
             text=(f"In {latest}, {f2['top_state']} led at {pct(f2['top'])} and {f2['bottom_state']} was lowest at "
                   f"{pct(f2['bottom'])}. Only {f2['n_above_national']} of {f2['n_states']} states (incl. DC) beat "
                   f"the national rate. Highest: {', '.join(f2['top5'])}. Lowest: {', '.join(f2['bottom5'])}."),
             so_what=("Benchmark virtual share against your own state, not the national average, before setting "
                      "targets.")),
        dict(id="rural", title="Rural patients use telehealth less than urban patients",
             stat=pp(-f3["gap"]), stat_label="rural vs urban, national",
             text=(f"Nationally {pct(f3['rural'])} of rural vs {pct(f3['urban'])} of urban eligible users had a "
                   f"telehealth service in {latest}. Rural use was lower in {f3['n_rural_lower']} of "
                   f"{f3['n_states']} states with both groups reported (DC has no rural ZIP codes); the widest gap was "
                   f"{f3['largest_gap_state']} ({pct(f3['largest_gap_rural'])} rural vs "
                   f"{pct(f3['largest_gap_urban'])} urban)."),
             so_what=("Rural outreach needs more than a video link: audio-only options, broadband help and "
                      "scheduling support are where the gap can close.")),
        dict(id="age", title="Under-65 beneficiaries with disabilities are the heaviest users",
             stat=pct(f4["under65"]), stat_label="of under-65 eligible users",
             text=(f"Beneficiaries under 65 (Medicare through disability or ESRD) used telehealth at "
                   f"{pct(f4['under65'])}, {f4['ratio']:.1f}x the 65-74 rate ({pct(f4['a65_74'])}). Use edges down "
                   f"with age: {pct(f4['a75_84'])} at 75-84 and {pct(f4['a85'])} at 85+. By entitlement, "
                   f"Disabled {pct(f4['disabled'])}, ESRD {pct(f4['esrd'])}, Aged {pct(f4['aged'])}."),
             so_what=("Protect virtual access for patients with disabilities and ESRD first; they would feel any "
                      "policy rollback most.")),
        dict(id="equity", title=f"Dual-eligible (low-income) beneficiaries use telehealth {f5['ratio']:.1f}x as often as Medicare-only",
             stat=f"{f5['ratio']:.1f}x", stat_label="dual-eligible vs Medicare-only",
             text=(f"Dual-eligible (Medicare & Medicaid) beneficiaries used telehealth at {pct(f5['dual'])} vs "
                   f"{pct(f5['medicare_only'])} for Medicare-only, higher in {f5['n_dual_higher']} of "
                   f"{f5['n_states']} states. By race/ethnicity, {f5['race_high']} beneficiaries were highest at "
                   f"{pct(f5['race_high_pct'])} and {f5['race_low']} lowest at {pct(f5['race_low_pct'])} "
                   f"(Non-Hispanic White {pct(f5['white'])})."),
             so_what=("Track virtual share by payer and demographic group in clinic dashboards; a cut to telehealth "
                      "falls hardest on dual-eligible patients.")),
    ]
    return dict(latest_period=latest, same_quarter_2024=same24, findings=findings,
                metrics=dict(plateau=f1, geography=f2, rural=f3, age=f4, equity=f5))


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsonable(v) for v in o]
    if hasattr(o, "item"):
        o = o.item()
    return round(o, 6) if isinstance(o, float) else o


def main() -> dict:
    res = _jsonable(compute())
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "findings.json").write_text(json.dumps(res, indent=2))
    md = [f"# Key findings (CMS Medicare Telehealth Trends, latest quarter {res['latest_period']})", ""]
    for i, f in enumerate(res["findings"], 1):
        md += [f"## {i}. {f['title']}", "", f"**{f['stat']}** {f['stat_label']}", "", f["text"], "",
               f"*So what:* {f['so_what']}", ""]
    (REPORTS / "findings.md").write_text("\n".join(md))
    print(f"[findings] {len(res['findings'])} findings -> {(REPORTS / 'findings.md').relative_to(ROOT)}")
    return res


if __name__ == "__main__":
    main()
