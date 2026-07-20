# Real-Time AI Surveillance and Safety Guidance System for Industrial Workplaces

A simple college-level prototype for industrial workplace surveillance using Streamlit, OpenCV, and Ultralytics YOLO.

## First milestone

This version focuses on:

- Video upload
- Person detection
- Restricted-zone intrusion detection
- Severity classification
- Recommended action display
- SQLite incident logging
- Incident history review

## What the final demo shows

The app is designed to demonstrate these cases during the final viva or presentation:

- Person entering a restricted area
- Worker without helmet
- Fire or smoke detection
- Severity classification
- Recommended safety action
- Evidence-image capture
- Incident database entry
- Acknowledge and resolve workflow

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

Training stays outside the Streamlit app. Use `train_custom.py` when you are ready to train:

```powershell
python train_custom.py --data dataset.yaml --model yolov8n.pt --epochs 50 --imgsz 640
```

After training, point the Streamlit model path field to the generated `best.pt` file.

### Demo mode

If a trained custom model is not available, enable the demo mode checkbox in the app.
It uses scripted sample incidents to show the complete workflow without changing the restricted-zone feature.

Demo mode is useful for:

- Final presentation rehearsal
- Showing the database and evidence capture flow
- Demonstrating incident status updates

## Project structure

- `app.py` - Streamlit dashboard and video processing workflow
- `detector.py` - YOLO loading, inference, and detection parsing
- `zone_monitor.py` - Restricted-zone validation and intrusion checks
- `rules.py` - Severity and recommendation rules
- `database.py` - SQLite helper functions
- `evidence.py` - Evidence image saving helpers
- `config.py` - Shared defaults and paths
- `train_custom.py` - Template for training a custom YOLO model
- `dataset.yaml` - Custom dataset class map

## Run setup on Windows

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the app:

```powershell
streamlit run app.py
```

## How to test

Use a short MP4 video of an industrial or lab walkway if available.

Suggested checks:

1. Upload a video and confirm it plays inside Streamlit.
2. Set the restricted zone and verify intrusion logging.
3. Enable demo mode if no trained custom model exists.
4. Confirm evidence images are saved in `evidence/`.
5. Open the Incident History tab and update status from `Open` to `Acknowledged` and then `Resolved`.
6. Check that incident rows appear in `incidents.db`.

## Final demonstration steps

1. Start the app with `streamlit run app.py`.
2. Upload a video or use demo mode.
3. Set the restricted zone over a visible walkway or work area.
4. Run analysis and show the restricted-area intrusion alert.
5. Continue the video until the no-helmet, fire, and smoke demo incidents appear.
6. Open the Incident History tab and show the database records, evidence image, and status update workflow.

## Likely viva questions

Q1. Why did you use YOLO?

A1. YOLO gives fast real-time object detection, which fits video-based workplace monitoring.

Q2. Why keep risk classification rule-based?

A2. A rule-based approach is simpler, easier to explain in viva, and suitable for a college prototype.

Q3. What does the restricted-zone logic do?

A3. It checks whether the centre of a detected person box enters the user-defined rectangle.

Q4. How do you avoid repeated alerts?

A4. The app uses a cooldown dictionary so the same event and zone are not logged on every frame.

Q5. Why save evidence images?

A5. Evidence helps supervisors review what happened and supports the incident record.

Q6. How do you update incident status?

A6. The Incident History tab lets you change a row from Open to Acknowledged or Resolved.

Q7. What happens if no custom model is available?

A7. Demo mode creates sample incidents so the full project flow can still be demonstrated.

Q8. Can the model be retrained from Streamlit?

A8. No. Training stays in `train_custom.py` so the app remains simple and stable.

Q9. Why use SQLite?

A9. SQLite is lightweight, easy to set up, and good for a single-machine college project.

Q10. How can the project be extended later?

A10. The current structure can later support PPE rules, better custom YOLO weights, and webcam input.

## Notes

- If `models/yolov8n.pt` does not exist, the app can still fall back to the Ultralytics pretrained `yolov8n.pt` checkpoint.
- The model path field in Streamlit accepts either a default checkpoint name or a full path to a custom `best.pt` file.
- The database file `incidents.db` is created automatically when the app runs.
- Evidence images are saved in `evidence/`.
- If a custom model is unavailable during the demo, use the demo mode checkbox to show the end-to-end workflow.

## Next feature set

After the first milestone works, extend the same structure for:

- PPE detection
- Fire and smoke detection
- Webcam input
- Custom YOLO model integration
