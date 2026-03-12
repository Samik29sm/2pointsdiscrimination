"""Default body locations and their typical two-point discrimination distances (mm).

``average_threshold`` is the literature-based mean two-point discrimination
threshold (mm) for each location.  Adjust these values to match the population
or reference you are working with; they are used to spread control trials
across the expected trial range.
"""

BODY_LOCATIONS = {
    "Fingertip of index finger": {
        "distances": [1, 2, 3, 4, 5, 6, 8, 10],
        "description": "Center around fingertip, middle of the finger",
        "average_threshold": 3,  # mm – typical fingertip threshold (Weinstein 1968)
    },
    "Palm": {
        "distances": [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 18, 20, 22, 26, 30, 35, 40],
        "description": "Center of thenar hypothenar axis (middle between thumb and pinky pad, deepest point of hand",
        "average_threshold": 12,  # mm – typical palm threshold
    },
    "Ventral forearm": {
        "distances": [2, 4, 6, 8, 10, 12, 14, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 39, 42, 45, 48, 52, 55, 60, 70],
        "description": "Midpoint between elbow and wrist",
        "average_threshold": 35,  # mm – typical ventral forearm threshold
    },
    "Lower back": {
        "distances": [2, 4, 6, 8, 10, 12, 14, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 39, 42, 45, 48, 52, 55, 60, 70],
        "description": "Above the posterior iliac spine (bony prominences/holes at the sides to the spine)",
        "average_threshold": 42,  # mm – typical lower-back threshold
    },
    "Lower leg": {
        "distances": [2, 4, 6, 8, 10, 12, 14, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 39, 42, 45, 48, 52, 55, 60, 70],
        "description": "Medial side of the leg, right below and side to tiberial tuberosity (bony prominence at sides to knee)",
        "average_threshold": 36,  # mm – typical lower-leg threshold
    },
    "Foot sole": {
        "distances": [2, 4, 6, 8, 10, 12, 14, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 45, 48, 51, 55, 60],
        "description": "Center of the medial longitudinal arch (curved inner arch of the foot running from heel to ball along inside edge)",
        "average_threshold": 22,  # mm – typical foot-sole threshold
    }
}


DEFAULT_LOCATION = "Fingertip of index finger"
