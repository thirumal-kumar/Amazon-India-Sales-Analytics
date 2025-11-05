import streamlit as st
import pandas as pd
import altair as alt
from utils import filter_controls, kpi_card, load_data

# ------------------------------------------
# Page Title
# ------------------------------------------
st.title("📊 📦 Product & Brand Insights")
st.caption("Identify top-performing products & brands")

# ------------------------------------------
# Load Data
# ------------------------------------------
df = load_data()
if df is None:
    st.warning("⚠ Please upload data from the Home Page to proceed.")
    st.stop()

# ------------------------------------------
# Auto-detect column names
# ------------------------------------------
def detect_column(possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

product_col = detect_column(["product", "product_name", "item_name", "title"])
brand_col = detect_column(["brand", "brand_name", "manufacturer"])
price_col = detect_column(["selling_price", "discounted_price_inr", "original_price_inr"])
quantity_col = detect_column(["quantity", "qty", "units"])
revenue_col = detect_column(["revenue", "final_amount_inr", "order_amount", "subtotal_inr"])

# Create revenue column if missing but price & quantity exist
if revenue_col is None:
    if price_col and quantity_col:
        df["revenue"] = df[price_col] * df[quantity_col]
        revenue_col = "revenue"
    else:
        df["revenue"] = 0
        revenue_col = "revenue"

# ------------------------------------------
# Apply Filters
# ------------------------------------------
df_filtered = filter_controls(df)

# ------------------------------------------
# KPI Cards
# ------------------------------------------
total_revenue = df_filtered[revenue_col].sum()
total_orders = len(df_filtered)
unique_products = df_filtered[product_col].nunique() if product_col else 0

col1, col2, col3 = st.columns(3)
kpi_card("Total Revenue", f"{total_revenue:,.0f} ₹", column=col1)
kpi_card("Total Orders", f"{total_orders:,}", column=col2)
kpi_card("Unique Products", f"{unique_products:,}", column=col3)

# ------------------------------------------
# Top 10 Products by Revenue
# ------------------------------------------
st.subheader("🏆 Top 10 Products by Revenue")
if product_col:
    product_data = (
        df_filtered.groupby(product_col)[revenue_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    if product_data[revenue_col].sum() > 0:
        chart = alt.Chart(product_data).mark_bar().encode(
            x=alt.X(product_col, sort="-y", title="Product"),
            y=alt.Y(revenue_col, title="Revenue (₹)"),
            tooltip=[product_col, revenue_col]
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("⚠ Revenue data unavailable for products.")
else:
    st.warning("⚠ No valid product column found in dataset.")

# ------------------------------------------
# Top 10 Brands by Revenue
# ------------------------------------------
st.subheader("🏷 Top 10 Brands by Revenue")
if brand_col:
    brand_data = (
        df_filtered.groupby(brand_col)[revenue_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    if brand_data[revenue_col].sum() > 0:
        chart = alt.Chart(brand_data).mark_bar().encode(
            x=alt.X(brand_col, sort="-y", title="Brand"),
            y=alt.Y(revenue_col, title="Revenue (₹)"),
            tooltip=[brand_col, revenue_col]
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("⚠ No revenue available for brands.")
else:
    st.warning("⚠ No valid brand column found in dataset.")

# ------------------------------------------
# Price vs Quantity Scatter Plot
# ------------------------------------------
st.subheader("📉 Price vs Quantity Sold")
if price_col and quantity_col:
    scatter_df = df_filtered[df_filtered[price_col] > 0]
    if not scatter_df.empty:
        scatter = alt.Chart(scatter_df).mark_circle(size=60, opacity=0.5).encode(
            x=alt.X(price_col, title="Selling Price (₹)"),
            y=alt.Y(quantity_col, title="Quantity Sold"),
            tooltip=[product_col, price_col, quantity_col] if product_col else [price_col, quantity_col]
        )
        st.altair_chart(scatter, use_container_width=True)
    else:
        st.info("⚠ No valid price data available for scatter plot.")
else:
    st.warning("⚠ Missing price or quantity data for scatter plot.")

# ------------------------------------------
# Footer
# ------------------------------------------
st.success("✅ Product & Brand Insights loaded successfully!")

