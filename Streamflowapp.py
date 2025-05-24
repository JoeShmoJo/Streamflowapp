import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.graph_objs as go

# --- Helper functions ---

def fetch_usgs(site_id):
    """Fetch USGS data for last 5 days."""
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=5)
    url = (
        f"https://waterservices.usgs.gov/nwis/iv/"
        f"?sites={site_id}&parameterCd=00060"
        f"&startDT={start.strftime('%Y-%m-%dT%H:%M')}"
        f"&endDT={end.strftime('%Y-%m-%dT%H:%M')}"
        f"&siteStatus=all&format=json"
    )
    r = requests.get(url)
    if not r.ok:
        return None, "USGS fetch failed"
    j = r.json()
    try:
        times = j['value']['timeSeries'][0]['values'][0]['value']
        df = pd.DataFrame(times)
        df['dateTime'] = pd.to_datetime(df['dateTime'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df[['dateTime', 'value']], None
    except Exception:
        return None, "No data or wrong site ID"

def fetch_wa_ecology(site_id):
    """Fetch WA Ecology data for last 5 days."""
    # Note: Ecology API docs: https://ecology.wa.gov/Water-Shorelines/Water-supply/Water-availability/Data-services
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=5)
    # Try to use their Hydstra API (JSON)
    url = (
        f"https://ofmgeodataws.ecology.wa.gov/hydstra/hydstra?service=series"
        f"&site_list={site_id}&varfrom=420"
        f"&datefrom={start.strftime('%d/%m/%Y')}&dateto={end.strftime('%d/%m/%Y')}&interval=hr"
        f"&format=json"
    )
    r = requests.get(url)
    if not r.ok:
        return None, "Ecology fetch failed"
    try:
        j = r.json()
        records = j['series'][0]['data']
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['t'], errors='coerce')
        df['value'] = pd.to_numeric(df['v'], errors='coerce')
        return df[['date', 'value']], None
    except Exception:
        return None, "No data or wrong Ecology site ID"

# --- Streamlit app ---

st.title("Last 5 Days Streamflow Viewer")

st.write("Enter USGS or Washington Dept. of Ecology site IDs (comma separated).")
st.caption("Examples: USGS 14222500, USGS 14178000, USGS 14128500, ECY 27A070")

# Preset IDs for convenience
default_ids = "USGS 14222500, USGS 14178000, USGS 14128500"

site_ids_input = st.text_input("Site IDs", default_ids)
site_ids = [x.strip() for x in site_ids_input.split(",") if x.strip()]

for site in site_ids:
    if site.upper().startswith("USGS"):
        site_id = site.split()[1]
        df, err = fetch_usgs(site_id)
        label = f"USGS {site_id}"
    elif site.upper().startswith("ECY") or site.upper().startswith("ECOL"):
        site_id = site.split()[1]
        df, err = fetch_wa_ecology(site_id)
        label = f"Ecology {site_id}"
    else:
        st.error(f"Invalid site ID format: {site}. Use 'USGS 14222500' or 'ECY 27A070'.")
        continue

    st.subheader(label)
    if err:
        st.error(f"Error: {err}")
        continue
    if df is None or df.empty:
        st.warning("No data found.")
        continue

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.iloc[:, 0], y=df.iloc[:, 1], mode="lines+markers", name=label
    ))
    fig.update_layout(
        xaxis_title="Date/Time",
        yaxis_title="Discharge (cfs)",
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)
