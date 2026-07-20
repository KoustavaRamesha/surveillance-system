import time
import sys
from pathlib import Path
# ensure project root on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.camera_worker import CameraWorker
from core.inference_manager import InferenceManager

MODEL = r"models/yolov8n.pt"


def on_frame(cid, frame):
    # forward to inference manager
    inf.submit_frame(cid, frame)


def on_detection(cid, dets, annotated):
    print(f"DETECTIONS from {cid}: {len(dets) if dets else 0}")


def on_status(cid, st):
    print(f"STATUS {cid}: {st}")


if __name__ == '__main__':
    inf = InferenceManager(model_path=MODEL, ai_fps=3, demo_mode=False)
    inf.detection_ready.connect(on_detection)
    inf.status_updated.connect(lambda s: print('INF_STATUS:', s))
    inf.start_manager()

    w = CameraWorker(camera_id='CAM-TEST', source=0)
    w.frame_received.connect(on_frame)
    w.status_updated.connect(on_status)
    w.start()

    try:
        time.sleep(12)
    finally:
        print('Stopping...')
        try:
            w.stop()
        except Exception:
            pass
        try:
            inf.stop_manager()
        except Exception:
            pass
        print('Stopped')
