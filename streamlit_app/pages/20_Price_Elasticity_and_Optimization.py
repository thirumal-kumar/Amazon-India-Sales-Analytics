import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils import load_data, filter_controls, page_title, kpi_card

# -----------------------------------------
# Page Title
# -----------------------------------------
page_title("💹 Price Elasticity & Optimization",
           "How price changes impact demand & revenue — find the sweet spot")

# -----------------------------------------
# Load data
# -----------------------------------------
df = load_data()
if df is None or df.empty:
    st.warning("⚠ Please load the dataset from the Home page.")
    st.stop()

# -----------------------------------------
# Auto-detect / build price & qty
# -----------------------------------------
needed_any = ["selling_price", "discounted_price_inr", "final_amount_inr", "quantity"]
missing_any = [c for c in needed_any if c not in df.columns]
# We only error out if price cannot be derived at all (see below)

# Ensure quantity
if "quantity" not in df.columns:
    st.error("❌ Required column 'quantity' is missing. Please include quantity sold per row.")
    st.stop()

# Build price column (best-effort)
price_col = None
if "selling_price" in df.columns:
    price_col = "selling_price"
elif "discounted_price_inr" in df.columns:
    price_col = "discounted_price_inr"
else:
    if "final_amount_inr" in df.columns:
        # Guard divide by zero
        df["__qty__"] = pd.to_numeric(df["quantity"], errors="coerce").replace({0: np.nan})
        df["price_auto"] = pd.to_numeric(df["final_amount_inr"], errors="coerce") / df["__qty__"]
        price_col = "price_auto"
    else:
        st.error("❌ Could not determine a price column. Expected one of: selling_price, discounted_price_inr, or final_amount_inr/quantity.")
        st.stop()

# Numeric safety
df["price"] = pd.to_numeric(df[price_col], errors="coerce")
df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
if "final_amount_inr" in df.columns:
    df["revenue"] = pd.to_numeric(df["final_amount_inr"], errors="coerce").fillna(0.0)
else:
    df["revenue"] = (df["price"].fillna(0) * df["quantity"].fillna(0))

# Basic guards
df = df[(df["price"] > 0) & (df["quantity"] >= 0)]
if df.empty:
    st.error("❌ No valid rows with positive price found after cleaning.")
    st.stop()

# -----------------------------------------
# Filters (Year / Category / State / City ...)
# -----------------------------------------
df_f = filter_controls(df)
if df_f.empty:
    st.info("ℹ No rows after applying filters.")
    st.stop()

# Ensure product id/name for per-product analysis
prod_col = None
for c in ["product_name", "product", "title", "item_name", "product_id"]:
    if c in df_f.columns:
        prod_col = c
        break
if prod_col is None:
    st.error("❌ Need a product column (product_name / product / product_id).")
    st.stop()

# -----------------------------------------
# KPIs
# -----------------------------------------
avg_price = float(df_f["price"].mean())
min_price = float(df_f["price"].min())
max_price = float(df_f["price"].max())

# Elasticity requires variation in price per product; we estimate # of products eligible
def _eligible(group):
    return group["price"].nunique() >= 5 and group["quantity"].sum() > 0

eligible_products = df_f.groupby(prod_col).filter(_eligible)[prod_col].nunique()

c1, c2, c3 = st.columns(3)
kpi_card("Avg Price", f"₹{avg_price:,.2f}", column=c1)
kpi_card("Price Range", f"₹{min_price:,.0f} – ₹{max_price:,.0f}", column=c2)
kpi_card("Products w/ Enough Price Variation", f"{eligible_products:,}", column=c3)

# -----------------------------------------
# Scatter: Price vs Quantity (overall)
# -----------------------------------------
st.subheader("📉 Price vs Quantity (All Items)")
scatter = (
    alt.Chart(df_f.sample(min(50000, len(df_f)), random_state=42) if len(df_f) > 50000 else df_f)
    .mark_circle(size=40, opacity=0.5)
    .encode(
        x=alt.X("price:Q", title="Price (₹)"),
        y=alt.Y("quantity:Q", title="Quantity Sold"),
        tooltip=[prod_col, "price", "quantity", "revenue"]
    )
    .properties(height=360)
)
st.altair_chart(scatter, use_container_width=True)

# -----------------------------------------
# Price Elasticity per Product
# PED via log-log regression: log(Q) = a + b*log(P)  =>  elasticity ~ b
# We need multiple price points per product, so we aggregate by price bins.
# -----------------------------------------
st.subheader("🧮 Price Elasticity of Demand (per product)")

# Bin price to reduce noise (e.g., 20 bins overall, then per product we aggregate)
# Better: dynamic bins based on unique prices per product; we use global bins for simplicity.
bins = st.slider("Number of price bins (aggregation)", 10, 60, 20)
df_f["price_bin"] = pd.cut(df_f["price"], bins=bins)

# Aggregate by product × price_bin
agg = (
    df_f.groupby([prod_col, "price_bin"], observed=True)
        .agg(avg_price=("price", "mean"),
             total_qty=("quantity", "sum"))
        .reset_index()
        .dropna(subset=["avg_price"])
)

# Keep only products with real variation
valid = agg.groupby(prod_col).filter(lambda g: g["avg_price"].nunique() >= 5 and g["total_qty"].sum() > 0)

def compute_elasticity(g: pd.DataFrame):
    # Remove non-positive quantities/prices
    gg = g[(g["avg_price"] > 0) & (g["total_qty"] > 0)].copy()
    if gg["avg_price"].nunique() < 5:
        return np.nan
    # log-log slope
    x = np.log(gg["avg_price"].values)
    y = np.log(gg["total_qty"].values)
    # simple OLS slope
    slope = np.polyfit(x, y, 1)[0]
    return round(slope, 3)

elasticity = (
    valid.groupby(prod_col)
         .apply(compute_elasticity)
         .reset_index(name="elasticity")
         .dropna(subset=["elasticity"])
)

# Label elasticity
def label_el(e):
    if e <= -1.0:
        return "Elastic (|E| ≥ 1)"
    elif -1.0 < e < 0:
        return "Inelastic (0 > E > -1)"
    else:
        return "Positive/Zero (Atypical)"

elasticity["label"] = elasticity["elasticity"].apply(label_el)

# KPI: counts by label
count_elastic = int((elasticity["label"] == "Elastic (|E| ≥ 1)").sum())
count_inelastic = int((elasticity["label"] == "Inelastic (0 > E > -1)").sum())
c4, c5, c6 = st.columns(3)
kpi_card("Elastic Products", f"{count_elastic:,}", column=c4)
kpi_card("Inelastic Products", f"{count_inelastic:,}", column=c5)
kpi_card("Atypical/Zero", f"{int(len(elasticity) - count_elastic - count_inelastic):,}", column=c6)

# Display top lists
left, right = st.columns(2)
with left:
    st.markdown("**Most Elastic (price-sensitive)**")
    st.dataframe(elasticity.sort_values("elasticity").head(10), use_container_width=True)
with right:
    st.markdown("**Most Inelastic (least sensitive)**")
    st.dataframe(elasticity.sort_values("elasticity", ascending=False).head(10), use_container_width=True)

# -----------------------------------------
# Revenue vs Price Curve (overall) — find revenue-maximizing price band
# -----------------------------------------
st.subheader("💰 Revenue vs Price — Find the Sweet Spot")

rev_curve = (
    df_f.groupby("price_bin", observed=True)
        .agg(avg_price=("price", "mean"), revenue=("revenue", "sum"))
        .dropna(subset=["avg_price"])
        .sort_values("avg_price")
        .reset_index(drop=True)
)

if not rev_curve.empty:
    # Best price band by revenue
    best_row = rev_curve.iloc[rev_curve["revenue"].idxmax()]
    best_price = float(best_row["avg_price"])
    best_rev = float(best_row["revenue"])

    c7, c8 = st.columns(2)
    kpi_card("Revenue-Maximizing Price (band avg.)", f"₹{best_price:,.0f}", column=c7)
    kpi_card("Revenue at Best Price", f"₹{best_rev:,.0f}", column=c8)

    # Line chart revenue vs avg price
    line = (
        alt.Chart(rev_curve)
        .mark_line(point=True)
        .encode(
            x=alt.X("avg_price:Q", title="Avg Price (₹)"),
            y=alt.Y("revenue:Q", title="Revenue (₹)"),
            tooltip=[alt.Tooltip("avg_price:Q", title="Avg Price", format=",.0f"),
                     alt.Tooltip("revenue:Q", title="Revenue", format=",.0f")]
        )
        .properties(height=360)
    )
    st.altair_chart(line, use_container_width=True)
else:
    st.info("ℹ Not enough variation to build a revenue curve.")

# -----------------------------------------
# Per-Product Optimization Explorer
# -----------------------------------------
st.subheader("🔎 Product-Level Price Explorer")

# Only offer products with enough variation
eligible_list = sorted(valid[prod_col].unique().tolist())
if not eligible_list:
    st.info("ℹ Not enough price variation per product to explore elasticity at product level.")
else:
    sel = st.selectbox("Choose a product to inspect", eligible_list)

    v = valid[valid[prod_col] == sel].sort_values("avg_price")
    # Rolling revenue by band for this product (requires revenue per row — approximate revenue = price * qty here)
    # We'll reconstruct per band revenue for the selected product from original df_f to be accurate.
    band_map = dict(zip(v["avg_price"].round(6), v["price_bin"].astype(str)))
    # Re-aggregate revenue per price_bin for this product
    pv = (
        df_f[df_f[prod_col] == sel]
        .groupby("price_bin", observed=True)
        .agg(avg_price=("price", "mean"), qty=("quantity","sum"), revenue=("revenue","sum"))
        .dropna(subset=["avg_price"])
        .sort_values("avg_price")
        .reset_index()
    )

    # Plot qty vs price (points) and revenue vs price (line)
    pts = (
        alt.Chart(pv)
        .mark_circle(size=70, opacity=0.7)
        .encode(
            x=alt.X("avg_price:Q", title="Avg Price (₹)"),
            y=alt.Y("qty:Q", title="Quantity (band total)"),
            tooltip=[alt.Tooltip("avg_price:Q", title="Avg Price", format=",.0f"),
                     alt.Tooltip("qty:Q", title="Quantity", format=",.0f"),
                     alt.Tooltip("revenue:Q", title="Revenue", format=",.0f")]
        )
        .properties(height=360)
    )
    ln = (
        alt.Chart(pv)
        .mark_line(point=True)
        .encode(
            x=alt.X("avg_price:Q", title="Avg Price (₹)"),
            y=alt.Y("revenue:Q", title="Revenue (₹)")
        )
    )
    st.altair_chart(pts + ln, use_container_width=True)

    # Suggest sweet spot (max revenue band) for this product
    if not pv.empty:
        best_idx = pv["revenue"].idxmax()
        best_p = float(pv.loc[best_idx, "avg_price"])
        best_r = float(pv.loc[best_idx, "revenue"])
        st.success(f"📌 Suggested price band for **{sel}**: **₹{best_p:,.0f}** (highest observed revenue ≈ **₹{best_r:,.0f}**).")
    else:
        st.info("ℹ Not enough data to suggest an optimal price for this product.")

# -----------------------------------------
# Notes
# -----------------------------------------
st.markdown("---")
st.caption(
    "Elasticity is estimated via log–log slope on price-binned quantity. "
    "‘Elastic’ means demand changes more than price (E ≤ -1). Results depend on data granularity and noise."
)

