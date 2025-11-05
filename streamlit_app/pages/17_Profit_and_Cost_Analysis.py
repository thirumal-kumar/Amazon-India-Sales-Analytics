import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils import load_data, filter_controls, page_title, kpi_card

# ----------------------------
# Page Title
# ----------------------------
page_title("💰 Profit & Cost Analysis", "Revenue, Cost, Discounts & Profitability Insights")

# ----------------------------
# Load Dataset
# ----------------------------
df = load_data()
if df is None or df.empty:
    st.warning("⚠ Please upload the dataset from the Home Page first.")
    st.stop()

# Ensure required columns exist
required_cols = ["final_amount_inr", "quantity", "order_date"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ Missing required column: {col}")
        st.stop()

df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df = df.dropna(subset=["order_date"])

# ----------------------------
# Apply Filters
# ----------------------------
df_filtered = filter_controls(df)

# ----------------------------
# Step 1: Cost, Discount & Profit Estimation
# ----------------------------
df_filtered["estimated_cost"] = df_filtered["final_amount_inr"] * 0.70

# Discount Loss
if "discounted_price_inr" in df_filtered.columns and "original_price_inr" in df_filtered.columns:
    df_filtered["discount_loss"] = (df_filtered["original_price_inr"] - df_filtered["discounted_price_inr"]) * df_filtered["quantity"]
else:
    df_filtered["discount_loss"] = 0

# Return Loss
if "return_status" in df_filtered.columns:
    df_filtered["return_loss"] = df_filtered.apply(
        lambda x: x["final_amount_inr"] if str(x["return_status"]).lower() == "returned" else 0, axis=1
    )
else:
    df_filtered["return_loss"] = 0

# Final Profit Calculation
df_filtered["profit"] = df_filtered["final_amount_inr"] - df_filtered["estimated_cost"] - df_filtered["discount_loss"] - df_filtered["return_loss"]
df_filtered["profit_margin"] = (df_filtered["profit"] / df_filtered["final_amount_inr"]) * 100

# ----------------------------
# KPIs
# ----------------------------
total_revenue = df_filtered["final_amount_inr"].sum()
total_cost = df_filtered["estimated_cost"].sum()
total_profit = df_filtered["profit"].sum()
profit_margin = (total_profit / total_revenue * 100) if total_revenue else 0

c1, c2, c3, c4 = st.columns(4)
kpi_card("Total Revenue", f"₹{total_revenue:,.0f}", column=c1)
kpi_card("Estimated Cost (70% of Sales)", f"₹{total_cost:,.0f}", column=c2)
kpi_card("Total Profit", f"₹{total_profit:,.0f}", column=c3)
kpi_card("Profit Margin %", f"{profit_margin:.2f}%", column=c4)

# ----------------------------
# 📈 Monthly Revenue vs Profit (FIXED – No transform_fold)
# ----------------------------
st.subheader("📈 Monthly Revenue vs Profit")

df_filtered["order_month"] = df_filtered["order_date"].dt.to_period("M").astype(str)

monthly_profit = (
    df_filtered.groupby("order_month")[["final_amount_inr", "profit"]]
    .sum()
    .reset_index()
    .rename(columns={"final_amount_inr": "Revenue", "profit": "Profit"})
)

# Melt into long format manually
monthly_long = monthly_profit.melt(id_vars="order_month", var_name="Metric", value_name="Value")

chart = (
    alt.Chart(monthly_long)
    .mark_line(point=True)
    .encode(
        x=alt.X("order_month:T", title="Month"),
        y=alt.Y("Value:Q", title="Amount (₹)"),
        color=alt.Color("Metric:N", title="Metric"),
        tooltip=["order_month", "Metric", "Value"]
    )
    .properties(height=400)
)
st.altair_chart(chart, use_container_width=True)

# ----------------------------
# 🏆 Category-wise Profitability
# ----------------------------
if "category" in df_filtered.columns:
    st.subheader("🏆 Top 10 Categories by Profit")
    category_profit = (
        df_filtered.groupby("category")["profit"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    st.bar_chart(category_profit.set_index("category"))
else:
    st.info("ℹ No 'category' column available for profit breakdown.")

# ----------------------------
# 🎯 Discount % vs Profit Impact
# ----------------------------
st.subheader("🎯 Discount % vs Profit Relationship")

if "discount_percent" in df_filtered.columns:
    scatter_data = df_filtered[df_filtered["discount_percent"].notna()]
    scatter_chart = (
        alt.Chart(scatter_data)
        .mark_circle(size=60, opacity=0.5)
        .encode(
            x=alt.X("discount_percent:Q", title="Discount %"),
            y=alt.Y("profit:Q", title="Profit (₹)"),
            tooltip=["discount_percent", "profit", "final_amount_inr"]
        )
        .properties(height=400)
    )
    st.altair_chart(scatter_chart, use_container_width=True)

# ----------------------------
# ⚠ Loss Due to Returns
# ----------------------------
st.subheader("⚠ Loss Due to Returns")
total_return_loss = df_filtered["return_loss"].sum()
st.info(f"💸 Total revenue lost due to returns: ₹{total_return_loss:,.0f}")

st.success("✅ Profit & Cost Analysis Module Loaded Successfully!")

