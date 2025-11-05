import streamlit as st
import pandas as pd
import altair as alt
from utils import load_data, filter_controls, kpi_card, page_title

# Page Title
page_title("🎉💰 Marketing & Festival Sales Analytics", "Impact of deals, festivals & promotions")

# Load dataset
df = load_data()
if df is None or df.empty:
    st.warning("⚠ Please upload or load dataset from Home page.")
    st.stop()

df_filtered = filter_controls(df)

# ✅ SAFELY HANDLE REVENUE
def compute_revenue(df):
    if "revenue" in df:
        return df["revenue"]
    elif "selling_price" in df and "quantity" in df:
        return df["selling_price"] * df["quantity"]
    elif "final_amount_inr" in df:
        return df["final_amount_inr"]
    elif "order_amount" in df:
        return df["order_amount"]
    else:
        return None

df_filtered["revenue"] = compute_revenue(df_filtered)

if df_filtered["revenue"] is None:
    st.error("❌ No usable revenue data found (expected one of: 'revenue', 'selling_price & quantity', 'final_amount_inr', 'order_amount').")
    st.stop()

# ---- KPI Cards ----
total_rev = df_filtered["revenue"].sum()
total_orders = len(df_filtered)
avg_order = total_rev / total_orders if total_orders > 0 else 0

col1, col2, col3 = st.columns(3)
kpi_card("Total Revenue", f"{total_rev:,.0f} ₹", col1)
kpi_card("Total Orders", f"{total_orders:,}", col2)
kpi_card("Avg Order Value", f"{avg_order:,.0f} ₹", col3)

# ---- Festival Sales ----
st.subheader("🎊 Festival Sales Performance")

festival_keywords = ["Diwali", "Holi", "Eid", "Christmas", "New Year", "Navratri"]

if "event_name" in df_filtered:
    fest_df = df_filtered[df_filtered["event_name"].str.contains("|".join(festival_keywords), case=False, na=False)]

    if not fest_df.empty:
        fest_sales = fest_df.groupby("event_name")["revenue"].sum().reset_index()
        st.write(fest_sales)

        chart = alt.Chart(fest_sales).mark_bar().encode(
            x="event_name:N",
            y="revenue:Q",
            tooltip=["event_name", "revenue"]
        ).properties(height=400, title="Revenue by Festival")

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("ℹ No festival-based sales found.")
else:
    st.info("⚠ 'event_name' column not found. Skipping festival analysis.")

# ---- Discount Sales Impact ----
st.subheader("💸 Discount Impact on Sales (if available)")

if "discount_percent" in df_filtered:
    df_filtered["discount_percent"] = pd.to_numeric(df_filtered["discount_percent"], errors="coerce")
    bins = [0, 10, 20, 30, 40, 50, 100]
    discount_bins = pd.cut(df_filtered["discount_percent"], bins=bins)
    discount_impact = df_filtered.groupby(discount_bins)["revenue"].sum().reset_index()
    discount_impact["discount_percent"] = discount_impact["discount_percent"].astype(str)
    
    if not discount_impact.empty:
        st.write(discount_impact)

        chart = alt.Chart(discount_impact).mark_bar().encode(
            x="discount_percent:N",
            y="revenue:Q",
            tooltip=["discount_percent", "revenue"]
        ).properties(height=400, title="Revenue by Discount Slab")

        st.altair_chart(chart, use_container_width=True)
else:
    st.info("⚠ No 'discount_percent' column available. Skipping discount analysis.")


