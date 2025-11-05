import sys, os
import streamlit as st
import pandas as pd

# ✅ Fix import path for Streamlit Cloud
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import page_title, save_uploaded_file, load_data_from_drive

st.set_page_config(page_title="Amazon India - Sales Analytics", layout="wide")

page_title("Amazon India - A Decade of Sales Analytics")
st.write("📂 Upload or Load the dataset to proceed.")

# ✅ Session state for consistent access across pages
if "data" not in st.session_state:
    st.session_state["data"] = None

# 🔹 File Uploader
uploaded_file = st.file_uploader("Upload CSV Dataset (Max 200MB)", type=["csv"])

if uploaded_file:
    file_path = save_uploaded_file(uploaded_file)
    if file_path:
        st.session_state["data"] = pd.read_csv(file_path)
        st.success("✅ Dataset uploaded and ready!")

# 🔹 Google Drive Button
drive_link = st.text_input("OR Paste Google Drive CSV Link:")
if st.button("📁 Load Dataset from Google Drive"):
    df_drive = load_data_from_drive(drive_link)
    if df_drive is not None:
        st.session_state["data"] = df_drive
        st.success("✅ Dataset loaded from Google Drive successfully!")

# 🔹 Dataset Preview
if st.session_state["data"] is not None:
    st.dataframe(st.session_state["data"].head())
    st.write(f"**Total Rows:** {len(st.session_state['data'])} | **Total Columns:** {st.session_state['data'].shape[1]}")
    st.success("✅ Dataset is ready for use in all other pages!")
else:
    st.info("💡 Upload a CSV or load from Google Drive to begin.")
