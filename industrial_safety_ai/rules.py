from __future__ import annotations

import re
from typing import Any, Dict


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
    "machinery_hazard",
    "overcrowding",
    "obstruction",
    "trip_hazard",
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
    "fall": "worker_fall",
    "worker fall": "worker_fall",
    "trip": "trip_hazard",
    "congestion": "overcrowding",
}

# -------------------------------------------------------------------------
# Comprehensive 5-Tier Industrial Safety Threat Hierarchy (DEFCON 1 to 5)
# -------------------------------------------------------------------------
THREAT_LEVELS: Dict[str, Dict[str, Any]] = {
    "Critical": {
        "level": 1,
        "name": "CRITICAL EMERGENCY",
        "code": "DEFCON 1",
        "color": "#EF4444",
        "accent": "#DC2626",
        "glow": "rgba(239, 68, 68, 0.35)",
        "icon": "🚨",
        "description": "Immediate catastrophic life safety or fire threat. Emergency procedures activated.",
    },
    "High": {
        "level": 2,
        "name": "SEVERE HAZARD",
        "code": "DEFCON 2",
        "color": "#F97316",
        "accent": "#EA580C",
        "glow": "rgba(249, 115, 22, 0.30)",
        "icon": "🚷",
        "description": "Restricted zone perimeter breach or machinery hazard. Security alert dispatched.",
    },
    "Medium": {
        "level": 3,
        "name": "ELEVATED RISK",
        "code": "DEFCON 3",
        "color": "#F59E0B",
        "accent": "#D97706",
        "glow": "rgba(245, 158, 11, 0.25)",
        "icon": "⚠️",
        "description": "PPE non-compliance (missing helmet / vest). Supervisor notification required.",
    },
    "Low": {
        "level": 4,
        "name": "GUARDED ADVISORY",
        "code": "DEFCON 4",
        "color": "#06B6D4",
        "accent": "#0891B2",
        "glow": "rgba(6, 182, 212, 0.20)",
        "icon": "ℹ️",
        "description": "Minor safety advisory, pathway obstruction, or loitering.",
    },
    "Info": {
        "level": 5,
        "name": "NORMAL / SECURE",
        "code": "DEFCON 5",
        "color": "#10B981",
        "accent": "#059669",
        "glow": "rgba(16, 185, 129, 0.20)",
        "icon": "🛡️",
        "description": "All zones monitored. Zero active safety breaches.",
    },
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
    "machinery_hazard": {
        "severity": "High",
        "recommendation": (
            "Halt machinery operation immediately. Clear perimeter and inspect safety interlocks."
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
    "overcrowding": {
        "severity": "Low",
        "recommendation": "Disperse excess personnel to maintain safe passage and emergency egress routes.",
    },
    "obstruction": {
        "severity": "Low",
        "recommendation": "Clear the walkway or emergency exit pathway of foreign objects.",
    },
    "trip_hazard": {
        "severity": "Low",
        "recommendation": "Secure loose cabling or floor obstacles immediately.",
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


def get_threat_level_meta(severity: str) -> Dict[str, Any]:
    """Return styling and metadata for a threat severity level."""
    s = str(severity).title()
    return THREAT_LEVELS.get(s, THREAT_LEVELS["Info"])


def compute_system_threat_level(active_severities: list[str]) -> Dict[str, Any]:
    """Compute the overall plant-wide threat DEFCON level based on active unresolved threats."""
    ranks = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    lowest_rank = 5
    highest_sev = "Info"
    for s in active_severities:
        s_clean = str(s).lower()
        rank = ranks.get(s_clean, 5)
        if rank < lowest_rank:
            lowest_rank = rank
            highest_sev = str(s).title()
    return THREAT_LEVELS.get(highest_sev, THREAT_LEVELS["Info"])
