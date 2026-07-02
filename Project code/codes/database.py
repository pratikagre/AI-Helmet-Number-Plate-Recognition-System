import sqlite3
import os
import streamlit as st

DB_FOLDER = "database"
DB_PATH = os.path.join(DB_FOLDER, "detection_records.db")

os.makedirs(DB_FOLDER, exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS detection_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    vehicle_count INTEGER,
    person_count INTEGER,
    helmet_detected INTEGER,
    triple_seat_detected INTEGER
)
""")
conn.commit()

try:
    cursor.execute("ALTER TABLE detection_records ADD COLUMN triple_seat_detected INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE detection_records ADD COLUMN number_plate TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE detection_records ADD COLUMN missing_plate_detected INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass

def insert_detection_record(timestamp, vehicle_count, person_count, helmet_detected, triple_seat_detected=False, missing_plate_detected=False, number_plate=None):
    cursor.execute(
        "INSERT INTO detection_records (timestamp, vehicle_count, person_count, helmet_detected, triple_seat_detected, missing_plate_detected, number_plate) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (timestamp, vehicle_count, person_count, int(helmet_detected), int(triple_seat_detected), int(missing_plate_detected), number_plate),
    )
    conn.commit()

import random
from datetime import datetime, timedelta
import cv2
import numpy as np
import os

def create_dummy_snapshot(plate):
    """Creates a blank dummy image representing a snapshot for testing emails."""
    snapshots_dir = "snapshots"
    os.makedirs(snapshots_dir, exist_ok=True)
    
    img = np.zeros((300, 500, 3), dtype=np.uint8)
    img[:] = (200, 200, 200) # Gray background
    cv2.putText(img, f"DUMMY SNAPSHOT", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(img, f"PLATE: {plate}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "(For testing purposes)", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 1)
    
    path = os.path.join(snapshots_dir, f"dummy_{plate.replace(' ', '')}.jpg")
    cv2.imwrite(path, img)
    return path

def insert_dummy_data():
    plates = ["MH 04 JL 8820", "DL 1C AA 1111", "MH 12 AB 1234", "RJ 14 CC 4321", "UP 32 EE 5555", "GJ 01 XX 9999"]
    for i in range(10):
        # random past time
        random_time = datetime.now() - timedelta(hours=random.randint(1, 48), minutes=random.randint(1, 60))
        timestamp = random_time.strftime("%Y-%m-%d %H:%M:%S")
        
        vehicle_count = random.randint(1, 3)
        person_count = random.randint(1, 4)
        
        # 30% chance of triple seat, 40% chance of no helmet
        triple_seat_detected = 1 if person_count > 2 and vehicle_count == 1 else 0
        helmet_detected = 1 if random.random() < 0.6 else 0
        
        plate = random.choice(plates) if random.random() > 0.3 else None
        
        # Determine if email needs to be sent
        violations = []
        if helmet_detected == 0:
            violations.append("No Helmet")
        if triple_seat_detected == 1:
            violations.append("Triple Seat")
        if not violations:
            violations.append("Plate Only Logged")
            
        if plate: # Send for any detected plate
            # Generate a fake snapshot and send email
            dummy_img_path = create_dummy_snapshot(plate)
            
            # Lazy import to prevent circular dependency
            from video_detection import send_challan_email
            
            try:
                # Triggering email but suppressing Streamlit rendering errors in this non-frontend scope
                send_challan_email(plate, violations, dummy_img_path)
            except Exception as e:
                print(f"Dummy email trigger error: {e}")
                
        insert_detection_record(timestamp, vehicle_count, person_count, helmet_detected, triple_seat_detected, 0, plate)

def database_tab():
    st.header("📊 Detection Records")
    
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("➕ Add Dummy Data"):
            insert_dummy_data()
            st.success("Dummy data added!")
            st.rerun()
            
    cursor.execute("SELECT * FROM detection_records ORDER BY id DESC")
    rows = cursor.fetchall()
    
    if len(rows) > 0:
        import pandas as pd
        cursor.execute("PRAGMA table_info(detection_records)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        df = pd.DataFrame(rows, columns=column_names)
        
        # Rename and format for readability
        rename_map = {
            "id": "ID", "timestamp": "Timestamp", "vehicle_count": "Vehicles", 
            "person_count": "Persons", "helmet_detected": "Helmet Detected", 
            "triple_seat_detected": "Triple Seat", "number_plate": "Number Plate",
            "missing_plate_detected": "Missing Plate"
        }
        df.rename(columns=rename_map, inplace=True)
        
        # Make boolean conversions for better readability
        if "Helmet Detected" in df.columns:
            df["Helmet Detected"] = df["Helmet Detected"].apply(lambda x: "Yes" if x == 1 else ("No (Violation)" if pd.notnull(x) else "N/A"))
        if "Triple Seat" in df.columns:
            df["Triple Seat"] = df["Triple Seat"].apply(lambda x: "Yes (Violation)" if x == 1 else "No")
        if "Missing Plate" in df.columns:
            df["Missing Plate"] = df["Missing Plate"].apply(lambda x: "Yes (Violation)" if x == 1 else "No")
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found in database.")
