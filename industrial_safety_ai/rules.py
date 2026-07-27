from __future__ import annotations

import re


SUPPORTED_MODEL_LABELS = (
    "person",
    "helmet",
    "safety_vest",
    "no_helmet",
    "no_vest",
    "fire",
    "smoke",
)

INCIDENT_CLASSES = {
    "restricted_area_intrusion",
    "no_helmet",
    "no_vest",
    "fire",
    "smoke",
    "worker_fall",
}

CLASS_ALIASES = {
    "no hardhat": "no_helmet",
    "no-hardhat": "no_helmet",
    "no_hardhat": "no_helmet",
    "no hard hat": "no_helmet",
    "without helmet": "no_helmet",
    "without_helmet": "no_helmet",
    "no helmet": "no_helmet",
    "no helmet detected": "no_helmet",
    "hardhat missing": "no_helmet",
    "no vest": "no_vest",
    "no-vest": "no_vest",
    "no_vest": "no_vest",
    "without vest": "no_vest",
    "without_vest": "no_vest",
    "safety vest": "safety_vest",
    "safety-vest": "safety_vest",
    "safety_vest": "safety_vest",
    "safety helmet": "helmet",
    "safety-helmet": "helmet",
    "helmet": "helmet",
    "fire": "fire",
    "smoke": "smoke",
    "person": "person",
}


EVENT_RULES: Dict[str, Dict[str, str]] = {
    "person": {
        "severity": "Low",
        "recommendation": "Monitor the worker and continue standard site supervision.",
    },
    "helmet": {
        "severity": "Low",
        "recommendation": "Helmet detected. Continue monitoring the worker and keep the safety check active.",
    },
    "safety_vest": {
        "severity": "Low",
        "recommendation": "Safety vest detected. Continue monitoring the worker and keep the safety check active.",
    },
    "restricted_area_intrusion": {
        "severity": "High",
        "recommendation": (
            "Warn the person, notify security, and verify whether the person is authorised to enter the area."
        ),
    },
    "no_helmet": {
        "severity": "Medium",
        "recommendation": (
            "Notify the worker and site supervisor. Allow entry only after the worker wears the required safety helmet."
        ),
    },
    "no_vest": {
        "severity": "Medium",
        "recommendation": (
            "Notify the worker and supervisor and ask the worker to wear the required safety vest."
        ),
    },
    "fire": {
        "severity": "Critical",
        "recommendation": (
            "Verify the camera feed, notify the fire and safety team, restrict entry, and begin the approved emergency procedure if confirmed."
        ),
    },
    "smoke": {
        "severity": "Critical",
        "recommendation": (
            "Verify the camera feed, notify the safety team, inspect the zone, and begin the approved emergency procedure if confirmed."
        ),
    },
    "worker_fall": {
        "severity": "Critical",
        "recommendation": (
            "Notify first-aid personnel, stop nearby work if safe, and verify the worker's condition."
        ),
    },
}

DEFAULT_RULE = {
    "severity": "Low",
    "recommendation": "Review the camera feed and follow site safety procedures.",
}


def normalize_class_name(label: str) -> str:
    cleaned = label.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return CLASS_ALIASES.get(cleaned, cleaned)


def get_event_rule(event_type: str) -> Dict[str, str]:
    key = normalize_class_name(event_type)
    return EVENT_RULES.get(key, DEFAULT_RULE)


def severity_for_event(event_type: str) -> str:
    return get_event_rule(event_type)["severity"]


def recommendation_for_event(event_type: str) -> str:
    return get_event_rule(event_type)["recommendation"]


def is_loggable_incident(event_type: str) -> bool:
    return normalize_class_name(event_type) in INCIDENT_CLASSES
