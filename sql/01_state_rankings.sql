-- State rankings for the latest quarter: telehealth use rate, rank among the 50 states + DC,
-- and difference from the national rate in percentage points.
WITH latest AS (SELECT period_idx FROM latest_quarter),
nat AS (SELECT pct_telehealth AS us_pct FROM quarterly_all, latest
        WHERE quarterly_all.period_idx = latest.period_idx AND geo_code = 'US')
SELECT q.period,
       q.geo_code,
       q.geo,
       RANK() OVER (ORDER BY q.pct_telehealth DESC)        AS rank_high_to_low,
       ROUND(q.pct_telehealth * 100, 1)                    AS pct_telehealth,
       ROUND((q.pct_telehealth - nat.us_pct) * 100, 1)     AS pp_vs_national,
       CAST(q.eligible_users AS INTEGER)                   AS eligible_users,
       CAST(q.telehealth_users AS INTEGER)                 AS telehealth_users
FROM quarterly_all q, latest, nat
WHERE q.period_idx = latest.period_idx AND q.geo_type = 'state'
ORDER BY rank_high_to_low, q.geo;
