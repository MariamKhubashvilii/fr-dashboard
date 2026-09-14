"""
Google Search Console API client for the Streamlit dashboard.

Handles service-account auth and cached data fetching. Swap in ga4_client.py
later with the same shape (get_service / fetch_*) to add a GA4 tab.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


@st.cache_resource(show_spinner=False)
def get_service(credentials_json: dict):
    """Build an authenticated Search Console API service from a service account key dict."""
    creds = service_account.Credentials.from_service_account_info(
        credentials_json, scopes=SCOPES
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


@st.cache_data(show_spinner=False, ttl=600)
def list_sites(_service) -> list[str]:
    """Return the site URLs this service account can access, sorted."""
    resp = _service.sites().list().execute()
    return sorted(s["siteUrl"] for s in resp.get("siteEntry", []))


@st.cache_data(show_spinner="Pulling Search Console data...", ttl=600)
def fetch_search_analytics(
    _service,
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    search_type: str = "web",
    row_limit: int = 25000,
    dimension_filters: list[dict] | None = None,
) -> pd.DataFrame:
    """Fetch search analytics rows for the given dimensions and return a tidy DataFrame."""
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "type": search_type,
        "rowLimit": row_limit,
    }
    if dimension_filters:
        body["dimensionFilterGroups"] = [{"filters": dimension_filters}]

    resp = _service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    rows = resp.get("rows", [])
    cols = [*dimensions, "clicks", "impressions", "ctr", "position"]
    if not rows:
        return pd.DataFrame(columns=cols)

    records = []
    for r in rows:
        entry = dict(zip(dimensions, r["keys"]))
        entry["clicks"] = r.get("clicks", 0)
        entry["impressions"] = r.get("impressions", 0)
        entry["ctr"] = r.get("ctr", 0.0)
        entry["position"] = r.get("position", 0.0)
        records.append(entry)

    df = pd.DataFrame(records)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df
