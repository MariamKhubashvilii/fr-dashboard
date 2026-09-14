"""
SEO Analytics Dashboard — Google Search Console (GA4 tab wired for later).

Run with: streamlit run app.py
"""
import datetime as dt
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gsc_client import fetch_search_analytics, get_service, list_sites

st.set_page_config(page_title="SEO Analytics Dashboard", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar: connection
# ---------------------------------------------------------------------------
st.sidebar.title("📈 SEO Dashboard")
st.sidebar.caption("Google Search Console analytics")

with st.sidebar.expander("🔑 Connection", expanded="service" not in st.session_state):
    creds_source = st.radio(
        "Credentials",
        ["Upload service account JSON", "Use local JSON file", "Use saved secret"],
        label_visibility="collapsed",
    )
    creds_dict = None
    if creds_source == "Upload service account JSON":
        uploaded = st.file_uploader("Service account key (.json)", type="json")
        if uploaded:
            creds_dict = json.load(uploaded)
    elif creds_source == "Use local JSON file":
        credentials_path = st.text_input(
            "Service account JSON path",
            value=os.environ.get("GSC_SERVICE_ACCOUNT_FILE", "service-account.json"),
        )
        try:
            with open(credentials_path, encoding="utf-8") as credentials_file:
                creds_dict = json.load(credentials_file)
        except FileNotFoundError:
            st.info(f"JSON file not found: {credentials_path}")
        except json.JSONDecodeError as e:
            st.error(f"Invalid service account JSON: {e}")
    else:
        if "gsc_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gsc_service_account"])
        else:
            st.info("No `gsc_service_account` found in st.secrets. Add one, or upload a key file instead.")

if creds_dict:
    try:
        st.session_state["service"] = get_service(creds_dict)
    except Exception as e:
        st.sidebar.error(f"Auth failed: {e}")
        st.stop()

if "service" not in st.session_state:
    st.title("📈 SEO Analytics Dashboard")
    st.info(
        "Connect a Google Search Console service account to get started. "
        "Expand **🔑 Connection** in the sidebar and upload your key file."
    )
    st.caption("First time setting this up? See README.md for the 5-minute walkthrough.")
    st.stop()

service = st.session_state["service"]
sites = list_sites(service)
if not sites:
    st.error(
        "This service account has no Search Console properties. "
        "Add its email as a user under Settings > Users and permissions in GSC (see README)."
    )
    st.stop()

site_url = st.sidebar.selectbox("Property", sites)

# ---------------------------------------------------------------------------
# Sidebar: date range + filters
# ---------------------------------------------------------------------------
st.sidebar.subheader("Date range")
preset = st.sidebar.radio("Preset", ["Last 7 days", "Last 28 days", "Last 90 days", "Custom"], index=1)
today = dt.date.today()
gsc_max_date = today - dt.timedelta(days=2)  # GSC data typically lags ~2 days

if preset == "Last 7 days":
    start_date, end_date = gsc_max_date - dt.timedelta(days=6), gsc_max_date
elif preset == "Last 28 days":
    start_date, end_date = gsc_max_date - dt.timedelta(days=27), gsc_max_date
elif preset == "Last 90 days":
    start_date, end_date = gsc_max_date - dt.timedelta(days=89), gsc_max_date
else:
    start_date, end_date = st.sidebar.date_input(
        "Range", value=(gsc_max_date - dt.timedelta(days=27), gsc_max_date), max_value=gsc_max_date
    )

compare = st.sidebar.checkbox("Compare to previous period", value=True)

st.sidebar.subheader("Filters")
device_filter = st.sidebar.selectbox("Device", ["All", "Desktop", "Mobile", "Tablet"])
country_filter = st.sidebar.text_input("Country (ISO-3, e.g. GBR)", "")
search_type = st.sidebar.selectbox("Search type", ["web", "image", "video", "news"], index=0)


def build_filters() -> list[dict] | None:
    filters = []
    if device_filter != "All":
        filters.append({"dimension": "device", "operator": "equals", "expression": device_filter.upper()})
    if country_filter.strip():
        filters.append({"dimension": "country", "operator": "equals", "expression": country_filter.strip().lower()})
    return filters or None


filters = build_filters()


def period_str(s: dt.date, e: dt.date) -> str:
    return f"{s.isoformat()} to {e.isoformat()}"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
fetch_args = dict(site_url=site_url, search_type=search_type, dimension_filters=filters)

df_daily = fetch_search_analytics(service, start_date=start_date.isoformat(), end_date=end_date.isoformat(), dimensions=["date"], **fetch_args)
df_queries = fetch_search_analytics(service, start_date=start_date.isoformat(), end_date=end_date.isoformat(), dimensions=["query"], **fetch_args)
df_pages = fetch_search_analytics(service, start_date=start_date.isoformat(), end_date=end_date.isoformat(), dimensions=["page"], **fetch_args)
df_country = fetch_search_analytics(service, start_date=start_date.isoformat(), end_date=end_date.isoformat(), dimensions=["country"], **fetch_args)
df_device = fetch_search_analytics(service, start_date=start_date.isoformat(), end_date=end_date.isoformat(), dimensions=["device"], **fetch_args)

if compare:
    period_len = (end_date - start_date).days + 1
    prev_end = start_date - dt.timedelta(days=1)
    prev_start = prev_end - dt.timedelta(days=period_len - 1)
    df_prev_daily = fetch_search_analytics(
        service, start_date=prev_start.isoformat(), end_date=prev_end.isoformat(), dimensions=["date"], **fetch_args
    )
else:
    df_prev_daily = pd.DataFrame()

# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------
st.title("📈 SEO Analytics Dashboard")
st.caption(f"{site_url} · {period_str(start_date, end_date)}")

tab_overview, tab_queries, tab_pages, tab_ga4 = st.tabs(["Overview", "Queries", "Pages", "GA4 (coming soon)"])


def kpi_row(df: pd.DataFrame, df_prev: pd.DataFrame) -> None:
    clicks = int(df["clicks"].sum()) if not df.empty else 0
    impressions = int(df["impressions"].sum()) if not df.empty else 0
    ctr = (clicks / impressions * 100) if impressions else 0.0
    position = (df["position"] * df["impressions"]).sum() / impressions if impressions else 0.0

    d_clicks = d_impr = d_ctr = d_pos = None
    if df_prev is not None and not df_prev.empty:
        p_clicks = int(df_prev["clicks"].sum())
        p_impr = int(df_prev["impressions"].sum())
        p_ctr = (p_clicks / p_impr * 100) if p_impr else 0.0
        p_pos = (df_prev["position"] * df_prev["impressions"]).sum() / p_impr if p_impr else 0.0
        d_clicks, d_impr = clicks - p_clicks, impressions - p_impr
        d_ctr, d_pos = round(ctr - p_ctr, 2), round(position - p_pos, 2)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clicks", f"{clicks:,}", delta=d_clicks)
    c2.metric("Impressions", f"{impressions:,}", delta=d_impr)
    c3.metric("Avg CTR", f"{ctr:.2f}%", delta=f"{d_ctr}pp" if d_ctr is not None else None)
    c4.metric("Avg Position", f"{position:.1f}", delta=d_pos, delta_color="inverse")


with tab_overview:
    kpi_row(df_daily, df_prev_daily)
    st.divider()

    if not df_daily.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_daily["date"], y=df_daily["clicks"], name="Clicks"))
        fig.add_trace(go.Scatter(x=df_daily["date"], y=df_daily["impressions"], name="Impressions", yaxis="y2"))
        fig.update_layout(
            title="Clicks & impressions over time",
            yaxis=dict(title="Clicks"),
            yaxis2=dict(title="Impressions", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.15),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data for this period.")

    col1, col2 = st.columns(2)
    with col1:
        if not df_country.empty:
            top_country = df_country.sort_values("clicks", ascending=False).head(10)
            st.plotly_chart(
                px.bar(top_country, x="clicks", y="country", orientation="h", title="Clicks by country"),
                use_container_width=True,
            )
    with col2:
        if not df_device.empty:
            st.plotly_chart(
                px.pie(df_device, values="clicks", names="device", title="Clicks by device"),
                use_container_width=True,
            )

with tab_queries:
    st.subheader("Top queries")
    if df_queries.empty:
        st.info("No query data for this period.")
    else:
        df_q = df_queries.sort_values("clicks", ascending=False).copy()
        df_q["ctr"] = (df_q["ctr"] * 100).round(2)
        df_q["position"] = df_q["position"].round(1)
        search = st.text_input("Filter queries containing...", "")
        if search:
            df_q = df_q[df_q["query"].str.contains(search, case=False, na=False)]
        st.dataframe(
            df_q.rename(columns={
                "query": "Query", "clicks": "Clicks", "impressions": "Impressions",
                "ctr": "CTR %", "position": "Avg Position",
            }),
            use_container_width=True, hide_index=True,
        )
        st.download_button("Download as CSV", df_q.to_csv(index=False).encode(), "top_queries.csv", "text/csv")

with tab_pages:
    st.subheader("Top pages")
    if df_pages.empty:
        st.info("No page data for this period.")
    else:
        df_p = df_pages.sort_values("clicks", ascending=False).copy()
        df_p["ctr"] = (df_p["ctr"] * 100).round(2)
        df_p["position"] = df_p["position"].round(1)
        st.dataframe(
            df_p.rename(columns={
                "page": "Page", "clicks": "Clicks", "impressions": "Impressions",
                "ctr": "CTR %", "position": "Avg Position",
            }),
            use_container_width=True, hide_index=True,
        )
        st.download_button("Download as CSV", df_p.to_csv(index=False).encode(), "top_pages.csv", "text/csv")

with tab_ga4:
    st.info(
        "GA4 slots in the same way: a `ga4_client.py` next to `gsc_client.py` with a "
        "`get_service` and `fetch_*` function, plus a tab here that mirrors Overview. "
        "Send over the Analytics Data API credentials when you're ready and this tab gets built out."
    )
