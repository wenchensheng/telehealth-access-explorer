-- National quarterly trend, with rural and urban rates side by side.
SELECT a.period, a.year, a.quarter_num,
       ROUND(a.pct_telehealth * 100, 1)                     AS pct_telehealth,
       CAST(a.telehealth_users AS INTEGER)                  AS telehealth_users,
       CAST(a.eligible_users AS INTEGER)                    AS eligible_users,
       ROUND(MAX(CASE WHEN r.segment = 'Rural' THEN r.pct_telehealth END) * 100, 1) AS rural_pct,
       ROUND(MAX(CASE WHEN r.segment = 'Urban' THEN r.pct_telehealth END) * 100, 1) AS urban_pct
FROM quarterly_all a
LEFT JOIN telehealth r ON r.geo_code = a.geo_code AND r.period = a.period AND r.dimension = 'rurality'
WHERE a.geo_code = 'US'
GROUP BY a.period, a.year, a.quarter_num, a.pct_telehealth, a.telehealth_users, a.eligible_users
ORDER BY a.period_idx;
