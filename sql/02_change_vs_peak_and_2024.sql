-- How far each geography has come down from its 2020 pandemic peak quarter, and how the
-- latest quarter compares with the same quarter of 2024 (same season, so no seasonal bias).
WITH latest AS (SELECT period_idx FROM latest_quarter),
peak AS (
    SELECT geo_code, period AS peak_period, pct_telehealth AS peak_pct
    FROM (SELECT geo_code, period, pct_telehealth,
                 ROW_NUMBER() OVER (PARTITION BY geo_code ORDER BY pct_telehealth DESC) AS rn
          FROM quarterly_all WHERE year = 2020)
    WHERE rn = 1),
cur AS (SELECT q.* FROM quarterly_all q, latest WHERE q.period_idx = latest.period_idx),
y2024 AS (SELECT q.geo_code, q.pct_telehealth AS pct_2024
          FROM quarterly_all q, latest WHERE q.period_idx = 2024 * 10 + latest.period_idx % 10)
SELECT cur.geo_code, cur.geo, cur.geo_type,
       peak.peak_period,
       ROUND(peak.peak_pct * 100, 1)                                   AS peak_pct,
       ROUND(y2024.pct_2024 * 100, 1)                                  AS same_qtr_2024_pct,
       cur.period                                                      AS latest_period,
       ROUND(cur.pct_telehealth * 100, 1)                              AS latest_pct,
       ROUND((cur.pct_telehealth - peak.peak_pct) * 100, 1)            AS pp_vs_peak,
       ROUND(cur.pct_telehealth / peak.peak_pct * 100, 0)              AS pct_of_peak_retained,
       ROUND((cur.pct_telehealth - y2024.pct_2024) * 100, 1)           AS pp_vs_2024
FROM cur JOIN peak USING (geo_code) LEFT JOIN y2024 USING (geo_code)
WHERE cur.geo_type IN ('state', 'national')
ORDER BY pct_of_peak_retained DESC;
