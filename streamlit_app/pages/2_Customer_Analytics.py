import streamlit as st
import pandas as pd
import altair as alt
from utils import load_data, page_title, kpi_card, filter_controls

# 📊 Page Title
page_title("Customer Analytics", "Understand customer demographics, behavior, and spending")

# 📥 Load Data
df = load_data()

# 🧹 Filters (Year, Category, City)
df_filtered = filter_controls(df)

if df_filtered.empty:
    st.warning("⚠️ No data available after applying filters!")
    st.stop()

# ===================== KPI Metrics =====================
total_customers = df_filtered["customer_id"].nunique()
repeat_customers = df_filtered["customer_id"].value_counts().loc[lambda x: x > 1].count()
prime_customers = df_filtered[df_filtered["is_prime_member"] == True]["customer_id"].nunique()
non_prime_customers = total_customers - prime_customers
avg_spend = df_filtered.groupby("customer_id")["final_amount_inr"].sum().mean()

col1, col2, col3, col4 = st.columns(4)
kpi_card("Total Customers", total_customers, col1)
kpi_card("Repeat Customers", repeat_customers, col2)
kpi_card("Prime Members", prime_customers, col3)
kpi_card("Avg Spend per Customer", f"₹{avg_spend:,.0f}", col4)

# ===================== Customer Tier Revenue =====================
st.subheader("💎 Spending by Customer Tier")

if "customer_tier" in df_filtered.columns:
    tier_revenue = (
        df_filtered.groupby("customer_tier")["final_amount_inr"]
        .sum().sort_values(ascending=False).reset_index()
    )

    chart = (
        alt.Chart(tier_revenue)
        .mark_bar()
        .encode(
            x=alt.X("customer_tier", title="Customer Tier"),
            y=alt.Y("final_amount_inr", title="Revenue (₹)"),
            tooltip=["customer_tier", "final_amount_inr"]
        )
        .properties(height=400, width=600)
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.error("❌ 'customer_tier' column not found in dataset")

# ===================== Age Group Spending =====================
st.subheader("🎯 Spending by Age Group")

if "customer_age_group" in df_filtered.columns:
    age_spending = (
        df_filtered.groupby("customer_age_group")["final_amount_inr"]
        .sum().reset_index()
    )

    chart = (
        alt.Chart(age_spending)
        .mark_bar()
        .encode(
            x=alt.X("customer_age_group", sort=None, title="Age Group"),
            y=alt.Y("final_amount_inr", title="Revenue (₹)"),
            tooltip=["customer_age_group", "final_amount_inr"]
        )
        .properties(height=400, width=600)
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.error("❌ 'customer_age_group' column not found")

# ===================== New vs Returning Customers =====================
st.subheader("🔁 New vs Returning Customers")

df_filtered["order_rank"] = df_filtered.groupby("customer_id")["order_date"].rank(method="first")
new_customers = df_filtered[df_filtered["order_rank"] == 1]["customer_id"].nunique()
returning_customers = total_customers - new_customers

st.write(f"🆕 New Customers: **{new_customers}** | 🔁 Returning Customers: **{returning_customers}**")

# Pie chart
pie_data = pd.DataFrame({
    "Customer Type": ["New", "Returning"],
    "Count": [new_customers, returning_customers]
})

pie_chart = (
    alt.Chart(pie_data)
    .mark_arc()
    .encode(theta="Count", color="Customer Type", tooltip=["Customer Type", "Count"])
)
st.altair_chart(pie_chart, use_container_width=True)


