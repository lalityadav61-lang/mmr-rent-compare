import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib
import re
from io import StringIO

# =========================
# Page & Global Styles
# =========================
st.set_page_config(page_title="Mumbai Rent Compare", layout="wide", page_icon=None)

# Minimal CSS polish (emoji-free badges)
st.markdown("""
<style>
.hero {
  padding: 18px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, #eef6ff 0%, #f7f7ff 100%);
  border: 1px solid #e9eef7;
  margin-bottom: 12px;
}
.badge-legend { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
.legend-chip {
  padding: 6px 10px; border-radius: 999px; font-weight: 600; font-size: 13px;
  border: 1px solid #e7e7e7; background: #fff;
}
.chip-budget   { background:#e8f5e9;  border-color:#c8e6c9;  color:#1b5e20; }
.chip-value    { background:#e3f2fd;  border-color:#bbdefb;  color:#0d47a1; }
.chip-mid      { background:#fff8e1;  border-color:#ffe082;  color:#9a6b00; }
.chip-uppermid { background:#fff3e0;  border-color:#ffcc80;  color:#a15d00; }
.chip-premium  { background:#ffebee;  border-color:#ffcdd2;  color:#b71c1c; }
.chip-luxury   { background:#f3e5f5;  border-color:#e1bee7;  color:#4a148c; }

.data-hint { color: #667085; font-size: 13px; }
.metric-card { border: 1px solid #eee; border-radius: 12px; padding: 14px; background: #fff; }
.small { font-size: 12px; color: #667085; }
.compare-card { border:1px solid #eee; border-radius:12px; padding:14px; background:#fff; }
.kv { display:flex; justify-content:space-between; margin:4px 0; font-size:14px; }
.kv b { color:#111; }
.kv span { color:#374151; }
</style>
""", unsafe_allow_html=True)

# =========================
# Cache-busting utilities
# =========================
def file_hash(path: str) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

@st.cache_data
def load_data(path: str, version: str) -> pd.DataFrame:
    return pd.read_csv(path)

csv_path = "mmr_rent_data.csv"
version = file_hash(csv_path)
df = load_data(csv_path, version)

# =========================
# Parsing & Ranking Logic
# =========================
for col in ["rent_median_1bhk", "rent_min_1bhk", "rent_max_1bhk"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

def parse_deposit_ratio(s: str) -> float:
    if pd.isna(s): return 4.0
    s = str(s).lower().strip()
    m = re.search(r"(\d+(\.\d+)?)\s*x", s)
    if m: return float(m.group(1))
    m2 = re.search(r"\d+(\.\d+)?", s)
    if m2: return float(m2.group(0))
    return 4.0

df["deposit_months_min"] = df["deposit_ratio"].apply(parse_deposit_ratio)

western_core = ["Bandra","Khar","Santacruz","Andheri","Jogeshwari","Goregaon","Malad","Kandivali","Borivali","Dahisar","Mira Road","Bhayander","Vasai","Naigaon","Nalasopara","Virar"]
central_core = ["Dadar","Matunga","Sion","Kurla","Ghatkopar","Vikhroli","Bhandup","Mulund","Thane","Kalwa","Mumbra","Diva","Dombivli","Kalyan","Ambernath","Badlapur","Vangani","Titwala"]
harbour_core = ["Chembur","Govandi","Mankhurd"]
south_core   = ["Lower Parel","Worli","Prabhadevi","Mahim","Wadala","Cuffe Parade","Malabar Hill","Colaba"]
navi_core    = ["Vashi","Airoli","Kopar Khairane","Ghansoli","Turbhe","Sanpada","Seawoods","Nerul","Belapur","Kharghar","Kamothe","Ulwe","New Panvel","Panvel","Taloja"]

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
    return 60

df["proximity_score"] = df.apply(lambda x: proximity_score(str(x["area"]), str(x["region"])), axis=1)

# Global sort for rank: Median → Deposit → Proximity → Area
df = df.sort_values(
    by=["rent_median_1bhk", "deposit_months_min", "proximity_score", "area"],
    ascending=[True, True, True, True]
).reset_index(drop=True)

df["global_rank"] = df["rent_median_1bhk"].rank(method="dense", ascending=True).astype("Int64")

def rank_badge(rank_val: int) -> str:
    if pd.isna(rank_val): return ""
    r = int(rank_val)
    if   1 <= r <= 15: return "Budget"
    elif 16 <= r <= 25: return "Value"
    elif 26 <= r <= 40: return "Mid"
    elif 41 <= r <= 50: return "Upper Mid"
    elif 51 <= r <= 55: return "Premium"
    else:               return "Luxury"

df["badge"] = df["global_rank"].apply(rank_badge)

# =========================
# Sidebar Filters
# =========================
st.sidebar.header("Filters")
zones = df["zone"].dropna().unique().tolist(); zones.sort()
zone_selected = st.sidebar.multiselect("Zone choose karo", zones, default=zones)

min_rent = int(df["rent_median_1bhk"].min())
max_rent = int(df["rent_median_1bhk"].max())
rent_range = st.sidebar.slider("1BHK Median (₹/mo)", min_rent, max_rent, (min_rent, max_rent), step=500)

search = st.sidebar.text_input("Area search (optional)", "")
group_zone = st.sidebar.checkbox("Zone-wise grouping (optional)", value=False)

# NEW: Sort options
sort_choice = st.sidebar.selectbox(
    "Sort by",
    ["Global Rank (asc)", "Median 1BHK (asc)", "Median 1BHK (desc)", "Area (A→Z)"],
    index=0
)

if st.sidebar.button("Reload latest data"):
    st.cache_data.clear()
    st.experimental_rerun()

# =========================
# Hero + Legend + Metrics
# =========================
st.markdown(f"""
<div class="hero">
  <h3 style="margin:0">Mumbai Rent Compare</h3>
  <div class="data-hint">Ranking: Median 1BHK → Deposit → Proximity. Badges are rank-based (emoji-free for better Windows support).</div>
  <div class="badge-legend" style="margin-top:8px;">
    <span class="legend-chip chip-budget">Budget</span>
    <span class="legend-chip chip-value">Value</span>
    <span class="legend-chip chip-mid">Mid</span>
    <span class="legend-chip chip-uppermid">Upper Mid</span>
    <span class="legend-chip chip-premium">Premium</span>
    <span class="legend-chip chip-luxury">Luxury</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Quick stats
total_areas = len(df)
cheapest_row = df.iloc[0]
highest_row  = df.iloc[-1]
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total Areas", f"{total_areas}")
    st.markdown('<div class="small">Across full MMR coverage</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Cheapest Median (1BHK)", f"₹{int(cheapest_row['rent_median_1bhk']):,}", help=f"{cheapest_row['area']} • {cheapest_row['zone']}")
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Highest Median (1BHK)", f"₹{int(highest_row['rent_median_1bhk']):,}", help=f"{highest_row['area']} • {highest_row['zone']}")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Filter dataset
# =========================
mask = df["zone"].isin(zone_selected) & df["rent_median_1bhk"].between(*rent_range)
if search.strip():
    s = search.strip().lower()
    mask &= df["area"].str.lower().str.contains(s)
filtered = df.loc[mask].copy()

# Sort for display
if group_zone:
    filtered = filtered.sort_values(
        by=["zone","rent_median_1bhk","deposit_months_min","proximity_score","area"],
        ascending=[True, True, True, True, True]
    )
else:
    if sort_choice == "Global Rank (asc)":
        filtered = filtered.sort_values(by=["global_rank","area"], ascending=[True, True])
    elif sort_choice == "Median 1BHK (asc)":
        filtered = filtered.sort_values(by=["rent_median_1bhk","area"], ascending=[True, True])
    elif sort_choice == "Median 1BHK (desc)":
        filtered = filtered.sort_values(by=["rent_median_1bhk","area"], ascending=[False, True])
    else:  # Area (A→Z)
        filtered = filtered.sort_values(by=["area"], ascending=True)

# =========================
# Table
# =========================
st.subheader("Areas (Global Rank + Badge)")

def fmt_money(v):
    try: return f"₹{int(v):,}"
    except: return v

show_cols = [
    "global_rank","badge","zone","area","region",
    "rent_median_1bhk","rent_min_1bhk","rent_max_1bhk","deposit_ratio"
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

# =========================
# Compare 2 Areas (new)
# =========================
st.markdown("### Compare 2 Areas")
areas_list = df["area"].dropna().sort_values().unique().tolist()
colA, colB = st.columns(2)
with colA:
    a1 = st.selectbox("Area A", areas_list, index=0)
with colB:
    a2 = st.selectbox("Area B", areas_list, index=min(1, len(areas_list)-1))

def area_row(a):
    return df.loc[df["area"]==a].iloc[0]

if a1 and a2:
    r1, r2 = area_row(a1), area_row(a2)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='compare-card'><h4 style='margin:0'>{a1}</h4>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Rank</b><span>{int(r1['global_rank'])}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Badge</b><span>{r1['badge']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Zone</b><span>{r1['zone']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Region</b><span>{r1['region']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Median 1BHK</b><span>₹{int(r1['rent_median_1bhk']):,}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Low–High</b><span>₹{int(r1['rent_min_1bhk']):,} – ₹{int(r1['rent_max_1bhk']):,}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Deposit</b><span>{r1['deposit_ratio']}</span></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='compare-card'><h4 style='margin:0'>{a2}</h4>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Rank</b><span>{int(r2['global_rank'])}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Badge</b><span>{r2['badge']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Zone</b><span>{r2['zone']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Region</b><span>{r2['region']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Median 1BHK</b><span>₹{int(r2['rent_median_1bhk']):,}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Low–High</b><span>₹{int(r2['rent_min_1bhk']):,} – ₹{int(r2['rent_max_1bhk']):,}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kv'><b>Deposit</b><span>{r2['deposit_ratio']}</span></div></div>", unsafe_allow_html=True)

# =========================
# Download filtered CSV
# =========================
csv_buf = StringIO()
download_cols = filtered[[
    "global_rank","zone","area","region","rent_median_1bhk","rent_min_1bhk","rent_max_1bhk","deposit_ratio","badge"
]].rename(columns={
    "global_rank":"rank",
    "badge":"rank_badge",
    "rent_median_1bhk":"median_1bhk",
    "rent_min_1bhk":"low",
    "rent_max_1bhk":"high",
})
download_cols.to_csv(csv_buf, index=False)
st.download_button("Download filtered CSV", csv_buf.getvalue(), file_name="mumbai_rent_compare_filtered.csv", mime="text/csv")

st.markdown("---")
st.caption("© Open approach; private portals ki scraping nahi. User-submitted & open sources only. Data ranges are indicative.")
