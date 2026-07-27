from zone_monitor import point_in_rectangle, detect_intrusions


def test_point_inside_zone():
    zone = {"x1": 100, "y1": 100, "x2": 400, "y2": 400}
    assert point_in_rectangle((250, 250), zone)


def test_point_outside_zone():
    zone = {"x1": 100, "y1": 100, "x2": 400, "y2": 400}
    assert not point_in_rectangle((50, 50), zone)


def test_detect_intrusions_finds_person_in_zone():
    zone = {"x1": 0, "y1": 0, "x2": 500, "y2": 500}
    detections = [
        {"label": "person", "centre": [250, 250], "confidence": 0.9, "box": [200, 200, 300, 300]},
        {"label": "helmet", "centre": [250, 250], "confidence": 0.8, "box": [200, 200, 300, 300]},
    ]
    intrusions = detect_intrusions(detections, zone)
    assert len(intrusions) == 1
    assert intrusions[0]["label"] == "person"
