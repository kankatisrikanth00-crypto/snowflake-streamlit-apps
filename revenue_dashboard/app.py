"""
Revenue Dashboard  —  app.py
Run:  streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import date, timedelta
from snowflake_conn import get_connection, load_revenue_data

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Revenue Command Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme / CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}
.stApp {
    background: #0a0d14;
    color: #e8eaf0;
}
section[data-testid="stSidebar"] {
    background: #0f1320;
    border-right: 1px solid #1e2540;
}
section[data-testid="stSidebar"] * { color: #b0b8d0 !important; }

/* KPI cards */
.kpi-row { display: flex; gap: 16px; margin-bottom: 8px; }
.kpi-card {
    flex: 1;
    background: linear-gradient(135deg, #111827 0%, #0f1823 100%);
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: var(--accent);
}
.kpi-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #6b7599;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 800;
    color: #e8eaf0;
    line-height: 1;
    margin-bottom: 6px;
}
.kpi-delta {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
}
.delta-pos { color: #34d399; }
.delta-neg { color: #f87171; }
.delta-neu { color: #94a3b8; }

/* Tenant badge */
.tenant-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: 'DM Mono', monospace;
}
/* Section headers */
.section-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #6b7599;
    margin: 24px 0 12px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #1e2540;
}
/* Demo banner */
.demo-banner {
    background: linear-gradient(90deg, #1e2d1a, #1a2a1a);
    border: 1px solid #2d4a2d;
    border-radius: 8px;
    padding: 10px 16px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: #5a9a5a;
    margin-bottom: 16px;
}
/* Plotly container */
[data-testid="stPlotlyChart"] {
    border-radius: 12px;
    overflow: hidden;
}
div[data-baseweb="select"] > div { background: #111827 !important; border-color: #1e2540 !important; }
</style>
""", unsafe_allow_html=True)

# ── Tenant palette ───────────────────────────────────────────
TENANT_COLORS = {
    "ALPHA": "#60a5fa",   # blue
    "BETA":  "#a78bfa",   # violet
    "GAMMA": "#34d399",   # emerald
    "DELTA": "#fb923c",   # orange
}
TENANT_ACCENTS = {
    "ALPHA": "#1d4ed8",
    "BETA":  "#6d28d9",
    "GAMMA": "#059669",
    "DELTA": "#c2410c",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Syne, sans-serif", color="#8892b0", size=12),
    xaxis=dict(gridcolor="#1a2035", linecolor="#1e2540", tickcolor="#1e2540"),
    yaxis=dict(gridcolor="#1a2035", linecolor="#1e2540", tickcolor="#1e2540", tickprefix="$"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e2540", borderwidth=1),
    margin=dict(l=10, r=10, t=40, b=10),
    hoverlabel=dict(bgcolor="#111827", bordercolor="#1e2540", font_family="DM Mono"),
)

# ── Load data ────────────────────────────────────────────────
conn = get_connection()
df = load_revenue_data(conn)
is_demo = conn is None

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Revenue Command Center")
    st.markdown("---")

    # Tenant filter
    st.markdown("**TENANTS**")
    all_tenants = ["ALPHA", "BETA", "GAMMA", "DELTA"]
    selected_tenants = []
    for t in all_tenants:
        col1, col2 = st.columns([3, 1])
        checked = col1.checkbox(t, value=True, key=f"cb_{t}")
        col2.markdown(
            f'<span class="tenant-badge" style="background:{TENANT_COLORS[t]}22;color:{TENANT_COLORS[t]};border:1px solid {TENANT_COLORS[t]}44">●</span>',
            unsafe_allow_html=True
        )
        if checked:
            selected_tenants.append(t)

    st.markdown("---")
    st.markdown("**DATE RANGE**")
    min_date = df["DATE"].min().date()
    max_date = df["DATE"].max().date()

    preset = st.selectbox("Quick select", ["Last 30 days", "Last 90 days", "Last 6 months", "Last 12 months", "YTD", "All time"], index=1)
    today = max_date
    if preset == "Last 30 days":
        default_start = today - timedelta(days=30)
    elif preset == "Last 90 days":
        default_start = today - timedelta(days=90)
    elif preset == "Last 6 months":
        default_start = today - timedelta(days=182)
    elif preset == "Last 12 months":
        default_start = today - timedelta(days=365)
    elif preset == "YTD":
        default_start = date(today.year, 1, 1)
    else:
        default_start = min_date

    date_range = st.date_input(
        "Custom range",
        value=(default_start, today),
        min_value=min_date,
        max_value=max_date,
    )
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = default_start, today

    st.markdown("---")
    granularity = st.selectbox("Aggregation", ["Daily", "Weekly", "Monthly"], index=0)

    st.markdown("---")
    if is_demo:
        st.markdown('<div class="demo-banner">⚡ DEMO MODE<br>Running on synthetic data.<br>Connect Snowflake via secrets.toml</div>', unsafe_allow_html=True)
    else:
        st.success("✓ Connected to Snowflake")

# ── Filter ───────────────────────────────────────────────────
if not selected_tenants:
    selected_tenants = all_tenants

mask = (
    (df["DATE"] >= pd.Timestamp(start_date)) &
    (df["DATE"] <= pd.Timestamp(end_date)) &
    (df["TENANT"].isin(selected_tenants))
)
dff = df[mask].copy()

# ── Aggregate by granularity ─────────────────────────────────
def aggregate(df_in, gran):
    if gran == "Weekly":
        df_in = df_in.copy()
        df_in["PERIOD"] = df_in["DATE"].dt.to_period("W").dt.start_time
    elif gran == "Monthly":
        df_in = df_in.copy()
        df_in["PERIOD"] = df_in["DATE"].dt.to_period("M").dt.start_time
    else:
        df_in = df_in.copy()
        df_in["PERIOD"] = df_in["DATE"]
    return df_in.groupby(["PERIOD", "TENANT"])[["REVENUE", "BUDGET", "WIN_THE_DAY"]].sum().reset_index()

agg = aggregate(dff, granularity)
agg_all = agg.groupby("PERIOD")[["REVENUE", "BUDGET", "WIN_THE_DAY"]].sum().reset_index()

# ── KPI computation ──────────────────────────────────────────
total_rev  = dff["REVENUE"].sum()
total_bud  = dff["BUDGET"].sum()
total_wtd  = dff["WIN_THE_DAY"].sum()
rev_vs_bud = (total_rev / total_bud - 1) * 100 if total_bud else 0
rev_vs_wtd = (total_rev / total_wtd - 1) * 100 if total_wtd else 0

# Period-over-period delta
days_in_range = (end_date - start_date).days + 1
prev_start = start_date - timedelta(days=days_in_range)
prev_mask = (
    (df["DATE"] >= pd.Timestamp(prev_start)) &
    (df["DATE"] < pd.Timestamp(start_date)) &
    (df["TENANT"].isin(selected_tenants))
)
prev_rev = df[prev_mask]["REVENUE"].sum()
pop_delta = (total_rev / prev_rev - 1) * 100 if prev_rev else 0

best_tenant = dff.groupby("TENANT")["REVENUE"].sum().idxmax() if not dff.empty else "—"
best_rev    = dff.groupby("TENANT")["REVENUE"].sum().max() if not dff.empty else 0

def fmt_dollars(v):
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}K"
    return f"${v:.0f}"

def delta_html(val, suffix="%"):
    if val > 0:
        return f'<span class="kpi-delta delta-pos">▲ {val:+.1f}{suffix} vs prev period</span>'
    elif val < 0:
        return f'<span class="kpi-delta delta-neg">▼ {val:.1f}{suffix} vs prev period</span>'
    else:
        return f'<span class="kpi-delta delta-neu">— flat</span>'

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:4px">
  <span style="font-size:26px;font-weight:800;color:#e8eaf0;letter-spacing:-0.5px">Revenue Command Center</span>
  <span style="font-family:'DM Mono',monospace;font-size:12px;color:#4a5568;letter-spacing:2px">COF-C03 DEMO BUILD</span>
</div>
""", unsafe_allow_html=True)

tenant_badges = " ".join([
    f'<span class="tenant-badge" style="background:{TENANT_COLORS[t]}22;color:{TENANT_COLORS[t]};border:1px solid {TENANT_COLORS[t]}55">{t}</span>'
    for t in selected_tenants
])
st.markdown(f"<div style='margin-bottom:20px'>{tenant_badges} &nbsp; <span style='font-family:DM Mono,monospace;font-size:11px;color:#4a5568'>{start_date} → {end_date}</span></div>", unsafe_allow_html=True)

# ── KPI Cards ────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="kpi-card" style="--accent:#60a5fa">
      <div class="kpi-label">Total Revenue</div>
      <div class="kpi-value">{fmt_dollars(total_rev)}</div>
      {delta_html(pop_delta)}
    </div>""", unsafe_allow_html=True)

with k2:
    color = "#34d399" if rev_vs_bud >= 0 else "#f87171"
    st.markdown(f"""
    <div class="kpi-card" style="--accent:{color}">
      <div class="kpi-label">vs Budget</div>
      <div class="kpi-value" style="color:{color}">{rev_vs_bud:+.1f}%</div>
      <span class="kpi-delta delta-neu">Budget: {fmt_dollars(total_bud)}</span>
    </div>""", unsafe_allow_html=True)

with k3:
    color2 = "#34d399" if rev_vs_wtd >= 0 else "#f87171"
    st.markdown(f"""
    <div class="kpi-card" style="--accent:#a78bfa">
      <div class="kpi-label">Win The Day %</div>
      <div class="kpi-value" style="color:{color2}">{rev_vs_wtd:+.1f}%</div>
      <span class="kpi-delta delta-neu">Target: {fmt_dollars(total_wtd)}</span>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card" style="--accent:{TENANT_COLORS.get(best_tenant,'#60a5fa')}">
      <div class="kpi-label">Top Tenant</div>
      <div class="kpi-value" style="font-size:22px">{best_tenant}</div>
      <span class="kpi-delta delta-neu">{fmt_dollars(best_rev)}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Main chart: Revenue vs Budget vs WTD ────────────────────
st.markdown('<div class="section-title">Daily Performance · Revenue vs Budget vs Win The Day</div>', unsafe_allow_html=True)

fig = go.Figure()

# WTD shaded area (background)
fig.add_trace(go.Scatter(
    x=agg_all["PERIOD"], y=agg_all["WIN_THE_DAY"],
    fill="tozeroy", fillcolor="rgba(167,139,250,0.05)",
    line=dict(color="rgba(167,139,250,0.25)", width=1, dash="dot"),
    name="Win The Day", hovertemplate="%{y:$,.0f}<extra>Win The Day</extra>"
))

# Budget line
fig.add_trace(go.Scatter(
    x=agg_all["PERIOD"], y=agg_all["BUDGET"],
    line=dict(color="#94a3b8", width=1.5, dash="dash"),
    name="Budget", hovertemplate="%{y:$,.0f}<extra>Budget</extra>"
))

# Per-tenant revenue bars
for tenant in selected_tenants:
    t_data = agg[agg["TENANT"] == tenant]
    fig.add_trace(go.Bar(
        x=t_data["PERIOD"], y=t_data["REVENUE"],
        name=tenant,
        marker_color=TENANT_COLORS[tenant],
        opacity=0.85,
        hovertemplate=f"<b>{tenant}</b><br>%{{y:$,.0f}}<extra></extra>"
    ))

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Syne, sans-serif", color="#8892b0", size=12),
    yaxis=dict(gridcolor="#1a2035", linecolor="#1e2540", tickcolor="#1e2540", tickprefix="$"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e2540", borderwidth=1,
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
    hoverlabel=dict(bgcolor="#111827", bordercolor="#1e2540", font_family="DM Mono"),
    barmode="stack",
    height=380,
    title=dict(text="", x=0),
    xaxis=dict(gridcolor="#1a2035", linecolor="#1e2540", tickcolor="#1e2540",
               rangeslider=dict(visible=True, thickness=0.04, bgcolor="#0a0d14")),
)
st.plotly_chart(fig, use_container_width=True)

# ── Row 2: Budget attainment gauge + Tenant breakdown ────────
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown('<div class="section-title">Budget Attainment</div>', unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round((total_rev / total_bud) * 100, 1) if total_bud else 0,
        number=dict(suffix="%", font=dict(size=32, color="#e8eaf0", family="Syne")),
        delta=dict(reference=100, relative=False, suffix=" pp vs target",
                   increasing=dict(color="#34d399"), decreasing=dict(color="#f87171")),
        gauge=dict(
            axis=dict(range=[0, 140], tickcolor="#1e2540", tickfont=dict(color="#6b7599")),
            bar=dict(color="#60a5fa", thickness=0.25),
            bgcolor="rgba(0,0,0,0)",
            steps=[
                dict(range=[0, 80],  color="rgba(248,113,113,0.1)"),
                dict(range=[80, 100], color="rgba(251,191,36,0.1)"),
                dict(range=[100, 112], color="rgba(52,211,153,0.1)"),
                dict(range=[112, 140], color="rgba(167,139,250,0.15)"),
            ],
            threshold=dict(line=dict(color="#a78bfa", width=2), thickness=0.8, value=112),
        )
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Syne", color="#8892b0"),
        height=260,
        margin=dict(l=20, r=20, t=20, b=10),
        annotations=[dict(text="WTD", x=0.5, y=0.28, showarrow=False,
                          font=dict(size=10, color="#a78bfa", family="DM Mono"),
                          xref="paper", yref="paper")]
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_right:
    st.markdown('<div class="section-title">Tenant Breakdown</div>', unsafe_allow_html=True)
    tenant_summary = dff.groupby("TENANT").agg(
        REVENUE=("REVENUE", "sum"),
        BUDGET=("BUDGET", "sum"),
        WIN_THE_DAY=("WIN_THE_DAY", "sum"),
    ).reset_index()
    tenant_summary["vs_budget"] = (tenant_summary["REVENUE"] / tenant_summary["BUDGET"] - 1) * 100
    tenant_summary["vs_wtd"]    = (tenant_summary["REVENUE"] / tenant_summary["WIN_THE_DAY"] - 1) * 100
    tenant_summary = tenant_summary[tenant_summary["TENANT"].isin(selected_tenants)]

    fig_bar = go.Figure()
    for m, color, name in [("REVENUE","#60a5fa","Revenue"), ("BUDGET","#94a3b8","Budget"), ("WIN_THE_DAY","#a78bfa","Win The Day")]:
        fig_bar.add_trace(go.Bar(
            x=tenant_summary["TENANT"], y=tenant_summary[m],
            name=name, marker_color=color, opacity=0.85,
            hovertemplate=f"<b>%{{x}}</b> {name}<br>%{{y:$,.0f}}<extra></extra>"
        ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Syne, sans-serif", color="#8892b0", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        barmode="group", height=260,
        xaxis=dict(gridcolor="#1a2035", linecolor="#1e2540"),
        yaxis=dict(gridcolor="#1a2035", tickprefix="$"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Row 3: Win Rate heatmap + Trend lines ────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.markdown('<div class="section-title">Win The Day — Hit Rate by Tenant</div>', unsafe_allow_html=True)
    dff2 = dff.copy()
    dff2["WON"] = (dff2["REVENUE"] >= dff2["WIN_THE_DAY"]).astype(int)
    dff2["MONTH"] = dff2["DATE"].dt.strftime("%b %y")
    monthly_win = dff2.groupby(["TENANT", "MONTH"])["WON"].mean().reset_index()
    months_ordered = dff2.sort_values("DATE")["DATE"].dt.strftime("%b %y").unique().tolist()

    pivot = monthly_win.pivot(index="TENANT", columns="MONTH", values="WON")
    pivot = pivot.reindex(columns=[m for m in months_ordered if m in pivot.columns])
    pivot = pivot.reindex(index=[t for t in all_tenants if t in pivot.index])

    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values * 100,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0,"#1a0a0a"],[0.4,"#7f1d1d"],[0.7,"#d97706"],[1,"#34d399"]],
        zmin=0, zmax=100,
        hovertemplate="%{y} · %{x}<br>Hit Rate: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            ticksuffix="%",
            tickfont=dict(color="#6b7599", family="DM Mono", size=10),
            len=0.8, thickness=10,
            bgcolor="rgba(0,0,0,0)",
        )
    ))
    fig_heat.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Syne, sans-serif", color="#8892b0", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        height=240,
        xaxis=dict(gridcolor="#1a2035", linecolor="#1e2540", tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with col_b:
    st.markdown('<div class="section-title">Revenue Trend by Tenant</div>', unsafe_allow_html=True)
    rolling = agg.copy()

    fig_trend = go.Figure()
    for tenant in selected_tenants:
        t_data = rolling[rolling["TENANT"] == tenant].sort_values("PERIOD")
        # 7-period rolling avg
        t_data = t_data.copy()
        t_data["SMOOTH"] = t_data["REVENUE"].rolling(7, min_periods=1).mean()
        fig_trend.add_trace(go.Scatter(
            x=t_data["PERIOD"], y=t_data["SMOOTH"],
            name=tenant,
            line=dict(color=TENANT_COLORS[tenant], width=2),
            hovertemplate=f"<b>{tenant}</b><br>%{{y:$,.0f}}<extra></extra>"
        ))
    fig_trend.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Syne, sans-serif", color="#8892b0", size=12),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor="#1a2035", linecolor="#1e2540"),
        yaxis=dict(gridcolor="#1a2035", tickprefix="$"),
        height=240,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.15),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Row 4: Detail table ──────────────────────────────────────
with st.expander("📋  Detailed Data Table", expanded=False):
    display_df = dff[["DATE","TENANT","REVENUE","BUDGET","WIN_THE_DAY"]].copy()
    display_df["vs Budget"] = ((display_df["REVENUE"] / display_df["BUDGET"] - 1) * 100).round(1).astype(str) + "%"
    display_df["Win?"] = display_df.apply(lambda r: "✅" if r["REVENUE"] >= r["WIN_THE_DAY"] else "❌", axis=1)
    display_df["DATE"] = display_df["DATE"].dt.date
    display_df["REVENUE"] = display_df["REVENUE"].map("${:,.0f}".format)
    display_df["BUDGET"]  = display_df["BUDGET"].map("${:,.0f}".format)
    display_df["WIN_THE_DAY"] = display_df["WIN_THE_DAY"].map("${:,.0f}".format)
    st.dataframe(display_df.sort_values("DATE", ascending=False), use_container_width=True, height=300)

# ── Footer ───────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:24px 0 8px;font-family:'DM Mono',monospace;font-size:11px;color:#2d3a55;letter-spacing:2px">
REVENUE COMMAND CENTER · BUILT WITH STREAMLIT + SNOWFLAKE
</div>
""", unsafe_allow_html=True)
