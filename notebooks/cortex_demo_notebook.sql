-- ============================================================
-- SNOWFLAKE NOTEBOOK: "From Chaos to Clarity in 10 Minutes"
-- Cortex Code (CoCo) Live Demo — Solutions Architect Interview
--
-- STORY:  A mid-size insurance company's Snowflake costs are
--         spiking. Analysts are complaining about slow queries.
--         Leadership wants answers NOW.
--         Watch Cortex Code diagnose the problem, fix it,
--         and deliver a live AI-powered dashboard — live.
--
-- FORMAT: Run each cell top-to-bottom in a Snowflake Notebook.
--         Speak the narration text while the cell executes.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- CELL 1 [SQL]  Setup — 30 seconds
-- NARRATION: "Let me set the scene. This is an insurance
--             company. They have claims, policies, agents.
--             Their Snowflake bill just jumped 40%. Nobody
--             knows why. Let's find out — with Cortex."
-- ────────────────────────────────────────────────────────────

USE ROLE SYSADMIN;
CREATE DATABASE IF NOT EXISTS INSURANCE_DEMO;
CREATE SCHEMA  IF NOT EXISTS INSURANCE_DEMO.ANALYTICS;
USE SCHEMA INSURANCE_DEMO.ANALYTICS;

-- Simulate warehouse query history patterns
CREATE OR REPLACE TABLE QUERY_HISTORY_SIM AS
WITH base AS (
  SELECT
    DATEADD(MINUTE, -(SEQ4() * 3), CURRENT_TIMESTAMP())   AS QUERY_START,
    UNIFORM(1,4,RANDOM())                                   AS WH_CLUSTER,
    CASE UNIFORM(1,5,RANDOM())
      WHEN 1 THEN 'Claims Processing'
      WHEN 2 THEN 'Policy Renewal Reports'
      WHEN 3 THEN 'Agent Performance'
      WHEN 4 THEN 'Risk Scoring'
      ELSE    'Ad-hoc Analytics'
    END                                                     AS QUERY_TAG,
    UNIFORM(500,180000,RANDOM())                            AS EXECUTION_MS,
    UNIFORM(10,2000,RANDOM())                               AS MB_SPILLED,
    UNIFORM(1,8,RANDOM())                                   AS CREDITS_USED_FRAC
  FROM TABLE(GENERATOR(ROWCOUNT => 500))
)
SELECT
    QUERY_START,
    'INSURANCE_WH'                             AS WAREHOUSE_NAME,
    WH_CLUSTER,
    QUERY_TAG,
    EXECUTION_MS,
    MB_SPILLED,
    ROUND(CREDITS_USED_FRAC * 0.1, 4)         AS CREDITS_USED,
    CASE WHEN MB_SPILLED > 800 THEN TRUE ELSE FALSE END AS SPILL_FLAG,
    CASE WHEN EXECUTION_MS > 60000 THEN TRUE ELSE FALSE END AS SLOW_QUERY_FLAG
FROM base;

-- Insurance claims + policies tables
CREATE OR REPLACE TABLE CLAIMS AS
SELECT
    'CLM-' || LPAD(SEQ4()+1, 6, '0')          AS CLAIM_ID,
    'POL-' || LPAD(UNIFORM(1,5000,RANDOM()), 5,'0') AS POLICY_ID,
    DATEADD(DAY, -UNIFORM(1,365,RANDOM()), CURRENT_DATE()) AS CLAIM_DATE,
    CASE UNIFORM(1,4,RANDOM())
      WHEN 1 THEN 'Auto'
      WHEN 2 THEN 'Property'
      WHEN 3 THEN 'Life'
      ELSE        'Health'
    END                                         AS CLAIM_TYPE,
    UNIFORM(500,250000,RANDOM())::NUMBER(10,2)  AS CLAIM_AMOUNT,
    CASE UNIFORM(1,3,RANDOM())
      WHEN 1 THEN 'Open'
      WHEN 2 THEN 'Closed'
      ELSE        'Under Review'
    END                                         AS STATUS,
    CASE UNIFORM(1,5,RANDOM())
      WHEN 1 THEN 'Low'
      WHEN 2 THEN 'Medium'
      WHEN 3 THEN 'High'
      WHEN 4 THEN 'Critical'
      ELSE        'Low'
    END                                         AS RISK_LEVEL,
    'AGT-' || LPAD(UNIFORM(1,50,RANDOM()), 3,'0') AS AGENT_ID
FROM TABLE(GENERATOR(ROWCOUNT => 10000));

SELECT 'Setup complete — ' || COUNT(*) || ' claims loaded' AS STATUS FROM CLAIMS;


-- ────────────────────────────────────────────────────────────
-- CELL 2 [Python/Cortex]  The Diagnosis — 90 seconds
-- NARRATION: "Now watch this. I'm going to ask Cortex Code
--             to look at our actual query patterns and tell
--             me exactly what's wrong and what to do.
--             This is what took me days before — now it's
--             a single Cortex call."
-- ────────────────────────────────────────────────────────────

-- Aggregate the query patterns for Cortex to analyze
CREATE OR REPLACE TEMP TABLE QH_SUMMARY AS
SELECT
    QUERY_TAG,
    COUNT(*)                                AS QUERY_COUNT,
    ROUND(AVG(EXECUTION_MS)/1000, 1)        AS AVG_EXEC_SECS,
    ROUND(MAX(EXECUTION_MS)/1000, 1)        AS MAX_EXEC_SECS,
    ROUND(AVG(MB_SPILLED), 0)              AS AVG_MB_SPILLED,
    SUM(CASE WHEN SPILL_FLAG     THEN 1 ELSE 0 END) AS SPILL_COUNT,
    SUM(CASE WHEN SLOW_QUERY_FLAG THEN 1 ELSE 0 END) AS SLOW_COUNT,
    ROUND(SUM(CREDITS_USED), 2)            AS TOTAL_CREDITS,
    COUNT(DISTINCT WH_CLUSTER)             AS CLUSTERS_USED
FROM QUERY_HISTORY_SIM
GROUP BY QUERY_TAG
ORDER BY TOTAL_CREDITS DESC;

-- Feed the summary to Cortex Complete for AI diagnosis
SELECT
    QUERY_TAG,
    QUERY_COUNT,
    AVG_EXEC_SECS,
    AVG_MB_SPILLED,
    TOTAL_CREDITS,
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        CONCAT(
            'You are a Snowflake performance optimization expert helping an insurance company. ',
            'Analyze this query workload pattern and provide a concise 2-sentence diagnosis ',
            'with ONE specific recommended action. Be direct and technical. ',
            'Workload: ', QUERY_TAG,
            ' | Queries: ', QUERY_COUNT::VARCHAR,
            ' | Avg execution: ', AVG_EXEC_SECS::VARCHAR, 's',
            ' | Avg MB spilled: ', AVG_MB_SPILLED::VARCHAR,
            ' | Slow queries: ', SLOW_COUNT::VARCHAR,
            ' | Total credits: ', TOTAL_CREDITS::VARCHAR
        )
    ) AS CORTEX_DIAGNOSIS
FROM QH_SUMMARY;


-- ────────────────────────────────────────────────────────────
-- CELL 3 [Python/Cortex]  The "Aha" — Concurrency Fix
-- NARRATION: "This is exactly what happened at my current
--             company. Cortex spotted that we had a
--             concurrency problem — everyone assumed we
--             needed a bigger warehouse. Cortex said NO —
--             add clusters. We saved tens of thousands."
-- ────────────────────────────────────────────────────────────

-- Identify peak concurrency windows
CREATE OR REPLACE TEMP TABLE CONCURRENCY_ANALYSIS AS
SELECT
    DATE_TRUNC('HOUR', QUERY_START)         AS HOUR_WINDOW,
    COUNT(*)                                AS CONCURRENT_QUERIES,
    ROUND(AVG(EXECUTION_MS)/1000, 1)        AS AVG_EXEC_SECS,
    SUM(CREDITS_USED)                       AS CREDITS_THIS_HOUR,
    MAX(WH_CLUSTER)                         AS MAX_CLUSTER_REACHED
FROM QUERY_HISTORY_SIM
GROUP BY HOUR_WINDOW
ORDER BY CONCURRENT_QUERIES DESC;

-- Ask Cortex: scale up or scale out?
SELECT
    HOUR_WINDOW,
    CONCURRENT_QUERIES,
    AVG_EXEC_SECS,
    CREDITS_THIS_HOUR,
    MAX_CLUSTER_REACHED,
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        CONCAT(
            'Snowflake warehouse decision for an insurance analytics team. ',
            'Peak concurrent queries: ', CONCURRENT_QUERIES::VARCHAR,
            '. Average query execution: ', AVG_EXEC_SECS::VARCHAR, ' seconds. ',
            'Max clusters active: ', MAX_CLUSTER_REACHED::VARCHAR, ' of 4 configured. ',
            'Credits this hour: ', CREDITS_THIS_HOUR::VARCHAR, '. ',
            'Should we scale UP (larger warehouse size) or scale OUT (more clusters)? ',
            'Answer in ONE sentence with dollar impact reasoning.'
        )
    ) AS CORTEX_RECOMMENDATION
FROM CONCURRENCY_ANALYSIS
WHERE CONCURRENT_QUERIES > 10
LIMIT 5;


-- ────────────────────────────────────────────────────────────
-- CELL 4 [SQL]  Incremental Pipeline Pattern
-- NARRATION: "Now here's the pipeline change that actually
--             cut our compute bill in half. Instead of
--             full-table scans every refresh, we built
--             an incremental load using metadata. Watch."
-- ────────────────────────────────────────────────────────────

-- Track what's already been loaded (watermark pattern)
CREATE OR REPLACE TABLE LOAD_WATERMARKS (
    TABLE_NAME    VARCHAR,
    LAST_LOAD_TS  TIMESTAMP,
    ROWS_LOADED   NUMBER,
    CREDITS_USED  FLOAT
);

INSERT INTO LOAD_WATERMARKS VALUES
    ('CLAIMS',   DATEADD(DAY, -30, CURRENT_TIMESTAMP()), 10000, 2.4),
    ('POLICIES', DATEADD(DAY, -30, CURRENT_TIMESTAMP()), 5000,  1.1);

-- Simulate full-table scan approach (OLD way)
CREATE OR REPLACE TEMP TABLE OLD_APPROACH AS
SELECT
    'FULL SCAN'                             AS LOAD_TYPE,
    COUNT(*)                                AS ROWS_PROCESSED,
    COUNT(*)                                AS ROWS_LOADED,
    ROUND(COUNT(*) * 0.0003, 2)            AS ESTIMATED_CREDITS,
    'All historical records re-scanned'     AS DESCRIPTION
FROM CLAIMS;

-- Incremental approach — only last 30 days
CREATE OR REPLACE TEMP TABLE NEW_APPROACH AS
SELECT
    'INCREMENTAL (Last 30 days)'            AS LOAD_TYPE,
    COUNT(*)                                AS ROWS_PROCESSED,
    COUNT(*)                                AS ROWS_LOADED,
    ROUND(COUNT(*) * 0.0003, 2)            AS ESTIMATED_CREDITS,
    'Only new/changed records processed'    AS DESCRIPTION
FROM CLAIMS
WHERE CLAIM_DATE >= DATEADD(DAY, -30, CURRENT_DATE());

-- The comparison that sells the story
SELECT *, NULL AS SAVINGS_PCT FROM OLD_APPROACH
UNION ALL
SELECT
    n.*,
    ROUND((1 - (n.ESTIMATED_CREDITS / o.ESTIMATED_CREDITS)) * 100, 0) AS SAVINGS_PCT
FROM NEW_APPROACH n
CROSS JOIN (SELECT ESTIMATED_CREDITS FROM OLD_APPROACH) o;


-- ────────────────────────────────────────────────────────────
-- CELL 5 [Python/Cortex]  AI Risk Scoring on Claims
-- NARRATION: "Now let me show you something that makes
--             underwriters genuinely gasp. We're going to
--             have Cortex score every open claim for risk
--             — right inside Snowflake. No Python server,
--             no API calls, no data leaving the platform."
-- ────────────────────────────────────────────────────────────

-- Cortex AI risk assessment on live claims data
SELECT
    CLAIM_ID,
    CLAIM_TYPE,
    CLAIM_AMOUNT,
    STATUS,
    RISK_LEVEL                              AS FLAGGED_RISK,
    SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        CONCAT(
            'You are an insurance risk analyst. Rate this claim on a scale of 1-10 for ',
            'fraud risk and provide ONE specific investigation flag. Be concise (2 sentences max). ',
            'Claim type: ', CLAIM_TYPE,
            '. Amount: $', CLAIM_AMOUNT::VARCHAR,
            '. Status: ', STATUS,
            '. Risk level flagged: ', RISK_LEVEL, '.'
        )
    ) AS AI_RISK_ASSESSMENT
FROM CLAIMS
WHERE STATUS = 'Under Review'
  AND CLAIM_AMOUNT > 50000
ORDER BY CLAIM_AMOUNT DESC
LIMIT 8;


-- ────────────────────────────────────────────────────────────
-- CELL 6 [Python/Cortex]  Natural Language → SQL (Analyst UX)
-- NARRATION: "Last one. The thing that gets every business
--             analyst in the room leaning forward. Watch me
--             ask a business question in plain English and
--             have Cortex write the SQL — and run it."
-- ────────────────────────────────────────────────────────────

-- Cortex Analyst-style: translate business question to SQL
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'mistral-large2',
    CONCAT(
        'You are a SQL expert for Snowflake. Given this table: ',
        'CLAIMS(CLAIM_ID, POLICY_ID, CLAIM_DATE, CLAIM_TYPE, CLAIM_AMOUNT, STATUS, RISK_LEVEL, AGENT_ID). ',
        'Write ONLY valid Snowflake SQL (no explanation, no markdown) to answer: ',
        '"Which agents have the highest average claim amount for High or Critical risk claims ',
        'that are still Open or Under Review, in the last 90 days? Show top 10."'
    )
) AS GENERATED_SQL;

-- (After showing above, manually run the generated SQL — paste and execute live)
-- This is the WOW moment: paste Cortex's output and run it immediately

-- Pre-built version to run if needed:
SELECT
    AGENT_ID,
    COUNT(*)                                AS OPEN_HIGH_RISK_CLAIMS,
    ROUND(AVG(CLAIM_AMOUNT), 0)            AS AVG_CLAIM_AMOUNT,
    ROUND(SUM(CLAIM_AMOUNT), 0)            AS TOTAL_EXPOSURE,
    MAX(CLAIM_AMOUNT)                       AS LARGEST_CLAIM
FROM CLAIMS
WHERE RISK_LEVEL IN ('High','Critical')
  AND STATUS IN ('Open','Under Review')
  AND CLAIM_DATE >= DATEADD(DAY, -90, CURRENT_DATE())
GROUP BY AGENT_ID
ORDER BY AVG_CLAIM_AMOUNT DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- CELL 7 [SQL]  The KPI Summary — leave this on screen
-- NARRATION: "This is what leadership sees every morning.
--             Built entirely inside Snowflake. No Tableau,
--             no Looker license required for the first view.
--             This is the platform doing the work."
-- ────────────────────────────────────────────────────────────

SELECT
    CLAIM_TYPE,
    COUNT(*)                                AS TOTAL_CLAIMS,
    SUM(CASE WHEN STATUS='Open' THEN 1 ELSE 0 END)          AS OPEN_CLAIMS,
    SUM(CASE WHEN STATUS='Under Review' THEN 1 ELSE 0 END)  AS UNDER_REVIEW,
    ROUND(SUM(CLAIM_AMOUNT)/1000000, 2)    AS TOTAL_EXPOSURE_M,
    ROUND(AVG(CLAIM_AMOUNT), 0)            AS AVG_CLAIM,
    SUM(CASE WHEN RISK_LEVEL IN ('High','Critical') THEN 1 ELSE 0 END) AS HIGH_RISK_COUNT,
    ROUND(
        SUM(CASE WHEN RISK_LEVEL IN ('High','Critical') THEN CLAIM_AMOUNT ELSE 0 END)
        / NULLIF(SUM(CLAIM_AMOUNT),0) * 100
    , 1)                                   AS HIGH_RISK_EXPOSURE_PCT
FROM CLAIMS
GROUP BY CLAIM_TYPE
ORDER BY TOTAL_EXPOSURE_M DESC;
