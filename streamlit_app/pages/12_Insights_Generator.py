import streamlit as st
import pandas as pd
import numpy as np
from utils import load_data, page_title, filter_controls, kpi_card

# ---------------------------------
# Page
# ---------------------------------
page_title("🧠 Insights Generator", "Auto-summarized business insights & anomalies from your decade of data")

df = load_data()
df_f = filter_controls(df)

if df_f.empty:
    st.warning("No data after filters.")
    st.stop()

# Ensure key columns exist
for c in ["order_date", "final_amount_inr", "category", "city", "payment_method",
          "is_festival_sale", "delivery_days", "return_status", "order_year", "order_month"]:
    if c not in df_f.columns:
        if c in ["final_amount_inr", "delivery_days"]:
            df_f[c] = np.nan
        elif c in ["is_festival_sale"]:
            df_f[c] = False
        else:
            df_f[c] = "Unknown"

df_f["order_date"] = pd.to_datetime(df_f["order_date"], errors="coerce")

# ---------------------------------
# Helper safe stats
# ---------------------------------
def pct(a, b):
    try:
        return 100.0 * a / b if b else 0.0
    except Exception:
        return 0.0

def topn(series, n=3):
    vc = series.value_counts(dropna=True)
    return [(idx, int(val)) for idx, val in vc.head(n).items()]

def topn_sum(df, by_col, val_col, n=5):
    g = df.groupby(by_col, dropna=True)[val_col].sum().sort_values(ascending=False).head(n)
    return list(g.items())

def yoy_growth(monthly_df):
    if monthly_df.empty:
        return 0.0
    monthly_df = monthly_df.copy().sort_values("date")
    if len(monthly_df) < 24:
        if len(monthly_df) >= 2:
            return pct(monthly_df.iloc[-1]["revenue"] - monthly_df.iloc[-2]["revenue"],
                       monthly_df.iloc[-2]["revenue"])
        return 0.0
    last12 = monthly_df.iloc[-12:]["revenue"].sum()
    prev12 = monthly_df.iloc[-24:-12]["revenue"].sum()
    return pct(last12 - prev12, prev12)

# ---------------------------------
# Build monthly series
# ---------------------------------
monthly = (
    df_f.dropna(subset=["order_date"])
       .assign(date=lambda x: pd.to_datetime(x["order_date"].dt.to_period("M").astype(str)))
       .groupby("date", as_index=False)["final_amount_inr"].sum()
       .rename(columns={"final_amount_inr": "revenue"})
       .sort_values("date")
)

# KPIs
total_rev = float(df_f["final_amount_inr"].sum())
orders = len(df_f)
aov = total_rev / orders if orders else 0.0

c1, c2, c3 = st.columns(3)
kpi_card("Total Revenue", total_rev, " ₹", column=c1)
kpi_card("Total Orders", orders, column=c2)  # ✅ fixed
kpi_card("Avg Order Value", aov, " ₹", column=c3)  # ✅ fixed

# ---------------------------------
# Generate Insights (rule-based NLP-lite)
# ---------------------------------
insights = []

# 1) Overall growth
growth = yoy_growth(monthly)
if growth >= 0:
    insights.append(f"Year-over-year revenue grew by **{growth:.1f}%** based on the latest window.")
else:
    insights.append(f"Year-over-year revenue declined by **{abs(growth):.1f}%** based on the latest window.")

# 2) Top categories & cities by revenue
cat_top = topn_sum(df_f, "category", "final_amount_inr", n=5)
if cat_top:
    cat_msg = ", ".join([f"{c} (₹{v:,.0f})" for c, v in cat_top[:3]])
    insights.append(f"Top categories by revenue: **{cat_msg}**.")
else:
    insights.append("Category breakdown unavailable.")

city_top = topn_sum(df_f, "city", "final_amount_inr", n=5)
if city_top:
    city_msg = ", ".join([f"{c} (₹{v:,.0f})" for c, v in city_top[:3]])
    insights.append(f"Top cities by revenue: **{city_msg}**.")
else:
    insights.append("City breakdown unavailable.")

# 3) Payment shifts
if "payment_method" in df_f.columns:
    pm_share = (df_f.groupby("payment_method")["final_amount_inr"]
                   .sum()
                   .sort_values(ascending=False))
    if not pm_share.empty:
        top_pm = pm_share.index[0]
        top_pm_share = pct(pm_share.iloc[0], float(pm_share.sum()))
        insights.append(f"Most revenue came via **{top_pm}** (~{top_pm_share:.1f}% share).")

# 4) Delivery speed & returns
if df_f["delivery_days"].notna().any():
    avg_del = float(df_f["delivery_days"].mean())
    insights.append(f"Average delivery time is **{avg_del:.1f} days**.")
    if "is_festival_sale" in df_f.columns:
        fest = df_f[df_f["is_festival_sale"] == True]["delivery_days"].mean()
        norm = df_f[df_f["is_festival_sale"] == False]["delivery_days"].mean()
        if not np.isnan(fest) and not np.isnan(norm):
            delta = fest - norm
            if abs(delta) >= 0.3:
                sign = "slower" if delta > 0 else "faster"
                insights.append(f"Festival orders are **{abs(delta):.1f} days {sign}** than normal.")
if "return_status" in df_f.columns:
    ret_rate = pct((df_f["return_status"] == "Returned").sum(), len(df_f))
    insights.append(f"Overall return rate is **{ret_rate:.2f}%**.")
    cat_grp = (df_f.assign(is_ret=lambda x: x["return_status"] == "Returned")
                  .groupby("category")
                  .agg(orders=("is_ret","size"), ret_rate=("is_ret","mean"))
                  .reset_index())
    cat_grp = cat_grp[cat_grp["orders"] >= max(100, 0.01 * len(df_f))]
    if not cat_grp.empty:
        worst = cat_grp.sort_values("ret_rate", ascending=False).iloc[0]
        insights.append(f"Highest return rate is in **{worst['category']}** at **{worst['ret_rate']*100:.2f}%**.")

# 5) Peak month
if not monthly.empty:
    peak = monthly.sort_values("revenue", ascending=False).iloc[0]
    insights.append(f"Peak monthly revenue was **₹{peak['revenue']:,.0f}** in **{peak['date'].strftime('%b %Y')}**.")

# 6) Festival impact
if "is_festival_sale" in df_f.columns:
    fest_rev = float(df_f[df_f["is_festival_sale"] == True]["final_amount_inr"].sum())
    share = pct(fest_rev, total_rev)
    insights.append(f"Festival orders contribute **{share:.1f}%** of total revenue.")
    if "festival_name" in df_f.columns:
        fn = (df_f[df_f["is_festival_sale"] == True]
                .groupby("festival_name")["final_amount_inr"]
                .sum()
                .sort_values(ascending=False))
        if not fn.empty:
            insights.append(f"Top festival by revenue: **{fn.index[0]}** (₹{fn.iloc[0]:,.0f}).")

# 7) AOV Trend Last 6 Months
if len(monthly) >= 6:
    if "transaction_id" in df_f.columns:
        m_orders = (df_f.assign(m=lambda x: pd.to_datetime(x["order_date"].dt.to_period("M").astype(str)))
                        .groupby("m")["transaction_id"].count().rename("orders"))
        m_df = monthly.set_index("date").join(m_orders, how="left").reset_index()
        m_df["aov"] = m_df["revenue"] / m_df["orders"].replace({0: np.nan})
        recent = m_df.dropna(subset=["aov"]).tail(6)
        if not recent.empty:
            tr = recent.iloc[-1]["aov"] - recent.iloc[0]["aov"]
            if abs(tr) > 1:
                direction = "↑ increased" if tr > 0 else "↓ decreased"
                insights.append(f"Avg order value has **{direction} by ₹{abs(tr):,.0f}** in the last 6 months.")

# ---------------------------------
# Render Insights
# ---------------------------------
st.subheader("📌 Executive Summary")
for line in insights:
    st.markdown(f"- {line}")

# Downloadable text summary
summary_text = "Amazon India — Executive Summary\n\n"
for line in insights:
    summary_text += f"• {line}\n"

st.download_button(
    "📥 Download Insights (TXT)",
    data=summary_text.encode("utf-8"),
    file_name="insights_summary.txt",
    mime="text/plain"
)

st.markdown("---")
st.caption("Insights generated locally using rule-based analytics (no external API).")

