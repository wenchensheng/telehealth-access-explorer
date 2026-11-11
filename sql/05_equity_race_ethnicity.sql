-- Telehealth use by race/ethnicity (CMS RTI race code) nationally: latest quarter vs the
-- same quarter of 2024, and the gap to Non-Hispanic White beneficiaries.
WITH latest AS (SELECT period_idx FROM latest_quarter),
r AS (SELECT t.period_idx, t.period, t.segment, t.pct_telehealth, t.eligible_users
      FROM telehealth t, latest
      WHERE t.geo_code = 'US' AND t.dimension = 'race' AND t.pct_telehealth IS NOT NULL
        AND t.period_idx IN (latest.period_idx, 2024 * 10 + latest.period_idx % 10)),
w AS (SELECT period_idx, pct_telehealth AS white FROM r WHERE segment = 'Non-Hispanic White')
SELECT r.period, r.segment AS race_ethnicity,
       ROUND(r.pct_telehealth * 100, 1)              AS pct_telehealth,
       ROUND((r.pct_telehealth - w.white) * 100, 1)  AS pp_vs_white,
       CAST(r.eligible_users AS INTEGER)             AS eligible_users
FROM r JOIN w USING (period_idx)
ORDER BY r.period_idx DESC, r.pct_telehealth DESC;
