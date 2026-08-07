"""
NewVersionDog camera service: raw + YOLO-annotated MJPEG/JPEG streams.

Endpoints (default port from camconfig.json, usually 8000):
  /frame.jpg, /stream.mjpg       — raw camera
  /annotated.jpg, /annotated.mjpg — YOLO11n hierarchy overlays
  /detections.json               — latest detections for movement control

Deploy notes (Pi):
  WorkingDirectory=/home/pi/system (see camera.service)
  pip3 install ultralytics opencv-python numpy  (+ Pi torch CPU wheel)
  Place yolo11n.pt in /home/pi/system/ (or let ultralytics download it)
  sudo systemctl restart camera
"""
import json
import logging
import socketserver
import threading
import time
from http import server
from threading import Condition, Event, Lock
from urllib.parse import urlparse

import cv2
import picamera
from picamera.array import PiRGBArray

from IRLClassification import classify_frame, model as object_model

PAGE = """\
<html>
<head>
<title>Camera</title>
</head>
<body>
<center>
<img src="stream.mjpg" width="320" height="240" />
<img src="annotated.mjpg" width="320" height="240" />
</center>
</body>
</html>
"""


class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def set_frame(self, jpeg_bytes):
        with self.condition:
            self.frame = jpeg_bytes
            self.condition.notify_all()

    def wait_frame(self):
        with self.condition:
            self.condition.wait()
            return self.frame


class DetectionState(object):
    def __init__(self):
        self.lock = Lock()
        self.latest_frame = None
        self.latest_detections = []
        self.frame_ready = Event()

    def set_frame(self, frame):
        with self.lock:
            self.latest_frame = frame
        self.frame_ready.set()

    def take_frame_copy(self, timeout=0.5):
        if not self.frame_ready.wait(timeout):
            return None
        with self.lock:
            if self.latest_frame is None:
                return None
            self.frame_ready.clear()
            return self.latest_frame.copy()

    def set_detections(self, detections):
        with self.lock:
            self.latest_detections = detections

    def get_detections(self):
        with self.lock:
            return list(self.latest_detections)


def draw_detections(img, detections):
    """Render YOLO detections with bbox, hierarchy category, label, and confidence."""
    h, w = img.shape[:2]
    for det in detections:
        try:
            x1, y1, x2, y2 = det["bbox"]
            x1 = int(max(0, min(w - 1, x1)))
            y1 = int(max(0, min(h - 1, y1)))
            x2 = int(max(0, min(w - 1, x2)))
            y2 = int(max(0, min(h - 1, y2)))
            if x2 <= x1 or y2 <= y1:
                continue

            hierarchy = det.get("hierarchy_category", det.get("class", "unknown"))
            original = det.get("original_class", hierarchy)
            conf = float(det.get("confidence", 0.0))
            if hierarchy != original:
                label = "%s: %s - %.1f%%" % (hierarchy, original, conf)
            else:
                label = "%s: %.1f%%" % (hierarchy, conf)

            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                img,
                (x1, max(0, y1 - text_height - baseline)),
                (x1 + text_width, y1),
                (0, 255, 0),
                -1,
            )
            cv2.putText(
                img,
                label,
                (x1, max(text_height, y1 - baseline)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
            )
        except Exception:
            continue
    return img


def encode_jpeg(frame):
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return None
    return buf.tobytes()


def detection_worker(state, stop_event):
    """Continuous async YOLO loop (OriginalRobot pattern)."""
    while not stop_event.is_set():
        frame_copy = state.take_frame_copy(timeout=0.5)
        if frame_copy is None:
            continue
        try:
            detections = classify_frame(frame_copy, conf_threshold=0.5)
        except Exception:
            detections = []
        state.set_detections(detections)


def capture_loop(camera, raw_capture, raw_output, ann_output, state, stop_event):
    """Capture BGR frames, publish raw JPEG, overlay latest detections for annotated JPEG."""
    for frame in camera.capture_continuous(
        raw_capture, format="bgr", use_video_port=True
    ):
        if stop_event.is_set():
            break
        try:
            image = frame.array
            # Copy before truncate clears the underlying buffer.
            frame_bgr = image.copy()
            raw_capture.truncate(0)

            state.set_frame(frame_bgr)

            raw_jpeg = encode_jpeg(frame_bgr)
            if raw_jpeg is not None:
                raw_output.set_frame(raw_jpeg)

            detections = state.get_detections()
            annotated = frame_bgr.copy()
            if detections:
                draw_detections(annotated, detections)
            ann_jpeg = encode_jpeg(annotated)
            if ann_jpeg is not None:
                ann_output.set_frame(ann_jpeg)
        except Exception as e:
            logging.warning("Capture loop error: %s", e)
            try:
                raw_capture.truncate(0)
            except Exception:
                pass
            time.sleep(0.05)


def _request_path(handler):
    return urlparse(handler.path).path


def _send_jpeg_once(handler, output):
    handler.send_response(200)
    handler.send_header("Age", 0)
    handler.send_header("Cache-Control", "no-cache, private")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Content-Type", "image/jpeg")
    try:
        frame = output.wait_frame()
        if frame is None:
            handler.send_error(503)
            return
        ts = time.time()
        ts_s = int(ts)
        ts_ms = int((ts - ts_s) * 1000)
        handler.send_header("Content-Length", len(frame))
        handler.send_header("TimeStamp", str(ts_s) + "." + str(ts_ms))
        handler.end_headers()
        handler.wfile.write(frame)
    except Exception as e:
        logging.warning(
            "Error serving frame to client %s: %s",
            handler.client_address, str(e),
        )


def _send_mjpeg(handler, output):
    handler.send_response(200)
    handler.send_header("Age", 0)
    handler.send_header("Cache-Control", "no-cache, private")
    handler.send_header("Pragma", "no-cache")
    handler.send_header(
        "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
    )
    handler.end_headers()
    try:
        while True:
            frame = output.wait_frame()
            if frame is None:
                continue
            ts = time.time()
            ts_s = int(ts)
            ts_ms = int((ts - ts_s) * 1000)
            handler.wfile.write(b"--FRAME\r\n")
            handler.send_header("Content-Type", "image/jpeg")
            handler.send_header("Content-Length", len(frame))
            handler.send_header("Timestamp", str(ts_s) + "." + str(ts_ms))
            handler.end_headers()
            handler.wfile.write(frame)
            handler.wfile.write(b"\r\n")
    except Exception as e:
        logging.warning(
            "Removed streaming client %s: %s",
            handler.client_address, str(e),
        )


class StreamingHandler(server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep camera service logs quiet under frequent UI polling.
        return

    def do_GET(self):
        path = _request_path(self)
        if path == "/":
            self.send_response(301)
            self.send_header("Location", "/index.html")
            self.end_headers()
        elif path == "/index.html":
            content = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        elif path == "/frame.jpg":
            _send_jpeg_once(self, raw_output)
        elif path == "/stream.mjpg":
            _send_mjpeg(self, raw_output)
        elif path == "/annotated.jpg":
            _send_jpeg_once(self, annotated_output)
        elif path == "/annotated.mjpg":
            _send_mjpeg(self, annotated_output)
        elif path == "/detections.json":
            payload = {
                "detections": detection_state.get_detections(),
                "model_loaded": object_model is not None,
                "timestamp": time.time(),
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


with open("camconfig.json") as fconf:
    config = json.load(fconf)

# Parse "640x480" or [640, 480]
res = config["resolution"]
if isinstance(res, str) and "x" in res.lower():
    parts = res.lower().split("x")
    resolution = (int(parts[0]), int(parts[1]))
else:
    resolution = tuple(res)

raw_output = StreamingOutput()
annotated_output = StreamingOutput()
detection_state = DetectionState()
stop_event = Event()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
if object_model is None:
    logging.warning(
        "YOLO model not loaded; annotated stream will match raw. "
        "Install ultralytics and place yolo11n.pt in /home/pi/system/"
    )
else:
    logging.info("YOLO11n model loaded for annotated camera stream")

with picamera.PiCamera(resolution=resolution, framerate=config["framerate"]) as camera:
    if "rotation" in config:
        camera.rotation = config["rotation"]
    raw_capture = PiRGBArray(camera, size=resolution)
    time.sleep(0.5)  # camera warm-up

    det_thread = threading.Thread(
        target=detection_worker,
        args=(detection_state, stop_event),
        daemon=True,
    )
    cap_thread = threading.Thread(
        target=capture_loop,
        args=(
            camera,
            raw_capture,
            raw_output,
            annotated_output,
            detection_state,
            stop_event,
        ),
        daemon=True,
    )
    det_thread.start()
    cap_thread.start()

    httpd = None
    try:
        address = ("", config["port"])
        httpd = StreamingServer(address, StreamingHandler)
        logging.info(
            "Camera server on port %s (raw + annotated + /detections.json)",
            config["port"],
        )
        httpd.serve_forever()
    finally:
        stop_event.set()
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                pass
