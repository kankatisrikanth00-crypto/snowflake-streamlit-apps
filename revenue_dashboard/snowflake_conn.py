"""
snowflake_conn.py  —  Snowflake connection helper
Set credentials in .env or Streamlit secrets (secrets.toml)
"""
import os
import pandas as pd
import streamlit as st

try:
    import snowflake.connector
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False


def get_connection():
    """Return a live Snowflake connection, or None if not configured."""
    if not SNOWFLAKE_AVAILABLE:
        return None
    try:
        creds = {
            "account":   st.secrets.get("snowflake", {}).get("account",   os.getenv("SF_ACCOUNT", "")),
            "user":      st.secrets.get("snowflake", {}).get("user",      os.getenv("SF_USER", "")),
            "password":  st.secrets.get("snowflake", {}).get("password",  os.getenv("SF_PASSWORD", "")),
            "warehouse": st.secrets.get("snowflake", {}).get("warehouse", os.getenv("SF_WAREHOUSE", "COMPUTE_WH")),
            "database":  st.secrets.get("snowflake", {}).get("database",  os.getenv("SF_DATABASE", "REVENUE_DB")),
            "schema":    st.secrets.get("snowflake", {}).get("schema",    os.getenv("SF_SCHEMA",   "ANALYTICS")),
        }
        if not creds["account"] or not creds["user"]:
            return None
        return snowflake.connector.connect(**creds)
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def load_revenue_data(_conn=None) -> pd.DataFrame:
    """
    Load DAILY_REVENUE from Snowflake if connected,
    otherwise return rich synthetic demo data.
    """
    if _conn is not None:
        try:
            cur = _conn.cursor()
            cur.execute("SELECT DATE, TENANT, REVENUE, BUDGET, WIN_THE_DAY FROM DAILY_REVENUE ORDER BY DATE")
            df = cur.fetch_pandas_all()
            df.columns = [c.upper() for c in df.columns]
            df["DATE"] = pd.to_datetime(df["DATE"])
            return df
        except Exception:
            pass

    # ── Synthetic fallback ──────────────────────────────────
    import numpy as np
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=730, freq="D")
    tenants = {
        "ALPHA": (45_000, 42_000, 1.12),
        "BETA":  (32_000, 30_000, 1.10),
        "GAMMA": (28_000, 27_000, 1.08),
        "DELTA": (19_000, 18_000, 1.15),
    }
    rows = []
    for t, (base_rev, base_bud, wtd_mult) in tenants.items():
        for i, d in enumerate(dates):
            trend = 1 + 0.0003 * i
            dow_adj = 0.47 if d.weekday() >= 5 else 1.0
            noise = 0.75 + 0.50 * rng.random()
            rev = round(base_rev * trend * noise * dow_adj, 2)
            bud = round(base_bud * (1 + 0.0002 * i), 2)
            wtd = round(bud * wtd_mult, 2)
            rows.append({"DATE": d, "TENANT": t, "REVENUE": rev, "BUDGET": bud, "WIN_THE_DAY": wtd})
    return pd.DataFrame(rows)
