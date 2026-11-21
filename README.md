# Online Retail: Data Cleaning, EDA and Slow-Moving Inventory Analysis

Python, Pandas, NumPy, Matplotlib, Seaborn, Jupyter Notebook
Dataset: UCI Online Retail (about 540K transactions, Dec 2010 to Dec 2011)

## What it does
1. Cleans the transactions: removes exact duplicates, separates cancellations,
   filters non-product stock codes, drops invalid rows and order-and-cancel outliers.
2. EDA: seasonality, country mix, top products, weekday x hour demand.
3. Slow-moving inventory: classifies each product by days since last sale
   (Active / Slow / Very slow / Dormant) and exports a clearance-review list.

## Run it
```
pip install -r requirements.txt
# put the dataset in data/ (see data/README.md)
jupyter notebook online_retail_analysis.ipynb
```

## Outputs
- `outputs/figures/` charts
- `outputs/clearance_candidates.csv` dormant products for review
- `outputs/product_status_all.csv` status for every product

## Results
Run the notebook and copy the numbers from its final "Key findings" cell here.

## Limitations
No stock-level data: "dormant" means no sales in the data window, so seasonal or
discontinued items need a manual check before any clearance decision.
