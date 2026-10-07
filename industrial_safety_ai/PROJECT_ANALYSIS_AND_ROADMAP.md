# Project Analysis & Roadmap — Real-Time AI Surveillance and Safety Guidance System for Industrial Workplaces

> This document is a complete technical walkthrough of the codebase: how every module works, how data flows through the system at runtime, the database schema, the threading model, tuning knobs, known issues/bugs found during review, and a prioritized roadmap of future improvements and requirements.
>
> It complements `README.md` (which focuses on setup/demo instructions) with a deep engineering view of the code.

---

## 1. What the project is

A **college-level prototype** of an industrial workplace safety surveillance system with two frontends sharing one backend:

| Frontend | Entry point | Purpose |
|---|---|---|
| **Desktop (PySide6)** | `main.py` | Live multi-camera monitoring, interactive restricted-zone drawing, real-time YOLO detection, active alerts (flashing tiles + mock SMS), incident logging with evidence images, acknowledge/resolve workflow |
| **Web (Streamlit)** | `app.py` | Video *upload* → batch analysis, live progress UI, incident history table with evidence viewer and status updates |

**Detection scope** (via a custom-trained YOLO model, or scripted demo mode):
`person`, `helmet`, `safety_vest`, `no_helmet`, `no_vest`, `fire`, `smoke` — plus a *derived* event `restricted_area_intrusion` (person centre-point inside a user-drawn rectangle). `worker_fall` has rules defined but **no detector path produces it yet** (future feature).

---

## 2. Repository layout

```
AI-surveillance-system/
├── yolov8n.pt                      # stock COCO checkpoint (fallback, repo root)
├── tools/probe_cameras.py          # quick USB camera index probe (0..7)
└── industrial_safety_ai/           # ← the application
    ├── main.py                     # Desktop entry point (PySide6 QApplication)
    ├── app.py                      # Streamlit web frontend
    ├── config.py                   # All paths + tuning constants (single source of truth)
    ├── database.py                 # SQLite incidents CRUD (WAL mode)
    ├── detector.py                 # YOLO load / infer / track / draw / demo events
    ├── zone_monitor.py             # Zone validation, point-in-rect, intrusion detection
    ├── rules.py                    # Label normalization, severity + recommendation rules
    ├── evidence.py                 # Evidence JPEG saving
    ├── dataset.yaml                # 7-class custom training spec
    ├── train_custom.py             # Offline YOLO training wrapper
    ├── requirements.txt / -dev.txt
    ├── core/                       # Desktop backend package
    │   ├── inference_manager.py    # QThread: shared YOLO inference loop
    │   ├── camera_worker.py        # QThread per-camera capture + reconnect
    │   ├── alert_manager.py        # Cooldown → evidence → DB → SMS pipeline
    │   ├── detection_stabilizer.py # EMA box smoothing + hit/miss confirmation
    │   ├── camera_db.py            # cameras table CRUD + zone storage
    │   ├── model_utils.py          # discover first available .pt model
    │   ├── settings_manager.py     # settings.json persistence (currently unused by UI)
    │   └── sms_notifier.py         # mock SMS dispatcher (print/log)
    ├── ui/                         # PySide6 widgets
    │   ├── main_window.py          # Main window: toolbar, grid, wiring (~565 lines)
    │   ├── camera_tile.py          # Video tile: fast cv2→QImage, red alert flash
    │   ├── alert_panel.py          # Active alerts list + Acknowledge/Resolve
    │   ├── camera_dialog.py        # Add-camera form + Test Connection
    │   └── zone_dialog.py          # Drag-to-draw restricted zone overlay
    ├── tests/                      # pytest: database, rules, zone_monitor, model_utils
    ├── tools/
    │   ├── enumerate_cameras.py    # probe USB indices 0..7
    │   ├── move_model_to_models.py # move repo-root yolov8n.pt → models/
    │   └── test_pipeline.py        # headless integration test (capture → inference)
    ├── models/  datasets/          # gitkeep'd (weights/datasets are gitignored)
    └── evidence/                   # saved incident screenshots (runtime artifact)
```

Runtime artifacts created automatically: `incidents.db` (+ `-wal`/`-shm`), `settings.json`, `evidence/`, `training_runs/`, `temp_uploads/`, `models/`, `datasets/`.

---

## 3. Architecture in one diagram

```
┌────────────────────────── Desktop (PySide6) ───────────────────────────┐
│ MainWindow (ui/main_window.py)                                         │
│  ├─ CameraDiscoveryWorker (QThread): scans USB idx 0..5, auto-adds     │
│  ├─ CameraWorker (QThread per camera): cap.read() → frame_received     │
│  │     • backend fallback DSHOW → MSMF → ANY, buffersize=1             │
│  │     • exponential reconnect backoff 2s → 30s                        │
│  │     • throttles emits to display_fps (8/s default)                  │
│  ├─ on_frame: cached config/zone → InferenceManager.submit_frame()     │
│  │     (bounded deque maxlen=2 — keeps ONLY the latest frame)          │
│  ├─ InferenceManager (single QThread, owns the GPU)                    │
│  │     per-camera loop each tick:                                      │
│  │       pop latest frame → per-camera YOLO model.track(persist=True,  │
│  │       imgsz=320, half=True, bytetrack) → DetectionStabilizer.update │
│  │       → zone intrusion check (+ zone rescale by ref_width/height)   │
│  │       → append synthetic "restricted_area_intrusion" detections     │
│  │       → draw_detections → detection_ready(cid, dets, annotated)     │
│  ├─ on_detections:                                                     │
│  │     • show annotated frame (≥33 ms throttle)                        │
│  │     • severity Critical → tile.set_alert_state(True) → red flash 3s │
│  │     • AlertManager.process_detections(...):                          │
│  │         cooldown(10 s per camera+zone+event) → save evidence jpg    │
│  │         → add_incident(SQLite) → SMS if Critical/High → panel item  │
│  └─ AlertPanel: Acknowledge/Resolve → update_incident_status()         │
└────────────────────────────────────────────────────────────────────────┘
          │ shares: detector, zone_monitor, rules, database, evidence, config
┌─────────┴──────────────── Web (Streamlit, app.py) ─────────────────────┐
│ Upload video → save to temp_uploads/ → process_video():                │
│   frame-skip loop → infer_frame (no tracking) or demo events →         │
│   draw zone + detections → detect_intrusions → cooldown → evidence →   │
│   add_incident → live placeholders (frame/alert/progress/summary)      │
│ Incident History tab: filters, dataframe, evidence viewer, status edit │
└────────────────────────────────────────────────────────────────────────┘
```

**Key architectural decisions**

| Decision | Why / how |
|---|---|
| One shared `InferenceManager` QThread | Model loaded once per camera only for *tracker-state* isolation (`persist=True` needs stable per-stream state); frames are dropped, never queued — always the freshest frame is processed |
| `deque(maxlen=2)` frame mailbox | Lock-protected; producer overwrites; consumer pops the latest and `clear()`s — prevents inference backlog on slow GPUs |
| Per-camera model instances (`_camera_models`) | ByteTrack state lives inside the Ultralytics model object; one instance per camera keeps track IDs from bleeding across cameras (trade-off: N× GPU/CPU memory) |
| SQLite with WAL + `check_same_thread=False` | Multi-thread reads/writes without locking the UI; `synchronous=NORMAL` for speed |
| Two UI display paths | Analytics-on: display driven by *annotated* inference frames (perfect sync of boxes and pixels); analytics-off: raw frames throttled at ~30 ms |
| DetectionStabilizer | Decouples noisy per-frame detections from UI/alerts: EMA smoothing (α=0.30), jump clamping (≤50% box size/frame), hits/misses confirmation (3 hits / 5 misses), confidence hysteresis (in ≥0.6, drop <0.35) |
| Zone coords stored with `ref_width/ref_height` | Zones drawn on the *scaled preview pixmap*; rescaled at inference time to actual frame dims so resolution changes don't break the zone |

---

## 4. Module-by-module walkthrough

### 4.1 Entry points

**`main.py`** — sets `OPENCV_LOG_LEVEL=SILENT`, creates `QApplication`, calls `ensure_project_dirs()` (mkdirs from `config` + `create_incidents_table()` + `create_cameras_table()`), then shows `MainWindow` and runs the Qt event loop.

**`app.py` (Streamlit)** — two tabs:
- *Analyse Video*: uploader (mp4/avi/mov/mkv) → temp file in `temp_uploads/` → `process_video()` loop with `frame_skip`, per-frame `infer_frame` (no tracking), zone validation from 4 numeric inputs, `_log_single_incident()` (cooldown `ALERT_COOLDOWN_SECONDS`, evidence save, `add_incident`), live placeholders for frame/alerts/progress/summary. Temp file deleted in `finally`.
- *Incident History*: `read_incidents()` with severity/status filters, pandas dataframe, evidence `st.image`, status update via `update_incident_status` + `st.rerun()`.
- Model is cached with `@st.cache_resource`; demo mode falls back to `generate_demo_detections` when the model is missing.

### 4.2 Shared detection core

**`detector.py`**
- `Detection` dataclass (slots) + `to_dict()`.
- `load_model()`: resolves path (`_resolve_model_source` falls back to well-known Ultralytics checkpoint names for auto-download), calls `model.fuse()` for Conv+BN speedup.
- `infer_frame()`: plain `model.predict` → normalized dicts (`label, confidence, box, centre`) — used by Streamlit.
- `track_frame()`: `model.track(persist=True, half=True, imgsz=320, tracker="bytetrack.yaml")` → adds `track_id`; optionally returns Ultralytics' `res0.plot()` image in diagnostic mode. Used by desktop.
- `draw_detections()`: color coding — red for `fire/smoke/no_helmet/no_vest`, orange for `restricted_area_intrusion/worker_fall`, green otherwise; text includes `ID:<tid>`.
- `generate_demo_detections()`: scripted events at processed-frame counts 3/6/9/12 (`DEMO_EVENT_SEQUENCE`) so the full workflow demos without a trained model.

**`zone_monitor.py`** — `validate_zone_coordinates()` (clamp to frame, require x1<x2/y1<y2), `point_in_rectangle()`, `draw_zone()`, `detect_intrusions()` (person centre inside zone).

**`rules.py`**
- `CLASS_ALIASES` + `normalize_class_name()` (lowercase → strip non-alnum → alias map). Handles dataset label variants like `no-hardhat`, `without helmet`.
- `EVENT_RULES`: severity (Low/Medium/High/Critical) + human-readable recommendation per event.
- `INCIDENT_CLASSES`: which labels become incidents (`person`, `helmet`, `safety_vest` are *not* loggable).
- ⚠️ Uses `Dict[str, Dict[str, str]]` annotations **without importing `Dict`** — only safe because of `from __future__ import annotations` (see §6).

**`database.py`** — incidents table schema:
`id, incident_uuid(12-hex), timestamp, event_type, severity, zone, confidence, recommendation, status(Open/Acknowledged/Resolved), evidence_image_path, original_image_path, camera_id, camera_name, camera_location, acknowledged_at, resolved_at, operator_note`.
Functions: `get_connection` (WAL, NORMAL sync, Row factory), `create_incidents_table`, `add_incident`, `read_incidents(severity?, status?)` (ORDER BY timestamp DESC, id DESC), `update_incident_status` (validates against `INCIDENT_STATUSES`).

**`evidence.py`** — `save_incident_frame()` → `evidence/<type>_<yyyymmdd_hhmmss>_<tag>_<8hex>.jpg` via `cv2.imwrite`.

**`config.py`** — all paths (`BASE_DIR`, `MODELS_DIR`, `DATASETS_DIR`, `EVIDENCE_DIR`, `TRAINING_RUNS_DIR`, `TEMP_DIR`, `DATABASE_PATH`) and every tunable: `DEFAULT_MODEL_PATH = models/yolo11m.pt`, `DEFAULT_AI_FPS = 8`, `DEFAULT_IMG_SIZE = 320`, tracker `bytetrack.yaml`, `DEFAULT_CONFIDENCE = 0.5`, stabilizer constants (EMA alpha, hits/misses, hysteresis 0.6/0.35, max-shift 0.5), `FRAME_QUEUE_MAXLEN = 2`, `ALERT_COOLDOWN_SECONDS = 10`, `DEFAULT_ZONE`, `INCIDENT_STATUSES`. Directories are created at import time (also re-created in `main.ensure_project_dirs`).

### 4.3 Desktop backend (`core/`)

**`camera_worker.py`** — `CameraWorker(QThread)` per camera:
- `_open_capture()`: numeric sources try `CAP_DSHOW → CAP_MSMF → CAP_ANY` (Windows reliability), sets `CAP_PROP_BUFFERSIZE=1`; string sources treated as URIs (RTSP/file).
- Loop: read frame → emit at `display_fps` rate (min-emit-interval gate) → on 5 consecutive failures treat as lost → release → reconnect with exponential backoff (2s→30s). Emits `frame_received(camera_id, frame)` and `status_updated(camera_id, status)` (Connecting / Online / No Frame / Reconnecting / Disconnected / Stopped).

**`inference_manager.py`** — `InferenceManager(QThread)`, the heart of the desktop app:
- `submit_frame(camera_id, frame, zone_config)`: under lock, updates `_camera_zones` and appends `(frame, ts)` to a `deque(maxlen=2)`.
- `run()`: loads the base model, then loops at `1/ai_fps`: pops the latest frame per camera → **lazy-creates a dedicated YOLO instance per camera** (tracker state isolation) → `track_frame(...)` (or `generate_demo_detections` in demo/no-model mode) → per-camera `DetectionStabilizer.update()` (skipped in diagnostic mode) → **zone intrusion check**: validates zone against frame size, rescales zone from `ref_width/ref_height` if present, `detect_intrusions()` on persons, and *appends a synthetic detection* with `label="restricted_area_intrusion"` and `zone=<name>` for each hit → annotates frame (Ultralytics plot in diagnostic mode) → attaches debug metadata (camera_id, inference_fps, queue_size, shapes) → `detection_ready.emit(camera_id, stable_detections, annotated)`.
- Diagnostic flags (`diagnostic_mode`, `diagnostic_person_only`) toggle raw-tracker comparison output and DEBUG logging.

**`detection_stabilizer.py`** — `DetectionStabilizer` keyed `camera_id → track_id → TrackState`:
- EMA on box + confidence with per-coordinate clamp (`STABILIZER_MAX_SHIFT_RATIO` of box size — prevents jitter jumps).
- `hits/misses` accounting; track "established" after `required_hits` AND smoothed conf ≥ 0.6.
- Output only visual-confirmed tracks (established OR conf ≥ 0.35); stale tracks removed after `allowed_misses`.
- ⚠️ Detections with `track_id < 0` are **skipped** (untracked detections never reach the output).

**`alert_manager.py`** — `AlertManager.process_detections(camera_id, camera_name, detections, annotated_frame)`:
- Skips labels not in `INCIDENT_CLASSES`; cooldown key = `camera_id:zone_name:label` (default cooldown 10 s).
- Saves the *annotated* frame as evidence → `add_incident(...)` → if severity ∈ {Critical, High} calls `send_sms_alert(...)` (mock) → returns logged incident dicts for the UI panel.
- ⚠️ Camera fields are not persisted (see §6, issue #4).

**`camera_db.py`** — cameras table (`camera_id` unique, `zone_config` JSON text, `analytics_enabled`, `recording_enabled`, etc.). `update_camera()` whitelists columns via `_ALLOWED_CAMERA_COLUMNS` (SQL-injection-safe dynamic SET). Startup `ALTER TABLE ... ADD COLUMN zone_config` migration wrapped in try/except for older DBs.

**`model_utils.py`** — `resolve_model_path()`: first `*.pt` in `models/` (sorted), else first in project root, else `None`. Note: alphabetically `yolo11m.pt` sorts before `yolov8n.pt`, so the heavier YOLOv11-m is picked if both exist.

**`sms_notifier.py`** — mock: prints `[SMS DISPATCHED]: ...` banner + logs. Production would swap in Twilio/AWS SNS.

**`settings_manager.py`** — JSON key/value settings (`settings.json`) with defaults (`theme`, `auto_connect_on_startup`). ⚠️ Currently **instantiated nowhere** — the app reads everything from `config.py` (future feature surface).

### 4.4 Desktop UI (`ui/`)

**`main_window.py`** — `MainWindow(QMainWindow)`:
- Toolbar: Add/Remove Camera, Connect Selected/All, Disconnect Selected/All, Focus Selected, **Draw Restricted Zone**, layout selector (1×1 / 2×2 / 3×3 / 4×4, default 2×2).
- Left: camera list (`QListWidget`, `camera_id` stored in `Qt.UserRole`). Center: tile grid. Right: `AlertPanel`.
- `CameraDiscoveryWorker(QThread)` scans USB indices 0..5 with `CAP_DSHOW`, emits found indices; `_on_camera_discovered()` auto-registers (`CAM-USB-<idx>`, analytics_enabled=True) and auto-connects.
- **Performance caches**: `_camera_config_cache` (avoids per-frame DB reads), `_parsed_zone_cache` (zone JSON parsed once at connect, not per frame), display throttles `_last_frame_display` / `_last_annotation_display` (≥33 ms ≈ 30 FPS cap).
- `on_frame()`: if `analytics_enabled` (cached) → `inference.submit_frame()` with cached zone; else display raw frame directly.
- `on_detections()`: draws annotated frame, updates tile info (top-3 labels), **red flash** if any detection severity is `critical`, then `AlertManager.process_detections()` → adds alerts to panel.
- Zone drawing flow: requires a connected tile with a pixmap → `ZoneDialog` (drag rectangle on scaled pixmap) → saved as JSON into `cameras.zone_config` via `update_camera()` → caches updated.
- `closeEvent()`: disconnect all workers, stop inference manager.

**`camera_tile.py`** — preview QLabel + info label. `show_frame()`: fast path — cv2 aspect-ratio downscale (`INTER_AREA`) → BGR→RGB → `QImage(Format_RGB888)` → pixmap. `set_alert_state(True)` → red border stylesheet + 3 s single-shot QTimer clear. Double-click → maximize toggle signal.

**`alert_panel.py`** — session alert list + Acknowledge/Resolve buttons → `update_incident_status(db_id, "Acknowledged"/"Resolved")` → appends `[ACK]`/`[RESOLVED]` to the row text.

**`camera_dialog.py`** — add-camera form (ID, name, location, source type USB/File/RTSP/HTTP, source path/URL, USB device index, username, enabled, analytics) + `Test Connection` (opens cv2 capture, reports resolution). Note: **no password field** for RTSP auth (use credentials-in-URL).

**`zone_dialog.py`** — `DrawableLabel(QLabel)` with rubber-band rectangle painting (red 3-px pen + 50-alpha fill); `get_zone_data()` returns `{x1,y1,x2,y2, ref_width, ref_height, name}` where ref = the *displayed pixmap* size (enables later rescaling to native frame coords). Minimum 10×10 px.

### 4.5 Training

**`train_custom.py`** — CLI wrapper around `YOLO(...).train()`; defaults: `dataset.yaml`, `yolov8n.pt`, 50 epochs, imgsz 640, output to `training_runs/industrial_safety`. **`dataset.yaml`** expects `datasets/images/train` + `datasets/images/val` with classes 0..6 = person, helmet, safety_vest, no_helmet, no_vest, fire, smoke.

### 4.6 Tests & tools

- `tests/` (pytest; `conftest.py` puts project root on `sys.path`):
  - `test_database.py` — insert/read + status update against tmp-path DBs.
  - `test_rules.py` — alias normalization, unknown-label passthrough, fire=Critical, person not loggable.
  - `test_zone_monitor.py` — point-in-rect + intrusion filtering.
  - `test_model_utils.py` — models-dir preference, root fallback, None when empty.
- `tools/enumerate_cameras.py`, `tools/move_model_to_models.py`, `tools/test_pipeline.py` (12 s headless capture→inference smoke test), and outer `tools/probe_cameras.py` — camera/diagnostic utilities.

---

## 5. Runtime data flow (end-to-end walkthrough)

1. **Startup** — `main.py` → `ensure_project_dirs()` (dirs + both tables) → `MainWindow`:
   - resolves model: `models/*.pt` → root `*.pt` → `config.DEFAULT_MODEL_PATH` → constructs `InferenceManager` and starts the thread (model loads in-thread; per-camera instances created lazily on first frame).
   - background USB scan (0..5) auto-adds and auto-connects discovered cameras.
2. **Capture** — `CameraWorker` reads frames, throttles to `display_fps`, emits `frame_received`.
3. **Handoff** — `MainWindow.on_frame` reads **cached** camera config; if analytics enabled, pushes `(frame, zone)` into the bounded queue (old frames auto-dropped).
4. **Inference loop** (8 FPS target) — latest frame per camera → per-camera YOLO `track()` (imgsz 320, FP16, ByteTrack persist) → stabilizer (EMA + hysteresis + confirmation) → zone rescale + intrusion synthesis → annotation + FPS/debug metadata → `detection_ready` signal.
5. **Display + alerting** (GUI thread) — tile shows the *same* annotated frame the boxes were computed on; critical labels flash the tile red for 3 s; `AlertManager` applies per-(camera,zone,event) cooldown → writes evidence JPG → inserts incident row (status Open) → SMS banner for Critical/High → alert appears in right panel.
6. **Workflow** — operator selects the alert → Acknowledge → Resolve; each button updates `incidents.status` in SQLite. Streamlit's History tab offers the same lifecycle with evidence image preview and filters.

---

## 6. Issues, risks & code smells found during review

### Actual bugs (latent)
1. **Missing typing imports** — `rules.py` (`Dict`), `core/detection_stabilizer.py` (`List`, `Dict`), `ui/main_window.py` (`List`) use typing names that are never imported. These are only harmless because every file has `from __future__ import annotations` (annotations never evaluated). Any use of `typing.get_type_hints()`, dataclass field resolution, or removal of the future-import will raise `NameError`.
2. **Default zone false positives** — in `inference_manager.py`, `zone_cfg = self._camera_zones.get(camera_id, DEFAULT_ZONE)`. Cameras with **no drawn zone silently inherit `DEFAULT_ZONE`** (rectangle 100,100→400,400 at capture resolution), so a person walking through that region triggers intrusions the user never configured. Expected: skip intrusion detection when no zone exists.
3. **`update_incident_status` never sets timestamps** — the `acknowledged_at` / `resolved_at` columns exist but are never written (lifecycle analytics impossible). Similarly `operator_note` and `original_image_path` are unused.
4. **Camera metadata not persisted with incidents** — `AlertManager` receives `camera_name` and knows `camera_id`, but `add_incident()` hardcodes `camera_id/camera_name/camera_location = None`. Incident rows therefore lose which camera produced them (the DB columns exist for exactly this).
5. **Desktop demo mode is unreachable** — `MainWindow` always constructs `InferenceManager(demo_mode=False)`; there is no UI checkbox (README promises one). Demo events only appear if model resolution fails (`model_path=None`). Also, in demo mode the intrusion event uses the **full frame as the zone** (`{"x1":0,...}`), bypassing the drawn zone entirely.
6. **`test_pipeline.py` fragile signal connections** — plain Python functions are connected to QThread signals with no running `QCoreApplication` event loop; delivery relies on direct connections and may drop output or crash depending on PySide6 version.
7. **`refresh_cameras()` ID parsing** — camera list items are round-tripped through display text (`text.split(" — ")`), so a camera *name* containing the em-dash separator corrupts the stored `camera_id`. Should rely solely on `Qt.UserRole`.

### Design risks
8. **N models, N× memory** — one full YOLO instance per connected camera (tracker-state isolation). With YOLOv11-m (~40 MB weights, bigger VRAM) several cameras can exhaust GPU memory. Mitigations: share one model + external tracker (e.g., standalone ByteTrack/supervision), or use smaller weights (yolov8n) for multi-camera.
9. **Model auto-pick can be heavy** — `resolve_model_path` takes the alphabetically-first `*.pt`; `yolo11m.pt` sorts before `yolov8n.pt`, so the *medium* model is used by default when present — slower than the nano the README implies.
10. **Heavy work on the GUI thread** — `AlertManager.process_detections` (evidence `cv2.imwrite`, SQLite insert, SMS) runs inside `on_detections` on the UI thread; a slow disk/DB write will stutter the video grid. (DB is already WAL + `check_same_thread=False`, so a worker thread is feasible.)
11. **`half=True`** in `track_frame` errors or is ignored on CPU-only machines — currently works only because CUDA is mandatory; a CPU fallback (`half=False` when no CUDA) is needed for portability.
12. **No logging strategy** — mixture of `print()`, ad-hoc `logging.debug` (only configured under diagnostic mode), and no file/rotation handlers; production debugging would be hard.
13. **`psutil` is installed but unused** (presumably planned for GPU/CPU/FPS stats in the UI).
14. **Evidence/temp growth unbounded** — evidence JPGs and `temp_uploads` (Streamlit cleans its temp file, evidence never expires) need a retention policy.
15. **`recording_enabled` / `expected_resolution` / `expected_fps` / `username`** columns exist in the cameras table but nothing reads or acts on them (future recording feature stub).
16. **Streamlit deprecations** — `use_container_width=True` is deprecated in newer Streamlit (use `width='stretch'`); the app also blocks the whole script during long analyses (no `st.fragment`/threading).
17. **Zone geometry** — rectangles only, coordinates are absolute pixels with a `ref_*` rescale; per-camera aspect changes (resolution switch mid-stream) can drift the zone; polygon zones would be more expressive.
18. **Inference display sync caveat** — with analytics enabled, the tile displays at inference rate (≈8 FPS), not camera rate; the non-analytics path displays at camera rate. Two different smoothness levels depending on the analytics flag.
19. **`test_pipeline.py` model path** — hardcodes `models/yolov8n.pt`, which is gitignored; the script fails out of the box on a fresh clone.
20. **No index on `incidents(severity)`, `(status)`, `(timestamp)`** — fine for a demo volume, will matter with real history.

---

## 7. Future improvements & requirements (prioritized roadmap)

### P0 — Correctness / must-fix before relying on it
1. Import `Dict`/`List` from `typing` in `rules.py`, `core/detection_stabilizer.py`, `ui/main_window.py` (or drop the annotations) — removes a hidden landmine.
2. Skip intrusion detection when a camera has **no** zone configured (return empty instead of `DEFAULT_ZONE`).
3. Persist camera identity: extend `add_incident(...)` with `camera_id/camera_name/camera_location` and pass them from `AlertManager`; write `acknowledged_at`/`resolved_at` in `update_incident_status` (accept a status-transition guard: Open→Acknowledged→Resolved).
4. Route alert/evidence/DB work off the GUI thread (move `AlertManager.process_detections` into the inference thread or a small worker QThread with its own signals).
5. Fix `refresh_cameras` to rely only on `Qt.UserRole` data.

### P1 — Reliability & operability
6. **Real logging**: module-level `logging` with file + console handlers, rotation, and per-camera tags; replace `print()` calls (also used for errors in `inference_manager`/`main_window`).
7. **CPU/GPU graceful degradation**: detect `torch.cuda.is_available()`; set `half=False`, adjust `imgsz`, and `device` accordingly; surface device name in the status bar.
8. **DB hardening**: indexes on `(timestamp)`, `(status)`, `(severity)`; pagination for history; schema `user_version` migrations instead of `ALTER TABLE` try/except; single shared connection factory per thread.
9. **Evidence lifecycle**: retention policy (e.g., delete evidence older than N days), optionally store images inside a blob/`evidence` folder structure per camera/day; add an evidence viewer to the desktop UI (currently only Streamlit can show evidence).
10. **Config surface**: wire `SettingsManager` into a Settings dialog (model path, ai_fps, imgsz, confidence, cooldown, tracker, theme, auto-connect) instead of constants; add model-path picker for `best.pt`.
11. **Desktop incident history tab** — the README's demo script says "Open the Incident History tab and update status" but the desktop UI only has the session AlertPanel; add a tab/table backed by `read_incidents()` with filters and evidence preview.

### P2 — Feature growth (aligned with README "Next feature set")
12. **PPE compliance scoring**: per-person aggregation of `helmet/no_helmet`, `safety_vest/no_vest` by `track_id` → compliance % per zone/shift; violation *dwell time* before logging (currently any single frame logs).
13. **Incident-linked video clips**: implement `recording_enabled` — ring-buffer the last N seconds per camera (e.g., `cv2.VideoWriter` or a rolling frame buffer) and export an MP4 clip when an incident fires; store `video_path` in a new column.
14. **Reporting dashboard**: shift reports (Open/Acknowledged/Resolved counts, top zones, heatmaps by hour), CSV/PDF export; trend analysis over `timestamp`.
15. **Multi-site / REST API**: FastAPI service exposing incidents/cameras + WebSocket live alerts; the desktop app becomes one client of a central server; token-based auth.
16. **Edge deployment**: export to ONNX / TensorRT (`model.export(format='engine')`), quantization, and per-stream batching to raise FPS per GPU; or Jetson-class targets.
17. **Real notifications**: replace the mock `sms_notifier` with Twilio/AWS SNS/email/Teams webhook behind an abstract `Notifier` interface + retry/backoff + recipient config; move secrets out of code (`settings.json`/env).
18. **Advanced zones**: polygons (shapely point-in-polygon), multiple zones per camera with individual names/severities, one-way tripwires, dwell-time rules.
19. **More events**: `worker_fall` (pose/proximity-to-floor heuristics), loitering, crowd density, PPE-in-zone combinations; per-class confidence thresholds.
20. **Recording & playback UI**: timeline scrubber, event markers on the timeline, snapshot export.

### P3 — Engineering quality
21. **Tests**: add coverage for `DetectionStabilizer` (hit/miss/EMA/clamp), `AlertManager` cooldown (mock evidence+DB), zone rescaling math, and `InferenceManager` demo path; mark model-dependent tests with a `@pytest.mark.slow`/GPU skip.
22. **Type-safety pass**: fix the `Dict/List` imports; run `mypy`/`ruff` in CI; add `pyproject.toml`.
23. **Packaging**: PyInstaller spec (pyinstaller already in dev requirements) bundling weights + models dir; splash screen; NSIS installer.
24. **i18n & theming**: Qt stylesheets (dark theme already default in settings), localization strings for recommendations.
25. **Camera onboarding**: auto-detect RTSP ONVIF profiles; store credentials securely (Windows Credential Manager / keyring); add a password field to `CameraDialog`.

---

## 8. Tuning cheat-sheet (config.py)

| Constant | Default | Effect |
|---|---|---|
| `DEFAULT_AI_FPS` | 8 | Inference loop target rate (desktop) |
| `DEFAULT_DISPLAY_FPS` | 15 | Nominal display cap (tile throttle is 33 ms) |
| `DEFAULT_IMG_SIZE` | 320 | YOLO inference resolution (lower = faster, less accurate) |
| `DEFAULT_CONFIDENCE` | 0.5 | Model confidence gate |
| `FRAME_QUEUE_MAXLEN` | 2 | Bounded per-camera frame queue (latest-wins) |
| `ALERT_COOLDOWN_SECONDS` | 10 | Dedup window per (camera, zone, event) |
| `DEFAULT_SMOOTHING_ALPHA` | 0.30 | EMA weight of the new observation |
| `DEFAULT_REQUIRED_HITS` / `DEFAULT_ALLOWED_MISSES` | 3 / 5 | Track confirmation / persistence |
| `STABILIZER_CONFIDENCE_HIGH/LOW` | 0.60 / 0.35 | Establish / drop hysteresis |
| `STABILIZER_MAX_SHIFT_RATIO` | 0.5 | Max box jump per update (fraction of box size) |
| `TRACKER_CONFIG` | `bytetrack.yaml` | Ultralytics tracker config |
| `DEFAULT_MODEL_PATH` | `models/yolo11m.pt` | Fallback model when no `.pt` is discovered |

---

## 9. Quick reference — who calls whom

```
main.py ──► MainWindow ──► CameraDiscoveryWorker ──► add_camera()/connect_selected()
   │              │
   │              ├─► CameraWorker.frame_received ──► on_frame ──► InferenceManager.submit_frame
   │              │        (QThread, cv2 capture)                      (bounded deque)
   │              │
   │              └─► InferenceManager.detection_ready ──► on_detections
   │                       │  track_frame → DetectionStabilizer → detect_intrusions
   │                       ├─► CameraTile.show_frame / set_alert_state
   │                       └─► AlertManager.process_detections
   │                               ├─► evidence.save_incident_frame
   │                               ├─► database.add_incident
   │                               └─► sms_notifier.send_sms_alert (Critical/High)
   │
   └─► AlertPanel (Acknowledge/Resolve) ──► database.update_incident_status

app.py (Streamlit) ──► load_model/infer_frame → detect_intrusions → save_incident_frame
                   └─► add_incident / read_incidents / update_incident_status
```

### Database tables

**`incidents`**: `id PK`, `incident_uuid`, `timestamp`, `event_type`, `severity`, `zone`, `confidence`, `recommendation`, `status` (Open/Acknowledged/Resolved), `evidence_image_path`, `original_image_path`, `camera_id`, `camera_name`, `camera_location`, `acknowledged_at`, `resolved_at`, `operator_note`.

**`cameras`**: `id PK`, `camera_id UNIQUE`, `name`, `location`, `source_type`, `source`, `username`, `enabled`, `analytics_enabled`, `recording_enabled`, `expected_resolution`, `expected_fps`, `zone_config` (JSON: x1,y1,x2,y2,ref_width,ref_height,name), `created_at`.

---

## 10. How to run / verify (summary)

```powershell
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt            # + CUDA torch wheels (see README)
python main.py                             # desktop live surveillance
streamlit run app.py                       # web upload analysis
python -m pytest tests/ -v                 # unit tests (no GPU needed)
python tools/test_pipeline.py              # headless capture→inference smoke test
python train_custom.py --data dataset.yaml --model yolov8n.pt --epochs 50
```
</arg_value></write_to_file>
</invoke>