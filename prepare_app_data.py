"""Pre-compute the small result files used by the Streamlit app (app.py).

Reads the raw UCI Online Retail dataset from data/ and writes CSV/JSON files to app_data/.
The cleaning logic mirrors online_retail_analysis.ipynb exactly, so the app and the notebook
always report the same numbers.

Run once (only needed if you change the cleaning logic):
    python prepare_app_data.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path("data")
OUT_DIR = Path("app_data")
OUTLIER_QTY = 50_000


def load_raw() -> pd.DataFrame:
    xlsx = DATA_DIR / "Online Retail.xlsx"
    csv = DATA_DIR / "OnlineRetail.csv"
    dtypes = {"InvoiceNo": str, "StockCode": str}
    if xlsx.exists():
        return pd.read_excel(xlsx, dtype=dtypes)
    if csv.exists():
        return pd.read_csv(csv, dtype=dtypes, encoding="ISO-8859-1")
    raise FileNotFoundError("Put 'Online Retail.xlsx' (or OnlineRetail.csv) in the data/ folder.")


def clean(raw: pd.DataFrame):
    steps = [("Raw transactions", len(raw), "Rows in the original file")]

    df = raw.drop_duplicates().copy()
    steps.append(("Exact duplicates removed", len(raw) - len(df), "Identical rows"))

    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    df["Description"] = df["Description"].str.strip()
    df["Country"] = df["Country"].str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    is_cancel = df["InvoiceNo"].str.startswith("C")
    cancellations = df[is_cancel].copy()
    sales = df[~is_cancel].copy()
    steps.append(("Cancellation lines separated", len(cancellations), "Invoices starting with 'C'"))

    def is_non_product(codes):
        return ~codes.str.match(r"^\d{5}")

    np_mask = is_non_product(sales["StockCode"])
    steps.append(("Non-product rows removed", int(np_mask.sum()),
                  "Postage, discounts, manual entries, fees, gift vouchers"))
    sales = sales[~np_mask].copy()
    cancellations = cancellations[~is_non_product(cancellations["StockCode"])].copy()

    bad = (sales["Quantity"] <= 0) | (sales["UnitPrice"] <= 0)
    steps.append(("Invalid rows removed", int(bad.sum()), "Zero or negative price or quantity"))
    sales = sales[~bad].copy()

    big_sales = sales[sales["Quantity"] >= OUTLIER_QTY]
    big_cancels = cancellations[cancellations["Quantity"].abs() >= OUTLIER_QTY]
    steps.append(("Order-and-cancel outliers removed", len(big_sales),
                  "Huge orders fully reversed minutes later"))
    sales = sales.drop(big_sales.index)
    cancellations = cancellations.drop(big_cancels.index)

    sales["Revenue"] = sales["Quantity"] * sales["UnitPrice"]
    cancellations["Value"] = cancellations["Quantity"] * cancellations["UnitPrice"]
    steps.append(("Clean sales rows", len(sales), "Rows used for the analysis"))
    return sales, cancellations, steps


def main():
    OUT_DIR.mkdir(exist_ok=True)
    raw = load_raw()
    sales, cancellations, steps = clean(raw)

    pd.DataFrame(steps, columns=["step", "rows", "note"]).to_csv(OUT_DIR / "cleaning_log.csv", index=False)

    monthly = (sales.groupby(sales["InvoiceDate"].dt.to_period("M").astype(str))["Revenue"]
               .sum().rename("revenue").reset_index().rename(columns={"InvoiceDate": "month"}))
    monthly.to_csv(OUT_DIR / "monthly_revenue.csv", index=False)

    (sales.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
     .rename("revenue").reset_index().to_csv(OUT_DIR / "country_revenue.csv", index=False))

    desc = (sales.groupby("StockCode")["Description"]
            .agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else ""))

    (sales.groupby("StockCode")["Revenue"].sum().sort_values(ascending=False).head(15)
     .rename("revenue").reset_index().assign(Description=lambda d: d["StockCode"].map(desc))
     .to_csv(OUT_DIR / "top_products.csv", index=False))

    heat = (sales.assign(Weekday=sales["InvoiceDate"].dt.day_name(), Hour=sales["InvoiceDate"].dt.hour)
            .groupby(["Weekday", "Hour"])["InvoiceNo"].nunique().rename("invoices").reset_index())
    heat.to_csv(OUT_DIR / "weekday_hour.csv", index=False)

    snapshot = sales["InvoiceDate"].max().normalize()
    prod = (sales.groupby("StockCode")
            .agg(first_sale=("InvoiceDate", "min"), last_sale=("InvoiceDate", "max"),
                 orders=("InvoiceNo", "nunique"), units=("Quantity", "sum"), revenue=("Revenue", "sum"))
            .join(desc.rename("Description")))
    prod["days_since_last_sale"] = (snapshot - prod["last_sale"].dt.normalize()).dt.days
    prod.reset_index().to_csv(OUT_DIR / "products.csv", index=False)

    total_rev = float(sales["Revenue"].sum())
    sepnov = float(sales.loc[sales["InvoiceDate"].dt.month.isin([9, 10, 11]), "Revenue"].sum())
    country_rev = sales.groupby("Country")["Revenue"].sum()
    cancel_value = float(cancellations["Value"].abs().sum())
    meta = {
        "raw_rows": int(len(raw)),
        "clean_rows": int(len(sales)),
        "n_products": int(len(prod)),
        "n_invoices": int(sales["InvoiceNo"].nunique()),
        "date_min": str(sales["InvoiceDate"].min().date()),
        "date_max": str(sales["InvoiceDate"].max().date()),
        "total_revenue": round(total_rev, 2),
        "sepnov_share": round(sepnov / total_rev, 4),
        "uk_share": round(float(country_rev["United Kingdom"] / country_rev.sum()), 4),
        "cancel_value": round(cancel_value, 2),
        "cancel_pct": round(cancel_value / total_rev, 4),
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    print("Wrote files to", OUT_DIR.resolve())


if __name__ == "__main__":
    main()
