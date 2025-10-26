import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib


st.set_page_config(page_title="MMR Rent Compare", layout="wide")

st.title("MMR Rent Compare – 1BHK Median (Hinglish)")
st.caption("Zones → Areas sorted by 1BHK median rent (ascending). Data demo hai – real entries baad me update karenge.")

# Load data
def file_hash(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

@st.cache_data
def load_data(path, version):
    return pd.read_csv(path)

csv_path = "mmr_rent_data.csv"
version = file_hash(csv_path)
df = load_data(csv_path, version)

# Controls
zones = df["zone"].unique().tolist()
zone_selected = st.multiselect("Zone choose karo", zones, default=zones)

min_rent, max_rent = int(df["rent_median_1bhk"].min()), int(df["rent_median_1bhk"].max())
rent_range = st.slider("1BHK Median Rent range (₹/mo)", min_rent, max_rent, (min_rent, max_rent), step=500)

search = st.text_input("Area search (optional)", "")

# Filter
mask = df["zone"].isin(zone_selected) & df["rent_median_1bhk"].between(*rent_range)
if search.strip():
    s = search.strip().lower()
    mask = mask & df["area"].str.lower().str.contains(s)

filtered = df.loc[mask].copy()

# Sort
sort_zone_first = st.checkbox("Zone-wise view (recommended)", value=True)
if sort_zone_first:
    filtered = filtered.sort_values(by=["zone","rent_median_1bhk","area"], ascending=[True, True, True])
else:
    filtered = filtered.sort_values(by=["rent_median_1bhk","area"], ascending=[True, True])

# Display
st.subheader("Areas (Ascending by 1BHK Median)")

def fmt_money(v): 
    return f"₹{int(v):,}"

show_cols = ["zone","area","region","rent_median_1bhk","rent_min_1bhk","rent_max_1bhk","deposit_ratio"]
rename = {
    "zone":"Zone",
    "area":"Area",
    "region":"Region",
    "rent_median_1bhk":"Median 1BHK",
    "rent_min_1bhk":"Low",
    "rent_max_1bhk":"High",
    "deposit_ratio":"Deposit"
}
view = filtered[show_cols].rename(columns=rename)
view["Median 1BHK"] = view["Median 1BHK"].apply(fmt_money)
view["Low"] = view["Low"].apply(fmt_money)
view["High"] = view["High"].apply(fmt_money)

st.dataframe(view, use_container_width=True)

st.markdown("---")
st.markdown("**How to update data:** `mmr_rent_data.csv` ko Excel/Google Sheet se export karke yahan replace karo. Columns same rehne chahiye.")

with st.expander("CSV column spec (zaruri)"):
    st.code("zone,area,region,rent_median_1bhk,rent_min_1bhk,rent_max_1bhk,deposit_ratio", language="text")

st.caption("© Open approach; private portals ki scraping nahi. User-submitted & open sources only.")
