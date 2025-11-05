import streamlit as st
import pandas as pd
from utils import load_data, page_title, kpi_card, filter_controls

# Page title
page_title("💳🚚 Payment & Delivery Insights", "How India pays and how fast orders arrive")

# Load dataset
df = load_data()

# Filter controls
df_filtered = filter_controls(df)

# --- KPI Metrics ---
total_orders = len(df_filtered)
total_revenue = df_filtered["final_amount_inr"].sum()
avg_delivery = df_filtered["delivery_days"].mean()

col1, col2, col3 = st.columns(3)
kpi_card("Total Orders", total_orders, col1)
kpi_card("Total Revenue (₹)", total_revenue, col2)
kpi_card("Avg Delivery Days", round(avg_delivery, 2), col3)

# --- Payment Method Share ---
st.subheader("📊 Payment Method Distribution")
payment_share = df_filtered["payment_method"].value_counts().reset_index()
payment_share.columns = ["Payment Method", "Count"]
st.bar_chart(payment_share.set_index("Payment Method"))

# --- Delivery Performance ---
st.subheader("⏱ Delivery Performance")
delivery_df = df_filtered[["delivery_days", "is_prime_member"]].copy()
delivery_df["Prime"] = delivery_df["is_prime_member"].apply(lambda x: "Prime" if x else "Non-Prime")
st.boxplot = st.plotly_chart(
    {
        "data": [
            {
                "y": delivery_df["delivery_days"],
                "x": delivery_df["Prime"],
                "type": "box"
            }
        ],
        "layout": {"title": "Delivery Days: Prime vs Non-Prime"}
    }
)

# --- Delivery Type Distribution ---
st.subheader("🚚 Delivery Type Breakdown")
if "delivery_type" in df_filtered.columns:
    delivery_type = df_filtered["delivery_type"].value_counts()
    st.bar_chart(delivery_type)
else:
    st.info("No 'delivery_type' column available in dataset.")

