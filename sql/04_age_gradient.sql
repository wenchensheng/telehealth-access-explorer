-- Telehealth use by age band, nationally and by state, for the latest quarter and the same
-- quarter of 2024. Under-65 Medicare beneficiaries qualify through disability or ESRD.
WITH latest AS (SELECT period_idx FROM latest_quarter)
SELECT t.geo_code, t.geo, t.period, t.segment AS age_band,
       ROUND(t.pct_telehealth * 100, 1)   AS pct_telehealth,
       CAST(t.eligible_users AS INTEGER)  AS eligible_users
FROM telehealth t, latest
WHERE t.dimension = 'age' AND t.geo_type IN ('state', 'national')
  AND t.period_idx IN (latest.period_idx, 2024 * 10 + latest.period_idx % 10)
ORDER BY t.geo_code = 'US' DESC, t.geo_code, t.period_idx DESC, t.segment;
