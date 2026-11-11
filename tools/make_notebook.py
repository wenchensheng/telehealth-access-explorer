"""Generate notebooks/analysis.ipynb (unexecuted). run_all.py executes it in place."""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("# Medicare Telehealth Access: where virtual care stuck, and for whom\n\n"
       "**Business question:** after the pandemic surge, how much do Medicare patients still use telehealth, and "
       "which states and patient groups depend on it most? A health system leader can use the answers to size "
       "virtual capacity and decide whom to protect if telehealth rules change after December 31, 2027.\n\n"
       "**Data:** CMS [Medicare Telehealth Trends](https://data.cms.gov/summary-statistics-on-use-and-payments/"
       "medicare-medicaid-service-type-reports/medicare-telehealth-trends), public aggregate data, 2020 Q1 to "
       "2026 Q1, Medicare fee-for-service only. Rate = beneficiaries with a telehealth service / "
       "telehealth-eligible users. Every number below is computed from the SQLite database built by `run_all.py`."),
    code("import sys, json\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd().parent / 'src'))\n"
         "import pandas as pd, matplotlib.pyplot as plt\nimport build_db, findings\n"
         "from paths import REPORTS\n"
         "plt.rcParams.update({'figure.dpi': 110, 'axes.spines.top': False, 'axes.spines.right': False})\n"
         "TEAL, ORANGE, GREY = '#12806f', '#e07a1f', '#9aa8ae'\n"
         "con = build_db.connect()\nF = findings.compute()\nM = F['metrics']\nprint('Latest quarter:', F['latest_period'])"),
    md("## Data quality\nChecks run by `src/clean.py` before anything is analyzed (full report: `reports/data_quality.md`)."),
    code("dq = pd.DataFrame(json.loads((REPORTS / 'data_quality.json').read_text()))\n"
         "pd.set_option('display.max_colwidth', 120)\ndq[['severity', 'check', 'detail']]"),
    md("## 1. National trend: a surge, then a steady base"),
    code("nat = build_db.query('07_national_trend', con)\n"
         "fig, ax = plt.subplots(figsize=(8, 3.4))\n"
         "ax.plot(nat.period, nat.pct_telehealth, color=TEAL, lw=2.5, label='All')\n"
         "ax.plot(nat.period, nat.urban_pct, color=GREY, lw=1.5, label='Urban')\n"
         "ax.plot(nat.period, nat.rural_pct, color=ORANGE, lw=1.5, label='Rural')\n"
         "ax.set_xticks(range(0, len(nat), 4), nat.period[::4]); ax.set_ylabel('% of eligible users'); ax.legend(frameon=False)\n"
         "ax.set_title('Medicare FFS beneficiaries with a telehealth service, by quarter'); plt.show()\n"
         "peak = nat.loc[nat.pct_telehealth.idxmax()]\n"
         "print(f\"Peak {peak.pct_telehealth}% in {peak.period}; latest {nat.pct_telehealth.iloc[-1]}% in {nat.period.iloc[-1]}\")\n"
         "print('2023 onward range:', nat[nat.year >= 2023].pct_telehealth.min(), '-', nat[nat.year >= 2023].pct_telehealth.max())"),
    md("## 2. State rankings: a fourfold spread"),
    code("rk = build_db.query('01_state_rankings', con)\n"
         "show = pd.concat([rk.head(8), rk.tail(8)])\n"
         "fig, ax = plt.subplots(figsize=(8, 4.6))\n"
         "ax.barh(show.geo[::-1], show.pct_telehealth[::-1], color=[TEAL if r <= 8 else ORANGE for r in show.rank_high_to_low[::-1]])\n"
         "us = nat.pct_telehealth.iloc[-1]; ax.axvline(us, color='k', ls='--', lw=1); ax.text(us, -1.2, f' US {us}%', fontsize=9)\n"
         "ax.set_xlabel('% of eligible users'); ax.set_title(f\"Highest and lowest 8 states, {rk.period.iloc[0]}\"); plt.show()\n"
         "print(f\"{rk.geo.iloc[0]} {rk.pct_telehealth.iloc[0]}% vs {rk.geo.iloc[-1]} {rk.pct_telehealth.iloc[-1]}% \"\n"
         "      f\"= {M['geography']['ratio']:.1f}x; {M['geography']['n_above_national']} of 51 above national\")"),
    code("chg = build_db.query('02_change_vs_peak_and_2024', con)\n"
         "chg[['geo', 'peak_period', 'peak_pct', 'same_qtr_2024_pct', 'latest_pct', 'pct_of_peak_retained', 'pp_vs_2024']].head(10)"),
    md("## 3. Rural vs urban gap by state"),
    code("ru = build_db.query('03_rural_urban_gap', con)\nst = ru[ru.geo_code != 'US']\n"
         "fig, ax = plt.subplots(figsize=(5.5, 5.5))\n"
         "ax.scatter(st.rural_pct, st.urban_pct, color=TEAL, s=28)\n"
         "lim = [0, max(st.urban_pct.max(), st.rural_pct.max()) + 2]; ax.plot(lim, lim, color=GREY, ls='--', lw=1)\n"
         "for r in st.nlargest(5, 'gap_pp').itertuples(): ax.annotate(r.geo_code, (r.rural_pct, r.urban_pct), xytext=(4, 2), textcoords='offset points', fontsize=8)\n"
         "ax.set_xlabel('Rural %'); ax.set_ylabel('Urban %'); ax.set_title('States above the line: urban > rural'); plt.show()\n"
         "print(f\"Rural lower than urban in {(st.gap_pp > 0).sum()} of {len(st)} states; national gap {ru[ru.geo_code=='US'].gap_pp.iloc[0]} pts\")\n"
         "st.head(5)"),
    md("## 4. Age gradient: under-65 (disability/ESRD) beneficiaries lead"),
    code("ag = build_db.query('04_age_gradient', con)\nn = ag[ag.geo_code == 'US'].pivot(index='age_band', columns='period', values='pct_telehealth')\n"
         "ax = n.plot.bar(figsize=(7, 3.2), color=[GREY, TEAL], rot=0); ax.set_ylabel('% of eligible users')\n"
         "ax.set_title('National telehealth use by age band'); ax.legend(frameon=False); plt.show()\nn"),
    md("## 5. Equity: dual status and race/ethnicity"),
    code("ds = build_db.query('06_equity_dual_status', con)\nrace = build_db.query('05_equity_race_ethnicity', con)\n"
         "fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2))\nusd = ds[ds.geo_code == 'US'].iloc[0]\n"
         "a1.bar(['Dual-eligible', 'Medicare only'], [usd.dual_pct, usd.medicare_only_pct], color=[TEAL, GREY]); a1.set_title('Dual status (national)')\n"
         "lat = race[race.period == race.period.max()]\n"
         "a2.barh(lat.race_ethnicity[::-1], lat.pct_telehealth[::-1], color=TEAL); a2.set_title('Race/ethnicity (national)')\nplt.tight_layout(); plt.show()\n"
         "print(f\"Dual-eligible higher than Medicare-only in {(ds[ds.geo_code!='US'].gap_pp > 0).sum()} of {len(ds)-1} states\")\nrace"),
    md("## Findings for a health system leader\nGenerated by `src/findings.py` from the same database; the app's Insights tab and the README use this exact text."),
    code("from IPython.display import Markdown\n"
         "Markdown('\\n\\n'.join(f\"**{i}. {f['title']}** ({f['stat']} {f['stat_label']})\\n\\n{f['text']}\\n\\n*So what:* {f['so_what']}\" "
         "for i, f in enumerate(F['findings'], 1)))"),
    code("# Cross-check: the SQL outputs agree with the findings module\n"
         "assert abs(nat.pct_telehealth.iloc[-1] - M['plateau']['latest'] * 100) < 0.051\n"
         "assert rk.geo.iloc[0] == M['geography']['top_state'] and rk.geo.iloc[-1] == M['geography']['bottom_state']\n"
         "assert (st.gap_pp > 0).sum() == M['rural']['n_rural_lower']\n"
         "assert abs(usd.dual_pct - M['equity']['dual'] * 100) < 0.051\n"
         "print('All cross-checks passed')"),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
out = ROOT / "notebooks" / "analysis.ipynb"
nbf.write(nb, out)
print(f"[notebook] wrote {out.relative_to(ROOT)}")
