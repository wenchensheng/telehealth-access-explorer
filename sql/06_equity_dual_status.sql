-- Dual-eligible (Medicare & Medicaid) vs Medicare-only beneficiaries by state, latest quarter.
-- Dual eligibility is a common proxy for low income.
WITH latest AS (SELECT period_idx FROM latest_quarter),
ds AS (SELECT t.geo_code, t.geo, t.geo_type, t.period,
              MAX(CASE WHEN segment = 'Medicare & Medicaid' THEN pct_telehealth END) AS dual,
              MAX(CASE WHEN segment = 'Medicare Only' THEN pct_telehealth END)       AS medicare_only
       FROM telehealth t, latest
       WHERE t.period_idx = latest.period_idx AND t.dimension = 'dual_status'
       GROUP BY t.geo_code, t.geo, t.geo_type, t.period)
SELECT period, geo_code, geo,
       ROUND(dual * 100, 1)                    AS dual_pct,
       ROUND(medicare_only * 100, 1)           AS medicare_only_pct,
       ROUND((dual - medicare_only) * 100, 1)  AS gap_pp,
       ROUND(dual / medicare_only, 2)          AS dual_to_medicare_only_ratio
FROM ds
WHERE geo_type IN ('state', 'national') AND dual IS NOT NULL AND medicare_only IS NOT NULL
ORDER BY gap_pp DESC;
