from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
from typing import Any

import cv2
import pandas as pd
import streamlit as st
from PIL import Image

from config import (
    APP_TITLE,
    ALERT_COOLDOWN_SECONDS,
    DEFAULT_CONFIDENCE,
    DEFAULT_FRAME_SKIP,
    DEFAULT_MODEL_PATH,
    DEFAULT_STATUS,
    DEFAULT_ZONE,
    INCIDENT_STATUSES,
    SUPPORTED_VIDEO_FORMATS,
    DATABASE_PATH,
    TEMP_DIR,
)
from database import add_incident, create_incidents_table, read_incidents, update_incident_status
from detector import draw_detections, generate_demo_detections, infer_frame, load_model
from evidence import save_incident_frame
from rules import is_loggable_incident, normalize_class_name, recommendation_for_event, severity_for_event
from zone_monitor import detect_intrusions, draw_zone, validate_zone_coordinates
from core.sms_notifier import send_sms_alert


st.set_page_config(page_title=APP_TITLE, layout="wide")


@st.cache_resource(show_spinner=False)
def get_cached_model(model_path: str) -> Any:
    return load_model(model_path)


def save_uploaded_video(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower()
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=TEMP_DIR)
    temp_file.write(uploaded_file.getbuffer())
    temp_file.flush()
    temp_file.close()
    return Path(temp_file.name)


def is_supported_video(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_VIDEO_FORMATS


def format_incidents_dataframe(incidents: list[dict[str, Any]]) -> pd.DataFrame:
    if not incidents:
        return pd.DataFrame(
            columns=[
                "id",
                "timestamp",
                "event_type",
                "severity",
                "zone",
                "confidence",
                "recommendation",
                "status",
                "evidence_image_path",
            ]
        )
    return pd.DataFrame(incidents)


def _current_summary_frame(incidents: list[dict[str, Any]]) -> pd.DataFrame:
    if not incidents:
        return pd.DataFrame(
            columns=["id", "event_type", "severity", "zone", "confidence", "status", "timestamp"]
        )
    return pd.DataFrame(
        [
            {
                "id": item["id"],
                "event_type": item["event_type"],
                "severity": item["severity"],
                "zone": item["zone"],
                "confidence": item["confidence"],
                "status": item["status"],
                "timestamp": item["timestamp"],
            }
            for item in incidents
        ]
    )


def _event_key(event_type: str, zone_name: str) -> str:
    return f"{normalize_class_name(event_type)}:{zone_name.strip().lower()}"


def _active_incident_counts(incidents: list[dict[str, Any]]) -> tuple[int, int, int]:
    open_count = sum(1 for item in incidents if item.get("status") == "Open")
    acknowledged_count = sum(1 for item in incidents if item.get("status") == "Acknowledged")
    resolved_count = sum(1 for item in incidents if item.get("status") == "Resolved")
    return open_count, acknowledged_count, resolved_count


def process_video(
    video_path: Path,
    model_path: str,
    confidence_threshold: float,
    frame_skip: int,
    zone: dict[str, int],
    progress_placeholder,
    frame_placeholder,
    alert_placeholder,
    active_incidents_placeholder,
    details_placeholder,
    summary_placeholder,
    use_demo_mode: bool,
) -> list[dict[str, Any]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Unable to open the selected video file.")

    model = None
    demo_mode_active = use_demo_mode
    if not demo_mode_active:
        try:
            model = get_cached_model(model_path)
        except FileNotFoundError as exc:
            cap.release()
            raise FileNotFoundError(
                f"{exc}. Enable demo mode or provide a trained custom best.pt file."
            ) from exc
    else:
        try:
            model = get_cached_model(model_path)
        except FileNotFoundError:
            demo_mode_active = True

    processed_incidents: list[dict[str, Any]] = []
    latest_logged_time: dict[str, datetime] = {}
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    frame_index = 0
    processed_frame_index = 0
    incident_counter = 0
    last_alert_message = "No incident detected yet."
    last_event_summary: dict[str, Any] | None = None

    def render_active_incidents() -> None:
        summary_df = _current_summary_frame(processed_incidents)
        if summary_df.empty:
            active_incidents_placeholder.info("No active incidents logged in this analysis run yet.")
        else:
            active_incidents_placeholder.dataframe(summary_df, use_container_width=True, hide_index=True)

        open_count, acknowledged_count, resolved_count = _active_incident_counts(processed_incidents)
        st.caption(f"Open: {open_count} | Acknowledged: {acknowledged_count} | Resolved: {resolved_count}")

        if last_event_summary:
            details_placeholder.markdown(
                "\n".join(
                    [
                        f"**Current Alert:** {last_event_summary['event_type'].replace('_', ' ').title()}",
                        f"**Risk Level:** {last_event_summary['severity']}",
                        f"**Recommended Action:** {last_event_summary['recommendation']}",
                        f"**Confidence:** {last_event_summary['confidence']:.2f}",
                        f"**Zone:** {last_event_summary['zone']}",
                        f"**Date and Time:** {last_event_summary['timestamp']}",
                    ]
                )
            )
        else:
            details_placeholder.info("Waiting for the first incident in the current analysis run.")

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_index += 1
        if frame_skip > 1 and frame_index % frame_skip != 0:
            continue

        frame_height, frame_width = frame.shape[:2]
        try:
            validated_zone = validate_zone_coordinates(zone, frame_width, frame_height)
        except ValueError as exc:
            cap.release()
            raise ValueError(str(exc)) from exc

        processed_frame_index += 1
        if demo_mode_active:
            detections = generate_demo_detections(frame, processed_frame_index, validated_zone)
        else:
            detections = infer_frame(model, frame, confidence_threshold)

        annotated_frame = draw_zone(frame, validated_zone)
        annotated_frame = draw_detections(annotated_frame, detections)
        intrusion_detections = detect_intrusions(detections, validated_zone)

        current_time = datetime.now()

        def _log_single_incident(event_type: str, detection: dict) -> dict | None:
            """Check cooldown, save evidence, write to DB, return incident record or None."""
            nonlocal incident_counter, last_alert_message, last_event_summary
            key = _event_key(event_type, validated_zone["name"])
            last_logged = latest_logged_time.get(key)
            if last_logged is not None:
                if (current_time - last_logged).total_seconds() < ALERT_COOLDOWN_SECONDS:
                    return None

            incident_counter += 1
            severity = severity_for_event(event_type)
            recommendation = recommendation_for_event(event_type)
            evidence_path = save_incident_frame(
                annotated_frame, event_type, f"frame{frame_index}_{incident_counter}"
            )
            incident_id = add_incident(
                event_type=event_type,
                severity=severity,
                zone=validated_zone["name"],
                confidence=float(detection.get("confidence", 0.0)),
                recommendation=recommendation,
                evidence_image_path=str(evidence_path),
                status=DEFAULT_STATUS,
            )
            latest_logged_time[key] = current_time
            if severity.lower() in {"critical", "high"}:
                send_sms_alert(
                    f"ALERT: {event_type.replace('_', ' ').title()} detected in {validated_zone['name']}."
                )
            last_alert_message = f"{event_type.replace('_', ' ').title()} detected in {validated_zone['name']}"
            last_event_summary = {
                "event_type": event_type,
                "severity": severity,
                "recommendation": recommendation,
                "confidence": round(float(detection.get("confidence", 0.0)), 2),
                "zone": validated_zone["name"],
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            return {
                "id": incident_id,
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": event_type,
                "severity": severity,
                "zone": validated_zone["name"],
                "confidence": round(float(detection.get("confidence", 0.0)), 2),
                "recommendation": recommendation,
                "status": DEFAULT_STATUS,
                "evidence_image_path": str(evidence_path),
            }

        # Log restricted-area intrusions
        for detection in intrusion_detections:
            record = _log_single_incident("restricted_area_intrusion", detection)
            if record:
                processed_incidents.append(record)

        # Log other safety incidents (no_helmet, fire, smoke, etc.)
        for detection in detections:
            normalized_label = normalize_class_name(detection.get("label", ""))
            if normalized_label == "person":
                continue
            if normalized_label in {"helmet", "safety_vest"}:
                continue
            if not is_loggable_incident(normalized_label):
                continue
            record = _log_single_incident(normalized_label, detection)
            if record:
                processed_incidents.append(record)

        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, caption=f"Processed frame {frame_index}", use_container_width=True)
        if processed_incidents:
            alert_placeholder.error(last_alert_message)
        else:
            alert_placeholder.info("No active incidents detected yet.")

        render_active_incidents()

        if total_frames > 0:
            progress_placeholder.progress(min(frame_index / total_frames, 1.0))
        else:
            progress_placeholder.progress(0.0)

    cap.release()
    summary_placeholder.success(f"Processing finished. Logged {len(processed_incidents)} new incident(s).")
    return processed_incidents


def render_history_tab() -> None:
    st.subheader("Incident History")
    try:
        severity_filter = st.selectbox("Filter by severity", ["All", "Low", "Medium", "High", "Critical"], key="severity_filter")
        status_filter = st.selectbox("Filter by status", ["All", *INCIDENT_STATUSES], key="status_filter")
        incidents = read_incidents(
            severity=None if severity_filter == "All" else severity_filter,
            status=None if status_filter == "All" else status_filter,
        )
        df = format_incidents_dataframe(incidents)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if not df.empty:
            incident_ids = df["id"].tolist()
            selected_incident_id = st.selectbox("Select incident ID", incident_ids)
            selected_row = df[df["id"] == selected_incident_id].iloc[0]
            evidence_path = selected_row.get("evidence_image_path", "")
            if evidence_path and Path(evidence_path).exists():
                st.image(Image.open(evidence_path), caption=f"Evidence for incident {selected_incident_id}", use_container_width=True)
            else:
                st.info("Evidence image not found for the selected incident.")

            current_status = selected_row.get("status", DEFAULT_STATUS)
            new_status = st.selectbox("Update status", INCIDENT_STATUSES, index=INCIDENT_STATUSES.index(current_status) if current_status in INCIDENT_STATUSES else 0)
            if st.button("Save status update", key="save_status"):
                update_incident_status(int(selected_incident_id), new_status)
                st.success("Incident status updated.")
                st.rerun()
    except Exception as exc:
        st.error(f"Unable to load incident history: {exc}")


def render_analysis_tab() -> None:
    st.subheader("Analyse Video")
    st.write("Upload a video and choose either the default `yolov8n.pt` checkpoint or a custom `best.pt` safety model.")
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "avi", "mov", "mkv"])

    model_path_value = st.text_input(
        "Model path",
        value=str(DEFAULT_MODEL_PATH),
        help="Use the default YOLO checkpoint or point to a custom best.pt file trained for safety classes.",
    )
    use_demo_mode = st.checkbox(
        "Enable demo mode when no trained custom model is available",
        value=False,
        help="Uses scripted sample incidents so the final demo can still show all required events.",
    )
    confidence_threshold = st.slider("Confidence threshold", 0.1, 1.0, float(DEFAULT_CONFIDENCE), 0.05)
    frame_skip = st.slider("Frame skip", 1, 10, int(DEFAULT_FRAME_SKIP), 1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        zone_x1 = st.number_input("Zone X1", min_value=0, value=int(DEFAULT_ZONE["x1"]))
    with col2:
        zone_y1 = st.number_input("Zone Y1", min_value=0, value=int(DEFAULT_ZONE["y1"]))
    with col3:
        zone_x2 = st.number_input("Zone X2", min_value=0, value=int(DEFAULT_ZONE["x2"]))
    with col4:
        zone_y2 = st.number_input("Zone Y2", min_value=0, value=int(DEFAULT_ZONE["y2"]))

    zone_name = st.text_input("Zone name", value=DEFAULT_ZONE["name"])

    if uploaded_file is not None:
        st.video(uploaded_file)

    start_clicked = st.button("Start analysis", type="primary", disabled=uploaded_file is None)

    frame_placeholder = st.empty()
    alert_placeholder = st.empty()
    details_placeholder = st.empty()
    active_incidents_placeholder = st.empty()
    progress_placeholder = st.empty()
    summary_placeholder = st.empty()

    if start_clicked and uploaded_file is not None:
        if not is_supported_video(uploaded_file.name):
            st.error("Unsupported video format. Please upload MP4, AVI, MOV, or MKV.")
            return

        try:
            create_incidents_table()
            video_path = save_uploaded_video(uploaded_file)
            zone = {
                "x1": int(zone_x1),
                "y1": int(zone_y1),
                "x2": int(zone_x2),
                "y2": int(zone_y2),
                "name": zone_name.strip() or DEFAULT_ZONE["name"],
            }
            process_video(
                video_path=video_path,
                model_path=model_path_value,
                confidence_threshold=float(confidence_threshold),
                frame_skip=int(frame_skip),
                zone=zone,
                progress_placeholder=progress_placeholder,
                frame_placeholder=frame_placeholder,
                alert_placeholder=alert_placeholder,
                active_incidents_placeholder=active_incidents_placeholder,
                details_placeholder=details_placeholder,
                summary_placeholder=summary_placeholder,
                use_demo_mode=use_demo_mode,
            )
        except FileNotFoundError as exc:
            st.error(str(exc))
        except ValueError as exc:
            st.error(str(exc))
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected error during processing: {exc}")
        finally:
            # Clean up temp video file
            try:
                if video_path.exists():
                    video_path.unlink()
            except Exception:
                pass


def main() -> None:
    st.title(APP_TITLE)
    st.caption("First milestone: video upload, person detection, intrusion detection, and incident logging.")

    create_incidents_table(DATABASE_PATH)

    analyse_tab, history_tab = st.tabs(["Analyse Video", "Incident History"])
    with analyse_tab:
        render_analysis_tab()
    with history_tab:
        render_history_tab()


if __name__ == "__main__":
    main()
