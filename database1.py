import sqlite3
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime  # Added missing import

def initialize_database():
    """Initialize the database connection and tables"""
    DB_FOLDER = "database"
    DB_PATH = os.path.join(DB_FOLDER, "detection_records.db")
    os.makedirs(DB_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()

    # Initialize database
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detection_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        vehicle_count INTEGER,
        person_count INTEGER,
        helmet_detected INTEGER,
        image_path TEXT,
        user_id INTEGER
    )
    """)
    conn.commit()
    return conn, cursor

def save_detection_record(conn, cursor, vehicle_count, person_count, helmet_detected, image_path=None, user_id=None):
    """Save detection record to database"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO detection_records (timestamp, vehicle_count, person_count, helmet_detected, image_path, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (timestamp, vehicle_count, person_count, int(helmet_detected), image_path, user_id)
    )  # Added missing closing parenthesis
    conn.commit()

def database_tab(conn, cursor):
    """Enhanced Database Records Tab with filtering and visualization"""
    st.title("📋 Detection Records Database")
    st.markdown("""
    <style>
        .database-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="database-container">', unsafe_allow_html=True)
    
    # Date range filter
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM detection_records")
    result = cursor.fetchone()
    min_date, max_date = result if result else (None, None)
    
    if min_date and max_date:
        min_date = pd.to_datetime(min_date).date()
        max_date = pd.to_datetime(max_date).date()
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        # Additional filters
        col1, col2 = st.columns(2)
        with col1:
            min_vehicles = st.number_input("Minimum Vehicles", 
                                         min_value=0, 
                                         value=0,
                                         help="Filter by minimum number of vehicles")
        with col2:
            compliance_filter = st.selectbox(
                "Compliance Status",
                ["All", "Compliant", "Non-Compliant"],
                help="Filter by helmet compliance status"
            )
        
        # Get filtered records
        query = """
        SELECT 
            id,
            timestamp as "Timestamp",
            vehicle_count as "Vehicles",
            person_count as "Persons",
            CASE 
                WHEN helmet_detected = 1 THEN 'Yes'
                ELSE 'No'
            END as "Helmet Detected",
            image_path as "Image Path",
            user_id as "User ID"
        FROM detection_records
        WHERE date(timestamp) BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        
        if min_vehicles > 0:
            query += " AND vehicle_count >= ?"
            params.append(min_vehicles)
        
        if compliance_filter == "Compliant":
            query += " AND helmet_detected = 1"
        elif compliance_filter == "Non-Compliant":
            query += " AND helmet_detected = 0"
        
        query += " ORDER BY timestamp DESC"
        
        df = pd.read_sql(query, conn, params=params)
        
        # Show statistics
        st.subheader("📊 Summary Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Records", len(df))
        
        with col2:
            if len(df) > 0:
                compliance_rate = df[df["Helmet Detected"] == "Yes"].shape[0] / len(df) * 100
                st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
            else:
                st.metric("Compliance Rate", "N/A")
        
        with col3:
            if len(df) > 0:
                avg_vehicles = df["Vehicles"].mean()
                st.metric("Avg Vehicles", f"{avg_vehicles:.1f}")
            else:
                st.metric("Avg Vehicles", "N/A")
        
        # Show records
        st.subheader("📋 Detection Records")
        
        # Add image preview column if images exist
        if not df[df["Image Path"].notnull()].empty:
            df["Preview"] = df["Image Path"].apply(
                lambda x: f'<a href="{x}" target="_blank"><img src="{x}" width="100"></a>' 
                if x else None
            )
            st.markdown(df.to_html(escape=False), unsafe_allow_html=True)
        else:
            st.dataframe(df, height=400, use_container_width=True)
        
        # Export options
        st.subheader("💾 Export Data")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export as CSV",
                data=csv,
                file_name=f"detections_{start_date}_to_{end_date}.csv",
                mime='text/csv'
            )
        
        with col2:
            with pd.ExcelWriter("temp.xlsx", engine='openpyxl') as writer:  # Using context manager
                df.to_excel(writer, index=False)
            with open("temp.xlsx", "rb") as f:
                excel_data = f.read()
            st.download_button(
                label="📥 Export as Excel",
                data=excel_data,
                file_name=f"detections_{start_date}_to_{end_date}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            os.remove("temp.xlsx")
    else:
        st.warning("No detection records found in the database.")
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    conn, cursor = initialize_database()
    database_tab(conn, cursor)