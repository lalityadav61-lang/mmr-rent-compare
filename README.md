# MMR Rent Compare (Hinglish)

Zones → Areas sorted by **1BHK median rent (ascending)**.

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Cloud - Free)
1. Push this folder to a **public GitHub repo**.
2. Open https://share.streamlit.io
3. **New app** → select your repo → `app.py` → Deploy.
4. Add your CSV edits by committing to GitHub; app auto-updates.

## CSV Columns
```
zone,area,region,rent_median_1bhk,rent_min_1bhk,rent_max_1bhk,deposit_ratio
```