# 🛒 Amazon India – A Decade of Sales Analytics (2015–2025)

This project is a Streamlit-based interactive dashboard that analyzes **10 years of Amazon India sales data**.  
It provides insights across revenue, customers, products, profit, returns, pricing, demand forecasting, and logistics.

---

## ✅ Key Features (Dashboard Pages)

✔ Revenue Trends (Yearly, Monthly, YoY Growth)  
✔ Customer Analytics (New vs Returning, RFM Segmentation)  
✔ Product & Brand Performance  
✔ Payment Method Insights (COD vs Online)  
✔ Order Returns & Logistics Metrics  
✔ Festival & Seasonal Sales Impact (Diwali, Big Billion Days, etc.)  
✔ Regional Insights (State / City / Zone-Level Revenue)  
✔ Sales Forecasting (Prophet / ARIMA models)  
✔ Customer Lifetime Value (CLV) Analysis  
✔ Market Basket Analysis (Frequent Itemsets / Association Rules)  
✔ Profit, Cost & Discount Impact  
✔ Price Elasticity & Revenue Optimization  
✔ Export to Excel and SQL (Report Export Page)

---

## 📂 Project Structure

Amazon-India-Sales-Analytics/
├── streamlit_app/
│ ├── Home.py
│ ├── utils.py
│ ├── pages/
│ │ ├── 1_Revenue_Trends.py
│ │ ├── 2_Customer_Analytics.py
│ │ ├── 3_Product_Performance.py
│ │ ├── 4_Payment_Insights.py
│ │ ├── 5_Logistics_and_Returns.py
│ │ ├── ...
│ │ ├── 21_Report_Export.py
├── data/
│ ├── cleaned_sample.csv (sample of main dataset)
├── requirements.txt
├── README.md

yaml
Copy code

---

## ⚙️ How to Run This Project

### ✅ 1. Install Dependencies
pip install -r requirements.txt

shell
Copy code

### ✅ 2. Run the Streamlit App
streamlit run streamlit_app/Home.py

yaml
Copy code

### ✅ 3. Upload Your CSV File in the Web App  
Once you upload the cleaned dataset, all dashboards will automatically load insights.

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Dashboard | Streamlit |
| Data Processing | Pandas, NumPy |
| Visualizations | Altair, Plotly, Matplotlib |
| Forecasting | Prophet / ARIMA (Statsmodels) |
| ML / Segmentation | Scikit-learn |
| Market Basket Analysis | Mlxtend |
| Database / Export | SQLAlchemy, OpenPyXL |

---

## 📌 Dataset Information

- Duration: **2015–2025 (10 years)**  
- Records: **1 Million+ Orders**  
- Columns include: `order_id, order_date, customer_id, product_name, brand, category, quantity, selling_price, discounted_price, payment_method, state, city, pincode, fulfillment, return_flag`

---

## 👤 Author

**Thirumal**  
GUVI – Data Analytics Assignment

---

⭐ *Feel free to fork, contribute or use this as a portfolio project.*
