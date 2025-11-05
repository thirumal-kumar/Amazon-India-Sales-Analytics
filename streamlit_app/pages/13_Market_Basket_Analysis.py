import streamlit as st
import pandas as pd
from utils import load_data, page_title
from mlxtend.frequent_patterns import apriori, association_rules

page_title("🛒 Market Basket Analysis (MBA)")

# ✅ Load data
df = load_data()

# ✅ Column check
if not set(["transaction_id", "product_id"]).issubset(df.columns):
    st.error("❌ Required columns 'transaction_id' and 'product_id' missing.")
    st.stop()

st.info("⚙ Filtering data for faster processing...")

# ✅ Use smaller sample for performance
basket_df = df[["transaction_id", "product_id"]].drop_duplicates()
basket_df = basket_df[basket_df["product_id"].notna()]

# ✅ Pivot to create basket matrix (Transaction × Product)
basket = basket_df.pivot_table(index="transaction_id",
                               columns="product_id",
                               aggfunc=lambda x: 1,
                               fill_value=0)

# ✅ Convert 1/0 to Boolean — required by mlxtend
basket = basket.astype(bool)

st.success(f"✅ Basket matrix created ({basket.shape[0]} rows × {basket.shape[1]} products)")

# ✅ Run Apriori
min_support = st.slider("📉 Minimum Support (%)", 0.001, 0.05, 0.01)
frequent_items = apriori(basket, min_support=min_support, use_colnames=True)

if frequent_items.empty:
    st.warning("⚠ No frequent itemsets found. Try lowering support.")
else:
    st.success(f"✅ Found {len(frequent_items)} frequent itemsets")
    st.dataframe(frequent_items.head())

# ✅ Build rules
if not frequent_items.empty:
    rules = association_rules(frequent_items, metric="confidence", min_threshold=0.3)

    if rules.empty:
        st.warning("⚠ No strong rules. Try lowering confidence threshold.")
    else:
        st.success("✅ Association Rules Generated")
        st.dataframe(rules.sort_values("lift", ascending=False).head(10))

st.success("✅ Market Basket Analysis Completed!")

