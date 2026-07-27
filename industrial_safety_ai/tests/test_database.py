from pathlib import Path

from database import create_incidents_table, add_incident, read_incidents, update_incident_status


def test_add_and_read_incident(tmp_path: Path):
    db = tmp_path / "test.db"
    create_incidents_table(db)
    row_id = add_incident(
        event_type="fire",
        severity="Critical",
        zone="Zone A",
        confidence=0.95,
        recommendation="Evacuate",
        evidence_image_path="/fake/path.jpg",
        db_path=db,
    )
    assert row_id > 0
    incidents = read_incidents(db_path=db)
    assert len(incidents) == 1
    assert incidents[0]["event_type"] == "fire"
    assert incidents[0]["status"] == "Open"


def test_update_status(tmp_path: Path):
    db = tmp_path / "test.db"
    create_incidents_table(db)
    row_id = add_incident(
        event_type="smoke",
        severity="Critical",
        zone="Zone B",
        confidence=0.80,
        recommendation="Inspect",
        evidence_image_path="/fake/path.jpg",
        db_path=db,
    )
    update_incident_status(row_id, "Acknowledged", db_path=db)
    incidents = read_incidents(db_path=db)
    assert incidents[0]["status"] == "Acknowledged"
