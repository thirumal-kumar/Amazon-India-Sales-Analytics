import streamlit as st
import pandas as pd
import os
import requests

# ✅ Google Drive raw download URL builder
def convert_drive_link(shared_link: str):
    if "drive.google.com" in shared_link and "id=" not in shared_link:
        file_id = shared_link.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return shared_link

# ✅ Title function
def page_title(title: str):
    st.markdown(f"<h2 style='text-align:center;'>{title}</h2>", unsafe_allow_html=True)

# ✅ Save uploaded file (drag & drop)
def save_uploaded_file(uploaded_file):
    try:
        os.makedirs("outputs", exist_ok=True)
        file_path = os.path.join("outputs", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"File saving error: {e}")
        return None

# ✅ Load CSV from Google Drive (if exists)
def load_data_from_drive(shared_link=None):
    if not shared_link:
        return None
    
    try:
        download_url = convert_drive_link(shared_link)
        response = requests.get(download_url)
        response.raise_for_status()

        if response.headers.get("Content-Type", "").startswith("text/csv"):
            return pd.read_csv(pd.compat.StringIO(response.text))
        else:
            st.warning("⚠ Google Drive returned HTML — not CSV. Please enable 'Anyone with link can view'.")
            return None
    except Exception as e:
        st.error(f"❌ Failed to load CSV from Drive: {e}")
        return None
