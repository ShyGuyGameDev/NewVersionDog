"""
YOLO11n object detection with hierarchy labels for NewVersionDog.

Deploy on the Pi (WorkingDirectory=/home/pi/system):
  - Place yolo11n.pt in /home/pi/system/ (auto-downloaded by ultralytics on first run if networked)
  - pip3 install ultralytics opencv-python numpy  (plus a Pi-compatible torch CPU wheel)
  - Restart: sudo systemctl restart camera
"""
import os

try:
    from ultralytics import YOLO  # type: ignore[import-not-found]
except ImportError as exc:
    YOLO = None
    _YOLO_IMPORT_ERROR = exc
else:
    _YOLO_IMPORT_ERROR = None

# Prefer model next to this file / camera working directory.
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolo11n.pt")
if not os.path.isfile(_MODEL_PATH):
    _MODEL_PATH = "yolo11n.pt"

if YOLO is not None:
    try:
        model = YOLO(_MODEL_PATH)
        _MODEL_LOAD_ERROR = None
    except Exception as exc:  # pragma: no cover - hardware/runtime dependent
        model = None
        _MODEL_LOAD_ERROR = exc
else:
    model = None
    _MODEL_LOAD_ERROR = _YOLO_IMPORT_ERROR

# Mapping of raw YOLO/COCO classes to higher-level hierarchy categories
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


def get_object_hierarchy(class_name):
    """Map a detected object class to its hierarchy category."""
    for hierarchy_category, objects in object_hierarchy.items():
        if class_name in objects:
            return hierarchy_category
    return "unknown"


def classify_frame(frame, conf_threshold=0.5):
    """
    Pure inference helper for Raspberry Pi use.

    Accepts an OpenCV BGR frame, runs YOLO11n with hierarchy mapping, and
    returns structured detections without touching cameras, GUIs, or disk.

    Returns:
        list[dict]: detections with keys class, original_class,
        hierarchy_category, confidence (0-100), bbox, center_x, center_y,
        frame_width.
    """
    detections = []
    frame_width = frame.shape[1] if hasattr(frame, "shape") and len(frame.shape) >= 2 else None

    if model is None:
        return detections

    try:
        results = model(frame, verbose=False)
    except Exception:
        return detections

    for r in results:
        names = model.names
        if not hasattr(r, "boxes") or len(r.boxes) == 0:
            continue

        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if conf < conf_threshold:
                continue

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            hierarchy_category = get_object_hierarchy(names[cls_id])

            detections.append({
                "class": hierarchy_category,
                "original_class": names[cls_id],
                "hierarchy_category": hierarchy_category,
                "confidence": conf * 100,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "center_x": float(center_x),
                "center_y": float(center_y),
                "frame_width": frame_width,
            })

    return detections
