# Smart Fire Detection System with DHT22 Sensor

## Overview

The Smart Fire Detection System is an intelligent safety solution that combines Computer Vision, IoT, and real-time monitoring to detect fire accidents quickly and automatically alert users.

This project uses a camera to identify fire-like objects and a DHT22 temperature sensor to monitor room temperature. When fire or abnormal temperature is detected, the system activates an alarm and automatically makes an emergency phone call using the Twilio API.

---

## Features

- Real-time fire detection using camera
- Temperature monitoring using DHT22 sensor
- Automatic emergency phone calling
- Live video processing with OpenCV
- Buzzer alarm activation
- Real-time alert system
- Raspberry Pi hardware integration
- IoT-based safety monitoring

---

## Technologies Used

- Python
- OpenCV
- NumPy
- Raspberry Pi
- DHT22 Sensor
- Twilio API
- GPIO Libraries
- Computer Vision
- IoT Technology

---

## Hardware Components

| Component | Purpose |
|---|---|
| Raspberry Pi | Main controller |
| DHT22 Sensor | Temperature monitoring |
| USB Camera / Pi Camera | Fire detection |
| Buzzer | Alarm system |
| Breadboard | Circuit connections |
| Jumper Wires | Hardware connectivity |

---

## System Workflow

```text
Camera Input → Fire Detection → Temperature Monitoring
                    ↓
          Threshold Comparison
                    ↓
       Fire or High Temperature?
                    ↓
        Alarm + Emergency Call
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/smart-fire-detection-system.git
```

### Navigate to Project Folder

```bash
cd smart-fire-detection-system
```

### Install Required Libraries

```bash
pip install opencv-python
pip install numpy
pip install adafruit-circuitpython-dht
pip install twilio
pip install RPi.GPIO
```

---

## Configuration

Replace the following values in the Python code:

```python
ACCOUNT_SID = "YOUR_ACCOUNT_SID"
AUTH_TOKEN = "YOUR_AUTH_TOKEN"

TWILIO_PHONE = "+1XXXXXXXXXX"
TARGET_PHONE = "+911234567890"
```

with your actual Twilio credentials and phone number.

---

## Run the Project

```bash
python smart_fire_detection.py
```

Press:

```text
q
```

to stop the system.

---

## Fire Detection Logic

The system detects fire using both computer vision and temperature monitoring.

\[
Alert =
\begin{cases}
1, & F = 1 \ \text{or} \ T > T_{threshold} \\
0, & \text{otherwise}
\end{cases}
\]

Where:

- \(F\) = Fire detected from camera
- \(T\) = Current temperature
- \(T_{threshold}\) = Maximum safe temperature

---

## Challenges Faced

- False detection from bright lights
- Sensor accuracy fluctuations
- Real-time processing optimization
- Hardware integration and GPIO configuration

---

## Future Improvements

- AI-based smoke detection
- Mobile application integration
- Cloud monitoring dashboard
- GPS emergency alerts
- Automatic sprinkler activation
- Deep learning fire classification

---

## Applications

- Smart Homes
- Industries
- Warehouses
- Laboratories
- Offices
- Server Rooms

---

## Project Structure

```text
smart-fire-detection-system/
│
├── smart_fire_detection.py
├── requirements.txt
├── README.md
├── images/
├── screenshots/
└── docs/
```

---

## Author

Developed as an IoT + AI based Smart Safety Project using Python and Raspberry Pi.

---

## License

This project is open-source and available under the MIT License.
