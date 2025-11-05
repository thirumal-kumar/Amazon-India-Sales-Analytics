import streamlit as st
import pandas as pd
from utils import page_title, load_data, filter_controls, kpi_card

# 🏷 Page Title
page_title("💎 Customer Lifetime Value (CLV) & RFM Analysis")

# ✅ Load data
df = load_data()

# ✅ Ensure proper date format
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

# ✅ Filters — use existing function
df_filtered = filter_controls(df)

# ✅ RFM Calculations
st.subheader("📊 RFM (Recency, Frequency, Monetary) Segmentation")

latest_date = df_filtered["order_date"].max()

rfm = df_filtered.groupby("customer_id").agg(
    recency=("order_date", lambda x: (latest_date - x.max()).days),
    frequency=("transaction_id", "nunique"),
    monetary=("final_amount_inr", "sum"),
).reset_index()

# ✅ Handle NaN or missing values
rfm = rfm.fillna(0)

# ✅ Avoid duplicate bin error in qcut — safe binning
rfm["R_score"] = pd.qcut(rfm["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1])
rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])

rfm["RFM_Score"] = rfm["R_score"].astype(int) + rfm["F_score"].astype(int) + rfm["M_score"].astype(int)

# ✅ Display KPIs
c1, c2, c3 = st.columns(3)
kpi_card("Total Customers", len(rfm), "", c1)
kpi_card("Avg Monetary Value", f"₹{rfm['monetary'].mean():,.0f}", "", c2)
kpi_card("Best RFM Score (Max=15)", int(rfm["RFM_Score"].max()), "", c3)

# ✅ Display Top Customers
st.subheader("🏆 Top 10 High-Value Customers (RFM Score > 12)")
st.dataframe(rfm.sort_values("RFM_Score", ascending=False).head(10))

# ✅ Plot Recency vs Monetary
st.subheader("🌀 Recency vs Monetary Value")
st.scatter_chart(rfm, x="recency", y="monetary")

st.success("✅ CLV & RFM Module Completed Successfully!")

