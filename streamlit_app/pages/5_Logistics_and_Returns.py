import streamlit as st
import pandas as pd
from utils import load_data, filter_controls, kpi_card, page_title

# ---------------- PAGE TITLE ---------------- #
page_title("🚚📦 Logistics & Returns Analysis", "Delivery performance & returns")

# ---------------- LOAD DATA ---------------- #
df = load_data()

if df is None or df.empty:
    st.stop()

# ---------------- FILTER DATA ---------------- #
df_filtered = filter_controls(df)

# Ensure essential column exists
if "delivery_days" not in df_filtered.columns:
    st.warning("Delivery data not available in this dataset.")
    st.stop()

# ---------------- KPI CARDS ---------------- #
c1, c2, c3 = st.columns(3)

# Total Orders
total_orders = len(df_filtered)
kpi_card("Total Orders", total_orders, column=c1)

# Average Delivery Time
avg_delivery = df_filtered["delivery_days"].mean()
kpi_card("Avg Delivery (Days)", round(avg_delivery, 2), suffix=" days", column=c2)

# Return Rate – Silent fallback
if "is_returned" in df_filtered.columns:
    return_rate = df_filtered["is_returned"].mean() * 100
    kpi_card("Return Rate", f"{return_rate:.2f}%", column=c3)
else:
    # Show as "--" if not available, no warning
    kpi_card("Return Rate", "--", column=c3)

# ---------------- DELIVERY TIME DISTRIBUTION ---------------- #
st.subheader("⏱ Delivery Time Distribution")
try:
    st.bar_chart(df_filtered["delivery_days"].value_counts().sort_index())
except:
    st.write(" ")

# ---------------- RETURN STATUS ---------------- #
# (Silent skip if no column for returns)
if "is_returned" in df_filtered.columns:
    st.subheader("📦 Return Status Overview")
    st.bar_chart(df_filtered["is_returned"].value_counts())

# ---------------- COURIER PERFORMANCE ---------------- #
# Priority-based courier column detection
courier_col = next(
    (col for col in ["courier", "delivery_partner", "shipping_provider", "logistics_name"] if col in df_filtered.columns),
    None
)

if courier_col:
    st.subheader("🚛 Top Couriers by Avg Delivery Time")
    courier_performance = (
        df_filtered.groupby(courier_col)["delivery_days"]
        .mean()
        .sort_values()
        .head(10)
    )
    st.bar_chart(courier_performance)

# ---------------- END ---------------- #
# ❌ No st.info(), st.warning — fully clean look

