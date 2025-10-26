import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib
import re

# ----- Page setup -----
st.set_page_config(page_title="MMR Rent Compare", layout="wide")
st.title("MMR Rent Compare – 1BHK Median (Hinglish)")
st.caption("Global ranking by: Median 1BHK → Deposit ratio → Travel proximity. Rank-based badges auto-assign (🟢🔵🟡🟠🔴👑).")

# ----- Cache-busting -----
def file_hash(path: str) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

@st.cache_data
def load_data(path: str, version: str) -> pd.DataFrame:
    return pd.read_csv(path)

csv_path = "mmr_rent_data.csv"
version = file_hash(csv_path)
df = load_data(csv_path, version)

# ----- Safety: numeric -----
for col in ["rent_median_1bhk", "rent_min_1bhk", "rent_max_1bhk"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ----- Deposit ratio parsing (e.g., '3x' or '3x-4x' -> 3.0) -----
def parse_deposit_ratio(s: str) -> float:
    if pd.isna(s):
        return 4.0
    s = str(s).lower().strip()
    m = re.search(r"(\d+(\.\d+)?)\s*x", s)  # first number before 'x'
    if m:
        return float(m.group(1))
    m2 = re.search(r"\d+(\.\d+)?", s)       # any number fallback
    if m2:
        return float(m2.group(0))
    return 4.0

df["deposit_months_min"] = df["deposit_ratio"].apply(parse_deposit_ratio)

# ----- Travel proximity heuristic (lower = closer/better) -----
western_core = [
    "Bandra","Khar","Santacruz","Andheri","Jogeshwari","Goregaon",
    "Malad","Kandivali","Borivali","Dahisar","Mira Road",
    "Bhayander","Vasai","Naigaon","Nalasopara","Virar"
]
central_core = [
    "Dadar","Matunga","Sion","Kurla","Ghatkopar","Vikhroli","Bhandup",
    "Mulund","Thane","Kalwa","Mumbra","Diva","Dombivli","Kalyan",
    "Ambernath","Badlapur","Vangani","Titwala"
]
harbour_core = ["Chembur","Govandi","Mankhurd"]
south_core = ["Lower Parel","Worli","Prabhadevi","Mahim","Wadala","Cuffe Parade","Malabar Hill","Colaba"]
navi_core = [
    "Vashi","Airoli","Kopar Khairane","Ghansoli","Turbhe","Sanpada","Seawoods",
    "Nerul","Belapur","Kharghar","Kamothe","Ulwe","New Panvel","Panvel","Taloja"
]

def first_match_idx(area_lower: str, names: list[str]) -> int | None:
    for idx, name in enumerate(names):
        if name.lower() in area_lower:
            return idx
    return None

def proximity_score(area: str, region: str) -> int:
    a = (area or "").lower()
    r = (region or "").lower()

    if "south" in r or any(k.lower() in a for k in south_core):
        idx = first_match_idx(a, south_core);   return idx if idx is not None else 0
    if "western" in r or any(k.lower() in a for k in western_core):
        idx = first_match_idx(a, western_core); return idx if idx is not None else 50
    if "central" in r or any(k.lower() in a for k in central_core):
        idx = first_match_idx(a, central_core); return idx if idx is not None else 50
    if "harbour" in r or "chembur" in a:
        idx = first_match_idx(a, harbour_core); return idx if idx is not None else 30
    if "navi" in r or any(k.lower() in a for k in navi_core):
        idx = first_match_idx(a, navi_core);    return idx if idx is not None else 40
    return 60  # fallback

df["proximity_score"] = df.apply(lambda x: proximity_score(str(x["area"]), str(x["region"])), axis=1)

# ----- Global sorting + dense rank (median -> deposit -> proximity -> area) -----
df = df.sort_values(
    by=["rent_median_1bhk", "deposit_months_min", "proximity_score", "area"],
    ascending=[True, True, True, True]
).reset_index(drop=True)

df["global_rank"] = df["rent_median_1bhk"].rank(method="dense", ascending=True).astype("Int64")

# ----- Rank → Badge mapping -----
def rank_badge(rank_val: int) -> str:
    if pd.isna(rank_val): return ""
    r = int(rank_val)
    if   1 <= r <= 15: return "🟢 Budget"
    elif 16 <= r <= 25: return "🔵 Value"
    elif 26 <= r <= 40: return "🟡 Mid"
    elif 41 <= r <= 50: return "🟠 Upper Mid"
    elif 51 <= r <= 55: return "🔴 Premium"
    else:               return "👑 Luxury"

df["badge"] = df["global_rank"].apply(rank_badge)

# ----- Controls -----
zones = df["zone"].dropna().unique().tolist(); zones.sort()
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
    group_zone = st.checkbox("Zone-wise grouping (optional)", value=False)

# ----- Filter (after global rank calculated) -----
mask = df["zone"].isin(zone_selected) & df["rent_median_1bhk"].between(*rent_range)
if search.strip():
    s = search.strip().lower()
    mask &= df["area"].str.lower().str.contains(s)
filtered = df.loc[mask].copy()

# ----- Sort view for display -----
if group_zone:
    filtered = filtered.sort_values(
        by=["zone","rent_median_1bhk","deposit_months_min","proximity_score","area"],
        ascending=[True, True, True, True, True]
    )
else:
    filtered = filtered.sort_values(by=["global_rank","area"], ascending=[True, True])

# ----- Display -----
st.subheader("Areas (Global Rank + Badge) — Median → Deposit → Proximity")

def fmt_money(v):
    try:
        return f"₹{int(v):,}"
    except Exception:
        return v

show_cols = [
    "global_rank",
    "badge",
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
    "badge": "Badge",
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

st.dataframe(view, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(
    "**Ranking logic:** Lowest median rent first → lower deposit better → closer-to-city better. "
    "Badges auto-assign based on global rank."
)
with st.expander("CSV column spec (zaruri)"):
    st.code("zone,area,region,rent_median_1bhk,rent_min_1bhk,rent_max_1bhk,deposit_ratio", language="text")
st.caption("© Open approach; private portals ki scraping nahi. User-submitted & open sources only.")
