M2O Dashboard – Mr. Brown Bakery & Coffee
A Streamlit dashboard that helps Mr. Brown Bakery & Coffee (Delhi NCR) raise menu-to-order (M2O) conversion on its delivery listings.

What it shows
- Summary: item visibility % (lowest first), other restaurant orders, CDO orders, and M2O takeaways
- KPIs: items listed, items missing an image or description, average rating, visibility %, I2C, C2O and ORS
- Funnel: impressions to menu, cart and order
- Menu additions: suggested items to add, based on search demand

Run locally (Windows)
```
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Files
- `app.py`: the dashboard
- `insights.py`: wins, concerns and takeaways
- `recommend.py`: menu addition suggestions
- Excel workbook: source data for the dashboard
