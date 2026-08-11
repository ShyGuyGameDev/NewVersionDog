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
from collections import deque
from typing import Deque, List, Optional, Tuple
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
# After a loss halt, require continuous sightings this long before walking again.
RESUME_CONFIRM_S = 0.45
# Zone must stay put this long before sending gs/gr (stops bias thrash).
ZONE_STABLE_S = 0.35
WALK_HEARTBEAT_S = 1.5
PI_CMD_TIMEOUT_S = 1.5
# Follow gait traffic uses a shorter timeout so a stuck Pi cannot stall the queue.
FOLLOW_CMD_TIMEOUT_S = 0.5
# Website Stop button uses stand; firmware "stop" can leave the dog unresponsive.
FOLLOW_HALT_CMD = "stand"

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
    """Mac-side follow: hysteresis zones → gait bias → Pi walk/halt.

    Perception (`tick`) never blocks on HTTP. A dedicated command worker
    serializes gs/gr/gait/stand so the 0.8s lost-hold uses real wall time.
    """

    def __init__(self, pi_command_base: str, enabled: bool = False):
        self.pi_command_base = pi_command_base
        self._lock = threading.Lock()
        self.enabled = enabled
        self.last_seen_t: Optional[float] = None
        self.hold_until_t: Optional[float] = None
        self.last_zone = "center"
        self.zone_candidate = "center"
        self.zone_candidate_since: Optional[float] = None
        self.applied_bias: Optional[int] = None
        self.desired_bias: Optional[int] = None
        self._pending_bias: Optional[int] = None  # enqueued but not yet applied
        self.walking = False
        self.holding = False
        self.last_walk_sent_t = 0.0
        self.last_x_norm: Optional[float] = None
        self.target_visible = False
        self._was_visible = False
        self._was_holding = False
        self._was_should_walk = False
        self._lost_halted = False  # True after a lost-timeout halt until resume confirms
        self._visible_since: Optional[float] = None
        self._stop_event = threading.Event()
        self._cmd_wake = threading.Event()
        # Queue items: ("raw", cmd) | ("sync_bias", bias) | ("gait",) | ("halt",)
        self._cmd_queue: Deque[Tuple] = deque()
        self._cmd_worker = threading.Thread(
            target=self._command_loop, name="follow-cmd", daemon=True
        )
        self._cmd_worker.start()

    def shutdown(self):
        """Stop the command worker (call on process exit)."""
        self._stop_event.set()
        self._cmd_wake.set()

    def set_enabled(self, enabled: bool):
        with self._lock:
            was = self.enabled
            self.enabled = enabled
            if was and not enabled:
                self.walking = False
                self.holding = False
                self.desired_bias = None
                self._pending_bias = None
                self.hold_until_t = None
                self._lost_halted = False
                self._visible_since = None
                self._was_visible = False
                self._was_holding = False
                self._was_should_walk = False
                self._enqueue_unlocked("halt", coalesce_halt=True)
        if was and not enabled:
            logger.info("Follow disabled; %s queued", FOLLOW_HALT_CMD)
        elif enabled and not was:
            logger.info("Follow enabled; target=%s", FOLLOW_TARGET)

    def status(self) -> dict:
        with self._lock:
            age = None
            if self.last_seen_t is not None:
                age = time.time() - self.last_seen_t
            hold_left = None
            if self.hold_until_t is not None:
                hold_left = max(0.0, self.hold_until_t - time.time())
            return {
                "enabled": self.enabled,
                "target": FOLLOW_TARGET,
                "gait": FOLLOW_GAIT,
                "halt_cmd": FOLLOW_HALT_CMD,
                "zone": self.last_zone,
                "bias": self.applied_bias,
                "desired_bias": self.desired_bias,
                "walking": self.walking,
                "holding": self.holding,
                "hold_remaining_s": hold_left,
                "target_visible": self.target_visible,
                "lost_halted": self._lost_halted,
                "last_seen_age_s": age,
                "x_norm": self.last_x_norm,
                "cmd_queue_len": len(self._cmd_queue),
                "cmd_backed_up": len(self._cmd_queue) > 2,
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

    def _enqueue_unlocked(self, kind: str, *args, coalesce_halt: bool = False):
        """Caller must hold self._lock. Coalesce duplicate gait/halt; keep bias syncs ordered."""
        if coalesce_halt or kind == "halt":
            # Drop pending gait/bias; keep a single halt at the end.
            kept: Deque[Tuple] = deque()
            for item in self._cmd_queue:
                if item[0] in ("gait", "sync_bias", "halt"):
                    continue
                kept.append(item)
            kept.append(("halt",))
            self._cmd_queue = kept
            self._pending_bias = None
        elif kind == "gait":
            # At most one pending gait (latest wins). Drop if a halt is already queued.
            if any(item[0] == "halt" for item in self._cmd_queue):
                return
            self._cmd_queue = deque(
                item for item in self._cmd_queue if item[0] != "gait"
            )
            self._cmd_queue.append(("gait",))
        elif kind == "sync_bias":
            if any(item[0] == "halt" for item in self._cmd_queue):
                return
            bias = int(args[0])
            # Replace any pending sync_bias with the latest target.
            self._cmd_queue = deque(
                item for item in self._cmd_queue if item[0] != "sync_bias"
            )
            self._cmd_queue.append(("sync_bias", bias))
            self._pending_bias = bias
        else:
            self._cmd_queue.append((kind, *args))
        self._cmd_wake.set()

    def _command_loop(self):
        while not self._stop_event.is_set():
            self._cmd_wake.wait(timeout=0.25)
            self._cmd_wake.clear()
            while not self._stop_event.is_set():
                with self._lock:
                    if not self._cmd_queue:
                        break
                    item = self._cmd_queue.popleft()
                kind = item[0]
                if kind == "halt":
                    send_pi_command(
                        self.pi_command_base, FOLLOW_HALT_CMD, timeout=FOLLOW_CMD_TIMEOUT_S
                    )
                elif kind == "gait":
                    ok = send_pi_command(
                        self.pi_command_base, FOLLOW_GAIT, timeout=FOLLOW_CMD_TIMEOUT_S
                    )
                    if ok:
                        with self._lock:
                            self.last_walk_sent_t = time.time()
                elif kind == "sync_bias":
                    bias = int(item[1])
                    send_pi_command(
                        self.pi_command_base, "gs", timeout=FOLLOW_CMD_TIMEOUT_S
                    )
                    for _ in range(max(0, bias)):
                        send_pi_command(
                            self.pi_command_base, "gr", timeout=FOLLOW_CMD_TIMEOUT_S
                        )
                    with self._lock:
                        self.applied_bias = bias
                        if self._pending_bias == bias:
                            self._pending_bias = None
                elif kind == "raw":
                    send_pi_command(
                        self.pi_command_base, str(item[1]), timeout=FOLLOW_CMD_TIMEOUT_S
                    )

    def tick(self, detections: List[dict], frame_width: int):
        """Update follow state from detections only — never blocks on Pi HTTP."""
        with self._lock:
            if not self.enabled:
                return
            prev_zone = self.last_zone
            was_visible = self._was_visible

        if frame_width <= 0:
            return

        target = self.select_target(detections)
        now = time.time()
        x_norm: Optional[float] = None
        zone = prev_zone

        if target is not None:
            x_norm = float(target["center_x"]) / float(frame_width)
            raw_zone = self.compute_zone(x_norm, prev_zone)
            with self._lock:
                self.last_seen_t = now
                # Fresh 0.8s hold starts whenever we still see the target, so a miss
                # keeps gait for LOST_TIMEOUT_S of wall time after the last hit.
                self.hold_until_t = now + LOST_TIMEOUT_S
                self.last_x_norm = x_norm
                self.target_visible = True
                if self._visible_since is None:
                    self._visible_since = now
                # Debounce zone before committing (stops gs/gr thrash on flicker).
                if raw_zone != self.zone_candidate:
                    self.zone_candidate = raw_zone
                    self.zone_candidate_since = now
                elif (
                    self.zone_candidate_since is not None
                    and (now - self.zone_candidate_since) >= ZONE_STABLE_S
                    and raw_zone != self.last_zone
                ):
                    self.last_zone = raw_zone
                zone = self.last_zone
            visible = True
        else:
            with self._lock:
                self.target_visible = False
                self._visible_since = None
                zone = self.last_zone
                x_norm = self.last_x_norm
                if was_visible:
                    # Discover miss now → guarantee a full 0.8s hold from this edge.
                    self.hold_until_t = now + LOST_TIMEOUT_S
            visible = False

        with self._lock:
            hold_until = self.hold_until_t
            lost_halted = self._lost_halted
            visible_since = self._visible_since

        should_walk = hold_until is not None and now < hold_until
        holding = should_walk and not visible

        # After a lost halt, demand stable reappearance before walking again.
        if should_walk and visible and lost_halted:
            if visible_since is None or (now - visible_since) < RESUME_CONFIRM_S:
                should_walk = False
                holding = False

        with self._lock:
            applied = self.applied_bias
            walking = self.walking
            last_walk = self.last_walk_sent_t
            was_holding = self._was_holding
            was_should_walk = self._was_should_walk
            self.holding = holding
            self._was_visible = visible

            if not should_walk:
                self._was_holding = False
                self._was_should_walk = False
                if walking:
                    self.walking = False
                    self._lost_halted = True
                    self.hold_until_t = None
                    self._enqueue_unlocked("halt", coalesce_halt=True)
                    logger.info("Follow: target lost → %s", FOLLOW_HALT_CMD)
                elif (
                    hold_until is not None
                    and now >= hold_until
                    and not self._lost_halted
                ):
                    self._lost_halted = True
                    self.hold_until_t = None
                    self._enqueue_unlocked("halt", coalesce_halt=True)
                    logger.info("Follow: target lost → %s", FOLLOW_HALT_CMD)
                return

            bias = self.zone_to_bias(zone)
            self.desired_bias = bias
            pending = self._pending_bias

            if holding and not was_holding:
                logger.info(
                    "Follow: holding last gait for %.1fs (target=%s)",
                    LOST_TIMEOUT_S, FOLLOW_TARGET,
                )
            elif not holding and was_holding and visible:
                logger.info("Follow: target reacquired → resume")
            elif should_walk and not was_should_walk and visible:
                logger.info("Follow: target acquired → walk")

            if visible:
                self._lost_halted = False

            self._was_holding = holding
            self._was_should_walk = True

            # Only steer while target is visible and zone has been stable.
            if visible and applied != bias and pending != bias:
                self._enqueue_unlocked("sync_bias", bias)
                logger.info(
                    "Follow: zone=%s bias=%s x=%.3f target=%s",
                    zone, bias, x_norm if x_norm is not None else -1.0, FOLLOW_TARGET,
                )

            need_walk = (not walking) or (now - last_walk >= WALK_HEARTBEAT_S)
            if need_walk:
                self.walking = True
                self.last_walk_sent_t = now
                self._enqueue_unlocked("gait")


class LatestFrame:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.frame_id = 0
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
            self.frame_id += 1

    def get_frame_copy(self) -> Tuple[Optional[np.ndarray], int]:
        with self.lock:
            if self.frame is None:
                return None, self.frame_id
            return self.frame.copy(), self.frame_id

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
    if st.get("holding"):
        mode = "HOLD"
        color = (0, 255, 255)
    elif st.get("walking"):
        mode = FOLLOW_GAIT.upper()
        color = (0, 200, 255)
    else:
        mode = "STOP"
        color = (0, 165, 255)
    bias = st.get("bias")
    bias_s = "?" if bias is None else str(bias)
    zone = st.get("zone") or "?"
    x = st.get("x_norm")
    x_s = f"{x:.2f}" if isinstance(x, float) else "-"
    age = st.get("last_seen_age_s")
    age_s = f"{age:.2f}s" if isinstance(age, float) else "-"
    hold_left = st.get("hold_remaining_s")
    hold_s = f"{hold_left:.2f}s" if isinstance(hold_left, float) and st.get("holding") else "-"
    qlen = st.get("cmd_queue_len") or 0
    backed = " Q!" if st.get("cmd_backed_up") else ""
    line = (
        f"Follow {FOLLOW_TARGET} | {zone} bias={bias_s} | {mode} "
        f"hold={hold_s} age={age_s} x={x_s} q={qlen}{backed}"
    )
    cv2.putText(frame, line, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2)
    # Zone guides
    h, w = frame.shape[:2]
    for frac, col in ((LEFT_X, (255, 128, 0)), (0.5 - CENTER_HALF, (180, 180, 180)),
                      (0.5 + CENTER_HALF, (180, 180, 180)), (RIGHT_X, (255, 128, 0))):
        xi = int(frac * w)
        cv2.line(frame, (xi, 0), (xi, h), col, 1)
    return frame


def detection_worker(
    model: YOLO,
    state: LatestFrame,
    stop: threading.Event,
    follow: Optional[ObjectFollowController],
):
    last_frame_id = -1
    while not stop.is_set():
        frame, frame_id = state.get_frame_copy()
        if frame is None:
            time.sleep(0.02)
            continue
        if frame_id == last_frame_id:
            # Do not re-infer / re-tick follow on a stale frame (camera gaps).
            time.sleep(0.01)
            continue
        last_frame_id = frame_id
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
        # Brief pause so the stop command can leave the queue before worker exit.
        time.sleep(0.15)
        follow.shutdown()
        if httpd is not None:
            httpd.shutdown()
        if not args.no_window:
            cv2.destroyAllWindows()
        logger.info("Stopped")


if __name__ == "__main__":
    main()
