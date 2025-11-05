import streamlit as st
import pandas as pd
import altair as alt
from utils import load_data, kpi_card, page_title, filter_controls

# ------------------------------
# Page Setup
# ------------------------------
st.set_page_config(page_title="Product Performance", layout="wide")
page_title("📦 Product Performance", "Top-performing products, brands, and categories")

# ------------------------------
# Load Data
# ------------------------------
df = load_data()

if df.empty:
    st.warning("⚠️ No data found. Please run the full pipeline.")
    st.stop()

required_cols = ["order_year", "order_month", "product_name", "brand", "category", "final_amount_inr"]
if any(col not in df.columns for col in required_cols):
    st.error("❌ Missing required columns in dataset. Please re-run pipeline.")
    st.stop()

# Apply filters from sidebar
df_filtered = filter_controls(df)

# ------------------------------
# KPIs
# ------------------------------
col1, col2, col3 = st.columns(3)

total_revenue = df_filtered["final_amount_inr"].sum()
total_products = df_filtered["product_name"].nunique()
top_product = (
    df_filtered.groupby("product_name")["final_amount_inr"]
    .sum()
    .sort_values(ascending=False)
    .idxmax()
)

# ✅ No prefix/suffix – match utils.kpi_card() signature
kpi_card("Total Revenue (₹)", f"{total_revenue:,.0f}", col1)
kpi_card("Unique Products", total_products, col2)
kpi_card("Top Product", top_product, col3)

# ------------------------------
# Top 10 Products by Revenue
# ------------------------------
st.subheader("🏆 Top 10 Products by Revenue")

top_products = (
    df_filtered.groupby("product_name")["final_amount_inr"]
    .sum()
    .reset_index()
    .sort_values(by="final_amount_inr", ascending=False)
    .head(10)
)

chart = (
    alt.Chart(top_products)
    .mark_bar()
    .encode(
        x="final_amount_inr:Q",
        y=alt.Y("product_name:N", sort="-x"),
        tooltip=["product_name", "final_amount_inr"]
    )
    .properties(height=400)
)

st.altair_chart(chart, use_container_width=True)

# ------------------------------
# Top Brands by Revenue
# ------------------------------
st.subheader("🏷️ Top 10 Brands by Revenue")

top_brands = (
    df_filtered.groupby("brand")["final_amount_inr"]
    .sum()
    .reset_index()
    .sort_values(by="final_amount_inr", ascending=False)
    .head(10)
)

brand_chart = (
    alt.Chart(top_brands)
    .mark_bar()
    .encode(
        x="final_amount_inr:Q",
        y=alt.Y("brand:N", sort="-x"),
        tooltip=["brand", "final_amount_inr"]
    )
    .properties(height=400)
)

st.altair_chart(brand_chart, use_container_width=True)

# ------------------------------
# Monthly Revenue Trend by Category
# ------------------------------
st.subheader("📅 Monthly Revenue by Category")

df_filtered["YearMonth"] = df_filtered["order_year"].astype(str) + "-" + df_filtered["order_month"].astype(str).str.zfill(2)

monthly_category = (
    df_filtered.groupby(["YearMonth", "category"])["final_amount_inr"]
    .sum()
    .reset_index()
)

line_chart = (
    alt.Chart(monthly_category)
    .mark_line()
    .encode(
        x="YearMonth:T",
        y="final_amount_inr:Q",
        color="category:N",
        tooltip=["YearMonth", "category", "final_amount_inr"]
    )
    .properties(height=400)
)

st.altair_chart(line_chart, use_container_width=True)

# End of page
st.success("✅ Product Performance Page Loaded Successfully!")

