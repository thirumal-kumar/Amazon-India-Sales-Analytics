#!/usr/bin/env python3
"""
eda_generator.py

Phase 2: Automated EDA + Insights Generator for Amazon India dataset.

Reads outputs/amazon_analytics.db and generates:
 - CSV summaries (sales_summary.csv, city_revenue.csv, category_trends.csv, brand_summary.csv, payment_share.csv, prime_summary.csv, top_products.csv)
 - PNG plots in outputs/eda/plots/
 - A simple outputs/eda/index.html linking generated artifacts

Usage:
    python eda_generator.py
"""

import os
import sqlite3
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---- Config ----
DB_PATH = "outputs/amazon_analytics.db"
OUT_DIR = "outputs/eda"
PLOTS_DIR = os.path.join(OUT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

pd.options.display.max_columns = 200

# ---- Helpers ----
def save_csv(df, name):
    path = os.path.join(OUT_DIR, name)
    df.to_csv(path, index=False)
    print("Saved CSV:", path)
    return path

def save_plot(fig, name):
    path = os.path.join(PLOTS_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("Saved plot:", path)
    return path

def read_table(sql):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, parse_dates=["order_date"])

# ---- Load data ----
print("Loading transactions from", DB_PATH)
tx = read_table("SELECT * FROM transactions")
print("Transactions rows:", len(tx))

# Ensure columns expected exist
if "order_date" in tx.columns:
    tx["order_date"] = pd.to_datetime(tx["order_date"], errors="coerce")
    tx["year"] = tx["order_date"].dt.year
    tx["month"] = tx["order_date"].dt.month
    tx["month_name"] = tx["order_date"].dt.strftime("%b")
else:
    raise RuntimeError("order_date column missing in transactions table")

# Some derived columns
tx["final_amount_inr"] = pd.to_numeric(tx["final_amount_inr"], errors="coerce").fillna(0.0)
tx["is_prime_member"] = tx.get("is_prime_member", False).astype(bool)

# ---- 1) Sales summary by year & month ----
print("Generating sales summary (year / month)...")
sales_by_year = tx.groupby("year", dropna=True)["final_amount_inr"].sum().reset_index().sort_values("year")
sales_by_year["orders"] = tx.groupby("year")["transaction_id"].count().values
save_csv(sales_by_year, "sales_by_year.csv")

fig = plt.figure(figsize=(8,4))
plt.plot(sales_by_year["year"], sales_by_year["final_amount_inr"], marker='o')
plt.title("Total Revenue by Year")
plt.xlabel("Year"); plt.ylabel("Revenue (INR)")
save_plot(fig, "revenue_by_year.png")

# monthly aggregated pivot for heatmap / trends
sales_monthly = tx.groupby(["year","month"])["final_amount_inr"].sum().reset_index()
pivot = sales_monthly.pivot(index="month", columns="year", values="final_amount_inr").fillna(0).sort_index()
save_csv(sales_monthly, "sales_monthly.csv")

fig = plt.figure(figsize=(10,6))
plt.imshow(pivot, aspect='auto', cmap='YlGnBu')
plt.colorbar(label='Revenue (INR)')
plt.yticks(range(len(pivot.index)), pivot.index)
plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45)
plt.title("Monthly Revenue Heatmap (month vs year)")
save_plot(fig, "monthly_revenue_heatmap.png")

# ---- 2) Category performance ----
print("Generating category performance...")
cat = tx.groupby("category")["final_amount_inr"].agg(['sum','count']).reset_index().rename(columns={'sum':'revenue','count':'orders'}).sort_values('revenue', ascending=False)
save_csv(cat, "category_performance.csv")

fig = plt.figure(figsize=(10,6))
topn = cat.head(12)
plt.barh(topn["category"][::-1], topn["revenue"][::-1])
plt.title("Top Categories by Revenue")
plt.xlabel("Revenue (INR)")
save_plot(fig, "top_categories.png")

# category trend by year
cat_year = tx.groupby(["year","category"])["final_amount_inr"].sum().reset_index()
save_csv(cat_year, "category_trends.csv")

# ---- 3) City performance ----
print("Generating city performance...")
city = tx.groupby("city")["final_amount_inr"].agg(['sum','count']).reset_index().rename(columns={'sum':'revenue','count':'orders'}).sort_values('revenue', ascending=False)
save_csv(city, "city_revenue.csv")

fig = plt.figure(figsize=(10,6))
top_cities = city.head(20)
plt.bar(top_cities["city"], top_cities["revenue"])
plt.xticks(rotation=75)
plt.title("Top 20 Cities by Revenue")
plt.ylabel("Revenue (INR)")
save_plot(fig, "top_cities.png")

# ---- 4) Brand / Product insights ----
print("Generating brand and product insights...")
# Read products table if exists
with sqlite3.connect(DB_PATH) as conn:
    products = pd.read_sql_query("SELECT * FROM products LIMIT 1", conn)

# top brands by revenue (join on product_id)
# if product metadata not present, attempt to aggregate by product_id
if "product_id" in tx.columns:
    top_products = tx.groupby(["product_id"])["final_amount_inr"].agg(['sum','count']).reset_index().rename(columns={'sum':'revenue','count':'orders'}).sort_values('revenue', ascending=False)
    save_csv(top_products.head(500), "top_products.csv")
    fig = plt.figure(figsize=(10,6))
    top = top_products.head(20)
    plt.barh(top["product_id"][::-1], top["revenue"][::-1])
    plt.title("Top 20 Products by Revenue")
    save_plot(fig, "top_products.png")

# ---- 5) Payment method breakdown ----
print("Generating payment method breakdown...")
pay = tx.groupby("payment_method")["final_amount_inr"].agg(['sum','count']).reset_index().rename(columns={'sum':'revenue','count':'orders'}).sort_values('revenue', ascending=False)
save_csv(pay, "payment_share.csv")

fig = plt.figure(figsize=(6,6))
plt.pie(pay["revenue"], labels=pay["payment_method"], autopct="%1.1f%%")
plt.title("Revenue Share by Payment Method")
save_plot(fig, "payment_share_pie.png")

# ---- 6) Prime vs Non-Prime analysis ----
print("Generating Prime vs Non-Prime analysis...")
prime = tx.groupby("is_prime_member")["final_amount_inr"].agg(['sum','count']).reset_index().rename(columns={'sum':'revenue','count':'orders'})
prime["avg_order_value"] = prime["revenue"] / prime["orders"]
save_csv(prime, "prime_vs_nonprime.csv")

fig = plt.figure(figsize=(6,4))
plt.bar(["Non-Prime","Prime"], prime.sort_values("is_prime_member")["revenue"])
plt.title("Revenue: Prime vs Non-Prime")
save_plot(fig, "prime_vs_nonprime.png")

# ---- 7) Seasonality / festival month analysis ----
print("Generating seasonal / monthly patterns...")
month_rev = tx.groupby(tx["order_date"].dt.month)["final_amount_inr"].sum().reindex(range(1,13)).fillna(0).reset_index().rename(columns={'order_date':'month','final_amount_inr':'revenue'})
save_csv(month_rev, "monthly_revenue.csv")
fig = plt.figure(figsize=(8,4))
plt.plot(range(1,13), month_rev["revenue"], marker='o')
plt.xticks(range(1,13))
plt.title("Monthly Revenue Pattern (Jan=1 ... Dec=12)")
save_plot(fig, "monthly_trend.png")

# ---- 8) Customer-level summary (RFM seeds) ----
print("Generating customer summary (basic)...")
cust = tx.groupby("customer_id").agg({
    "order_date": lambda s: s.max(),
    "transaction_id": "count",
    "final_amount_inr": "sum"
}).reset_index().rename(columns={"order_date":"last_order_date","transaction_id":"orders","final_amount_inr":"lifetime_value"})
cust["recency_days"] = (pd.to_datetime(tx["order_date"].max()) - pd.to_datetime(cust["last_order_date"])).dt.days
save_csv(cust.sort_values("lifetime_value", ascending=False).head(500), "top_customers.csv")
save_csv(cust.describe().reset_index(), "customer_describe.csv")

# ---- 9) Simple anomalies & outlier list (top suspicious prices) ----
print("Generating anomalies list and outliers...")
if "final_amount_inr" in tx.columns:
    q1 = tx["final_amount_inr"].quantile(0.25)
    q3 = tx["final_amount_inr"].quantile(0.75)
    iqr = q3 - q1
    cap = q3 + 5 * iqr
    suspicious = tx[tx["final_amount_inr"] > cap].sort_values("final_amount_inr", ascending=False).head(1000)
    suspicious.to_csv(os.path.join(OUT_DIR, "suspicious_high_prices.csv"), index=False)
    print("Saved suspicious_high_prices.csv (top 1000)")

# ---- 10) Quick text report (insights.txt) ----
print("Building summary text insights...")
insights = []
total_revenue = tx["final_amount_inr"].sum()
total_orders = len(tx)
avg_aov = total_revenue / total_orders if total_orders else 0
insights.append(f"Total revenue: ₹{total_revenue:,.0f}")
insights.append(f"Total orders: {total_orders:,}")
insights.append(f"Avg order value: ₹{avg_aov:,.0f}")
top_cat = cat.head(5)["category"].tolist()
insights.append(f"Top categories by revenue: {', '.join(top_cat)}")
top_city = city.head(5)["city"].tolist()
insights.append(f"Top cities by revenue: {', '.join(top_city)}")
insights.append("See CSVs and plots in outputs/eda/ and outputs/eda/plots/ for details.")

with open(os.path.join(OUT_DIR, "insights.txt"), "w") as f:
    f.write("\n".join(insights))
print("Saved insights.txt")

# ---- 11) Create an index.html linking artifacts ----
print("Creating index.html for quick navigation...")
html = "<html><head><meta charset='utf-8'><title>EDA Artifacts</title></head><body>"
html += "<h1>EDA Artifacts</h1><ul>"
for fname in sorted(os.listdir(OUT_DIR)):
    if fname == "plots": continue
    path = os.path.join(".", fname)
    if os.path.isdir(os.path.join(OUT_DIR, fname)):
        continue
    html += f"<li><a href='{path}' target='_blank'>{fname}</a></li>"
# list plots
html += "<li>Plots:<ul>"
for p in sorted(os.listdir(PLOTS_DIR)):
    html += f"<li><a href='./plots/{p}' target='_blank'>{p}</a></li>"
html += "</ul></li>"
html += "</ul></body></html>"
with open(os.path.join(OUT_DIR, "index.html"), "w") as f:
    f.write(html)
print("Saved index.html in", OUT_DIR)

print("EDA generation complete. Files in", OUT_DIR)

