import streamlit as st
import pandas as pd
import altair as alt
from utils import load_data, kpi_card, page_title, filter_controls

# ---------------- Load Data ----------------
df = load_data()

# ---------------- Page Title ----------------
page_title("🪔🎉 Festival & Seasonal Sales Trends", "Analyze sales spikes during Diwali, Holi, and other festivals")

# ---------------- Sidebar Filters ----------------
df_filtered = filter_controls(df)

if df_filtered.empty:
    st.warning("⚠ No data available after applying filters.")
    st.stop()

# Ensure required columns exist
required_cols = ["final_amount_inr", "is_festival_sale", "festival_name", "order_year", "order_month"]
for col in required_cols:
    if col not in df_filtered.columns:
        st.error(f"❌ Missing required column: {col}")
        st.stop()

# ---------------- KPI Metrics ----------------
festival_sales = df_filtered[df_filtered["is_festival_sale"] == True]
total_festival_revenue = festival_sales["final_amount_inr"].sum()
total_festival_orders = len(festival_sales)
avg_festival_order_value = (
    total_festival_revenue / total_festival_orders if total_festival_orders > 0 else 0
)

col1, col2, col3 = st.columns(3)
with col1:
    kpi_card("Festival Revenue", total_festival_revenue, "₹")
with col2:
    kpi_card("Festival Orders", total_festival_orders)
with col3:
    kpi_card("Avg Festival Order", round(avg_festival_order_value, 2), "₹")

# ---------------- Festival Revenue by Month ----------------
st.subheader("📈 Monthly Revenue Comparison (Festival vs Non-Festival)")

df_filtered["is_festival_label"] = df_filtered["is_festival_sale"].apply(lambda x: "Festival" if x else "Non-Festival")

monthly_trends = (
    df_filtered.groupby(["order_year", "order_month", "is_festival_label"])
    ["final_amount_inr"]
    .sum()
    .reset_index()
)

monthly_trends["Period"] = monthly_trends["order_year"].astype(str) + "-" + monthly_trends["order_month"].astype(str)

chart = (
    alt.Chart(monthly_trends)
    .mark_line(point=True)
    .encode(
        x="Period:N",
        y="final_amount_inr:Q",
        color="is_festival_label:N",
        tooltip=["order_year", "order_month", "is_festival_label", "final_amount_inr"]
    )
    .properties(height=400, width=700)
)
st.altair_chart(chart, use_container_width=True)

# ---------------- Top Festival Revenue ----------------
st.subheader("🏆 Top Revenue-Generating Festivals")

top_festivals = (
    festival_sales.groupby("festival_name")["final_amount_inr"]
    .sum()
    .reset_index()
    .sort_values(by="final_amount_inr", ascending=False)
    .head(10)
)

chart2 = (
    alt.Chart(top_festivals)
    .mark_bar()
    .encode(
        x=alt.X("festival_name:N", title="Festival"),
        y=alt.Y("final_amount_inr:Q", title="Total Revenue (₹)"),
        tooltip=["festival_name", "final_amount_inr"]
    )
    .properties(height=400, width=700)
)
st.altair_chart(chart2, use_container_width=True)

# ---------------- Sales Spike Analysis ----------------
st.subheader("📆 Sales Spike During Festival vs Normal Days")

avg_sales = df_filtered.groupby("is_festival_label")["final_amount_inr"].mean().reset_index()
avg_sales["final_amount_inr"] = avg_sales["final_amount_inr"].round(2)

chart3 = (
    alt.Chart(avg_sales)
    .mark_bar()
    .encode(
        x="is_festival_label:N",
        y="final_amount_inr:Q",
        tooltip=["is_festival_label", "final_amount_inr"]
    )
    .properties(height=400, width=500)
)
st.altair_chart(chart3, use_container_width=True)

