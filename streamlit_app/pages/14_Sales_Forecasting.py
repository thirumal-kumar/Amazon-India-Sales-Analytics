import streamlit as st
import pandas as pd
import warnings
from utils import load_data, page_title
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt

# Suppress warnings
warnings.filterwarnings("ignore")

# Page title and information
page_title("📈 Sales Forecasting", "Predict future revenue & growth trends")

# Load data
df = load_data()

if df is None or df.empty:
    st.warning("⚠ Please load the dataset from the **Home Page** first.")
else:
    st.success("✅ Dataset Loaded Successfully")

    # Ensure order_date is datetime
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])

    # Only use order_date and revenue
    df_time = df.groupby("order_date")["final_amount_inr"].sum().reset_index()

    # Convert to time-series index & resample to monthly ('ME' = Month End)
    df_time = df_time.set_index("order_date").resample("ME").sum()

    if df_time.empty:
        st.warning("⚠ No valid date or revenue data for forecasting.")
    else:
        st.write("📊 **Monthly Revenue Trend (After Resampling)**")
        st.line_chart(df_time)

        # Build SARIMA Model
        try:
            model = SARIMAX(df_time, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
            model_fit = model.fit(disp=False)

            # Forecast next 12 months
            forecast = model_fit.forecast(steps=12)
            forecast.index = pd.date_range(
                start=df_time.index[-1] + pd.offsets.MonthEnd(1), periods=12, freq="ME"
            )

            # Plot actual vs forecast
            st.write("📈 **Forecasted Revenue for Next 12 Months**")
            fig, ax = plt.subplots(figsize=(12, 5))
            df_time.plot(ax=ax, label="Actual Revenue")
            forecast.plot(ax=ax, label="Forecasted Revenue", linestyle="--")
            ax.set_title("Actual vs Forecasted Monthly Revenue")
            ax.set_ylabel("Revenue (₹)")
            ax.legend()
            st.pyplot(fig)

            st.success("✅ Sales Forecasting Completed Successfully!")

        except Exception as e:
            st.error(f"❌ Error during forecasting: {e}")

