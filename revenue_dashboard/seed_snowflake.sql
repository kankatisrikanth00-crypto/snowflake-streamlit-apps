-- ============================================================
-- REVENUE DASHBOARD - Snowflake Seed Script
-- Run this in your Snowflake worksheet to create dummy data
-- ============================================================

USE ROLE SYSADMIN;
CREATE DATABASE IF NOT EXISTS REVENUE_DB;
CREATE SCHEMA IF NOT EXISTS REVENUE_DB.ANALYTICS;
USE SCHEMA REVENUE_DB.ANALYTICS;

-- ── Daily Revenue Table ─────────────────────────────────────
CREATE OR REPLACE TABLE DAILY_REVENUE (
    DATE        DATE,
    TENANT      VARCHAR(10),   -- ALPHA | BETA | GAMMA | DELTA
    REVENUE     NUMBER(12,2),
    BUDGET      NUMBER(12,2),
    WIN_THE_DAY NUMBER(12,2)   -- stretch / aspirational target
);

-- ── Seed 2 years of data for 4 tenants ─────────────────────
INSERT INTO DAILY_REVENUE
WITH
  dates AS (
    SELECT DATEADD(DAY, SEQ4(), '2023-01-01') AS dt
    FROM TABLE(GENERATOR(ROWCOUNT => 730))
    WHERE dt <= CURRENT_DATE
  ),
  tenants AS (
    SELECT 'ALPHA' AS tenant, 45000 AS base_rev, 42000 AS base_bud, 1.12 AS wtd_mult UNION ALL
    SELECT 'BETA',  32000, 30000, 1.10 UNION ALL
    SELECT 'GAMMA', 28000, 27000, 1.08 UNION ALL
    SELECT 'DELTA', 19000, 18000, 1.15
  )
SELECT
    d.dt                                                    AS DATE,
    t.tenant                                                AS TENANT,
    ROUND(
        t.base_rev
        * (1 + 0.0003 * DATEDIFF(DAY, '2023-01-01', d.dt))  -- growth trend
        * (0.75 + 0.50 * UNIFORM(0::FLOAT, 1::FLOAT, RANDOM())) -- daily variation
        * CASE DAYOFWEEK(d.dt) WHEN 1 THEN 0.45 WHEN 7 THEN 0.50 ELSE 1.0 END -- weekend dip
    , 2)                                                    AS REVENUE,
    ROUND(
        t.base_bud
        * (1 + 0.0002 * DATEDIFF(DAY, '2023-01-01', d.dt))
    , 2)                                                    AS BUDGET,
    ROUND(
        t.base_bud
        * (1 + 0.0002 * DATEDIFF(DAY, '2023-01-01', d.dt))
        * t.wtd_mult
    , 2)                                                    AS WIN_THE_DAY
FROM dates d
CROSS JOIN tenants t;

-- Verify
SELECT TENANT, COUNT(*) AS days, SUM(REVENUE) AS total_rev
FROM DAILY_REVENUE
GROUP BY TENANT
ORDER BY TENANT;
