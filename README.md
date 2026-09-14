# Friends Reconnected Dashboard

Streamlit dashboard for Google Search Console data, with a placeholder tab for GA4.

## 1. Get a service account key (one-time, ~5 min)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create (or pick) a project.
2. Enable the **Search Console API** under APIs & Services > Library.
3. Go to IAM & Admin > Service Accounts > Create service account. Any name is fine, no roles needed.
4. Open the new service account > Keys > Add key > Create new key > JSON. This downloads a `.json` file — keep it private, don't commit it.
5. Copy the service account's email address (looks like `xxx@yyy.iam.gserviceaccount.com`).

## 2. Give it access to your GSC property

1. Open [Search Console](https://search.google.com/search-console) for friendsreconnected.co.uk.
2. Settings > Users and permissions > Add user.
3. Paste the service account email, permission level "Restricted" is enough (read-only dashboard).

## 3. Run it locally

```bash
cd "Friends Reconnected Dashboard"
pip install -r requirements.txt
streamlit run app.py
```

In the sidebar, expand **Connection**, choose "Upload service account JSON", and upload the key file from step 1. The dashboard will list every property that account can see.

For a project-local JSON file, replace the contents of `service-account.json` in this folder with the downloaded Google service-account key. Then choose **Use local JSON file**; it defaults to that filename, so no laptop-specific path is needed.

You can also set a different default path before starting Streamlit:

```bash
export GSC_SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
streamlit run app.py
```

The real key is ignored by Git through `.gitignore`. Keep it private and never commit it to the repository.

## 4. Optional: store the key as a secret instead of uploading it each time

Create `.streamlit/secrets.toml`:

```toml
[gsc_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "xxx@yyy.iam.gserviceaccount.com"
client_id = "..."
# ...the rest of the fields from the downloaded JSON
```

Then pick "Use saved secret" in the sidebar. If you deploy to Streamlit Community Cloud, paste the same TOML into the app's Secrets settings.

## 5. Adding GA4 later

Drop a `ga4_client.py` next to `gsc_client.py` with the same shape (`get_service`, `fetch_*` functions using `google-analytics-data`), then add a tab in `app.py` that mirrors the Overview tab. The GA4 Data API uses the same service-account pattern — add the service account as a Viewer in GA4's Admin > Property Access Management instead of GSC's user list.

## Notes

- GSC data usually lags 1-2 days; the date pickers already account for that.
- `rowLimit` is set to the API max (25,000) per dimension query, which covers most sites in a single call.
- API calls are cached for 10 minutes (`st.cache_data(ttl=600)`) so flipping between tabs and filters doesn't re-hit the API every time.
