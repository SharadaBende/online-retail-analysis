# Online Retail: Data Cleaning, EDA and Slow-Moving Inventory Analysis

**Live dashboard:** https://online-retail-analysis-demo.streamlit.app/

**Stack:** Python, Pandas, NumPy, Matplotlib, Seaborn, Jupyter Notebook, Streamlit
**Data:** UCI Online Retail dataset (541,909 transactions, 1 Dec 2010 to 9 Dec 2011, UK-based online gift retailer)

## Results (all computed by the notebook)

**Cleaning**
- Removed 5,268 exact duplicate rows.
- Separated 9,251 cancellation lines (invoices starting with `C`) into their own table.
- Removed 2,406 non-product rows (postage, discounts, manual entries, fees, gift vouchers) using a 5-digit stock-code rule.
- Removed 2,480 invalid rows (zero or negative price/quantity).
- Excluded 2 order-and-cancel outliers (74,215 and 80,995 units, each fully reversed minutes later) that distorted top-product revenue.
- Clean sales table: 522,502 rows, 3,790 products, 19,771 invoices, about 10.0M GBP revenue.

**Slow-moving inventory** (days since last sale, measured from the last date in the data)
- 635 dormant products (no sale in more than 90 days): 16.8% of products but only 1.9% of revenue.
- Exported as `outputs/clearance_candidates.csv` for clearance review.

**Demand patterns**
- Sep to Nov = 36% of all revenue (41% of Jan to Nov 2011); November is the peak month.
- UK = 85% of revenue.
- Busiest weekday is Thursday, busiest hour is 12:00; there are no Saturday sales in the data.
- Cancellations are about 2.3% of sales revenue.
- Top product by revenue: REGENCY CAKESTAND 3 TIER.

## Interactive dashboard
**Live demo:** https://online-retail-analysis-demo.streamlit.app/

A Streamlit app (`app.py`) lets you explore the results: change the dormant threshold with a slider, search the clearance list and download it as CSV.
```
streamlit run app.py
```
It reads small precomputed files from `app_data/` (built by `prepare_app_data.py`), so it needs no raw data to run.

## Project structure
```
online-retail-analysis/
├── online_retail_analysis.ipynb   # full analysis, already executed (outputs included)
├── app.py                         # Streamlit dashboard
├── prepare_app_data.py            # builds app_data/ from the raw dataset
├── app_data/                      # small precomputed files used by the app
├── requirements.txt               # app dependencies (used for deployment)
├── requirements-notebook.txt      # adds Jupyter for running the notebook
├── data/                          # raw dataset (not committed to git)
└── outputs/
    ├── figures/                   # 5 charts (PNG)
    ├── clearance_candidates.csv   # dormant products for review
    └── product_status_all.csv     # status of every product
```

## Run it
```
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-notebook.txt
jupyter notebook online_retail_analysis.ipynb
```
The notebook reads `data/Online Retail.xlsx`. Tunable parameters (`DORMANT_DAYS`, `OUTLIER_QTY`) are at the top.

## Method notes and limitations
- "Product" means a 5-digit stock code (with optional letter suffix).
- Rows with a missing `CustomerID` are kept, since the analysis is product-level.
- There is no stock-level data, so "dormant" means no sales in the data window. Seasonal or discontinued items need a manual check before any clearance decision. A sensitivity table in the notebook shows how the dormant count changes with the threshold.
- December 2011 is a partial month (data ends 9 Dec).

## Data source
Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33 (CC BY 4.0)