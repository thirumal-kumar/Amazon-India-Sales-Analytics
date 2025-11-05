import streamlit as st
import pandas as pd
import os
from utils import page_title, kpi_card, filter_controls

# ========================= PAGE HEADER ==========================
page_title("🏠 Amazon India – Sales Analytics Dashboard")

st.markdown("""
Welcome to the **Amazon India Sales Analytics (2015–2025)** dashboard!  
Explore **revenue trends, product performance, customer analytics, logistics, marketing, forecasting, and more.**
""")

# ========================= DATA LOADING ==========================
st.sidebar.header("📂 Upload / Load Dataset")

uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

# Auto-load cleaned CSV if available
default_path = "outputs/amazon_cleaned.csv"

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.session_state["df"] = df
    st.success("✅ Dataset uploaded successfully!")
elif os.path.exists(default_path):
    df = pd.read_csv(default_path)
    st.session_state["df"] = df
    st.info("✅ Loaded dataset automatically from outputs/amazon_cleaned.csv")
else:
    st.warning("📌 Please upload a dataset to continue.")
    st.stop()

df = st.session_state["df"]

# ========================= CLEAN COLUMN NAMES =========================
df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

# Convert date & add time fields
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df["order_year"] = df["order_date"].dt.year
df["order_month"] = df["order_date"].dt.to_period("M")

# ========================= FILTER PANEL =========================
df_filtered = filter_controls(df)

# ========================= KPI CARDS =========================
col1, col2, col3 = st.columns(3)

total_revenue = df_filtered["final_amount_inr"].sum()
total_orders = len(df_filtered)
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

kpi_card("Total Revenue", int(total_revenue), suffix=" ₹", column=col1)
kpi_card("Total Orders", total_orders, column=col2)
kpi_card("Avg Order Value", int(avg_order_value), suffix=" ₹", column=col3)

# ========================= DATA PREVIEW (LIMITED) =========================
st.markdown("### 📁 Preview Dataset (first 200 rows only)")
st.dataframe(df_filtered.head(200))  # Prevent websocket crash

st.markdown("---")
st.caption("📊 Amazon India Sales Analytics | © 2025 Research Edition")

