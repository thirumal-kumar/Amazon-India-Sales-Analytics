import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# ---------------------------------------------------
# 🎨 Page Configuration
# ---------------------------------------------------
st.set_page_config(
    page_title="🛒 Amazon India: A Decade of Sales Analytics",
    layout="wide",
    page_icon="🛍️"
)

# ---------------------------------------------------
# 🧠 Load Data
# ---------------------------------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect("amazon_analytics.db")
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["year"] = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.strftime("%b")
    else:
        st.error("⚠️ 'order_date' column missing in database.")
    return df

df = load_data()

# ---------------------------------------------------
# 🧰 Sidebar Filters
# ---------------------------------------------------
st.sidebar.header("🔍 Filters")

years = sorted(df["year"].dropna().unique())
categories = sorted(df["category"].dropna().unique())
cities = sorted(df["city"].dropna().unique())
payments = sorted(df["payment_method"].dropna().unique())

selected_years = st.sidebar.multiselect("📆 Select Year(s)", years, default=years[-3:])
selected_categories = st.sidebar.multiselect("🏷️ Select Categories", categories, default=categories[:5])
selected_cities = st.sidebar.multiselect("🌆 Select Cities", cities[:10])
selected_payments = st.sidebar.multiselect("💳 Select Payment Methods", payments)

filtered_df = df.copy()
if selected_years:
    filtered_df = filtered_df[filtered_df["year"].isin(selected_years)]
if selected_categories:
    filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]
if selected_cities:
    filtered_df = filtered_df[filtered_df["city"].isin(selected_cities)]
if selected_payments:
    filtered_df = filtered_df[filtered_df["payment_method"].isin(selected_payments)]

# ---------------------------------------------------
# 🧮 KPI Metrics
# ---------------------------------------------------
st.title("🛒 Amazon India: A Decade of Sales Analytics")
st.caption("Explore sales performance from 2015–2025 using interactive filters and charts")

total_sales = filtered_df["final_amount_inr"].sum()
total_orders = len(filtered_df)
avg_order_value = total_sales / total_orders if total_orders else 0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Revenue (₹)", f"{total_sales:,.0f}")
col2.metric("📦 Total Orders", f"{total_orders:,}")
col3.metric("💳 Avg Order Value (₹)", f"{avg_order_value:,.0f}")

# ---------------------------------------------------
# 📈 Sales Over Time
# ---------------------------------------------------
st.subheader("📊 Sales Trend Over Time")

sales_trend = (
    filtered_df.groupby("order_date")["final_amount_inr"].sum().reset_index()
    if not filtered_df.empty else pd.DataFrame(columns=["order_date", "final_amount_inr"])
)

if not sales_trend.empty:
    fig_trend = px.line(
        sales_trend,
        x="order_date",
        y="final_amount_inr",
        title="Daily Sales Trend",
        markers=True
    )
    st.plotly_chart(fig_trend, use_container_width=False, width="stretch")
else:
    st.warning("No data available for selected filters.")

# ---------------------------------------------------
# 🏙️ City-Wise Performance
# ---------------------------------------------------
st.subheader("🌆 Top Performing Cities")

city_sales = (
    filtered_df.groupby("city")["final_amount_inr"].sum()
    .reset_index()
    .sort_values("final_amount_inr", ascending=False)
    .head(10)
)

if not city_sales.empty:
    fig_city = px.bar(
        city_sales,
        x="city",
        y="final_amount_inr",
        title="Top 10 Cities by Sales",
        text_auto=True,
        color="final_amount_inr",
        color_continuous_scale="Tealgrn"
    )
    st.plotly_chart(fig_city, use_container_width=False, width="stretch")

# ---------------------------------------------------
# 🏷️ Category-Wise Breakdown
# ---------------------------------------------------
st.subheader("🏷️ Category-Wise Revenue Share")

category_sales = (
    filtered_df.groupby("category")["final_amount_inr"].sum()
    .reset_index()
    .sort_values("final_amount_inr", ascending=False)
)

if not category_sales.empty:
    fig_pie = px.pie(
        category_sales,
        names="category",
        values="final_amount_inr",
        title="Revenue Share by Category",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig_pie, use_container_width=False, width="stretch")

# ---------------------------------------------------
# 💳 Payment Method Insights
# ---------------------------------------------------
st.subheader("💳 Payment Method Distribution")

payment_breakdown = (
    filtered_df.groupby("payment_method")["final_amount_inr"].sum()
    .reset_index()
    .sort_values("final_amount_inr", ascending=False)
)

if not payment_breakdown.empty:
    fig_payment = px.bar(
        payment_breakdown,
        x="payment_method",
        y="final_amount_inr",
        title="Payment Method Contribution",
        text_auto=True,
        color="payment_method"
    )
    st.plotly_chart(fig_payment, use_container_width=False, width="stretch")

# ---------------------------------------------------
# 📅 Monthly Trend Comparison
# ---------------------------------------------------
st.subheader("📅 Monthly Sales Comparison")

monthly_sales = (
    filtered_df.groupby(["year", "month"])["final_amount_inr"].sum()
    .reset_index()
    .sort_values(["year", "month"])
)

if not monthly_sales.empty:
    fig_month = px.bar(
        monthly_sales,
        x="month",
        y="final_amount_inr",
        color="year",
        barmode="group",
        title="Monthly Sales Trend (by Year)"
    )
    st.plotly_chart(fig_month, use_container_width=False, width="stretch")

# ---------------------------------------------------
# 🧾 Data Table
# ---------------------------------------------------
st.subheader("📋 Raw Data Preview")
st.dataframe(filtered_df.head(100), use_container_width=False, width="stretch")

st.success("✅ Dashboard ready! Explore filters and visual insights.")

