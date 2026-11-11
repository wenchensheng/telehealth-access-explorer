# Data-quality report

Source file: `TMEDTREND_PUBLIC_260914.csv` (37,324 rows x 13 columns). Clean output: 33,976 rows.

| Result | Check | Detail |
|---|---|---|
| PASS | schema | 13 columns: ['Year', 'quarter', 'Bene_Geo_Desc', 'Bene_Mdcd_Mdcr_Enrl_Stus', 'Bene_Race_Desc', 'Bene_Sex_Desc', 'Bene_Mdcr_Entlmt_Stus', 'Bene_Age_Desc', 'Bene_RUCA_Desc', 'Total_Bene_TH_Elig', 'Total_PartB_Enrl', 'Total_Bene_Telehealth', 'Pct_Telehealth'] |
| PASS | geographies | 56 geographies (50 states + DC, PR, VI, other territories, National, Missing Data); unexpected=[] absent=[] |
| PASS | unique key | 0 duplicate rows on ['Year', 'quarter', 'Bene_Geo_Desc', 'Bene_RUCA_Desc', 'Bene_Age_Desc', 'Bene_Race_Desc', 'Bene_Mdcd_Mdcr_Enrl_Stus', 'Bene_Sex_Desc', 'Bene_Mdcr_Entlmt_Stus'] |
| PASS | period coverage | each geography has [31] distinct periods (2020-2026, quarters 1-4 plus annual 'Overall') |
| PASS | suppressed cells | 4,026 of 37,324 rows have no rate (suppressed or not applicable). Mostly 'Unknown' rural/urban and 'Other/Unknown' race: {'Other/Unknown': 1953, 'Unknown': 1860, 'American Indian/Alaska Native': 88, 'Rural': 62, 'Urban': 31, 'All': 31, 'Asian/Pacific Islander': 1} |
| PASS | rate within 0-1 | min=0.0000 max=0.8202 |
| PASS | users <= eligible | 0 rows where telehealth users exceed eligible users |
| PASS | rate = users / eligible | max absolute difference 0.000050 (CMS rounds to 4 decimals) |
| PASS | states sum to national | sum of geographies / national eligible users ranges 0.9998-1.0000 |
| WARN | eligible-user jumps >20% q/q | 1 state-quarters: ['Vermont 2026-Q1 (+27%)']. Kept as published; treat with care. |
| PASS | tidy key unique | 33,976 tidy rows, 56 geographies, 31 periods |
| PASS | cross-tab rows excluded | 3,348 national-only rows that cross two characteristics (e.g. dual status x age) are not used, because states are only published one characteristic at a time |
