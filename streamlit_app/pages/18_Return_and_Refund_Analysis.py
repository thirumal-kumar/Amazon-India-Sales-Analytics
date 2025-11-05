import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils import load_data, filter_controls, page_title, kpi_card

# ----------------------------
# Page Title
# ----------------------------
page_title("📦 Return & Refund Loss Analysis", "Where do we lose money—and why?")

# ----------------------------
# Load Dataset
# ----------------------------
df = load_data()
if df is None or df.empty:
    st.warning("⚠ Please upload/load data from the Home page.")
    st.stop()

# ----------------------------
# Normalize & Safety
# ----------------------------
# Ensure order_date exists and is datetime
if "order_date" not in df.columns:
    st.error("❌ Required column 'order_date' is missing.")
    st.stop()

df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df = df.dropna(subset=["order_date"])

# Ensure revenue column
revenue_col = None
for c in ["final_amount_inr", "order_amount", "subtotal_inr"]:
    if c in df.columns:
        revenue_col = c
        break
if revenue_col is None:
    st.error("❌ Could not find a revenue column (expected 'final_amount_inr' / 'order_amount' / 'subtotal_inr').")
    st.stop()

# ----------------------------
# Apply Filters (Year/Category/State/City)
# ----------------------------
df_f = filter_controls(df)
if df_f is None or df_f.empty:
    st.info("ℹ️ No rows after applying filters.")
    st.stop()

# ----------------------------
# Return Flag (robust parsing)
# ----------------------------
def is_returned(val):
    if pd.isna(val):
        return False
    s = str(val).strip().lower()
    return s in {"returned", "refund", "refunded", "return_initiated", "return-approved", "return", "replaced"}

return_col = None
for c in ["return_status", "is_returned", "refund_status"]:
    if c in df_f.columns:
        return_col = c
        break

if return_col is None:
    # Create a safe default (all non-returned)
    df_f["__returned__"] = False
    return_col = "__returned__"

df_f["__is_returned__"] = df_f[return_col].apply(is_returned)

# ----------------------------
# Core metrics
# ----------------------------
df_f["__revenue__"] = pd.to_numeric(df_f[revenue_col], errors="coerce").fillna(0.0)

total_revenue = float(df_f["__revenue__"].sum())
total_orders = int(len(df_f))

returned_orders = int(df_f["__is_returned__"].sum())

# BEST default: full-value loss on a returned order
df_f["__return_loss__"] = np.where(df_f["__is_returned__"], df_f["__revenue__"], 0.0)
total_return_loss = float(df_f["__return_loss__"].sum())

return_rate_pct = (returned_orders / total_orders * 100.0) if total_orders else 0.0
loss_pct_of_revenue = (total_return_loss / total_revenue * 100.0) if total_revenue else 0.0

# Most affected category (by loss)
cat_col = "category" if "category" in df_f.columns else None
if cat_col:
    top_cat = (
        df_f.groupby(cat_col)["__return_loss__"]
        .sum().sort_values(ascending=False)
    )
    most_affected_category = top_cat.index[0] if not top_cat.empty else "N/A"
else:
    most_affected_category = "N/A"

# ----------------------------
# KPI Cards
# ----------------------------
c1, c2, c3, c4 = st.columns(4)
kpi_card("Total Return Loss", f"₹{total_return_loss:,.0f}", column=c1)
kpi_card("Return Rate", f"{return_rate_pct:.2f}%", column=c2)
kpi_card("Loss as % of Revenue", f"{loss_pct_of_revenue:.2f}%", column=c3)
kpi_card("Most Affected Category", most_affected_category, column=c4)

# ----------------------------
# Monthly Return Trend (₹ loss & count)
# ----------------------------
st.subheader("📅 Monthly Return Trend")

df_f["order_month"] = df_f["order_date"].dt.to_period("M").dt.to_timestamp()

mt = (
    df_f.groupby("order_month", as_index=False)
        .agg(
            return_loss=("__return_loss__", "sum"),
            return_count=("__is_returned__", "sum")
        )
        .sort_values("order_month")
)

# Long format for Altair (robust, no transform_fold)
mt_long = (
    mt.rename(columns={"return_loss": "Return Loss (₹)", "return_count": "Return Count"})
      .melt(id_vars="order_month", var_name="Metric", value_name="Value")
)

trend_chart = (
    alt.Chart(mt_long)
    .mark_line(point=True)
    .encode(
        x=alt.X("order_month:T", title="Month"),
        y=alt.Y("Value:Q", title="Value"),
        color=alt.Color("Metric:N", title="Metric"),
        tooltip=[alt.Tooltip("order_month:T", title="Month"),
                 alt.Tooltip("Metric:N"),
                 alt.Tooltip("Value:Q", format=",.0f")]
    )
    .properties(height=380)
)
st.altair_chart(trend_chart, use_container_width=True)

# ----------------------------
# Category-wise Return Loss
# ----------------------------
st.subheader("🏷 Category-wise Return Loss")
if cat_col:
    cat_loss = (
        df_f.groupby(cat_col)["__return_loss__"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={cat_col: "Category", "__return_loss__": "Return Loss (₹)"})
        .head(10)
    )

    cat_chart = (
        alt.Chart(cat_loss)
        .mark_bar()
        .encode(
            x=alt.X("Return Loss (₹):Q", title="Return Loss (₹)"),
            y=alt.Y("Category:N", sort="-x", title="Category"),
            tooltip=["Category", alt.Tooltip("Return Loss (₹):Q", format=",.0f")]
        )
        .properties(height=400)
    )
    st.altair_chart(cat_chart, use_container_width=True)
else:
    st.info("ℹ 'category' column not found. Skipping category analysis.")

# ----------------------------
# State-wise Return Loss
# ----------------------------
st.subheader("🗺 State-wise Return Loss")
state_col = None
for c in ["customer_state", "state", "ship_state"]:
    if c in df_f.columns:
        state_col = c
        break

if state_col:
    state_loss = (
        df_f.groupby(state_col)["__return_loss__"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={state_col: "State", "__return_loss__": "Return Loss (₹)"})
        .head(15)
    )

    state_chart = (
        alt.Chart(state_loss)
        .mark_bar()
        .encode(
            x=alt.X("Return Loss (₹):Q", title="Return Loss (₹)"),
            y=alt.Y("State:N", sort="-x", title="State"),
            tooltip=["State", alt.Tooltip("Return Loss (₹):Q", format=",.0f")]
        )
        .properties(height=400)
    )
    st.altair_chart(state_chart, use_container_width=True)
else:
    st.info("ℹ No state column found (expected 'customer_state' / 'state').")

# ----------------------------
# Top Products by Return Loss
# ----------------------------
st.subheader("📦 Top 10 Products by Return Loss")
prod_col = None
for c in ["product_name", "product", "title", "item_name", "product_id"]:
    if c in df_f.columns:
        prod_col = c
        break

if prod_col:
    prod_loss = (
        df_f.groupby(prod_col)["__return_loss__"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={prod_col: "Product", "__return_loss__": "Return Loss (₹)"})
        .head(10)
    )
    st.dataframe(prod_loss.style.format({"Return Loss (₹)": "₹{:,.0f}"}), use_container_width=True)
else:
    st.info("ℹ Product column not found. Skipping product-level analysis.")

# ----------------------------
# Optional: Reasons for Return (if available)
# ----------------------------
reason_col = None
for c in ["return_reason", "refund_reason", "return_category"]:
    if c in df_f.columns:
        reason_col = c
        break

if reason_col:
    st.subheader("🧾 Reasons for Return — Loss Impact")
    reason_loss = (
        df_f.groupby(reason_col)["__return_loss__"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={reason_col: "Reason", "__return_loss__": "Return Loss (₹)"})
    )
    reason_chart = (
        alt.Chart(reason_loss.head(12))
        .mark_bar()
        .encode(
            x=alt.X("Return Loss (₹):Q", title="Return Loss (₹)"),
            y=alt.Y("Reason:N", sort="-x", title="Reason"),
            tooltip=["Reason", alt.Tooltip("Return Loss (₹):Q", format=",.0f")]
        )
        .properties(height=400)
    )
    st.altair_chart(reason_chart, use_container_width=True)

# ----------------------------
# Smart Summary
# ----------------------------
st.markdown("---")
st.subheader("🧠 Quick Insights")
lines = []

# 1) Peak loss month
if not mt.empty and mt["return_loss"].sum() > 0:
    peak_row = mt.sort_values("return_loss", ascending=False).iloc[0]
    lines.append(f"• Highest monthly return loss was **₹{peak_row['return_loss']:,.0f}** in **{peak_row['order_month'].strftime('%b %Y')}**.")

# 2) Category highlight
if cat_col and not top_cat.empty:
    lines.append(f"• **{top_cat.index[0]}** contributes the most to return loss (₹{top_cat.iloc[0]:,.0f}).")

# 3) Return rate vs. revenue note
lines.append(f"• Overall return rate is **{return_rate_pct:.2f}%**, causing **{loss_pct_of_revenue:.2f}%** revenue loss.")

for l in lines:
    st.markdown(l)

st.success("✅ Return & Refund Loss Analysis loaded successfully.")

