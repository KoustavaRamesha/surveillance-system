from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent

def _load_env_file():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass

_load_env_file()

MODELS_DIR = BASE_DIR / "models"
DATASETS_DIR = BASE_DIR / "datasets"
EVIDENCE_DIR = BASE_DIR / "evidence"
TRAINING_RUNS_DIR = BASE_DIR / "training_runs"
TEMP_DIR = BASE_DIR / "temp_uploads"
DATABASE_PATH = BASE_DIR / "incidents.db"

APP_TITLE = "Real-Time AI Surveillance and Safety Guidance System for Industrial Workplaces"
DEFAULT_MODEL_PATH = MODELS_DIR / "yolo11m.pt"
DEFAULT_FRAME_SKIP = 3
ALERT_COOLDOWN_SECONDS = 10
DEFAULT_ZONE = {"x1": 100, "y1": 100, "x2": 400, "y2": 400, "name": "Restricted Zone"}
SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv"}
DEFAULT_STATUS = "Open"
INCIDENT_STATUSES = ["Open", "Acknowledged", "Resolved"]
DEFAULT_AI_FPS = 8
DEFAULT_DISPLAY_FPS = 60
DEFAULT_IMG_SIZE = 320
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
DEFAULT_INFERENCE_FPS = 8

# Bounded per-camera latest-frame queue size (1 keeps only latest)
FRAME_QUEUE_MAXLEN = 2

# Twilio SMS Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_API_KEY_SID = os.getenv("TWILIO_API_KEY_SID", "")
TWILIO_API_KEY_SECRET = os.getenv("TWILIO_API_KEY_SECRET", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_TO_NUMBER = os.getenv("TWILIO_TO_NUMBER", "")
TWILIO_SMS_ENABLED = os.getenv("TWILIO_SMS_ENABLED", "true").lower() in ("true", "1", "yes")

for directory in (MODELS_DIR, DATASETS_DIR, EVIDENCE_DIR, TRAINING_RUNS_DIR, TEMP_DIR):
    directory.mkdir(parents=True, exist_ok=True)
