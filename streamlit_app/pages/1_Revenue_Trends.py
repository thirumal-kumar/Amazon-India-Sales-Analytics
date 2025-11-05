import streamlit as st
import pandas as pd
import plotly.express as px
from utils import page_title, kpi_card, filter_controls

# Set page configuration
page_title("Revenue Trends", "Analyze decade-long Amazon India sales performance (2015–2025)")

# ✅ Check if data is loaded in session_state
if "data" not in st.session_state:
    st.warning("⚠ Please upload or load the dataset from the Home Page.")
    st.stop()

# ✅ Load dataset from session_state
df = st.session_state["data"]

# ✅ Standardize column names
df.columns = df.columns.str.lower().str.strip()

# ✅ Support multiple revenue column names (local & cloud compatibility)
revenue_columns = ["selling_price", "discounted_price_inr", "final_amount_inr", "subtotal_inr"]
revenue_col = next((col for col in revenue_columns if col in df.columns), None)

if revenue_col is None:
    st.error("❌ No valid revenue column found. Expected one of: selling_price, discounted_price_inr, final_amount_inr, subtotal_inr")
    st.stop()

# ✅ Convert order_date to datetime if it exists
if "order_date" in df.columns:
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
else:
    st.error("❌ Required column 'order_date' is missing from dataset.")
    st.stop()

# ✅ Apply Filters (Year, Category, State, City)
df_filtered = filter_controls(df)

# ✅ KPI Cards
total_revenue = df_filtered[revenue_col].sum()
total_orders = len(df_filtered)
avg_order_value = df_filtered[revenue_col].mean()

c1, c2, c3 = st.columns(3)
kpi_card("Total Revenue", f"{total_revenue:,.0f} ₹", col=c1)
kpi_card("Total Orders", f"{total_orders:,}", col=c2)
kpi_card("Avg Order Value", f"{avg_order_value:,.0f} ₹", col=c3)

# ✅ Monthly Revenue Trend
df_filtered["year_month"] = df_filtered["order_date"].dt.to_period("M").astype(str)
monthly_revenue = df_filtered.groupby("year_month")[revenue_col].sum().reset_index()

st.subheader("📈 Monthly Sales Trend")
fig = px.line(monthly_revenue, x="year_month", y=revenue_col,
              labels={revenue_col: "Revenue (₹)", "year_month": "Month"},
              title="Monthly Revenue Trend")
fig.update_traces(mode="lines+markers")
st.plotly_chart(fig, use_container_width=True)

# ✅ Success Message
st.success("✅ Revenue Trends loaded successfully!")
