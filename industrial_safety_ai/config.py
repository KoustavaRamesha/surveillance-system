from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATASETS_DIR = BASE_DIR / "datasets"
EVIDENCE_DIR = BASE_DIR / "evidence"
TRAINING_RUNS_DIR = BASE_DIR / "training_runs"
TEMP_DIR = BASE_DIR / "temp_uploads"
DATABASE_PATH = BASE_DIR / "incidents.db"

APP_TITLE = "Real-Time AI Surveillance and Safety Guidance System for Industrial Workplaces"
DEFAULT_MODEL_PATH = MODELS_DIR / "yolov8n.pt"
DEFAULT_FRAME_SKIP = 3
ALERT_COOLDOWN_SECONDS = 10
DEFAULT_ZONE = {"x1": 100, "y1": 100, "x2": 400, "y2": 400, "name": "Restricted Zone"}
SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv"}
DEFAULT_STATUS = "Open"
INCIDENT_STATUSES = ["Open", "Acknowledged", "Resolved"]
DEFAULT_AI_FPS = 30
DEFAULT_DISPLAY_FPS = 30
DEFAULT_IMG_SIZE = 416
# Stabilizer / smoothing defaults
STABILIZER_IOU_THRESHOLD = 0.35
STABILIZER_ALPHA = 0.6
STABILIZER_MAX_MISSES = 3
STABILIZER_MIN_HITS = 1

# Confidence hysteresis to reduce flicker from borderline detections
STABILIZER_CONFIDENCE_HIGH = 0.6
STABILIZER_CONFIDENCE_LOW = 0.35

# Maximum allowed box shift per update as a fraction of box size (prevents large jumps)
STABILIZER_MAX_SHIFT_RATIO = 0.5

# New configurable settings for tracking and inference
TRACKER_CONFIG = "bytetrack.yaml"
DEFAULT_TRACKER = "bytetrack"
DEFAULT_CONFIDENCE = 0.5
DEFAULT_IOU_THRESHOLD = 0.35
DEFAULT_SMOOTHING_ALPHA = 0.30
DEFAULT_REQUIRED_HITS = 3
DEFAULT_ALLOWED_MISSES = 5
DEFAULT_INFERENCE_FPS = 5

# Bounded per-camera latest-frame queue size (1 keeps only latest)
FRAME_QUEUE_MAXLEN = 2

for directory in (MODELS_DIR, DATASETS_DIR, EVIDENCE_DIR, TRAINING_RUNS_DIR, TEMP_DIR):
    directory.mkdir(parents=True, exist_ok=True)
