from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import numpy as np
import threading
import time

app = Flask(__name__)

latest_message = "CLEAR"
message_lock = threading.Lock()

def detection_loop():
    global latest_message

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)
    picam2.start()
    time.sleep(0.5)

    LOWER_RED1 = np.array([0,   180, 180])
    UPPER_RED1 = np.array([10,  255, 255])
    LOWER_RED2 = np.array([170, 180, 180])
    UPPER_RED2 = np.array([180, 255, 255])
    MIN_CONTOUR_AREA = 2500

    print("Red detection running...")

    while True:
        frame_rgb = picam2.capture_array()
        hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)

        mask1 = cv2.inRange(hsv, LOWER_RED1, UPPER_RED1)
        mask2 = cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
        mask = cv2.bitwise_or(mask1, mask2)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        detected = any(cv2.contourArea(c) > MIN_CONTOUR_AREA for c in contours)

        if detected:
            print("RED")
            with message_lock:
                latest_message = "RED"
            time.sleep(5)
        else:
            with message_lock:
                latest_message = "CLEAR"

PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Red Detector</title>
  <style>
    body { margin:0; height:100vh; display:flex; flex-direction:column;
           align-items:center; justify-content:center;
           background:#111; color:#888; font-family:-apple-system,sans-serif;
           transition: background 0.2s; }
    body.red { background:#c00; color:#fff; }
    #status { font-size:22vw; font-weight:bold; }
    #conn { font-size:5vw; margin-top:2vh; }
    #log { font-size:4vw; margin-top:3vh; text-align:center; }
  </style>
</head>
<body>
  <div id="status">CLEAR</div>
  <div id="conn">connecting...</div>
  <div id="log"></div>
  <script>
    const statusEl = document.getElementById('status');
    const connEl = document.getElementById('conn');
    const logEl = document.getElementById('log');

    function connect() {
      const es = new EventSource('/stream');
      es.onopen = () => { connEl.textContent = 'connected'; };
      es.onmessage = (e) => {
        statusEl.textContent = e.data;
        document.body.classList.toggle('red', e.data === 'RED');
        if (e.data === 'RED') {
          logEl.textContent = 'Last RED: ' + new Date().toLocaleTimeString();
        }
      };
      es.onerror = () => {
        connEl.textContent = 'connection lost, retrying...';
        es.close();
        setTimeout(connect, 1000);
      };
    }
    connect();
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return PAGE

@app.route("/stream")
def stream():
    def generate():
        last = None
        count = 0
        while True:
            with message_lock:
                current = latest_message
            # Send on change, plus a heartbeat every ~10s to keep the link alive
            if current != last or count >= 50:
                yield f"data: {current}\n\n"
                last = current
                count = 0
            count += 1
            time.sleep(0.2)
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})

@app.route("/status")
def status():
    with message_lock:
        return latest_message

if __name__ == "__main__":
    threading.Thread(target=detection_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)