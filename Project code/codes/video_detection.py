import streamlit as st
import cv2
import numpy as np
import os
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
from database import insert_detection_record
import pytesseract
import re
import smtplib
from email.message import EmailMessage
import time
import threading

# Global dictionary to track recently notified plates to avoid spamming
recently_notified = {}
NOTIFICATION_COOLDOWN = 60 # seconds

# Dummy RTO Database Simulation
# In a real scenario, this would connect to an RTO API to get the owner's email
RTO_DATABASE = {
    "MH 04 JL 8820": "22pratikagre@gmail.com", # Change to actual owner's email
    "DL 1C AA 1111": "22pratikagre@gmail.com",
    "MH 12 AB 1234": "22pratikagre@gmail.com",
    "RJ 14 CC 4321": "22pratikagre@gmail.com",
    "UP 32 EE 5555": "22pratikagre@gmail.com",
    "GJ 01 XX 9999": "22pratikagre@gmail.com",
    "MH 32 AF 4884": "22pratikagre@gmail.com", # Added from user image
    "MH 32 AF4884": "22pratikagre@gmail.com"
}

def send_challan_email(plate_number, violations, snapshot_path=None):
    # Setup sender email credentials
    sender_email = "22pratikagre@gmail.com" 
    sender_password = "cgbvwnynkqlsztcb"
    
    # 1. Fetch Owner's Email based on Number Plate
    # If not registered in dummy db, default to the tracking admin email
    receiver_email = RTO_DATABASE.get(plate_number, "22pratikagre@gmail.com")
    
    msg = EmailMessage()
    msg['Subject'] = f"🚨 E-Challan Alert: Traffic Violation Detected for {plate_number}"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    violation_str = ", ".join(violations)
    
    content = f"""
    Dear Vehicle Owner,
    
    An automated traffic enforcement camera has detected a violation associated with your vehicle registration number.
    
    Vehicle Number Plate: {plate_number}
    Detected Infraction(s): {violation_str}
    Time of Detection: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    A snapshot of the incident is attached to this email for your reference.
    Please ensure to follow traffic rules for everyone's safety.
    
    Regards,
    Traffic Police Automation System
    """
    msg.set_content(content)
    
    # Attach image if available
    if snapshot_path and os.path.exists(snapshot_path):
        with open(snapshot_path, 'rb') as img:
            img_data = img.read()
            msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=os.path.basename(snapshot_path))
    
    # Send email in a separate thread so it doesn't block video processing
    def send_email_thread():
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)
            print(f"Challan email sent successfully for {plate_number}")
        except Exception as e:
            print(f"Failed to send email: {e}")
            
    threading.Thread(target=send_email_thread).start()

# Helper function to validate Number Plate structure
def is_standard_number_plate(text):
    text = text.upper()
    text = "".join(filter(str.isalnum, text))
    
    if len(text) < 8 or len(text) > 11:
        return text, False
        
    corrected = list(text)
    if len(corrected) >= 8:
        for i in range(2):
            if corrected[i] == '0': corrected[i] = 'O'
            elif corrected[i] == '1': corrected[i] = 'I'
            elif corrected[i] == '8': corrected[i] = 'B'
        
        for i in range(len(corrected)-4, len(corrected)):
            if corrected[i] == 'O': corrected[i] = '0'
            elif corrected[i] == 'I': corrected[i] = '1'
            elif corrected[i] == 'B': corrected[i] = '8'
            elif corrected[i] == 'S': corrected[i] = '5'
            elif corrected[i] == 'Z': corrected[i] = '2'
            
    corrected_str = "".join(corrected)
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"
    
    if re.match(pattern, corrected_str):
        return corrected_str, True
    return text, False

# Set Tesseract path (Update if needed on your system)
# Ignore errors if not strictly found, handled gracefully later
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load the YOLO models
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
model = YOLO(os.path.join(SCRIPT_DIR, "best.pt"))
try:
    person_model = YOLO(os.path.join(SCRIPT_DIR, "yolov8n.pt"))  # Standard YOLOv8 detects individual people well
except:
    person_model = None

# Define class names
class_names = ["Helmet", "Number Plate", "Person", "Motorbike"]

# Ensure snapshot folder exists
SNAPSHOT_FOLDER = "snapshots"
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

def save_snapshot(frame):
    """Saves a snapshot if a number plate is detected."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = os.path.join(SNAPSHOT_FOLDER, f"snapshot_{timestamp}.jpg")
    cv2.imwrite(snapshot_path, frame)
    st.success(f"📸 Snapshot saved: {snapshot_path}")
    return snapshot_path

def process_video(cap):
    """Processes video or webcam frame-by-frame and applies detection."""
    stframe = st.empty()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        processed_frame, vehicle_count, person_count, helmet_detected, missing_helmet_detected, number_plate_detected, triple_seat_detected, missing_plate_detected, detected_plates = draw_detections(frame, results)

        # Insert data into the database
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plate_str = ", ".join(detected_plates) if detected_plates else None
        insert_detection_record(timestamp, vehicle_count, person_count, helmet_detected, triple_seat_detected, missing_plate_detected, plate_str)

        # Save snapshot if number plate detected
        snapshot_path_saved = None
        if number_plate_detected:
            snapshot_path_saved = save_snapshot(processed_frame)
            
        # Check for Challan Condition: Standard Plate + Any Detection
        current_time = time.time()
        for idx in range(len(detected_plates)):
            plate_info = detected_plates[idx]
            if "(Standard)" in plate_info or "(Stylish)" in plate_info:
                # Extract actual plate text
                clean_plate = plate_info.split()[0]
                
                # If there's any detection in this frame
                violations = []
                if missing_helmet_detected:
                    violations.append("No Helmet")
                if triple_seat_detected:
                    violations.append("Triple Seat")
                if not violations:
                    violations.append("Plate Only Logged")
                    
                # Setup Alert string
                if "Plate Only Logged" in violations:
                    alert_str = f"ℹ️ PLATE DETECTED: {clean_plate}"
                else:
                    alert_str = f"🚨 CHALLAN GENERATED: {clean_plate} for {', '.join(violations)}"

                # Check if already notified recently
                last_notified = recently_notified.get(clean_plate, 0)
                if current_time - last_notified > NOTIFICATION_COOLDOWN:
                    st.info(alert_str)
                    send_challan_email(clean_plate, violations, snapshot_path_saved)
                    recently_notified[clean_plate] = current_time

        # Display processed frame
        stframe.image(processed_frame, channels="BGR", use_column_width=True)

    cap.release()

def process_image(image):
    """Processes a single image for detection."""
    frame = np.array(image)
    results = model(frame)
    processed_frame, vehicle_count, person_count, helmet_detected, missing_helmet_detected, number_plate_detected, triple_seat_detected, missing_plate_detected, detected_plates = draw_detections(frame, results)
    
    # Save snapshot if number plate detected
    snapshot_path_saved = None
    if number_plate_detected:
        snapshot_path_saved = save_snapshot(processed_frame)
        
    # Check for Challan Condition in Image
    for idx in range(len(detected_plates)):
        plate_info = detected_plates[idx]
        if "(Standard)" in plate_info or "(Stylish)" in plate_info:
            clean_plate = plate_info.split()[0]
            violations = []
            if missing_helmet_detected:
                violations.append("No Helmet")
            if triple_seat_detected:
                violations.append("Triple Seat")
            if not violations:
                violations.append("Plate Only Logged")
                
            if "Plate Only Logged" in violations:
                st.info(f"ℹ️ PLATE DETECTED: {clean_plate}")
            else:
                st.error(f"🚨 CHALLAN GENERATED: {clean_plate} for {', '.join(violations)}")
                
            send_challan_email(clean_plate, violations, snapshot_path_saved)
    
    st.image(processed_frame, channels="BGR", use_column_width=True)

def draw_detections(frame, results):
    """Draw bounding boxes and labels on detected objects."""
    helmet_detected, vehicle_count, person_count, number_plate_detected = False, 0, 0, False
    triple_seat_detected = False
    missing_plate_detected = False
    missing_helmet_detected = False
    detected_plates = []
    
    bike_boxes = []
    person_boxes = []
    helmet_boxes = []
    plate_boxes = []

    # Run the person model to detect individual people
    if person_model:
        person_results = person_model(frame, verbose=False)
        for r in person_results:
            boxes = r.boxes.xyxy.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy()
            for box, cls in zip(boxes, classes):
                # Class 0 in standard YOLOv8 is 'person'
                if int(cls) == 0:
                    x1, y1, x2, y2 = map(int, box)
                    person_boxes.append((x1, y1, x2, y2))
                    person_count += 1

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        for box, cls in zip(boxes, classes):
            x1, y1, x2, y2 = map(int, box)
            
            # Since best.pt has: 0='helmet', 1='plate', 2='rider'
            if int(cls) == 0:  # Helmet
                label = "Helmet"
                helmet_detected = True
                helmet_boxes.append((x1, y1, x2, y2))
                color = (0, 255, 0)  # Green
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            elif int(cls) == 1:  # Number Plate
                number_plate_detected = True
                plate_boxes.append((x1, y1, x2, y2))
                
                # Attempt OCR to read the plate
                plate_text = ""
                is_standard = False
                try:
                    plate_img = frame[y1:y2, x1:x2]
                    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    text = pytesseract.image_to_string(thresh, config="--psm 7")
                    plate_text, is_standard = is_standard_number_plate(text)
                except Exception as e:
                    print(f"OCR Exception: {e}")
                    pass
                
                # Default empty plate label behavior if OCR is empty
                if not plate_text:
                    label = "Non-HSRP Plate"
                    color = (0, 0, 255)  # Red
                    detected_plates.append("Unknown (Stylish)")
                else:
                    if is_standard:
                        label = f"HSRP: {plate_text}"
                        color = (0, 255, 0)  # Green
                        detected_plates.append(f"{plate_text} (Standard)")
                    else:
                        label = f"Non-HSRP Plate"
                        color = (0, 0, 255)  # Red
                        detected_plates.append(f"{plate_text} (Stylish)")
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            elif int(cls) == 2:  # Rider Group
                label = "Rider Group"
                bike_boxes.append((x1, y1, x2, y2))
                vehicle_count += 1
                color = (255, 165, 0)  # Orange
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
    # No Helmet and Triple Seat Detection logic
    for bx1, by1, bx2, by2 in bike_boxes:
        persons_on_bike = 0
        for px1, py1, px2, py2 in person_boxes:
            # Check if person center is within the bike box
            px_center = (px1 + px2) // 2
            py_center = (py1 + py2) // 2
            
            if bx1 <= px_center <= bx2 and by1 <= py_center <= by2:
                persons_on_bike += 1
                
                # Check for helmet overlap for this person
                has_helmet = False
                for hx1, hy1, hx2, hy2 in helmet_boxes:
                    # Expand person box upwards slightly to catch helmets just above the person box
                    expanded_py1 = max(0, py1 - 50)
                    inter_x1 = max(px1, hx1)
                    inter_y1 = max(expanded_py1, hy1)
                    inter_x2 = min(px2, hx2)
                    inter_y2 = min(py2, hy2)
                    
                    if inter_x1 < inter_x2 and inter_y1 < inter_y2:
                        has_helmet = True
                        break
                        
                if not has_helmet:
                    missing_helmet_detected = True
                    # Draw No Helmet
                    color = (0, 0, 255) # Red
                    label = "No Helmet"
                    cv2.rectangle(frame, (px1, py1), (px2, py2), color, 2)
                    cv2.putText(frame, label, (px1, max(15, py1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                else:
                    cv2.circle(frame, (px_center, py_center), 5, (0, 255, 0), -1)
                    
        # Check for missing number plate for this bike
        has_plate = False
        for px1, py1, px2, py2 in plate_boxes:
            px_center = (px1 + px2) // 2
            py_center = (py1 + py2) // 2
            
            margin = 30
            if (bx1 - margin <= px_center <= bx2 + margin) and (by1 - margin <= py_center <= by2 + margin):
                has_plate = True
                break
                
        if not has_plate:
            missing_plate_detected = True
            color = (0, 0, 255) # Red
            label = "No Number Plate"
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2)
            cv2.putText(frame, label, (bx1, max(15, by2 + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
        if persons_on_bike > 2:
            triple_seat_detected = True
            alert_text = f"TRIPLE SEAT ({persons_on_bike})"
            text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Highlight bike box in red
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 3)
            # Draw red background for text
            cv2.rectangle(frame, (bx1, max(0, by1 - 30)), (bx1 + text_size[0] + 10, max(0, by1 - 30) + text_size[1] + 10), (0, 0, 255), -1)
            cv2.putText(frame, alert_text, (bx1 + 5, max(0, by1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    if triple_seat_detected:
        warn_text = " WARNING: TRIPLE SEAT DETECTED! "
        text_size = cv2.getTextSize(warn_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.rectangle(frame, (10, 10), (10 + text_size[0], 10 + text_size[1] + 15), (0, 0, 255), -1)
        cv2.putText(frame, warn_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return frame, vehicle_count, person_count, helmet_detected, missing_helmet_detected, number_plate_detected, triple_seat_detected, missing_plate_detected, detected_plates

def video_detection_tab():
    """Streamlit Video Detection Tab."""
    st.header("📹 Video, Image & Live Camera Detection")

    option = st.radio("Choose Input Type:", ("📂 Upload Video", "📸 Upload Image", "📱 Use Mobile Camera", "🎥 Use Webcam"))

    if option == "📂 Upload Video":
        uploaded_video = st.file_uploader("Upload a video file", type=["mp4", "avi", "mov"])
        if uploaded_video is not None:
            temp_video_path = "temp_video.mp4"
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_video.read())
            cap = cv2.VideoCapture(temp_video_path)
            process_video(cap)

    elif option == "📸 Upload Image":
        uploaded_image = st.file_uploader("Upload an image file", type=["jpg", "jpeg", "png"])
        if uploaded_image is not None:
            image = cv2.imdecode(np.frombuffer(uploaded_image.read(), np.uint8), cv2.IMREAD_COLOR)
            process_image(image)

    elif option == "📱 Use Mobile Camera":
        ip_camera_url = st.text_input("Enter Mobile Camera Stream URL:", "http://100.76.208.230:8080/video")
        if st.button("Start Detection"):
            cap = cv2.VideoCapture(ip_camera_url)
            process_video(cap)

    elif option == "🎥 Use Webcam":
        if st.button("Start Webcam Detection"):
            cap = cv2.VideoCapture(0)
            process_video(cap)
