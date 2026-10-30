from picamera2 import Picamera2
import cv2
import numpy as np
import time
import threading
from flask import Flask, Response

latest_status = "CLEAR"
status_lock   = threading.Lock()

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Color Detector</title>
  <style>
    body {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
      background: #111;
      font-family: sans-serif;
    }
    #status {
      font-size: 20vw;
      font-weight: bold;
      color: white;
      transition: color 0.3s;
    }
  </style>
</head>
<body>
  <div id="status">...</div>
  <script>
    const el = new EventSource("/stream");
    el.onmessage = e => {
      const s = document.getElementById("status");
      s.textContent = e.data;
      document.body.style.background = e.data === "RED" ? "#cc0000" : "#111";
    };
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/stream")
def stream():
    def event_stream():
        with status_lock:
            current = latest_status
        yield f"data: {current}\n\n"
        last = current
        while True:
            with status_lock:
                current = latest_status
            if current != last:
                yield f"data: {current}\n\n"
                last = current
            time.sleep(0.2)
    return Response(event_stream(), mimetype="text/event-stream")

def detection_loop():
    global latest_status
    picam2 = Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
    picam2.start()
    time.sleep(0.5)

    LOWER_RED1 = np.array([0,   180, 180])
    UPPER_RED1 = np.array([10,  255, 255])
    LOWER_RED2 = np.array([170, 180, 180])
    UPPER_RED2 = np.array([180, 255, 255])
    MIN_AREA   = 2500

    print("[Camera] Detection running...")
    while True:
        frame = picam2.capture_array()
        hsv   = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        mask  = cv2.bitwise_or(
            cv2.inRange(hsv, LOWER_RED1, UPPER_RED1),
            cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
        )
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = any(cv2.contourArea(c) > MIN_AREA for c in contours)
        new_status = "RED" if detected else "CLEAR"
        with status_lock:
            if new_status != latest_status:
                latest_status = new_status
                print(f"[Camera] {new_status}")
        time.sleep(0.05)

if __name__ == "__main__":
    t = threading.Thread(target=detection_loop, daemon=True)
    t.start()
    print("[Server] Running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
