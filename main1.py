# MUST BE THE FIRST STREAMLIT COMMAND
import streamlit as st
st.set_page_config(
    page_title="Safety Vision AI", 
    layout="wide",
    page_icon="🛡️"
)

# Regular imports
import sqlite3
import os
from datetime import datetime
from streamlit_option_menu import option_menu
import hashlib  # For password hashing

# Import tab functions
from video_detection1 import video_detection_tab
from database1 import database_tab
from home1 import home_tab
from dashboard1 import dashboard_tab

def initialize_database():
    """Initialize the safety database connection and tables"""
    # Create database directory if it doesn't exist
    os.makedirs("database", exist_ok=True)
    
    conn = sqlite3.connect("database/safety.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Create users table with hashed passwords
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        registration_date TEXT,
        last_login TEXT
    )
    ''')
    
    # Create detection records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detection_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        vehicle_count INTEGER,
        person_count INTEGER,
        helmet_detected INTEGER,
        image_path TEXT,
        user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')
    
    conn.commit()
    return conn, cursor

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, provided_password):
    """Verify a stored password against one provided by user"""
    return stored_hash == hashlib.sha256(provided_password.encode()).hexdigest()

def load_css():
    """Load custom CSS styles"""
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
            border-right: 1px solid #2a2a4a;
        }
        .user-profile {
            padding: 1rem;
            margin-bottom: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            border-left: 4px solid #0078ff;
        }
        .sidebar-footer {
            position: absolute;
            bottom: 0;
            width: 100%;
            padding: 1rem;
            font-size: 0.8rem;
            color: #aaa;
            text-align: center;
        }
        .stButton>button {
            border: none;
            background: linear-gradient(90deg, #0078ff 0%, #00c6ff 100%) !important;
            color: white !important;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .feature-box {
            background: rgba(255, 255, 255, 0.05);
            padding: 1.5rem;
            border-radius: 10px;
            margin-top: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

def authentication_page(conn, cursor):
    """Render the authentication page"""
    st.title("🛡️ SafetyVision AI")
    st.markdown("### Intelligent Traffic Safety Monitoring System")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/3713/3713543.png", width=200)
        st.markdown("""
        <div class="feature-box">
            <h4>Key Features:</h4>
            <ul>
                <li>Real-time helmet detection</li>
                <li>Number plate recognition</li>
                <li>Traffic violation analytics</li>
                <li>Interactive dashboard</li>
                <li>Historical data tracking</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        auth_option = st.radio(
            "Authentication",
            ["Log In", "Sign Up"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if auth_option == "Log In":
            with st.form("login_form"):
                st.subheader("🔑 Log In")
                login_email = st.text_input("Email")
                login_password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Log In", use_container_width=True):
                    cursor.execute(
                        "SELECT id, name, password_hash FROM users WHERE email=?", 
                        (login_email,)
                    )
                    user_data = cursor.fetchone()

                    if user_data and verify_password(user_data[2], login_password):
                        st.session_state.user_authenticated = True
                        st.session_state.user_email = login_email
                        st.session_state.user_name = user_data[1]
                        st.session_state.user_id = user_data[0]
                        
                        # Update last login time
                        cursor.execute(
                            "UPDATE users SET last_login=? WHERE id=?",
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_data[0])
                        )
                        conn.commit()
                        
                        st.rerun()
                    else:
                        st.error("Invalid credentials! Please try again.")
        
        else:  # Sign Up
            with st.form("signup_form"):
                st.subheader("📝 Create Account")
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                phone = st.text_input("Mobile Number")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("Sign Up", use_container_width=True):
                    if password != confirm_password:
                        st.error("Passwords don't match!")
                    elif not all([name, email, phone, password]):
                        st.error("Please fill all fields!")
                    else:
                        try:
                            # Hash password before storing
                            hashed_password = hash_password(password)
                            cursor.execute(
                                "INSERT INTO users (name, email, phone, password_hash, registration_date) VALUES (?, ?, ?, ?, ?)", 
                                (name, email, phone, hashed_password, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            )
                            conn.commit()
                            st.success("Account created successfully! Please log in.")
                        except sqlite3.IntegrityError:
                            st.error("Email already exists! Please log in instead.")

def save_detection_record(conn, cursor, vehicle_count, person_count, helmet_detected, image_path=None):
    """Save a detection record to the database"""
    if 'user_id' in st.session_state:
        user_id = st.session_state.user_id
    else:
        user_id = None
        
    cursor.execute(
        """INSERT INTO detection_records 
        (timestamp, vehicle_count, person_count, helmet_detected, image_path, user_id) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
         vehicle_count, 
         person_count, 
         int(helmet_detected), 
         image_path,
         user_id)
    )
    conn.commit()
    return cursor.lastrowid

def main_app(conn, cursor):
    """Main application after authentication"""
    with st.sidebar:
        st.markdown(f"""
        <div class="user-profile">
            <h3>👋 Welcome, {st.session_state.user_name}!</h3>
            <p>{st.session_state.user_email}</p>
        </div>
        """, unsafe_allow_html=True)
        
        selected = option_menu(
            menu_title="SafetyVision AI",
            options=["🏠 Home", "📷 Live Detection", "📊 Database", "📈 Dashboard"],
            icons=["house", "camera", "database", "bar-chart"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#1a1a1a"},
                "icon": {"color": "orange", "font-size": "16px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#373737"},
                "nav-link-selected": {"background-color": "#0078ff"},
            }
        )
        
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.user_authenticated = False
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.user_id = None
            st.rerun()
            
        st.markdown("---")
        st.markdown("""
        <div class="sidebar-footer">
            <p>SafetyVision AI v2.0</p>
            <p>© 2025 All Rights Reserved</p>
        </div>
        """, unsafe_allow_html=True)

    if selected == "🏠 Home":
        home_tab(conn)
    elif selected == "📷 Live Detection":
        video_detection_tab(conn, cursor, save_detection_record)
    elif selected == "📊 Database":
        database_tab(conn, cursor)
    elif selected == "📈 Dashboard":
        dashboard_tab(conn, cursor)

def main():
    """Main application function"""
    # Initialize session state
    if "user_authenticated" not in st.session_state:
        st.session_state.user_authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_name" not in st.session_state:
        st.session_state.user_name = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    # Initialize database and load CSS
    conn, cursor = initialize_database()
    load_css()
    
    # Render appropriate page based on auth status
    if st.session_state.user_authenticated:
        main_app(conn, cursor)
    else:
        authentication_page(conn, cursor)

if __name__ == "__main__":
    main()