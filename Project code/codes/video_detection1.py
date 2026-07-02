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
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import pytesseract
import re

# Set Tesseract path (Update if needed on your system)
tesseract_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_win_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_win_path

# Load the YOLO model
@st.cache_resource
def load_model():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    return YOLO(os.path.join(SCRIPT_DIR, "best.pt"))

model = load_model()

# Define class names and colors
class_names = ["Helmet", "Number Plate", "Person", "Motorbike"]
class_colors = {
    "Helmet": (0, 255, 0),        # Green
    "Number Plate": (0, 0, 255),   # Red
    "Person": (0, 255, 255),       # Yellow
    "Motorbike": (255, 0, 0)       # Blue
}

# Snapshot folder
SNAPSHOT_FOLDER = "snapshots"
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

# WebRTC configuration
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

def save_snapshot(frame):
    """Saves a snapshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    snapshot_path = os.path.join(SNAPSHOT_FOLDER, f"snapshot_{timestamp}.jpg")
    cv2.imwrite(snapshot_path, frame)
    return snapshot_path

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

def draw_detections(frame, results):
    """Draw bounding boxes and labels on detected objects."""
    helmet_detected = False
    vehicle_count = 0
    person_count = 0
    number_plate_detected = False
    
    bike_boxes = []
    plate_boxes = []
    
    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        confidences = r.boxes.conf.cpu().numpy()
        
        for box, cls, conf in zip(boxes, classes, confidences):
            x1, y1, x2, y2 = map(int, box)
            label = class_names[int(cls)]
            color = class_colors.get(label, (255, 255, 255))
            
            # Handle Number Plate Special Detection for HSRP
            if label == "Number Plate":
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
                except Exception:
                    pass
                
                if not is_standard:
                    # Non-HSRP or Unreadable plate logic
                    color = (0, 0, 255) # Red for Non-HSRP
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame, 
                        f"Non-HSRP Plate", 
                        (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, color, 2
                    )
                else:
                    # Good HSRP logic
                    color = (0, 255, 0) # Green for HSRP
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame, 
                        f"HSRP: {plate_text}", 
                        (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, color, 2
                    )
            else:
                # Update counters and handle other detections
                if label == "Person":
                    person_count += 1
                elif label == "Helmet":
                    helmet_detected = True
                elif label == "Motorbike":
                    vehicle_count += 1
                    bike_boxes.append((x1, y1, x2, y2))
                
                # Draw bounding box and label for regular objects
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame, 
                    f"{label} {conf:.2f}", 
                    (x1, max(15, y1 - 10)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, color, 2
                )
            
    # Check for missing plates
    for bx1, by1, bx2, by2 in bike_boxes:
        has_plate = False
        # We will consider a bike to have a number plate if the number plate bounding box
        # intersects significantly with the bike's bounding box.
        for px1, py1, px2, py2 in plate_boxes:
            # Check for overlap: inter_x1 < inter_x2 and inter_y1 < inter_y2
            # Also check if plate center is inside or near the bike box
            px_center = (px1 + px2) // 2
            py_center = (py1 + py2) // 2
            
            # Generous bounding box check for the plate relative to the bike
            # We add a margin since plates might be detected slightly outside the bike box boundary
            margin = 30
            if (bx1 - margin <= px_center <= bx2 + margin) and (by1 - margin <= py_center <= by2 + margin):
                has_plate = True
                break
                
        if not has_plate:
            # Only draw "No Number Plate" if no plate was associated with this bike at all
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
            cv2.putText(frame, "No Number Plate", (bx1, by2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    return frame, vehicle_count, person_count, helmet_detected, number_plate_detected

def process_frame(frame, conn, cursor, save_detection_record):
    """Process a single frame and handle detections"""
    results = model(frame)
    processed_frame, vehicle_count, person_count, helmet_detected, number_plate_detected = draw_detections(frame, results)
    
    # Only save snapshot if helmet is absent and number plate is detected
    snapshot_path = None
    if not helmet_detected and number_plate_detected:
        snapshot_path = save_snapshot(processed_frame)
        st.session_state.last_snapshot = snapshot_path
    
    # Save record to database
    save_detection_record(
        conn, cursor,
        vehicle_count=vehicle_count,
        person_count=person_count,
        helmet_detected=helmet_detected,
        image_path=snapshot_path
    )
    
    return processed_frame

def video_detection_tab(conn, cursor, save_detection_record):
    """Streamlit Video Detection Tab with database integration."""
    st.title("📹 Real-time Detection")
    st.markdown("""
    <style>
        .detection-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    def video_frame_callback(frame):
        """Callback function for video processing."""
        img = frame.to_ndarray(format="bgr24")
        processed_frame = process_frame(img, conn, cursor, save_detection_record)
        return av.VideoFrame.from_ndarray(processed_frame, format="bgr24")
    
    st.markdown('<div class="detection-container">', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎥 Live Camera", "📱 Mobile Camera", "📂 Upload Video", "📸 Upload Image"])
    
    with tab1:
        st.subheader("Real-time Webcam Detection")
        st.info("""
        This feature uses your device's camera to detect:
        - Helmets
        - Number plates (only when helmet is absent)
        - Persons
        - Motorbikes
        """)
        
        webrtc_ctx = webrtc_streamer(
            key="webcam",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={
                "video": {
                    "width": {"ideal": 1280},
                    "height": {"ideal": 720},
                    "facingMode": "user"
                },
                "audio": False
            },
            async_processing=True,
        )
        
        if 'last_snapshot' in st.session_state and st.session_state.last_snapshot:
            st.image(st.session_state.last_snapshot, 
                    caption="Last Non-Compliant Detection (No Helmet + Number Plate)",
                    use_container_width=True)
    
    with tab2:
        st.subheader("Mobile Camera Detection")
        st.info("Connect to a mobile device camera stream for detection")
        
        col1, col2 = st.columns(2)
        with col1:
            ip_camera_url = st.text_input("Enter Mobile Camera Stream URL:", 
                                        "http://100.105.106.153:8080/video")
        with col2:
            frame_skip = st.number_input("Frame Skip Interval", 
                                        min_value=1, 
                                        value=5,
                                        help="Process every nth frame to reduce load")
        
        if st.button("Start Mobile Camera Detection"):
            cap = cv2.VideoCapture(ip_camera_url)
            stframe = st.empty()
            frame_count = 0
            
            try:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        st.warning("Stream ended or connection lost")
                        break
                    
                    frame_count += 1
                    if frame_count % frame_skip != 0:
                        continue
                    
                    # Process frame
                    processed_frame = process_frame(frame, conn, cursor, save_detection_record)
                    stframe.image(processed_frame, channels="BGR", use_container_width=True)
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                cap.release()
    
    with tab3:
        st.subheader("Video File Detection")
        uploaded_video = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov"])
        
        if uploaded_video is not None:
            col1, col2 = st.columns(2)
            with col1:
                frame_skip = st.number_input("Frame Skip Interval (Video)", 
                                            min_value=1, 
                                            value=5,
                                            help="Process every nth frame to reduce load")
            
            temp_file = "temp_video.mp4"
            with open(temp_file, "wb") as f:
                f.write(uploaded_video.read())
            
            st.video(temp_file)
            
            if st.button("Process Video"):
                cap = cv2.VideoCapture(temp_file)
                stframe = st.empty()
                frame_count = 0
                
                try:
                    while cap.isOpened():
                        ret, frame = cap.read()
                        if not ret:
                            break
                        
                        frame_count += 1
                        if frame_count % frame_skip != 0:
                            continue
                        
                        # Process frame
                        processed_frame = process_frame(frame, conn, cursor, save_detection_record)
                        stframe.image(processed_frame, channels="BGR", use_container_width=True)
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    cap.release()
                    os.remove(temp_file)
    
    with tab4:
        st.subheader("Image File Detection")
        uploaded_image = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
        
        if uploaded_image is not None:
            image = cv2.imdecode(np.frombuffer(uploaded_image.read(), np.uint8), cv2.IMREAD_COLOR)
            processed_frame = process_frame(image, conn, cursor, save_detection_record)
            st.image(processed_frame, channels="BGR", use_container_width=True)
            
            if 'last_snapshot' in st.session_state and st.session_state.last_snapshot:
                st.success(f"Non-compliant detection saved at {st.session_state.last_snapshot}")
    
    st.markdown('</div>', unsafe_allow_html=True)