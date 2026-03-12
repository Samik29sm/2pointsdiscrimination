"""Default body locations and their typical two-point discrimination distances (mm)."""

BODY_LOCATIONS = {
    "Fingertip": {
        "distances": [2, 3, 4, 5, 6, 8, 10, 12, 15, 20],
        "description": "Distal phalanx of index finger",
    },
    "Palm": {
        "distances": [5, 8, 10, 12, 15, 18, 20, 25, 30],
        "description": "Center of palm",
    },
    "Forearm": {
        "distances": [15, 20, 25, 30, 35, 40, 45, 50],
        "description": "Volar surface of forearm",
    },
    "Upper Arm": {
        "distances": [25, 30, 35, 40, 45, 50, 55, 60],
        "description": "Lateral surface of upper arm",
    },
    "Back": {
        "distances": [30, 35, 40, 45, 50, 55, 60, 65, 70],
        "description": "Upper back between shoulder blades",
    },
    "Lip": {
        "distances": [2, 3, 4, 5, 6, 8, 10],
        "description": "Lower lip",
    },
    "Forehead": {
        "distances": [10, 15, 20, 25, 30, 35, 40],
        "description": "Center of forehead",
    },
    "Cheek": {
        "distances": [8, 10, 12, 15, 18, 20, 25],
        "description": "Cheek area",
    },
}

DEFAULT_LOCATION = "Fingertip"
