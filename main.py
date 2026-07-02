import torch
# Monkeypatch torch.load to default weights_only to False for PyTorch 2.6+ compatibility
orig_load = torch.load
def patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return orig_load(*args, **kwargs)
torch.load = patched_load

import streamlit as st
import sqlite3

# ---- Page Configuration ----
st.set_page_config(page_title="Helmet & Number Plate Detection", layout="wide")

# Import modules correctly
from video_detection import video_detection_tab
from database import database_tab
from home import home_tab  # Ensure correct import
from dashboard import dashboard_tab

# ---- Database Setup ----
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Create users table if not exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    password TEXT NOT NULL
)
''')
conn.commit()

# ---- Set Background & Styling ----
page_bg = """
<style>
    [data-testid="stAppViewContainer"] {
        background-image: url("https://th.bing.com/th/id/OIP.5N4jjWRg9lG3YAGyxX916QHaE7?w=304&h=203&c=7&r=0&o=5&dpr=1.3&pid=1.7");
        background-size: 1190px 750px; /* Adjust as needed */
        background-repeat: no-repeat;
        background-position: right top; /* Moves image to the right */
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background-color: #2C2C2C !important;
        color: #EAEAEA !important;
    }
    [data-testid="stSidebar"] * {
        color: #EAEAEA !important;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background-color: rgba(0,0,0,0);
    }
    .stButton>button {
        background-color: #007BFF !important;
        color: #FFFFFF !important;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        padding: 8px 16px;
    }
    .stButton>button:hover {
        background-color: #32CD32 !important;
    }
</style>
"""
st.markdown(page_bg, unsafe_allow_html=True)

# ---- User Authentication ----
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# ---- Sidebar Navigation (Only After Login) ----
if st.session_state.user_authenticated:
    st.sidebar.title("🚀 Helmet & Number Plate Detection")
    
    # Logout button
    if st.sidebar.button("🚪 Log Out"):
        st.session_state.user_authenticated = False
        st.session_state.user_email = None
        st.rerun()
    
    # Page Navigation
    page = st.sidebar.radio(
        "Navigation", 
        ["🏠 Home", "📷 Live Tracking", "📊 Database", "📈 Dashboard"]
    )

    # ---- Load Pages ----
    if page == "🏠 Home":
        home_tab()
    elif page == "📷 Live Tracking":
        video_detection_tab()
    elif page == "📊 Database":
        database_tab()
    elif page == "📈 Dashboard":
        dashboard_tab()

else:
    # ---- Signup & Login Sidebar ----
    st.sidebar.subheader("🔐 Authentication")
    auth_option = st.sidebar.radio("Choose Option:", ["Sign In", "Log In"])

    # ---- Sign-Up Page ----
    if auth_option == "Sign In":
        st.sidebar.subheader("📝 Create a New Account")
        name = st.sidebar.text_input("Full Name")
        email = st.sidebar.text_input("Email")
        phone = st.sidebar.text_input("Mobile Number")
        password = st.sidebar.text_input("Set Password", type="password")

        if st.sidebar.button("Sign Up"):
            if name and email and phone and password:
                cursor.execute("SELECT * FROM users WHERE email=?", (email,))
                existing_user = cursor.fetchone()
                if existing_user:
                    st.sidebar.error("❌ Email already exists! Please Log In.")
                else:
                    cursor.execute("INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)", 
                                   (name, email, phone, password))
                    conn.commit()
                    st.sidebar.success("✅ Account Created! Please Log In.")
            else:
                st.sidebar.error("❌ Please fill in all fields.")

    # ---- Login Page ----
    elif auth_option == "Log In":
        st.sidebar.subheader("🔑 Log In to Your Account")
        login_email = st.sidebar.text_input("Email")
        login_password = st.sidebar.text_input("Password", type="password")

        if st.sidebar.button("Log In"):
            cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (login_email, login_password))
            user_data = cursor.fetchone()

            if user_data:
                st.session_state.user_authenticated = True
                st.session_state.user_email = login_email
                st.sidebar.success("✅ Login Successful!")
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid Credentials! Please Sign In First.")

    st.warning("🔒 Please Log In or Sign Up to access the system.")
