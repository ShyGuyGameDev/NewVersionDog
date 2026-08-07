"""
NewVersionDog camera service — raw MJPEG/JPEG only (no YOLO on this Pi).

Endpoints (port from camconfig.json, usually 8000):
  /frame.jpg, /stream.mjpg       — raw camera
  /annotated.jpg, /annotated.mjpg — same as raw (Mac runs YOLO separately)
  /detections.json               — empty stub for API compatibility

YOLO11n runs on a Mac/laptop; pull frames from:
  http://<pi-ip>:8000/frame.jpg  or  /stream.mjpg

Restart after deploy:
  sudo systemctl restart camera
"""
import io
import json
import logging
import socketserver
import time
from http import server
from threading import Condition
from urllib.parse import urlparse

import picamera

PAGE = """\
<html>
<head>
<title>Camera</title>
</head>
<body>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""


class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b"\xff\xd8"):
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)


def _request_path(handler):
    return urlparse(handler.path).path


def _send_jpeg_once(handler, output):
    handler.send_response(200)
    handler.send_header("Age", 0)
    handler.send_header("Cache-Control", "no-cache, private")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Content-Type", "image/jpeg")
    try:
        with output.condition:
            output.condition.wait()
            frame = output.frame
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
            with output.condition:
                output.condition.wait()
                frame = output.frame
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
        elif path in ("/frame.jpg", "/annotated.jpg"):
            # annotated aliases raw — YOLO runs on Mac, not this Pi
            _send_jpeg_once(self, output)
        elif path in ("/stream.mjpg", "/annotated.mjpg"):
            _send_mjpeg(self, output)
        elif path == "/detections.json":
            body = json.dumps({
                "detections": [],
                "model_loaded": False,
                "note": "YOLO runs on Mac; use dog_yolo_mac.py",
                "timestamp": time.time(),
            }).encode("utf-8")
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.info("Starting raw camera server (YOLO off-board on Mac)")

with picamera.PiCamera(resolution=config["resolution"], framerate=config["framerate"]) as camera:
    output = StreamingOutput()
    if "rotation" in config:
        camera.rotation = config["rotation"]
    camera.start_recording(output, format="mjpeg")
    try:
        address = ("", config["port"])
        httpd = StreamingServer(address, StreamingHandler)
        logging.info("Camera server on port %s", config["port"])
        httpd.serve_forever()
    finally:
        camera.stop_recording()
