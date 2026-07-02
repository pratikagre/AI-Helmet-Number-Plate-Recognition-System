import os
import cv2
import sqlite3
import pytesseract
import numpy as np
from datetime import datetime
import torch

# Monkeypatch torch.load to default weights_only to False for PyTorch 2.6+ compatibility
orig_load = torch.load
def patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return orig_load(*args, **kwargs)
torch.load = patched_load

from ultralytics import YOLO

# Set the path for Tesseract OCR (Change if installed in a different location)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load YOLO model for number plate detection
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
model = YOLO(os.path.join(SCRIPT_DIR, "best.pt"))

# Snapshot folder path
SNAPSHOT_FOLDER = r"C:\Users\ashis\Downloads\helmet\snapshots"

# SQLite database setup
DB_PATH = "number_plates.db"

def create_database():
    """Creates SQLite database if not exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS detections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        image_path TEXT,
                        number_plate TEXT
                    )''')
    conn.commit()
    conn.close()

def get_latest_snapshot(folder):
    """Returns the latest snapshot from the folder"""
    files = [f for f in os.listdir(folder) if f.endswith(".jpg")]
    if not files:
        print("No snapshots found.")
        return None
    latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(folder, f)))
    return os.path.join(folder, latest_file)

def extract_number_plate(image_path):
    """Detects and extracts the number plate using YOLO and OCR"""
    img = cv2.imread(image_path)
    results = model(img)
    
    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        for box, cls in zip(boxes, classes):
            label = model.names[int(cls)]
            if label == "Number Plate":
                x1, y1, x2, y2 = map(int, box)
                plate_img = img[y1:y2, x1:x2]
                
                # Convert to grayscale and apply thresholding
                gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # Use OCR to extract text
                plate_text = pytesseract.image_to_string(thresh, config="--psm 7")
                plate_text = "".join(filter(str.isalnum, plate_text))  # Clean output
                return plate_text if plate_text else "Unknown"
    
    return "Not Detected"

def store_in_database(image_path, number_plate):
    """Stores detection result in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO detections (timestamp, image_path, number_plate) VALUES (?, ?, ?)", 
                   (timestamp, image_path, number_plate))
    conn.commit()
    conn.close()

def main():
    """Main function to process the latest snapshot"""
    create_database()
    
    latest_image = get_latest_snapshot(SNAPSHOT_FOLDER)
    if latest_image:
        print(f"Processing: {latest_image}")
        number_plate = extract_number_plate(latest_image)
        print(f"Extracted Number Plate: {number_plate}")
        store_in_database(latest_image, number_plate)
        print("Data stored in database successfully!")

if __name__ == "__main__":
    main()
