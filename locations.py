"""Default body locations and their typical two-point discrimination distances (mm)."""

BODY_LOCATIONS = {
    "Fingertip": {
        "distances": [2, 3, 4, 5, 6, 8, 10, 12, 15, 20],
        "typical_threshold": "2–4 mm",
        "description": "Distal phalanx of index finger",
    },
    "Palm": {
        "distances": [5, 8, 10, 12, 15, 18, 20, 25, 30],
        "typical_threshold": "8–12 mm",
        "description": "Center of palm",
    },
    "Forearm": {
        "distances": [15, 20, 25, 30, 35, 40, 45, 50],
        "typical_threshold": "30–40 mm",
        "description": "Volar surface of forearm",
    },
    "Upper Arm": {
        "distances": [25, 30, 35, 40, 45, 50, 55, 60],
        "typical_threshold": "40–50 mm",
        "description": "Lateral surface of upper arm",
    },
    "Back": {
        "distances": [30, 35, 40, 45, 50, 55, 60, 65, 70],
        "typical_threshold": "40–60 mm",
        "description": "Upper back between shoulder blades",
    },
    "Lip": {
        "distances": [2, 3, 4, 5, 6, 8, 10],
        "typical_threshold": "4–6 mm",
        "description": "Lower lip",
    },
    "Forehead": {
        "distances": [10, 15, 20, 25, 30, 35, 40],
        "typical_threshold": "20–25 mm",
        "description": "Center of forehead",
    },
    "Cheek": {
        "distances": [8, 10, 12, 15, 18, 20, 25],
        "typical_threshold": "15–20 mm",
        "description": "Cheek area",
    },
}

DEFAULT_LOCATION = "Fingertip"
