-- Rural vs urban telehealth use by state in the latest quarter (rural/urban from the
-- beneficiary's ZIP code via RUCA). gap_pp > 0 means urban beneficiaries use telehealth more.
WITH latest AS (SELECT period_idx FROM latest_quarter),
ru AS (SELECT t.geo_code, t.geo, t.geo_type, t.period,
              MAX(CASE WHEN segment = 'Rural' THEN pct_telehealth END) AS rural,
              MAX(CASE WHEN segment = 'Urban' THEN pct_telehealth END) AS urban,
              MAX(CASE WHEN segment = 'Rural' THEN eligible_users END) AS rural_eligible
       FROM telehealth t, latest
       WHERE t.period_idx = latest.period_idx AND t.dimension = 'rurality'
       GROUP BY t.geo_code, t.geo, t.geo_type, t.period)
SELECT period, geo_code, geo,
       ROUND(rural * 100, 1)                AS rural_pct,
       ROUND(urban * 100, 1)                AS urban_pct,
       ROUND((urban - rural) * 100, 1)      AS gap_pp,
       ROUND(urban / rural, 2)              AS urban_to_rural_ratio,
       CAST(rural_eligible AS INTEGER)      AS rural_eligible_users
FROM ru
WHERE geo_type IN ('state', 'national') AND rural IS NOT NULL AND urban IS NOT NULL
ORDER BY gap_pp DESC;
