# ============================================================
# SMART FIRE DETECTION SYSTEM
# Using Python + OpenCV + DHT22 + Twilio
# ============================================================

import cv2
import numpy as np
import time
import board
import adafruit_dht
from twilio.rest import Client
import RPi.GPIO as GPIO

# ============================================================
# TWILIO CONFIGURATION
# ============================================================

ACCOUNT_SID = "YOUR_ACCOUNT_SID"
AUTH_TOKEN = "YOUR_AUTH_TOKEN"

TWILIO_PHONE = "+1XXXXXXXXXX"
TARGET_PHONE = "+911234567890"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ============================================================
# GPIO SETUP
# ============================================================

BUZZER_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# ============================================================
# DHT22 SENSOR SETUP
# ============================================================

dht_sensor = adafruit_dht.DHT22(board.D4)

# ============================================================
# CAMERA SETUP
# ============================================================

camera = cv2.VideoCapture(0)

# ============================================================
# FIRE DETECTION SETTINGS
# ============================================================

FIRE_PIXEL_THRESHOLD = 1500
TEMPERATURE_THRESHOLD = 45

alert_sent = False

# ============================================================
# FUNCTION: MAKE EMERGENCY CALL
# ============================================================

def make_call():

    global alert_sent

    if alert_sent:
        return

    try:
        call = client.calls.create(
            twiml='''
                <Response>
                    <Say>
                        Emergency Alert!
                        Fire has been detected in the room.
                    </Say>
                </Response>
            ''',
            to=TARGET_PHONE,
            from_=TWILIO_PHONE
        )

        print("Emergency Call Sent")
        print(call.sid)

        alert_sent = True

    except Exception as e:
        print("Call Error:", e)

# ============================================================
# FUNCTION: ACTIVATE BUZZER
# ============================================================

def buzzer_on():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)

def buzzer_off():
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# ============================================================
# MAIN LOOP
# ============================================================

while True:

    # --------------------------------------------------------
    # READ CAMERA FRAME
    # --------------------------------------------------------

    ret, frame = camera.read()

    if not ret:
        print("Camera Error")
        break

    # --------------------------------------------------------
    # CONVERT FRAME TO HSV
    # --------------------------------------------------------

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # --------------------------------------------------------
    # FIRE COLOR RANGE
    # --------------------------------------------------------

    lower_fire = np.array([0, 120, 200])
    upper_fire = np.array([35, 255, 255])

    # --------------------------------------------------------
    # CREATE FIRE MASK
    # --------------------------------------------------------

    mask = cv2.inRange(hsv, lower_fire, upper_fire)

    # --------------------------------------------------------
    # COUNT FIRE PIXELS
    # --------------------------------------------------------

    fire_pixels = cv2.countNonZero(mask)

    # --------------------------------------------------------
    # READ TEMPERATURE
    # --------------------------------------------------------

    try:
        temperature = dht_sensor.temperature

    except RuntimeError:
        temperature = 0

    # --------------------------------------------------------
    # DISPLAY TEMPERATURE
    # --------------------------------------------------------

    cv2.putText(
        frame,
        f"Temperature: {temperature} C",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    # --------------------------------------------------------
    # FIRE DETECTION LOGIC
    # --------------------------------------------------------

    fire_detected = fire_pixels > FIRE_PIXEL_THRESHOLD
    high_temperature = temperature > TEMPERATURE_THRESHOLD

    # --------------------------------------------------------
    # ALERT CONDITION
    # --------------------------------------------------------

    if fire_detected or high_temperature:

        # ALERT MESSAGE
        cv2.putText(
            frame,
            "FIRE ALERT!",
            (50, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3
        )

        # PRINT ALERT
        print("================================")
        print("FIRE DETECTED")
        print("Temperature:", temperature)
        print("================================")

        # TURN ON BUZZER
        buzzer_on()

        # MAKE PHONE CALL
        make_call()

    else:

        buzzer_off()

    # --------------------------------------------------------
    # SHOW CAMERA WINDOW
    # --------------------------------------------------------

    cv2.imshow("Smart Fire Detection System", frame)

    # --------------------------------------------------------
    # EXIT CONDITION
    # --------------------------------------------------------

    key = cv2.waitKey(1)

    if key == ord('q'):
        break

# ============================================================
# CLEANUP
# ============================================================

camera.release()
cv2.destroyAllWindows()

GPIO.cleanup()