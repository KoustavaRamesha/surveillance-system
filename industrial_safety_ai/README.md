# Real-Time AI Surveillance and Safety Guidance System for Industrial Workplaces

A college-level prototype for industrial workplace surveillance using PySide6 (desktop) and Streamlit (web), OpenCV, and Ultralytics YOLO. It is highly optimized to run at true real-time speeds using NVIDIA CUDA.

## Architecture

The project has two frontends sharing a common backend:

```
Desktop App (main.py → ui/main_window.py)
│   ├── ui/zone_dialog.py           — Interactive restricted zone drawing
│   ├── core/inference_manager.py   — YOLO inference thread (GPU-accelerated)
│   ├── core/camera_worker.py       — per-camera capture thread
│   ├── core/alert_manager.py       — incident logging + active alerts
│   ├── core/sms_notifier.py        — SMS alert dispatcher for critical incidents
│   ├── core/detection_stabilizer.py — smoothing/filtering
│   ├── core/camera_db.py           — camera CRUD + zone configuration storage
│   ├── core/model_utils.py         — model file discovery
│   └── core/settings_manager.py    — persistent settings
│
Streamlit App (app.py)
│   └── Self-contained video upload + analysis workflow
│
Shared Modules
    ├── detector.py      — YOLO loading, inference, tracking
    ├── zone_monitor.py  — Restricted-zone intrusion detection
    ├── rules.py         — Severity/recommendation rules, label normalization
    ├── database.py      — SQLite incident CRUD (WAL mode enabled)
    ├── evidence.py      — Evidence image saving
    └── config.py        — Shared defaults and paths
```

## Key Features

- **Real-Time Video Analytics**: Process high-speed camera feeds smoothly at 30 FPS using CUDA-accelerated YOLO object detection.
- **Interactive Restricted Zones**: Draw custom restricted areas directly on the camera feed using the built-in UI tool.
- **Active Alert System**: Instantly warns operators by flashing camera borders red when critical incidents (e.g., Fire, Zone Intrusions) occur.
- **SMS Notifications**: Dispatches automated SMS alerts for high-severity safety breaches (mocked for demo purposes).
- **Automated Incident Logging**: Automatically captures evidence screenshots and saves them into an SQLite database.
- **Dual Dashboard Support**: Use either the robust Desktop PySide6 UI or the Web-based Streamlit UI.

## What the final demo shows

- Defining a restricted zone by drawing a box on the camera feed.
- Person entering the drawn restricted area (triggering an active flashing alert and SMS).
- Worker without helmet.
- Fire or smoke detection.
- Recommended safety action.
- Evidence-image capture.
- Acknowledge and resolve workflow via the Incident Database.

## Custom safety model

You can keep using the default `yolov8n.pt` checkpoint for person detection and restricted-zone intrusion, or point the app to a custom `best.pt` file trained for safety classes.

The custom model can detect these classes:
- `person`
- `helmet`
- `safety_vest`
- `no_helmet`
- `no_vest`
- `fire`
- `smoke`

Label normalisation is built into the app, so variants such as `no-hardhat`, `no_hardhat`, `without_helmet`, and `no helmet` are mapped to `no_helmet`.

### Training a custom model

Training stays outside the main app. Use `train_custom.py` when you are ready to train:

```powershell
python train_custom.py --data dataset.yaml --model yolov8n.pt --epochs 50 --imgsz 640
```

After training, point the model path field to the generated `best.pt` file.

### Demo mode

If a trained custom model is not available, enable the demo mode checkbox in the app.
It uses scripted sample incidents to show the complete workflow without changing the restricted-zone feature.

Demo mode is useful for:
- Final presentation rehearsal
- Showing the database and evidence capture flow
- Demonstrating incident status updates

## Run setup on Windows

Ensure you have a modern NVIDIA GPU for real-time 30 FPS inference.

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install PyTorch with CUDA support (Mandatory for GPU acceleration)
pip uninstall -y torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

For development (includes pytest and pyinstaller):

```powershell
pip install -r requirements-dev.txt
```

## Running the app

### Desktop app (PySide6)

```powershell
python main.py
```

The desktop app will:
- Auto-discover USB cameras
- Let you draw interactive Restricted Zones
- Start CUDA YOLO inference in a background thread
- Show live camera feeds perfectly synced with detection overlays (Zero UI lag)
- Flash red warnings and dispatch SMS alerts during critical incidents
- Log incidents with evidence images

### Streamlit app

```powershell
streamlit run app.py
```

The Streamlit app provides video upload and analysis with a web-based interface.

## How to test

### Automated tests

```powershell
python -m pytest tests/ -v
```

### Manual testing

1. Start `python main.py` and connect a camera.
2. Select the camera, click "Draw Restricted Zone", and outline a custom area.
3. Walk into the restricted area on camera.
4. Verify the camera tile flashes red, an incident is logged in the side panel, and `[SMS DISPATCHED]` prints in the console.
5. Open the Incident History tab and update status from `Open` to `Acknowledged` and then `Resolved`.

## Likely viva questions

**Q1. Why did you use YOLO?**  
A1. YOLO gives fast real-time object detection, which fits video-based workplace monitoring.

**Q2. How is it able to run in real-time without lagging?**  
A2. The inference engine leverages PyTorch CUDA to offload heavy AI math onto the NVIDIA GPU. The UI render loop is also completely decoupled and perfectly synced to the inference loop, preventing visual trailing or freezing.

**Q3. How does the Restricted Zone feature work?**  
A3. A user interactively draws a bounding box over the live camera feed. This is saved to the SQLite DB as JSON. The inference thread then cross-references the coordinates of detected persons against the saved zone polygon to detect intrusions.

**Q4. How do you handle Active Alerts?**  
A4. The AlertManager evaluates rule severities. If a critical incident (like Fire or Intrusion) occurs, it triggers an immediate PySide6 QTimer to flash the camera UI red and hooks into a mock SMS API to notify safety staff.

**Q5. Why save evidence images?**  
A5. Evidence helps supervisors review what happened and supports the incident record.

**Q6. What happens if no custom model is available?**  
A6. Demo mode creates sample incidents so the full project flow can still be demonstrated.

**Q7. Why use SQLite with WAL mode?**  
A7. SQLite is lightweight and easy to set up. WAL (Write-Ahead Logging) mode was enabled to allow the multi-threaded PySide6 app to read and write to the database simultaneously without freezing the UI or locking the database.

## Notes

- If `models/yolov8n.pt` does not exist, the app can still fall back to the Ultralytics pretrained `yolov8n.pt` checkpoint.
- The database file `incidents.db` is created automatically when the app runs.
- Evidence images are saved in `evidence/`.

## Next feature set

After the first milestone works, extend the same structure for:
- Advanced PPE detection with compliance scoring
- Recording and playback with incident-linked video clips
- Reporting dashboard with shift reports and trend analysis
- Multi-site networking with REST API
- Edge deployment with ONNX/TensorRT optimization
