from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

from config import TRAINING_RUNS_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a custom YOLO model for industrial safety detection.")
    parser.add_argument("--data", default=str(Path(__file__).resolve().parent / "dataset.yaml"), help="Path to dataset.yaml")
    parser.add_argument("--model", default="yolov8n.pt", help="Pretrained model checkpoint")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size")
    parser.add_argument("--project", default=str(TRAINING_RUNS_DIR), help="Directory to store training outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TRAINING_RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Training stays outside Streamlit so the demo app remains simple and fast.
    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        project=args.project,
        name="industrial_safety",
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
