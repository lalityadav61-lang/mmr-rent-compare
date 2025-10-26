import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib

# ----- Page setup -----
st.set_page_config(page_title="MMR Rent Compare", layout="wide")
st.title("MMR Rent Compare – 1BHK Median (Hinglish)")
st.caption("Global ranking (1–60) by 1BHK median rent. Same median = same rank (dense).")

# ----- Cache-busting helpers -----
def file_hash(path: str) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

@st.cache_data
def load_data(path: str, version: str) -> pd.DataFrame:
    return pd.read_csv(path)

csv_path = "mmr_rent_data.csv"
version = file_hash(csv_path)
df = load_data(csv_path, version)

# Safety: numeric dtypes
for col in ["rent_median_1bhk", "rent_min_1bhk", "rent_max_1bhk"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ----- Global Rank (computed on full dataset, NOT after filter) -----
df["global_rank"] = (
    df["rent_median_1bhk"]
    .rank(method="dense", ascending=True)
    .astype("Int64")
)

# ----- Controls -----
zones = df["zone"].dropna().unique().tolist()
zones.sort()
zone_selected = st.multiselect("Zone choose karo", zones, default=zones)

min_rent = int(df["rent_median_1bhk"].min())
max_rent = int(df["rent_median_1bhk"].max())
rent_range = st.slider("1BHK Median Rent range (₹/mo)", min_rent, max_rent, (min_rent, max_rent), step=500)

search = st.text_input("Area search (optional)", "")

cols_top = st.columns([1, 3, 2])
with cols_top[0]:
    if st.button("Reload latest data"):
        st.cache_data.clear()
        st.experimental_rerun()
with cols_top[2]:
    sort_zone_first = st.checkbox("Zone-wise grouping (optional)", value=False)

# ----- Filter (applied AFTER rank is computed) -----
mask = df["zone"].isin(zone_selected) & df["rent_median_1bhk"].between(*rent_range)
if search.strip():
    s = search.strip().lower()
    mask &= df["area"].str.lower().str.contains(s)
filtered = df.loc[mask].copy()

# ----- Sort view -----
if sort_zone_first:
    filtered = filtered.sort_values(by=["zone", "rent_median_1bhk", "area"], ascending=[True, True, True])
else:
    filtered = filtered.sort_values(by=["global_rank", "area"], ascending=[True, True])

# ----- Display -----
st.subheader("Areas (Global Rank by 1BHK Median)")

def fmt_money(v):
    try:
        return f"₹{int(v):,}"
    except Exception:
        return v

show_cols = [
    "global_rank",
    "zone",
    "area",
    "region",
    "rent_median_1bhk",
    "rent_min_1bhk",
    "rent_max_1bhk",
    "deposit_ratio",
]
rename = {
    "global_rank": "Rank",
    "zone": "Zone",
    "area": "Area",
    "region": "Region",
    "rent_median_1bhk": "Median 1BHK",
    "rent_min_1bhk": "Low",
    "rent_max_1bhk": "High",
    "deposit_ratio": "Deposit",
}
view = filtered[show_cols].rename(columns=rename)
for col in ["Median 1BHK", "Low", "High"]:
    view[col] = view[col].apply(fmt_money)

st.dataframe(view, use_container_width=True)

st.markdown("---")
st.markdown(
    "**Note:** Global rank poore dataset par based hai (filter ke baad nahi). "
    "Same median rent waale areas ko same rank milta hai (dense ranking)."
)
with st.expander("CSV column spec (zaruri)"):
    st.code("zone,area,region,rent_median_1bhk,rent_min_1bhk,rent_max_1bhk,deposit_ratio", language="text")
st.caption("© Open approach; private portals ki scraping nahi. User-submitted & open sources only.")
