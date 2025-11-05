import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils import load_data, page_title, kpi_card, filter_controls

page_title("📈 Forecasting & Time-Series Trends",
           "Monthly revenue, seasonality, and 12-month projections")

df = load_data()
df_f = filter_controls(df)
if df_f.empty:
    st.warning("No data after filters.")
    st.stop()

df_f["order_date"] = pd.to_datetime(df_f["order_date"], errors="coerce")
df_f = df_f.dropna(subset=["order_date"])

monthly = (
    df_f.assign(month=pd.to_datetime(df_f["order_date"].dt.to_period("M").astype(str)))
        .groupby("month", as_index=False)["final_amount_inr"].sum()
        .rename(columns={"final_amount_inr": "revenue"})
        .sort_values("month")
)

if len(monthly) < 4:
    st.error("Not enough monthly data to forecast.")
    st.stop()

total = float(monthly["revenue"].sum())
months = monthly["month"].nunique()
avg_m = float(monthly["revenue"].mean())

# ✅ FIXED col → column
c1, c2, c3 = st.columns(3)
kpi_card("Total Revenue (filtered)", total, " ₹", column=c1)
kpi_card("Months available", months, column=c2)
kpi_card("Avg Monthly Revenue", avg_m, " ₹", column=c3)

st.markdown("### 📅 Historical Monthly Revenue")
hist = (
    alt.Chart(monthly).mark_line(point=True)
    .encode(x=alt.X("month:T"), y=alt.Y("revenue:Q"),
            tooltip=[alt.Tooltip("month:T"), alt.Tooltip("revenue:Q", format=",.0f")])
    .properties(width=900, height=380)
)
st.altair_chart(hist)

monthly["month_num"] = monthly["month"].dt.month

def build_forecast(dfm: pd.DataFrame, horizon=12):
    y = dfm["revenue"].astype(float).to_numpy()
    n = len(y)
    if n < 15:
        ma = y[-3:].mean() if n >= 3 else y.mean()
        last = dfm["month"].max()
        fut = pd.date_range(last + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
        return fut, np.full(horizon, ma), None, None

    t = np.arange(n)
    slope, intercept = np.polyfit(t, y, 1)
    trend = intercept + slope * t
    dfm = dfm.copy()
    dfm["trend"] = trend
    dfm["moy"] = dfm["month"].dt.month
    dfm["seasonal"] = dfm["revenue"] - dfm["trend"]
    seas = dfm.groupby("moy")["seasonal"].mean().to_dict()

    last_t = t[-1]
    last_m = dfm["month"].max()
    fut = pd.date_range(last_m + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    t_f = np.arange(last_t+1, last_t+1+horizon)
    trend_f = intercept + slope * t_f
    seas_f = np.array([seas.get(m, 0.0) for m in fut.month])
    return fut, trend_f + seas_f, seas, (slope, intercept)

f_idx, f_vals, seas_means, params = build_forecast(monthly, 12)
fdf = pd.DataFrame({"month": f_idx, "forecast": f_vals})

st.markdown("### 🔮 12-Month Forecast")
combo = (
    alt.Chart(monthly).mark_line(point=True).encode(
        x="month:T", y="revenue:Q", color=alt.value("#1f77b4"),
        tooltip=[alt.Tooltip("month:T"), alt.Tooltip("revenue:Q", format=",.0f")]
    ) +
    alt.Chart(fdf).mark_line(point=True).encode(
        x="month:T", y="forecast:Q", color=alt.value("#d62728"),
        tooltip=[alt.Tooltip("month:T"), alt.Tooltip("forecast:Q", format=",.0f")]
    )
).properties(width=900, height=380)
st.altair_chart(combo)

