import streamlit as st
import pandas as pd
import numpy as np
from utils import load_data, filter_controls, page_title, kpi_card

st.set_page_config(page_title="Inventory & Demand Forecasting", layout="wide")

# ----------------------------
# Page Header
# ----------------------------
page_title("📦 Inventory & Demand Forecasting", "Forecast product demand & optimize stock levels")

# ----------------------------
# Load Dataset
# ----------------------------
df = load_data()

# ----------------------------
# Handle Missing Column Names (Auto-Fix)
# ----------------------------
column_mapping = {
    "order_date": ["order_date", "date", "order_timestamp"],
    "product": ["product", "product_name", "item", "product_title"],
    "product_id": ["product_id", "asin", "product_code", "sku"],
    "quantity": ["quantity", "qty", "units", "order_quantity"]
}

for required, possible in column_mapping.items():
    for col in possible:
        if col in df.columns:
            df.rename(columns={col: required}, inplace=True)
            break

# Now check if any required column is still missing
missing = [col for col in column_mapping.keys() if col not in df.columns]
if missing:
    st.error(f"❌ Required columns missing even after mapping: {missing}")
    st.stop()

# ----------------------------
# Ensure proper dtypes
# ----------------------------
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df = df.dropna(subset=["order_date"])
df["order_year"] = df["order_date"].dt.year
df["order_month"] = df["order_date"].dt.to_period("M")

# ----------------------------
# Sidebar Filters
# ----------------------------
df_filtered = filter_controls(df)

# ----------------------------
# KPI Metrics
# ----------------------------
col1, col2, col3 = st.columns(3)
kpi_card("Total Transactions", len(df_filtered), col1)
kpi_card("Unique Products", df_filtered["product_id"].nunique(), col2)
kpi_card("Total Revenue", f"₹{df_filtered['final_amount_inr'].sum():,.0f}", col3)

# ----------------------------
# Monthly Demand Trend
# ----------------------------
st.markdown("### 📈 Overall Monthly Demand (Total Quantity Ordered)")
monthly_demand = df_filtered.groupby("order_month")["quantity"].sum().reset_index()
monthly_demand["order_month"] = monthly_demand["order_month"].astype(str)
st.line_chart(monthly_demand.set_index("order_month"))

# ----------------------------
# Product-wise Forecast (Simple)
# ----------------------------
st.markdown("### 🔮 Product Demand Forecasting")
top_products = df_filtered.groupby("product")["quantity"].sum().sort_values(ascending=False).head(10).index
selected_product = st.selectbox("Select Product", top_products)

product_data = df_filtered[df_filtered["product"] == selected_product]
product_monthly = product_data.groupby("order_month")["quantity"].sum().reset_index()
product_monthly["order_month"] = product_monthly["order_month"].astype(str)

# Moving Average Forecast
if len(product_monthly) >= 3:
    forecast = product_monthly["quantity"].rolling(3).mean().iloc[-1]
    st.success(f"📌 Forecast for next month of **{selected_product}**: **{int(forecast)} units**")
else:
    st.warning("Not enough data to forecast (need ≥ 3 months).")

st.bar_chart(product_monthly.set_index("order_month"))

# ----------------------------
# Simulated Stock Alerts
# ----------------------------
st.markdown("### ⚠ Low Stock Alert (Simulated)")
df_filtered["stock"] = np.random.randint(10, 500, size=len(df_filtered))
low_stock = df_filtered[df_filtered["stock"] < 50][["product", "stock"]].drop_duplicates().head(20)
st.dataframe(low_stock)

st.success("✅ Inventory & Demand Forecasting Module Loaded Successfully!")

