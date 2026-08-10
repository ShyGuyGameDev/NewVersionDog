#!/usr/bin/env python3
"""
Pull NewVersionDog camera frames, run YOLO11n overlays, and serve annotated
JPEGs for the robot website right-hand camera panel.

Optional object-follow gait: Mac computes steer bias and HTTP-commands the Pi
(/command?cmd=direct&v1=...) to walk/stop. Change FOLLOW_TARGET to switch object.

Usage:
  source "../../.venv/bin/activate"
  python dog_yolo_mac.py
  # or:
  python dog_yolo_mac.py --url http://10.1.1.146:8000/frame.jpg --serve-port 8010
  python dog_yolo_mac.py --no-window          # follow on by default
  python dog_yolo_mac.py --no-follow --no-window

Endpoints (default port 8010):
  /annotated.jpg   — latest YOLO-annotated JPEG (for website)
  /detections.json — latest detections
  /start           — mark active / ensure inference running
  /health          — status JSON
  /follow/on       — enable object follow
  /follow/off      — disable object follow (sends stop)
  /follow/status   — follow state JSON

Keys (OpenCV window): q = quit
"""
from __future__ import annotations

import argparse
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

import cv2
import numpy as np
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_URL = "http://10.1.1.146:8000/frame.jpg"
DEFAULT_SERVE_PORT = 8010
DEFAULT_PI_COMMAND_BASE = "http://10.1.1.146:9072/command"
MODEL_PATH = "yolo11n.pt"
CONF_THRESHOLD = 0.5

# Change this only to switch the chased object (COCO class or hierarchy category).
FOLLOW_TARGET = "tennis racket"
# Gait command sent while following (firmware: walk / trot).
FOLLOW_GAIT = "trot"

# Steer / gait (matches website GAIT_NORMAL_RIGHT_BIAS = 1)
RIGHT_X = 0.60
LEFT_X = 0.40
CENTER_HALF = 0.06  # center when 0.44 < x < 0.56
DEFAULT_BIAS = 1
RIGHT_BIAS = 2
LEFT_BIAS = 0
LOST_TIMEOUT_S = 0.8
WALK_HEARTBEAT_S = 1.5
PI_CMD_TIMEOUT_S = 1.5

object_hierarchy = {
    "stick": ["skis", "baseball bat", "snowboard", "tennis racket"],
    "ball": ["frisbee", "sports ball"],
    "person": ["person"],
    "animal": [
        "bird", "cat", "dog", "horse", "sheep", "cow",
        "elephant", "bear", "zebra", "giraffe",
    ],
    "vehicle": ["car", "airplane", "bus", "train", "truck", "boat"],
    "bike": ["bicycle", "motorcycle"],
    "backpack": ["backpack", "suitcase"],
    "umbrella": ["umbrella"],
    "handbag": ["handbag"],
    "tie": ["tie"],
    "miscellaneous": [
        "bench", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "kite", "skateboard", "surfboard", "vase",
        "teddy bear", "hair drier", "toothbrush",
    ],
    "bottle": ["bottle"],
    "cup": ["cup", "wine glass"],
    "utensiles": ["fork", "knife", "spoon"],
    "bowl": ["bowl"],
    "food": [
        "banana", "apple", "sandwich", "orange", "broccoli",
        "carrot", "hot dog", "pizza", "donut", "cake",
    ],
    "chair": ["chair", "couch"],
    "plant": ["potted plant"],
    "bed": ["bed"],
    "table": ["dining table"],
    "toilet": ["toilet"],
    "tv": ["tv"],
    "laptop": ["laptop"],
    "mouse": ["mouse"],
    "remote": ["remote"],
    "keyboard": ["keyboard"],
    "phone": ["cell phone"],
    "appliance": ["microwave", "oven", "toaster", "sink", "refrigerator"],
    "book": ["book"],
    "clock": ["clock"],
    "scissors": ["scissors"],
}

class_to_hierarchy = {
    obj: category
    for category, objects in object_hierarchy.items()
    for obj in objects
}


def get_object_hierarchy(class_name: str) -> str:
    return class_to_hierarchy.get(class_name, "unknown")


def fetch_jpeg_frame(url: str, timeout: float = 3.0) -> Optional[np.ndarray]:
    try:
        with urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.warning("Frame fetch failed: %s", e)
        return None


def send_pi_command(command_base: str, cmd: str, timeout: float = PI_CMD_TIMEOUT_S) -> bool:
    """GET {base}?cmd=direct&v1={cmd} — same path as the robot website scmd()."""
    try:
        qs = urlencode({"cmd": "direct", "v1": cmd})
        url = f"{command_base.rstrip('/')}?{qs}"
        with urlopen(url, timeout=timeout) as resp:
            resp.read()
        return True
    except (URLError, TimeoutError, OSError) as e:
        logger.warning("Pi command '%s' failed: %s", cmd, e)
        return False


def classify_frame(model: YOLO, frame: np.ndarray) -> List[dict]:
    detections = []
    results = model(frame, verbose=False)
    names = model.names
    for r in results:
        if not hasattr(r, "boxes") or len(r.boxes) == 0:
            continue
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < CONF_THRESHOLD:
                continue
            cls_id = int(box.cls[0])
            original = names[cls_id]
            hierarchy = get_object_hierarchy(original)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            detections.append({
                "hierarchy_category": hierarchy,
                "original_class": original,
                "confidence": conf * 100,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "center_x": float((x1 + x2) / 2),
                "center_y": float((y1 + y2) / 2),
            })
    return detections


def draw_detections(frame: np.ndarray, detections: List[dict]) -> np.ndarray:
    out = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        hierarchy = det["hierarchy_category"]
        original = det["original_class"]
        conf = det["confidence"]
        if hierarchy != original:
            label = f"{hierarchy}: {original} - {conf:.1f}%"
        else:
            label = f"{hierarchy}: {conf:.1f}%"
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(out, (x1, max(0, y1 - th - baseline)), (x1 + tw, y1), (0, 255, 0), -1)
        cv2.putText(
            out, label, (x1, max(th, y1 - baseline)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2,
        )
    return out


def _placeholder_jpeg(message: str, size=(640, 480)) -> bytes:
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    cv2.putText(
        img, message, (20, size[1] // 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
    )
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return buf.tobytes() if ok else b""


class ObjectFollowController:
    """Mac-side follow: hysteresis zones → gait bias → Pi walk/stop."""

    def __init__(self, pi_command_base: str, enabled: bool = False):
        self.pi_command_base = pi_command_base
        self._lock = threading.Lock()
        self.enabled = enabled
        self.last_seen_t: Optional[float] = None
        self.last_zone = "center"
        self.applied_bias: Optional[int] = None
        self.walking = False
        self.last_walk_sent_t = 0.0
        self.last_x_norm: Optional[float] = None
        self.target_visible = False

    def set_enabled(self, enabled: bool):
        with self._lock:
            was = self.enabled
            self.enabled = enabled
        if was and not enabled:
            self._stop()
            with self._lock:
                self.walking = False
                self.applied_bias = None
            logger.info("Follow disabled; stop sent")
        elif enabled and not was:
            logger.info("Follow enabled; target=%s", FOLLOW_TARGET)

    def status(self) -> dict:
        with self._lock:
            age = None
            if self.last_seen_t is not None:
                age = time.time() - self.last_seen_t
            return {
                "enabled": self.enabled,
                "target": FOLLOW_TARGET,
                "gait": FOLLOW_GAIT,
                "zone": self.last_zone,
                "bias": self.applied_bias,
                "walking": self.walking,
                "target_visible": self.target_visible,
                "last_seen_age_s": age,
                "x_norm": self.last_x_norm,
            }

    def select_target(self, detections: List[dict]) -> Optional[dict]:
        needle = FOLLOW_TARGET.lower().strip()
        matches = []
        for det in detections:
            original = str(det.get("original_class", "")).lower()
            hierarchy = str(det.get("hierarchy_category", "")).lower()
            if original == needle or hierarchy == needle:
                matches.append(det)
        if not matches:
            return None
        return max(matches, key=lambda d: float(d.get("confidence", 0)))

    def compute_zone(self, x_norm: float, prev_zone: str) -> str:
        center_lo = 0.5 - CENTER_HALF  # 0.44
        center_hi = 0.5 + CENTER_HALF  # 0.56
        if x_norm >= RIGHT_X:
            return "right"
        if x_norm <= LEFT_X:
            return "left"
        if center_lo < x_norm < center_hi:
            return "center"
        # Hysteresis bands: 0.40–0.44 and 0.56–0.60
        return prev_zone

    @staticmethod
    def zone_to_bias(zone: str) -> int:
        if zone == "right":
            return RIGHT_BIAS
        if zone == "left":
            return LEFT_BIAS
        return DEFAULT_BIAS

    def _send(self, cmd: str) -> bool:
        return send_pi_command(self.pi_command_base, cmd)

    def sync_bias(self, target_bias: int):
        """Reset turn with gs, then apply N× gr (absolute; 0 means gs only)."""
        self._send("gs")
        for _ in range(max(0, int(target_bias))):
            self._send("gr")

    def _stop(self):
        self._send("stop")

    def tick(self, detections: List[dict], frame_width: int):
        with self._lock:
            if not self.enabled:
                return
            prev_zone = self.last_zone

        if frame_width <= 0:
            return

        target = self.select_target(detections)
        now = time.time()
        x_norm = None
        zone = prev_zone

        if target is not None:
            x_norm = float(target["center_x"]) / float(frame_width)
            zone = self.compute_zone(x_norm, prev_zone)
            with self._lock:
                self.last_seen_t = now
                self.last_zone = zone
                self.last_x_norm = x_norm
                self.target_visible = True
            last_seen = now
        else:
            with self._lock:
                self.target_visible = False
                last_seen = self.last_seen_t
                zone = self.last_zone
                x_norm = self.last_x_norm

        should_walk = last_seen is not None and (now - last_seen) < LOST_TIMEOUT_S

        with self._lock:
            applied = self.applied_bias
            walking = self.walking
            last_walk = self.last_walk_sent_t

        if not should_walk:
            if walking:
                self._stop()
                with self._lock:
                    self.walking = False
                    self.applied_bias = None
                logger.info("Follow: target lost → stop")
            return

        bias = self.zone_to_bias(zone)
        if applied != bias:
            self.sync_bias(bias)
            with self._lock:
                self.applied_bias = bias
            logger.info(
                "Follow: zone=%s bias=%s x=%.3f target=%s",
                zone, bias, x_norm if x_norm is not None else -1.0, FOLLOW_TARGET,
            )

        need_walk = (not walking) or (now - last_walk >= WALK_HEARTBEAT_S)
        if need_walk:
            if self._send(FOLLOW_GAIT):
                with self._lock:
                    self.walking = True
                    self.last_walk_sent_t = now


class LatestFrame:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.detections: List[dict] = []
        self.annotated_jpeg: bytes = _placeholder_jpeg("Starting YOLO...")
        self.model_loaded = False
        self.camera_ok = False
        self.active = True
        self.last_start = time.time()
        self.fail_streak = 0
        self.follow: Optional[ObjectFollowController] = None

    def set_frame(self, frame: np.ndarray):
        with self.lock:
            self.frame = frame

    def get_frame_copy(self) -> Optional[np.ndarray]:
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def set_detections(self, detections: List[dict]):
        with self.lock:
            self.detections = detections

    def get_detections(self) -> List[dict]:
        with self.lock:
            return list(self.detections)

    def set_annotated(self, frame: np.ndarray, camera_ok: bool, fail_streak: int = 0):
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        with self.lock:
            if ok:
                self.annotated_jpeg = buf.tobytes()
            self.camera_ok = camera_ok
            self.fail_streak = fail_streak

    def get_annotated_jpeg(self) -> bytes:
        with self.lock:
            return self.annotated_jpeg

    def mark_start(self):
        with self.lock:
            self.active = True
            self.last_start = time.time()

    def status(self) -> dict:
        with self.lock:
            payload = {
                "ok": True,
                "model_loaded": self.model_loaded,
                "camera_ok": self.camera_ok,
                "active": self.active,
                "fail_streak": self.fail_streak,
                "detections": len(self.detections),
                "last_start": self.last_start,
                "timestamp": time.time(),
                "follow_target": FOLLOW_TARGET,
            }
            follow = self.follow
        if follow is not None:
            payload["follow"] = follow.status()
        else:
            payload["follow"] = {"enabled": False, "target": FOLLOW_TARGET}
        return payload


def draw_follow_overlay(frame: np.ndarray, follow: Optional[ObjectFollowController]) -> np.ndarray:
    if follow is None:
        return frame
    st = follow.status()
    if not st.get("enabled"):
        return frame
    mode = FOLLOW_GAIT.upper() if st.get("walking") else "STOP"
    bias = st.get("bias")
    bias_s = "?" if bias is None else str(bias)
    zone = st.get("zone") or "?"
    x = st.get("x_norm")
    x_s = f"{x:.2f}" if isinstance(x, float) else "-"
    line = f"Follow {FOLLOW_TARGET} | {zone} bias={bias_s} | {mode} x={x_s}"
    color = (0, 200, 255) if st.get("walking") else (0, 165, 255)
    cv2.putText(frame, line, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    # Zone guides
    h, w = frame.shape[:2]
    for frac, col in ((LEFT_X, (255, 128, 0)), (0.5 - CENTER_HALF, (180, 180, 180)),
                      (0.5 + CENTER_HALF, (180, 180, 180)), (RIGHT_X, (255, 128, 0))):
        x = int(frac * w)
        cv2.line(frame, (x, 0), (x, h), col, 1)
    return frame


def detection_worker(
    model: YOLO,
    state: LatestFrame,
    stop: threading.Event,
    follow: Optional[ObjectFollowController],
):
    while not stop.is_set():
        frame = state.get_frame_copy()
        if frame is None:
            time.sleep(0.02)
            continue
        try:
            dets = classify_frame(model, frame)
        except Exception as e:
            logger.warning("Inference error: %s", e)
            dets = []
        state.set_detections(dets)
        if dets:
            summary = ", ".join(
                f"{d['hierarchy_category']}({d['original_class']} {d['confidence']:.0f}%)"
                for d in dets[:6]
            )
            logger.info("Detections: %s", summary)
        if follow is not None:
            try:
                follow.tick(dets, frame.shape[1])
            except Exception as e:
                logger.warning("Follow tick error: %s", e)


def _cors_headers(handler: BaseHTTPRequestHandler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "*")
    handler.send_header("Cache-Control", "no-cache, private")
    handler.send_header("Pragma", "no-cache")


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, code: int = 200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    _cors_headers(handler)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(state: LatestFrame, follow: Optional[ObjectFollowController]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_OPTIONS(self):
            self.send_response(204)
            _cors_headers(self)
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/annotated.jpg", "/frame.jpg"):
                body = state.get_annotated_jpeg()
                self.send_response(200)
                _cors_headers(self)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/start":
                state.mark_start()
                _json_response(self, {
                    "ok": True,
                    "started": True,
                    "message": "YOLO active",
                    **state.status(),
                })
                logger.info("Start requested from %s", self.client_address[0])
            elif path == "/follow/on":
                if follow is None:
                    _json_response(self, {"ok": False, "error": "follow not configured"}, 500)
                else:
                    follow.set_enabled(True)
                    _json_response(self, {"ok": True, **follow.status()})
            elif path == "/follow/off":
                if follow is None:
                    _json_response(self, {"ok": False, "error": "follow not configured"}, 500)
                else:
                    follow.set_enabled(False)
                    _json_response(self, {"ok": True, **follow.status()})
            elif path == "/follow/status":
                if follow is None:
                    _json_response(self, {"ok": True, "enabled": False, "target": FOLLOW_TARGET})
                else:
                    _json_response(self, {"ok": True, **follow.status()})
            elif path in ("/health", "/status", "/detections.json"):
                payload = state.status()
                if path == "/detections.json":
                    payload = {
                        "detections": state.get_detections(),
                        "model_loaded": payload["model_loaded"],
                        "camera_ok": payload["camera_ok"],
                        "timestamp": payload["timestamp"],
                        "follow": payload.get("follow"),
                    }
                _json_response(self, payload)
            else:
                self.send_error(404)
                self.end_headers()

    return Handler


def start_http_server(
    state: LatestFrame,
    port: int,
    follow: Optional[ObjectFollowController],
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(state, follow))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Serving annotated frames on http://0.0.0.0:%s/annotated.jpg", port)
    return server


def main():
    parser = argparse.ArgumentParser(description="Dog camera YOLO11n (Mac)")
    parser.add_argument("--url", default=DEFAULT_URL, help="Dog camera JPEG URL")
    parser.add_argument("--model", default=MODEL_PATH, help="YOLO weights path")
    parser.add_argument(
        "--serve-port", type=int, default=DEFAULT_SERVE_PORT,
        help="HTTP port for annotated.jpg /start /health (0 to disable)",
    )
    parser.add_argument(
        "--no-window", action="store_true",
        help="Headless mode (no OpenCV window; for LaunchAgent)",
    )
    parser.add_argument(
        "--follow", action="store_true", default=True,
        help="Enable object-follow gait at startup (default: on)",
    )
    parser.add_argument(
        "--no-follow", action="store_false", dest="follow",
        help="Disable object-follow gait at startup (use /follow/on later)",
    )
    parser.add_argument(
        "--pi-command-base", default=DEFAULT_PI_COMMAND_BASE,
        help="Pi web command base URL (…/command)",
    )
    args = parser.parse_args()

    follow = ObjectFollowController(
        pi_command_base=args.pi_command_base,
        enabled=args.follow,
    )
    state = LatestFrame()
    state.follow = follow

    httpd = None
    if args.serve_port > 0:
        httpd = start_http_server(state, args.serve_port, follow)

    logger.info("Loading model %s ...", args.model)
    model = YOLO(args.model)
    state.model_loaded = True
    logger.info("Model loaded. Pulling frames from %s", args.url)
    logger.info(
        "Follow target=%s enabled=%s pi=%s",
        FOLLOW_TARGET, args.follow, args.pi_command_base,
    )

    stop = threading.Event()
    worker = threading.Thread(
        target=detection_worker, args=(model, state, stop, follow), daemon=True
    )
    worker.start()

    window = "Dog camera (YOLO11n) — press q to quit"
    fail_streak = 0
    try:
        while True:
            frame = fetch_jpeg_frame(args.url)
            if frame is None:
                fail_streak += 1
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                msg = f"Waiting for camera... ({fail_streak})"
                cv2.putText(
                    blank, msg,
                    (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                )
                state.set_annotated(blank, camera_ok=False, fail_streak=fail_streak)
                if not args.no_window:
                    cv2.imshow(window, blank)
                    if cv2.waitKey(200) & 0xFF == ord("q"):
                        break
                else:
                    time.sleep(0.2)
                continue

            fail_streak = 0
            state.set_frame(frame)
            annotated = draw_detections(frame, state.get_detections())
            cv2.putText(
                annotated, "Mac YOLO11n",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
            )
            annotated = draw_follow_overlay(annotated, follow)
            state.set_annotated(annotated, camera_ok=True, fail_streak=0)

            if not args.no_window:
                cv2.imshow(window, annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                time.sleep(0.01)
    finally:
        stop.set()
        follow.set_enabled(False)
        if httpd is not None:
            httpd.shutdown()
        if not args.no_window:
            cv2.destroyAllWindows()
        logger.info("Stopped")


if __name__ == "__main__":
    main()
