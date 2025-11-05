import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import timedelta
from utils import load_data, filter_controls, page_title, kpi_card

# -----------------------------------------
# Page Title
# -----------------------------------------
page_title("🧲 Customer Churn Prediction", "Who’s at risk of leaving — and how many?")

# -----------------------------------------
# Load & Basic Checks
# -----------------------------------------
df = load_data()
if df is None or df.empty:
    st.warning("⚠ Please load the dataset from the Home page.")
    st.stop()

required = ["customer_id", "order_date", "final_amount_inr"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# Ensure datetime
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
df = df.dropna(subset=["order_date"])

# -----------------------------------------
# Filters (Year / Category / State etc.)
# -----------------------------------------
df_f = filter_controls(df)
if df_f.empty:
    st.info("ℹ No rows after applying filters.")
    st.stop()

# -----------------------------------------
# Sidebar Controls
# -----------------------------------------
st.sidebar.markdown("### ⚙️ Churn Parameters")
months_thresh = st.sidebar.slider("Inactivity threshold (months)", 2, 18, 6, help="Customers inactive for ≥ this many months are flagged as churned.")
use_dataset_max_as_today = st.sidebar.checkbox("Use dataset max date as 'today' (recommended)", value=True)

# -----------------------------------------
# Churn & RFM Calculation
# -----------------------------------------
snapshot_date = df_f["order_date"].max() if use_dataset_max_as_today else pd.Timestamp.today()
days_threshold = int(months_thresh * 30.4375)  # average month length

# Monetary aggregation base
df_f["amount"] = pd.to_numeric(df_f["final_amount_inr"], errors="coerce").fillna(0.0)

# Frequency base column (prefer transaction_id if present)
freq_col = "transaction_id" if "transaction_id" in df_f.columns else None

rfm = (
    df_f.groupby("customer_id").agg(
        last_purchase=("order_date", "max"),
        frequency=(freq_col, "nunique") if freq_col else ("order_date", "count"),
        monetary=("amount", "sum"),
    )
    .reset_index()
)

rfm["recency_days"] = (snapshot_date - rfm["last_purchase"]).dt.days
rfm["is_churned"] = (rfm["recency_days"] >= days_threshold).astype(int)

# RFM scoring (quantiles, safe rank to avoid ties issues)
rfm["R_score"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5,4,3,2,1])  # lower recency is better → higher score
rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1,2,3,4,5])
rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1,2,3,4,5])
for c in ["R_score","F_score","M_score"]:
    rfm[c] = rfm[c].astype(int)

# Simple churn risk score (higher = riskier): high recency + low frequency + low monetary
# Normalize components to [0,1] and combine with weights
def minmax(x):
    x = x.astype(float)
    if x.max() == x.min():
        return pd.Series(0.5, index=x.index)
    return (x - x.min()) / (x.max() - x.min())

rfm_norm = pd.DataFrame({
    "recency_n": minmax(rfm["recency_days"]),
    "frequency_n": minmax(rfm["frequency"]),
    "monetary_n": minmax(rfm["monetary"]),
})

rfm["churn_risk_score"] = (0.50 * rfm_norm["recency_n"]) + (0.25 * (1 - rfm_norm["frequency_n"])) + (0.25 * (1 - rfm_norm["monetary_n"]))
# Scale to 0–100
rfm["churn_risk_score"] = (rfm["churn_risk_score"] * 100).round(1)

# Label
rfm["status"] = np.where(rfm["is_churned"] == 1, "Churned", "Active")

# -----------------------------------------
# KPIs
# -----------------------------------------
total_customers = int(rfm.shape[0])
churned_customers = int((rfm["is_churned"] == 1).sum())
active_customers = total_customers - churned_customers
churn_rate = (churned_customers / total_customers * 100.0) if total_customers else 0.0

c1, c2, c3, c4 = st.columns(4)
kpi_card("Total Customers", f"{total_customers:,}", column=c1)
kpi_card("Active Customers", f"{active_customers:,}", column=c2)
kpi_card("Churned Customers", f"{churned_customers:,}", column=c3)
kpi_card("Churn Rate", f"{churn_rate:.2f}%", column=c4)

# -----------------------------------------
# Churn vs Active (Count)
# -----------------------------------------
st.subheader("👥 Active vs Churned Customers")
status_counts = rfm["status"].value_counts().reset_index()
status_counts.columns = ["Status", "Count"]

bar1 = (
    alt.Chart(status_counts)
    .mark_bar()
    .encode(
        x=alt.X("Status:N", title="Status"),
        y=alt.Y("Count:Q", title="Customers"),
        tooltip=["Status", "Count"]
    )
    .properties(height=350)
)
st.altair_chart(bar1, use_container_width=True)

# -----------------------------------------
# Recency Distribution (Days)
# -----------------------------------------
st.subheader("⏳ Recency (Days since last purchase)")
hist = (
    alt.Chart(rfm)
    .mark_bar()
    .encode(
        x=alt.X("recency_days:Q", bin=alt.Bin(maxbins=40), title="Recency (days)"),
        y=alt.Y("count():Q", title="Customers"),
        tooltip=[alt.Tooltip("count():Q", title="Customers")]
    )
    .properties(height=350)
)
st.altair_chart(hist, use_container_width=True)

# -----------------------------------------
# High-Risk Segments (Heatmap)
# -----------------------------------------
st.subheader("🔥 High-Risk Segments (R × F)")
rfm["R_bucket"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=["Best","Good","Mid","Low","Worst"])
rfm["F_bucket"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=["Worst","Low","Mid","Good","Best"])

seg = (
    rfm.groupby(["R_bucket","F_bucket"])
       .agg(avg_risk=("churn_risk_score","mean"), customers=("customer_id","count"))
       .reset_index()
)

heat = (
    alt.Chart(seg)
    .mark_rect()
    .encode(
        x=alt.X("R_bucket:N", title="Recency (lower is better)"),
        y=alt.Y("F_bucket:N", title="Frequency (higher is better)"),
        color=alt.Color("avg_risk:Q", title="Avg Risk", scale=alt.Scale(scheme="reds")),
        tooltip=["R_bucket","F_bucket","customers","avg_risk"]
    )
    .properties(height=350)
)
st.altair_chart(heat, use_container_width=True)

# -----------------------------------------
# Top Churn-Risk Customers (Table + Download)
# -----------------------------------------
st.subheader("📄 Top Churn-Risk Customers")
cols_show = ["customer_id","status","recency_days","frequency","monetary","churn_risk_score","last_purchase"]
topn = int(st.slider("Rows to show", 10, 200, 50))
st.dataframe(
    rfm.sort_values(["is_churned","churn_risk_score","recency_days"], ascending=[False, False, False])[cols_show].head(topn),
    use_container_width=True
)

# Download churned list
churned_df = rfm[rfm["is_churned"] == 1][cols_show].sort_values(["churn_risk_score","recency_days"], ascending=False)
st.download_button(
    "📥 Download Churned Customers CSV",
    data=churned_df.to_csv(index=False).encode("utf-8"),
    file_name=f"churned_customers_{months_thresh}m.csv",
    mime="text/csv"
)

# -----------------------------------------
# Smart Notes
# -----------------------------------------
st.markdown("---")
st.subheader("🧠 Insights")
notes = []
notes.append(f"• Snapshot date: **{snapshot_date.strftime('%d %b %Y')}**; churn threshold: **{months_thresh} months (~{days_threshold} days)**.")
notes.append(f"• Churn rate is **{churn_rate:.2f}%** ({churned_customers:,} of {total_customers:,}).")
if not seg.empty:
    worst = seg.sort_values("avg_risk", ascending=False).iloc[0]
    notes.append(f"• Highest-risk segment: **R={worst['R_bucket']} × F={worst['F_bucket']}** with avg risk **{worst['avg_risk']:.1f}** across **{int(worst['customers'])}** customers.")
if "category" in df_f.columns:
    # Optional category-level churn view (based on last category purchased)
    cust_last = df_f.sort_values("order_date").groupby("customer_id").tail(1)[["customer_id","category"]]
    merged = rfm.merge(cust_last, on="customer_id", how="left")
    cat_churn = merged.groupby("category")["is_churned"].mean().sort_values(ascending=False)
    if not cat_churn.empty:
        top_cat = cat_churn.index[0]
        notes.append(f"• Highest churn share observed among last-purchased **{top_cat}** customers (category-level heuristic).")

for n in notes:
    st.markdown(n)

st.success("✅ Customer Churn Prediction loaded successfully.")

