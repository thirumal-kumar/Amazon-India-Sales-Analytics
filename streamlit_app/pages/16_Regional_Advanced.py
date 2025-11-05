# 16_Regional_Advanced.py

import streamlit as st
import pandas as pd
import altair as alt
from utils import load_data, page_title, filter_controls, kpi_card

# ------------------- Page Title -------------------
page_title("📍 Advanced Regional Analysis",
           "Analyze sales, revenue, and customer behavior across Indian regions")

# ------------------- Load Data -------------------
df = load_data()
if df is None:
    st.warning("⚠ Please upload data in the Home Page first.")
    st.stop()

# Ensure required columns exist
required_cols = {
    "state": ("state", "customer_state", "ship_state"),
    "revenue": ("final_amount_inr", "revenue", "amount")
}

col_map = {}
missing = []

# Map available columns
for key, options in required_cols.items():
    found = None
    for col in options:
        if col in df.columns:
            found = col
            break
    if found:
        col_map[key] = found
    else:
        missing.append(key)

if missing:
    st.error(f"❌ Missing required fields: {missing}. Please check dataset.")
    st.stop()

# Rename to uniform names
df["state"] = df[col_map["state"]]
df["revenue"] = df[col_map["revenue"]]

# Convert to numeric
df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")

# Sidebar Filters (State, Date, Category & more)
df_filtered = filter_controls(df)

# ------------------- KPI Metrics -------------------
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Total Revenue (₹)", f"{df_filtered['revenue'].sum():,.0f}")
with c2:
    kpi_card("Total Orders", len(df_filtered))
with c3:
    kpi_card("Unique States", df_filtered["state"].nunique())

# ------------------- Top States by Revenue -------------------
st.subheader("🏆 Top Performing States by Revenue")
state_sales = (df_filtered.groupby("state")["revenue"]
               .sum()
               .sort_values(ascending=False)
               .reset_index()
               .head(10))

chart = alt.Chart(state_sales).mark_bar().encode(
    x=alt.X("revenue:Q", title="Revenue (₹)"),
    y=alt.Y("state:N", sort='-x', title="State")
).properties(width="container", height=400)

st.altair_chart(chart, use_container_width=True)

# ------------------- Revenue Contribution Pie Chart -------------------
st.subheader("🍕 Revenue Contribution by State")
state_sales["percentage"] = (state_sales["revenue"] / state_sales["revenue"].sum()) * 100

pie = alt.Chart(state_sales).mark_arc().encode(
    theta="revenue:Q",
    color="state:N",
    tooltip=["state", "revenue", "percentage"]
).properties(width=500, height=400)

st.altair_chart(pie, use_container_width=True)

# ------------------- City-Level Drilldown -------------------
st.subheader("📍 City-Level Revenue Breakdown")
if "customer_city" in df_filtered.columns:
    city_df = (df_filtered.groupby("customer_city")["revenue"]
               .sum()
               .sort_values(ascending=False)
               .reset_index()
               .head(15))

    city_chart = alt.Chart(city_df).mark_bar().encode(
        x=alt.X("revenue:Q", title="Revenue (₹)"),
        y=alt.Y("customer_city:N", sort='-x', title="City")
    ).properties(width="container", height=400)

    st.altair_chart(city_chart, use_container_width=True)
else:
    st.info("ℹ City data (customer_city) not available in this dataset.")

