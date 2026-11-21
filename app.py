"""Streamlit dashboard: Online Retail cleaning, EDA and slow-moving inventory analysis.

Run locally:  streamlit run app.py
The app reads small precomputed files from app_data/ (built by prepare_app_data.py),
so it starts fast and does not need the 23 MB raw dataset.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Online Retail: Slow-Moving Inventory", page_icon="📦", layout="wide")
sns.set_theme(style="whitegrid")

DATA = Path(__file__).parent / "app_data"
GITHUB = "https://github.com/SharadaBende/online-retail-analysis"
STATUS_ORDER = ["Active", "Slow", "Very slow", "Dormant"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_data
def load():
    meta = json.loads((DATA / "meta.json").read_text())
    log = pd.read_csv(DATA / "cleaning_log.csv")
    monthly = pd.read_csv(DATA / "monthly_revenue.csv")
    country = pd.read_csv(DATA / "country_revenue.csv")
    top = pd.read_csv(DATA / "top_products.csv", dtype={"StockCode": str})
    heat = pd.read_csv(DATA / "weekday_hour.csv")
    prod = pd.read_csv(DATA / "products.csv", dtype={"StockCode": str},
                       parse_dates=["first_sale", "last_sale"])
    return meta, log, monthly, country, top, heat, prod


def classify(days: pd.Series, dormant_days: int) -> pd.Series:
    return pd.cut(days, bins=[-1, 30, 60, dormant_days, np.inf], labels=STATUS_ORDER)


meta, log, monthly, country, top, heat, prod = load()

# ---------------- sidebar ----------------
st.sidebar.header("Settings")
dormant_days = st.sidebar.slider("Dormant threshold (days with no sale)", 61, 365, 90)
st.sidebar.caption(
    "A product is **Dormant** if its last sale was more than this many days before the "
    f"end of the data ({meta['date_max']}). The default of 90 days is what the notebook and README use."
)
st.sidebar.markdown(f"[View code on GitHub]({GITHUB})")

prod = prod.assign(status=classify(prod["days_since_last_sale"], dormant_days))
dormant = prod[prod["status"] == "Dormant"]
dormant_pct_products = len(dormant) / len(prod)
dormant_pct_revenue = dormant["revenue"].sum() / prod["revenue"].sum()

# ---------------- header ----------------
st.title("📦 Online Retail: Cleaning, EDA and Slow-Moving Inventory")
st.caption(
    f"UCI Online Retail dataset: {meta['raw_rows']:,} transactions, "
    f"{meta['date_min']} to {meta['date_max']}. Python, Pandas, Matplotlib, Seaborn, Streamlit."
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Clean transactions", f"{meta['clean_rows']:,}", f"from {meta['raw_rows']:,} raw", delta_color="off")
k2.metric("Products analysed", f"{meta['n_products']:,}")
k3.metric(f"Dormant products (>{dormant_days}d)", f"{len(dormant):,}", f"{dormant_pct_products:.1%} of products", delta_color="off")
k4.metric("Revenue from dormant products", f"{dormant_pct_revenue:.1%}", f"total £{meta['total_revenue']:,.0f}", delta_color="off")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Demand patterns", "Slow-moving inventory", "Method"])

# ---------------- tab 1: overview ----------------
with tab1:
    st.subheader("Data cleaning funnel")
    funnel = log.rename(columns={"step": "Step", "rows": "Rows", "note": "What it is"})
    st.dataframe(funnel.assign(Rows=funnel["Rows"].map("{:,}".format)), hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Monthly revenue")
        month_num = monthly["month"].str[-2:].astype(int)
        colors = ["#d95f02" if m in (9, 10, 11) else "#7f9fbf" for m in month_num]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(monthly["month"], monthly["revenue"], color=colors)
        ax.set_ylabel("Revenue (£)")
        ax.grid(axis="x", visible=False)
        plt.xticks(rotation=60)
        st.pyplot(fig)
        st.caption(
            f"Sep to Nov (orange) = {meta['sepnov_share']:.0%} of all revenue. "
            "December 2011 is a partial month (data ends 9 Dec)."
        )
    with c2:
        st.subheader("Top 10 products by revenue")
        t = top.head(10).iloc[::-1]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.barh([f"{c} | {d[:26]}" for c, d in zip(t["StockCode"], t["Description"])], t["revenue"], color="#e15759")
        ax.set_xlabel("Revenue (£)")
        ax.grid(axis="y", visible=False)
        st.pyplot(fig)
        st.caption("Computed after excluding the two order-and-cancel outliers.")

# ---------------- tab 2: demand ----------------
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Country mix")
        show_uk = st.checkbox("Include the United Kingdom", value=False)
        data = country if show_uk else country[country["Country"] != "United Kingdom"]
        data = data.head(10).iloc[::-1]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.barh(data["Country"], data["revenue"], color="#4c78a8")
        ax.set_xlabel("Revenue (£)")
        ax.grid(axis="y", visible=False)
        st.pyplot(fig)
        st.caption(f"The UK is {meta['uk_share']:.0%} of revenue, so it is hidden by default to show the other markets.")
    with c2:
        st.subheader("Demand by weekday and hour")
        pivot = heat.pivot(index="Weekday", columns="Hour", values="invoices").fillna(0)
        pivot = pivot.reindex([d for d in WEEKDAYS if d in pivot.index])
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.heatmap(pivot, cmap="YlOrRd", linewidths=0.3, cbar_kws={"label": "Unique invoices"}, ax=ax)
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("")
        st.pyplot(fig)
        busiest_day = pivot.sum(axis=1).idxmax()
        busiest_hour = int(pivot.sum(axis=0).idxmax())
        st.caption(f"Busiest day: {busiest_day}. Busiest hour: {busiest_hour}:00. There are no Saturday sales in the data.")

# ---------------- tab 3: slow-moving ----------------
with tab3:
    st.subheader(f"Products by days since last sale (dormant = more than {dormant_days} days)")
    summary = (prod.groupby("status", observed=True)
               .agg(products=("revenue", "size"), revenue=("revenue", "sum")).reindex(STATUS_ORDER))
    summary["pct_products"] = summary["products"] / summary["products"].sum() * 100
    summary["pct_revenue"] = summary["revenue"] / summary["revenue"].sum() * 100

    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(7, 4))
        x = np.arange(len(STATUS_ORDER))
        ax.bar(x - 0.2, summary["pct_products"], 0.4, label="% of products", color="#4c78a8")
        ax.bar(x + 0.2, summary["pct_revenue"], 0.4, label="% of revenue", color="#f58518")
        ax.set_xticks(x)
        ax.set_xticklabels(STATUS_ORDER)
        ax.set_ylabel("Percent")
        ax.legend()
        ax.grid(axis="x", visible=False)
        st.pyplot(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(prod["days_since_last_sale"], bins=40, color="#7f9fbf")
        ax.axvline(dormant_days, color="red", ls="--", label=f"Dormant > {dormant_days} days")
        ax.set_xlabel("Days since last sale")
        ax.set_ylabel("Products")
        ax.legend()
        st.pyplot(fig)

    st.dataframe(
        summary.rename(columns={"products": "Products", "revenue": "Revenue (£)",
                                "pct_products": "% of products", "pct_revenue": "% of revenue"})
        .style.format({"Products": "{:,.0f}", "Revenue (£)": "{:,.0f}", "% of products": "{:.1f}", "% of revenue": "{:.1f}"})
    )

    st.subheader("How sensitive is the dormant count to the threshold?")
    rows = []
    for d in [60, 90, 120, 180, 270]:
        m = prod["days_since_last_sale"] > d
        rows.append({"Threshold (days)": d, "Dormant products": int(m.sum()),
                     "% of products": round(m.mean() * 100, 1),
                     "% of revenue": round(prod.loc[m, "revenue"].sum() / prod["revenue"].sum() * 100, 1)})
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.subheader("Clearance review list")
    query = st.text_input("Search by product name or code", "")
    table = (dormant.assign(avg_unit_price=lambda d: d["revenue"] / d["units"])
             .sort_values("days_since_last_sale", ascending=False)
             [["StockCode", "Description", "last_sale", "days_since_last_sale", "orders", "units", "revenue", "avg_unit_price"]])
    if query:
        mask = (table["Description"].fillna("").str.contains(query, case=False, regex=False)
                | table["StockCode"].str.contains(query, case=False, regex=False))
        table = table[mask]
    st.caption(f"{len(table):,} products shown")
    st.dataframe(table, hide_index=True)
    st.download_button("Download list as CSV", table.to_csv(index=False).encode("utf-8"),
                       file_name="clearance_candidates.csv", mime="text/csv")

# ---------------- tab 4: method ----------------
with tab4:
    st.markdown(f"""
**Cleaning steps (in order)**
1. Remove exact duplicate rows.
2. Separate cancellations (invoice numbers starting with `C`).
3. Remove non-product codes: a real product code starts with 5 digits, so postage, discounts, manual entries, fees and gift vouchers are dropped.
4. Remove rows with zero or negative price or quantity.
5. Remove order-and-cancel outliers: single lines of {50_000:,}+ units that were fully reversed minutes later.

**Slow-moving classification:** each product is classified by days since its last sale, measured from the last date in the data ({meta['date_max']}): Active (0-30), Slow (31-60), Very slow (61 to the threshold), Dormant (more than the threshold).

**Limitations**
- There is no stock-level data, so "dormant" means *no sales in the data window*. Seasonal or discontinued items need a manual check before any clearance decision.
- The data covers about 13 months, and December 2011 is a partial month.
- Rows with a missing CustomerID are kept, because the analysis is at product level.

**Data:** Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33 (CC BY 4.0)

**Code:** [{GITHUB}]({GITHUB})
""")
