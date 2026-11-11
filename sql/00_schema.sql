-- Tidy table loaded by src/build_db.py from data/processed/telehealth_clean.csv.
-- One row per geography x period x (dimension, segment). pct_telehealth = telehealth_users / eligible_users.
CREATE TABLE telehealth (
    geo              TEXT NOT NULL,    -- 'California', 'National', ...
    geo_code         TEXT NOT NULL,    -- 'CA', 'US', 'PR', ...
    geo_type         TEXT NOT NULL,    -- state (50 + DC) | territory | national | missing
    year             INTEGER NOT NULL,
    quarter_num      INTEGER NOT NULL, -- 1-4, 0 = full year
    period           TEXT NOT NULL,    -- '2026-Q1' or '2025'
    period_idx       INTEGER NOT NULL, -- year*10 + quarter, sortable
    period_type      TEXT NOT NULL,    -- quarter | annual
    dimension        TEXT NOT NULL,    -- all | rurality | age | race | dual_status | sex | entitlement
    segment          TEXT NOT NULL,
    eligible_users   REAL,             -- beneficiaries with >=1 telehealth-eligible service (in person or virtual)
    telehealth_users REAL,             -- beneficiaries with >=1 telehealth service (incl. audio-only)
    partb_enrollees  REAL,
    pct_telehealth   REAL,
    PRIMARY KEY (geo_code, period, dimension, segment)
);

-- Latest published quarter, used by most queries.
CREATE VIEW latest_quarter AS
SELECT MAX(period_idx) AS period_idx FROM telehealth WHERE period_type = 'quarter';

-- Headline rate (no breakdown) for every geography and quarter.
CREATE VIEW quarterly_all AS
SELECT geo, geo_code, geo_type, year, quarter_num, period, period_idx, eligible_users, telehealth_users, pct_telehealth
FROM telehealth WHERE period_type = 'quarter' AND dimension = 'all';
