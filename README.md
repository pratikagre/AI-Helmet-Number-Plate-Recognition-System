# AI-Based Helmet & Number Plate Recognition System 🏍️👮‍♂️

An automated system designed to detect traffic violations in real-time, generate e-challans, and log violation records. The system utilizes YOLOv8 for object detection and PyTesseract for Optical Character Recognition (OCR) on vehicle number plates.

---

## 🚀 Key Features

*   **Real-time Object Detection:** Identifies riders, motorbikes, helmets, and number plates using a custom YOLOv8 model.
*   **Helmet Detection & Violation Logging:** Detects if a rider is not wearing a helmet and automatically flags it as a violation.
*   **Triple-Seat Detection:** Identifies instances of three or more people riding a single motorbike.
*   **Number Plate OCR (HSRP Verification):** Reads vehicle number plates using PyTesseract OCR and classifies them as standard (HSRP) or stylish (Non-HSRP/Violation).
*   **Automated E-Challan Dispatch:** Automatically sends an email notification (E-Challan) with a captured snapshot of the incident to the vehicle owner's registered email address.
*   **Database Management:** Stores all violation records in a SQLite database with details like timestamp, vehicles, persons, helmet usage status, and number plates.
*   **Interactive Dashboard:** Interactive visualizations and data tables using Streamlit and Plotly to review and filter violation statistics.
*   **VS Code Integration:** Includes ready-to-use launch configurations (`launch.json`) for seamless running and debugging using **F5**.
*   **PyTorch 2.6+ Compatible:** Includes a built-in compatibility patch for PyTorch 2.6+'s strict `weights_only` weight-loading security.

---

## 🛠️ Tech Stack

*   **Frontend / UI:** Streamlit (Python)
*   **Computer Vision / Deep Learning:** OpenCV, Ultralytics YOLOv8, PyTorch
*   **OCR Engine:** PyTesseract
*   **Database:** SQLite3
*   **Email Protocol:** SMTP (Secure SSL Connection)

---

## 📦 Installation & Setup

### Prerequisites
1.  **Python 3.12** installed on your system.
2.  **Tesseract OCR** installed on your system:
    *   **Windows:** Download installer from [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and install. By default, it installs to `C:\Program Files\Tesseract-OCR\tesseract.exe`.
    *   **Linux/Ubuntu:** `sudo apt-get install tesseract-ocr`

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/pratikagre/AI-Helmet-Number-Plate-Recognition-System.git
    cd AI-Helmet-Number-Plate-Recognition-System
    ```

2.  **Install Required Dependencies:**
    ```bash
    pip install -r "Project code/requiremnets.txt"
    ```

---

## 🏃‍♂️ How to Run

### Method 1: Via VS Code (Recommended)
1.  Open the cloned project folder `AI-Helmet-Number-Plate-Recognition-System` in VS Code.
2.  Select **Python 3.12** as your interpreter (`Ctrl + Shift + P` -> `Python: Select Interpreter`).
3.  Go to the **Run & Debug** panel (`Ctrl + Shift + D`) and press **F5** (or click the green play button next to `Python: Streamlit (main.py)`).

### Method 2: Via Terminal
1.  Open your terminal/command prompt.
2.  Change directory to the `codes` directory:
    ```bash
    cd "Project code/codes"
    ```
3.  Run the Streamlit server:
    ```bash
    streamlit run main.py
    ```
4.  Open the local URL displayed in your terminal (typically `http://localhost:8501`) in your web browser.

---

## 🔒 Configuration

*   **Email Credentials:** The system uses Gmail SMTP to send challans. You can modify the sender credentials (`sender_email`, `sender_password` via App Passwords) inside `Project code/codes/video_detection.py` under `send_challan_email()`.
*   **RTO Mapping:** You can map vehicle number plates to owner emails inside the `RTO_DATABASE` dictionary in `video_detection.py` to test email delivery.

---

## 📜 License

This project is licensed under the MIT License.
