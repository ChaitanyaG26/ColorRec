from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import numpy as np
import time

app = Flask(__name__)

picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(video_config)
picam2.start()
time.sleep(0.5)

ENCODE_PARAM = [int(cv2.IMWRITE_JPEG_QUALITY), 40]

LOWER_RED1 = np.array([0, 180, 180])
UPPER_RED1 = np.array([10, 255, 255])
LOWER_RED2 = np.array([170, 180, 180])
UPPER_RED2 = np.array([180, 255, 255])
MIN_CONTOUR_AREA = 500

prev_time = time.time()

def gen_frames():
    global prev_time
    while True:
        frame_rgb = picam2.capture_array()  # RGB format
        hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)

        mask1 = cv2.inRange(hsv, LOWER_RED1, UPPER_RED1)
        mask2 = cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
        mask = cv2.bitwise_or(mask1, mask2)

        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            if cv2.contourArea(c) > MIN_CONTOUR_AREA:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)

        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        cv2.putText(frame_bgr, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame_bgr, ENCODE_PARAM)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video')
def video():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return """
    <html>
        <head><title>Pi Red Detection Stream</title></head>
        <body>
            <h1>Pi Red Detection Stream</h1>
            <img src="/video" style="width:100%; max-width:720px;">
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)