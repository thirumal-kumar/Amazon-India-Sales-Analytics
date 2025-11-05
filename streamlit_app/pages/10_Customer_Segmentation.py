import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils import load_data, kpi_card, page_title, filter_controls

# ---------------- Load Data ----------------
df = load_data()

# ---------------- Page Title ----------------
page_title("💎 👥 Customer Segmentation & RFM Analysis",
           "Identify high-value, loyal, inactive, and at-risk customers")

# ---------------- Filter Data ----------------
df_filtered = filter_controls(df)

if df_filtered.empty:
    st.warning("⚠ No data after filtering.")
    st.stop()

# ---------------- Validate Required Columns ----------------
required_cols = ["customer_id", "order_date", "final_amount_inr"]
for col in required_cols:
    if col not in df_filtered.columns:
        st.error(f"❌ Missing column: {col}")
        st.stop()

# Ensure order_date is datetime
df_filtered["order_date"] = pd.to_datetime(df_filtered["order_date"], errors="coerce")

# ---------------- RFM Calculation ----------------
snapshot_date = df_filtered["order_date"].max() + pd.Timedelta(days=1)

rfm = df_filtered.groupby("customer_id").agg({
    "order_date": lambda x: (snapshot_date - x.max()).days,  # Recency
    "transaction_id": "count" if "transaction_id" in df_filtered.columns else "count", # Frequency
    "final_amount_inr": "sum"  # Monetary
}).reset_index()

rfm.columns = ["customer_id", "recency", "frequency", "monetary"]

# ---------------- RFM Scoring (1 to 5) ----------------
rfm["R_score"] = pd.qcut(rfm["recency"], 5, labels=[5,4,3,2,1])  # Lower recency → better
rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1,2,3,4,5])
rfm["M_score"] = pd.qcut(rfm["monetary"], 5, labels=[1,2,3,4,5])

rfm["RFM_Score"] = rfm["R_score"].astype(str) + rfm["F_score"].astype(str) + rfm["M_score"].astype(str)

# ---------------- Customer Segmentation ----------------
def segment_customer(row):
    if row["R_score"] >= 4 and row["F_score"] >= 4:
        return "🏆 Champion"
    elif row["R_score"] >= 4 and row["F_score"] <= 2:
        return "🆕 New Customer"
    elif row["R_score"] <= 2 and row["F_score"] >= 4:
        return "⚠ At Risk"
    elif row["R_score"] <= 2 and row["F_score"] <= 2:
        return "❌ Lost"
    else:
        return "💎 Loyal"

rfm["Segment"] = rfm.apply(segment_customer, axis=1)

# ---------------- KPI Cards ----------------
total_customers = rfm.shape[0]
loyal_count = (rfm["Segment"] == "💎 Loyal").sum()
champions = (rfm["Segment"] == "🏆 Champion").sum()

col1, col2, col3 = st.columns(3)
with col1:
    kpi_card("Total Customers", total_customers)
with col2:
    kpi_card("Loyal Customers", loyal_count)
with col3:
    kpi_card("Top Champions", champions)

# ---------------- Segment Distribution Pie Chart ----------------
st.subheader("📊 Customer Segment Distribution")

segment_counts = rfm["Segment"].value_counts().reset_index()
segment_counts.columns = ["Segment", "Count"]

pie_chart = (
    alt.Chart(segment_counts)
    .mark_arc()
    .encode(
        theta="Count:Q",
        color="Segment:N",
        tooltip=["Segment", "Count"]
    )
    .properties(width=600, height=400)
)

st.altair_chart(pie_chart, use_container_width=True)

# ---------------- Top Customers (RFM Score) ----------------
st.subheader("🏅 Top 10 Customers by RFM Score")
st.dataframe(rfm.sort_values(by=["RFM_Score", "monetary"], ascending=False).head(10))

# ---------------- Export Option ----------------
st.download_button(
    label="📥 Download Full RFM Segmentation CSV",
    data=rfm.to_csv(index=False).encode("utf-8"),
    file_name="customer_rfm_segmentation.csv",
    mime="text/csv"
)

