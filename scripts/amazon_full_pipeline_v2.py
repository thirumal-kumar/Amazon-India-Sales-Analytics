# -*- coding: utf-8 -*-
"""
Amazon India Analytics – Pipeline v2 (hardened)
- Robust cleaning for Category / City / Payment / Prime / Ratings
- Derives: order_year, order_month, order_quarter, month_label, order_value_segment
- Writes SQLite (transactions) + CSV (outputs/amazon_cleaned.csv)
- Generates EDA CSVs in outputs/eda/
- Saves a compact QA report in outputs/qa/cleaning_summary.csv
"""

import os
import re
import sqlite3
from datetime import datetime
import numpy as np
import pandas as pd

OUTPUT_DIR = "outputs"
EDA_DIR = os.path.join(OUTPUT_DIR, "eda")
QA_DIR = os.path.join(OUTPUT_DIR, "qa")
DB_PATH = os.path.join(OUTPUT_DIR, "amazon_analytics.db")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EDA_DIR, exist_ok=True)
os.makedirs(QA_DIR, exist_ok=True)

# ---------------------------
# Helpers
# ---------------------------
def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def clean_price(x):
    if pd.isna(x):
        return np.nan
    s = str(x)
    # strip currency & commas
    s = re.sub(r"[₹$,]", "", s, flags=re.I).strip()
    # ignore textual placeholders
    if s == "" or re.search(r"(price.*request|na|n/?a|none|null)", s, re.I):
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

CATEGORY_KEYWORDS = [
    (r"(smartphone|mobile|phone)", "Smartphones"),
    (r"(laptop|notebook|ultrabook)", "Laptops"),
    (r"(tablet|ipad)", "Tablets"),
    (r"(watch|wearable)", "Smart Watches"),
    (r"(tv|television|entertain)", "TV & Entertainment"),
    (r"(audio|headphone|earbud|earphone|speaker|soundbar)", "Audio"),
]

def clean_category(val, subcat=None, product_name=None):
    """
    Map messy category strings to normalized 6 buckets.
    Falls back to subcategory / product_name keyword match before returning 'Other'.
    """
    for source in (val, subcat, product_name):
        if pd.isna(source):
            continue
        s = normalize_space(str(source)).lower()
        # handle separators like "Electronics - Smartphones" or "Electronicss - Audio"
        s = s.replace("&", " ").replace("/", " ").replace("-", " ")
        for pat, lab in CATEGORY_KEYWORDS:
            if re.search(pat, s, re.I):
                return lab
        # direct exacts seen in your data
        unified = {
            "electronics smartphones": "Smartphones",
            "electronics laptops": "Laptops",
            "electronics tablets": "Tablets",
            "electronics smart watch": "Smart Watches",
            "electronics tv and entertainment": "TV & Entertainment",
            "electronics audio": "Audio",
        }
        if s in unified:
            return unified[s]
    return "Other"

CITY_FIX = {
    "Bangalore": "Bengaluru",
    "Banglore": "Bengaluru",
    "Bengalore": "Bengaluru",
    "Calcutta": "Kolkata",
    "Madras": "Chennai",
    "Delhi Ncr": "Delhi",
    "Chenai": "Chennai",
}

def clean_city(city):
    if pd.isna(city) or str(city).strip() == "":
        return "Unknown"
    s = normalize_space(str(city)).title()
    return CITY_FIX.get(s, s)

def clean_payment(x):
    if pd.isna(x):
        return "Other"
    s = normalize_space(str(x)).upper()
    if re.search(r"(UPI|GOOGLE ?PAY|G?PAY|PHONE ?PE|BHIM)", s):
        return "UPI"
    if re.search(r"(CREDIT|CC)", s):
        return "Credit Card"
    if re.search(r"(DEBIT|DC)", s):
        return "Debit Card"
    if re.search(r"(COD|C\.?O\.?D)", s):
        return "COD"
    if re.search(r"(NET ?BANK)", s):
        return "Net Banking"
    if re.search(r"(WALLET|PAYTM|AMAZON ?PAY)", s):
        return "Wallet"
    if re.search(r"(BNPL|PAY ?LATER|LAZY ?PAY|SIMPL)", s):
        return "BNPL"
    return "Other"

def to_bool(x):
    if isinstance(x, (int, float)): return int(x) == 1
    s = str(x).strip().lower()
    if s in {"true","yes","y","1"}: return True
    if s in {"false","no","n","0"}: return False
    return False

def clean_rating(r):
    if pd.isna(r): return np.nan
    s = str(r).lower().strip()
    s = s.replace("stars","").replace("star","")
    s = s.replace("/5.0","").replace("/5","")
    s = s.replace("out of 5","")
    s = s.strip()
    try:
        val = float(s)
        return np.nan if val <= 0 else min(val, 5.0)
    except Exception:
        # patterns like "4/5" or "3.5/5"
        m = re.match(r"(\d+(\.\d+)?)[ ]*/[ ]*(\d+(\.\d+)?)", s)
        if m:
            num = float(m.group(1)); den = float(m.group(3))
            if den > 0: return round(min(num/den*5.0, 5.0), 2)
        return np.nan

def parse_date_series(s):
    # tolerant mixed formats with dayfirst; then coerce again without to catch ISO
    d = pd.to_datetime(s, errors="coerce", dayfirst=True)
    mask = d.isna()
    if mask.any():
        d2 = pd.to_datetime(s[mask], errors="coerce", dayfirst=False)
        d.loc[mask] = d2
    return d

def clean_delivery_days(x):
    if pd.isna(x): return np.nan
    s = str(x).strip().lower()
    if s in {"same day","same-day","today"}: return 0
    m = re.match(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        a,b = int(m.group(1)), int(m.group(2))
        return float((a+b)/2)
    m = re.match(r"(\d+)", s)
    if m:
        val = int(m.group(1))
        # clamp unrealistic values
        if val < 0: return np.nan
        if val > 30: return np.nan
        return float(val)
    return np.nan

def value_segment(amount):
    if pd.isna(amount): return "Unknown"
    a = float(amount)
    if a <= 5000: return "Low"
    if a <= 20000: return "Mid"
    if a <= 50000: return "High"
    if a <= 100000: return "Premium"
    return "Luxury"

# ---------------------------
# Load & Clean
# ---------------------------
def load_and_clean(csv_path: str) -> pd.DataFrame:
    print(f"📂 Loading: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded shape: {df.shape}")

    # unify city column -> 'city'
    city_cols = [c for c in df.columns if c.lower() in {"city","customer_city"}]
    if city_cols:
        df["city"] = df[city_cols[0]]
    else:
        df["city"] = "Unknown"

    # dates
    df["order_date"] = parse_date_series(df.get("order_date"))
    df = df.dropna(subset=["order_date"]).copy()

    # prices
    for col in ["original_price_inr","discounted_price_inr","final_amount_inr","subtotal_inr"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_price)

    # choose final_amount; fallback to discounted/original
    if "final_amount_inr" not in df.columns:
        df["final_amount_inr"] = np.nan
    df["final_amount_inr"] = (
        df["final_amount_inr"]
        .fillna(df.get("discounted_price_inr"))
        .fillna(df.get("subtotal_inr"))
        .fillna(df.get("original_price_inr"))
    )
    df["final_amount_inr"] = df["final_amount_inr"].fillna(0)

    # rating
    if "customer_rating" in df.columns:
        df["customer_rating"] = df["customer_rating"].apply(clean_rating)

    # prime flags -> is_prime (bool)
    if "is_prime_member" in df.columns:
        df["is_prime"] = df["is_prime_member"].apply(to_bool)
    elif "is_prime" in df.columns:
        df["is_prime"] = df["is_prime"].apply(to_bool)
    elif "is_prime_eligible" in df.columns:
        df["is_prime"] = df["is_prime_eligible"].apply(to_bool)
    else:
        df["is_prime"] = False

    # payment
    if "payment_method" in df.columns:
        df["payment_method"] = df["payment_method"].apply(clean_payment)
    else:
        df["payment_method"] = "Other"

    # delivery_days
    if "delivery_days" in df.columns:
        df["delivery_days"] = df["delivery_days"].apply(clean_delivery_days)

    # categories (use category, subcategory, product_name)
    df["category"] = df.apply(
        lambda r: clean_category(
            r.get("category"),
            r.get("subcategory"),
            r.get("product_name"),
        ),
        axis=1,
    )

    # city normalization
    df["city"] = df["city"].apply(clean_city)

    # derived time fields
    df["order_year"] = df["order_date"].dt.year
    df["order_month_num"] = df["order_date"].dt.month
    df["order_quarter"] = df["order_date"].dt.quarter
    df["month_label"] = df["order_date"].dt.strftime("%Y-%m")  # 'YYYY-MM'

    # value segment
    df["order_value_segment"] = df["final_amount_inr"].apply(value_segment)

    # basic QA flags
    df["is_possible_duplicate"] = False
    dup_keys = ["customer_id","product_id","order_date","final_amount_inr"]
    if all(k in df.columns for k in dup_keys):
        counts = df.groupby(dup_keys)["transaction_id"].transform("count")
        df["is_possible_duplicate"] = counts > 1

    return df

# ---------------------------
# SQL + EDA
# ---------------------------
def save_to_sqlite(df: pd.DataFrame):
    print("💾 Writing to SQLite...")
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("transactions", conn, if_exists="replace", index=False)
    # helpful indexes
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_year ON transactions(order_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_city ON transactions(city)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_cat  ON transactions(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_cust ON transactions(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_prod ON transactions(product_id)")
    except Exception:
        pass
    conn.execute("VACUUM")
    conn.close()
    print(f"✅ Database saved: {DB_PATH}")

def generate_eda(df: pd.DataFrame):
    print("📊 Generating analytics summaries...")

    eda = {}

    # Category performance (count/sum/mean)
    eda["category_performance.csv"] = (
        df.groupby("category", as_index=False)["final_amount_inr"]
          .agg(count="count", revenue="sum", avg="mean")
          .sort_values("revenue", ascending=False)
    )

    # City revenue
    eda["city_revenue.csv"] = (
        df.groupby("city", as_index=False)["final_amount_inr"]
          .sum().rename(columns={"final_amount_inr":"revenue"})
          .sort_values("revenue", ascending=False)
    )

    # Payment share
    eda["payment_share.csv"] = (
        df.groupby("payment_method", as_index=False)["final_amount_inr"]
          .sum().rename(columns={"final_amount_inr":"revenue"})
          .sort_values("revenue", ascending=False)
    )

    # Yearly sales
    eda["sales_by_year.csv"] = (
        df.groupby("order_year", as_index=False)["final_amount_inr"]
          .sum().rename(columns={"final_amount_inr":"revenue"})
          .sort_values("order_year")
    )

    # Monthly revenue (YYYY-MM label)
    eda["monthly_revenue.csv"] = (
        df.groupby("month_label", as_index=False)["final_amount_inr"]
          .sum().rename(columns={"final_amount_inr":"revenue"})
          .sort_values("month_label")
    )

    # Top products / customers
    if "product_name" in df.columns:
        eda["top_products.csv"] = (
            df.groupby(["product_id","product_name"], as_index=False)["final_amount_inr"]
              .sum().rename(columns={"final_amount_inr":"revenue"})
              .sort_values("revenue", ascending=False).head(50)
        )
    else:
        eda["top_products.csv"] = (
            df.groupby(["product_id"], as_index=False)["final_amount_inr"]
              .sum().rename(columns={"final_amount_inr":"revenue"})
              .sort_values("revenue", ascending=False).head(50)
        )

    eda["top_customers.csv"] = (
        df.groupby("customer_id", as_index=False)["final_amount_inr"]
          .sum().rename(columns={"final_amount_inr":"revenue"})
          .sort_values("revenue", ascending=False).head(50)
    )

    # Prime vs non-prime
    eda["prime_vs_nonprime.csv"] = (
        df.groupby("is_prime", as_index=False)["final_amount_inr"]
          .sum().rename(columns={"final_amount_inr":"revenue"})
    )

    # Save all EDA CSVs
    for name, data in eda.items():
        data.to_csv(os.path.join(EDA_DIR, name), index=False)

    # Insights summary
    insights_path = os.path.join(EDA_DIR, "insights.txt")
    total_revenue = float(df["final_amount_inr"].sum())
    total_orders  = int(len(df))
    avg_order     = float(df["final_amount_inr"].mean())

    top_city = (df.groupby("city")["final_amount_inr"].sum().sort_values(ascending=False).index[0]
                if df["city"].notna().any() else "Unknown")
    top_category = (df.groupby("category")["final_amount_inr"].sum().sort_values(ascending=False).index[0]
                    if df["category"].notna().any() else "Other")

    with open(insights_path, "w") as f:
        f.write(f"Total revenue: ₹{total_revenue:,.0f}\n")
        f.write(f"Total orders: {total_orders:,}\n")
        f.write(f"Avg order value: ₹{avg_order:,.0f}\n")
        f.write(f"Top city: {top_city}\n")
        f.write(f"Top category: {top_category}\n")

    print(f"✅ EDA summaries saved in: {EDA_DIR}")

def save_clean_csv(df: pd.DataFrame):
    out = os.path.join(OUTPUT_DIR, "amazon_cleaned.csv")
    df.to_csv(out, index=False)
    print(f"📤 Cleaned CSV exported: {out}")

def write_qa_report(df_before: pd.DataFrame, df_after: pd.DataFrame):
    rows_before = len(df_before)
    rows_after = len(df_after)
    dropped = rows_before - rows_after

    def counts(series, topn=5):
        vc = series.value_counts(dropna=False).head(topn)
        return "; ".join(f"{k}({v})" for k,v in vc.items())

    qa = []
    qa.append({"metric":"rows_before", "value": rows_before})
    qa.append({"metric":"rows_after", "value": rows_after})
    qa.append({"metric":"rows_dropped_due_to_invalid_dates", "value": dropped})

    for col in ["category","city","payment_method"]:
        qa.append({
            "metric": f"top_{col}_after",
            "value": counts(df_after[col])
        })

    qa_df = pd.DataFrame(qa)
    qa_path = os.path.join(QA_DIR, "cleaning_summary.csv")
    qa_df.to_csv(qa_path, index=False)
    print(f"🧪 QA summary saved: {qa_path}")

# ---------------------------
# Main
# ---------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Amazon Analytics Pipeline v2 (hardened)")
    parser.add_argument("--input_csv", required=True, help="Path to input CSV")
    parser.add_argument("--export_csv", action="store_true", help="Also export cleaned CSV")
    args = parser.parse_args()

    raw = pd.read_csv(args.input_csv)  # for QA counts
    df = load_and_clean(args.input_csv)
    write_qa_report(raw, df)
    save_to_sqlite(df)
    generate_eda(df)
    if args.export_csv:
        save_clean_csv(df)
    print("\n✅ Pipeline v2 complete. Dashboard-ready data generated.\n")

if __name__ == "__main__":
    main()

