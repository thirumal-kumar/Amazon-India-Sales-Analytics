import streamlit as st
import pandas as pd
import altair as alt
from utils import filter_controls, kpi_card, load_data

# ------------------------------
# Page Title
# ------------------------------
st.title("🗺️🚚 Regional Demand & Logistics")
st.caption("Revenue by region/state/city • Delivery performance • Prime vs Non-Prime • Festival effects")

# ------------------------------
# Load Data
# ------------------------------
df = load_data()
if df is None:
    st.warning("⚠ Please upload data from the Home Page to proceed.")
    st.stop()

# ------------------------------
# Ensure 'revenue' exists
# ------------------------------
if "revenue" not in df.columns:
    if "final_amount_inr" in df.columns:
        df["revenue"] = df["final_amount_inr"]
    elif "subtotal_inr" in df.columns:
        df["revenue"] = df["subtotal_inr"]
    else:
        df["revenue"] = 0

# ------------------------------
# Apply Filters (Year, Category, State, City)
# ------------------------------
df_filtered = filter_controls(df)

# ------------------------------
# Utility: Clean boolean-like columns (True/False/Yes/No/0/1)
# ------------------------------
def clean_bool_column(df, col):
    if col not in df.columns:
        return df
    df[col] = df[col].astype(str).str.strip().str.lower()
    df[col] = df[col].replace({
        'true': 1, 'false': 0,
        'yes': 1, 'no': 0,
        '1': 1, '0': 0,
        'y': 1, 'n': 0,
        't': 1, 'f': 0
    })
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

# Clean selected boolean fields
for col in ["is_prime_member", "is_festival_sale", "is_possible_duplicate"]:
    df_filtered = clean_bool_column(df_filtered, col)

# ------------------------------
# KPI Cards
# ------------------------------
c1, c2, c3 = st.columns(3)

# 1️⃣ Top State by Revenue
if "customer_state" in df_filtered.columns:
    state_rev = df_filtered.groupby("customer_state")["revenue"].sum().sort_values(ascending=False)
    top_state = state_rev.index[0] if not state_rev.empty else "N/A"
else:
    top_state = "N/A"

# 2️⃣ Fastest Delivery State
if "customer_state" in df_filtered.columns and "delivery_days" in df_filtered.columns:
    delivery_speed = df_filtered.groupby("customer_state")["delivery_days"].mean().sort_values()
    fastest_state = delivery_speed.index[0] if not delivery_speed.empty else "N/A"
else:
    fastest_state = "N/A"

# 3️⃣ Prime Order Percentage
if "is_prime_member" in df_filtered.columns:
    prime_percentage = df_filtered["is_prime_member"].mean() * 100
else:
    prime_percentage = 0

# Display KPI cards (corrected column= instead of col=)
kpi_card("Top State by Revenue", top_state, column=c1)
kpi_card("Fastest Delivery State", fastest_state, column=c2)
kpi_card("Prime Order %", f"{prime_percentage:.1f}%", column=c3)

# ------------------------------
# Revenue by State – Bar Chart
# ------------------------------
st.subheader("📍 Revenue by State")
if "customer_state" in df_filtered.columns:
    rev_state = (
        df_filtered.groupby("customer_state")["revenue"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    chart = alt.Chart(rev_state).mark_bar().encode(
        x=alt.X("customer_state", sort="-y", title="State"),
        y=alt.Y("revenue", title="Revenue (₹)"),
        tooltip=["customer_state", "revenue"]
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)
else:
    st.warning("⚠ 'customer_state' column missing.")

# ------------------------------
# Prime vs Non-Prime Revenue – Pie Chart
# ------------------------------
st.subheader("🌟 Prime vs Non-Prime Revenue")
if "is_prime_member" in df_filtered.columns:
    prime_data = (
        df_filtered.groupby("is_prime_member")["revenue"]
        .sum()
        .reset_index()
        .replace({1: "Prime", 0: "Non-Prime"})
    )
    chart = alt.Chart(prime_data).mark_arc().encode(
        theta="revenue",
        color="is_prime_member",
        tooltip=["is_prime_member", "revenue"]
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.warning("⚠ 'is_prime_member' column missing.")

# ------------------------------
# Average Delivery Days by State
# ------------------------------
st.subheader("🚚 Avg Delivery Days by State")
if "customer_state" in df_filtered.columns and "delivery_days" in df_filtered.columns:
    delivery_data = (
        df_filtered.groupby("customer_state")["delivery_days"]
        .mean()
        .sort_values()
        .reset_index()
    )
    chart = alt.Chart(delivery_data).mark_bar().encode(
        x=alt.X("delivery_days", title="Avg Delivery Days"),
        y=alt.Y("customer_state", sort="-x", title="State"),
        tooltip=["customer_state", "delivery_days"]
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)
else:
    st.warning("⚠ Delivery metrics missing.")

# ------------------------------
# Footer
# ------------------------------
st.success("✅ Regional Demand & Logistics Insights loaded successfully!")

