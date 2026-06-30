"""
shot_standards.py
===================================================================
The "perfect form" reference numbers.

For every shot we store, for each of the 10 angles, a target window:
    {"min": ..., "ideal": ..., "max": ..., "weight": ...}   (degrees)

  - min / ideal / max : if the player's angle is between min and max the
    joint is in good shape; the closer to `ideal`, the better.
  - weight : how much this joint counts toward the overall score.
        1.0 = primary, structural angle (knees, elbows, torso) - these
              are the most reliable and matter most.
        0.5-0.6 = secondary angle (wrist, arm-lift). Useful detail, but
              noisier in a 2-D photo, so it counts less. Still measured,
              shown and graded - it just cannot wreck a good score alone.

A small tolerance (see GRACE_DEGREES in analyzer.py) is applied on top
of these windows, so a joint that is only 1-2 degrees outside is still
treated as good - pose estimation is never pixel-perfect.

-------------------------------------------------------------------
IMPORTANT - PLEASE CALIBRATE THESE WITH YOUR PHASE 3 DATA
-------------------------------------------------------------------
These numbers are *sensible starting values* from general tennis
biomechanics for a RIGHT-HANDED player at the KEY moment of the shot
(contact / point of execution). They are NOT measured from one specific
professional and will not be perfect for every camera angle.

Left-handed players are handled automatically by the analyzer, which
mirrors the left/right targets - you do NOT need a separate table.
===================================================================
"""

# Helper so the table below stays short and readable.
# w defaults to 1.0 (primary). Pass a smaller w for secondary angles.
def _a(mn, ideal, mx, w=1.0):
    return {"min": mn, "ideal": ideal, "max": mx, "weight": w}


SHOT_STANDARDS = {

    "forehand": {
        "label": "Forehand",
        "moment": "point of contact",
        "tips": "Driven groundstroke on the racket side. Look for a stable, "
                "slightly bent base and the racket arm extending into the ball.",
        "angles": {
            "left_hip_knee_ankle":        _a(150, 168, 180),       # front leg fairly straight
            "right_hip_knee_ankle":       _a(130, 152, 175),       # back/drive leg loaded
            "left_hip_shoulder_elbow":    _a(20,  55,  110, 0.5),  # non-racket arm out for balance
            "right_hip_shoulder_elbow":   _a(25,  60,  115, 0.5),  # racket arm swung forward
            "left_shoulder_elbow_wrist":  _a(30,  70,  120),       # non-dominant arm tucked
            "right_shoulder_elbow_wrist": _a(115, 140, 165),       # racket arm extending
            "left_elbow_wrist_index":     _a(120, 155, 180, 0.5),
            "right_elbow_wrist_index":    _a(120, 150, 180, 0.5),  # firm, slightly laid-back wrist
            "left_shoulder_hip_knee":     _a(150, 167, 180),       # torso upright-ish
            "right_shoulder_hip_knee":    _a(150, 167, 180),
        },
    },

    "backhand": {
        "label": "Backhand (two-handed)",
        "moment": "point of contact",
        "tips": "Both arms drive a two-handed backhand, so the two elbow angles "
                "are fairly similar. Keep a bent, balanced base.",
        "angles": {
            "left_hip_knee_ankle":        _a(140, 160, 178),
            "right_hip_knee_ankle":       _a(135, 156, 175),
            "left_hip_shoulder_elbow":    _a(20,  50,  100, 0.5),
            "right_hip_shoulder_elbow":   _a(20,  50,  100, 0.5),
            "left_shoulder_elbow_wrist":  _a(90,  125, 160),
            "right_shoulder_elbow_wrist": _a(85,  120, 158),
            "left_elbow_wrist_index":     _a(120, 155, 180, 0.5),
            "right_elbow_wrist_index":    _a(120, 155, 180, 0.5),
            "left_shoulder_hip_knee":     _a(145, 165, 180),
            "right_shoulder_hip_knee":    _a(145, 165, 180),
        },
    },

    "serve": {
        "label": "Serve",
        "moment": "point of contact (full extension)",
        "tips": "At contact the body is fully stretched up: legs driving "
                "straight, racket arm almost straight overhead.",
        "angles": {
            "left_hip_knee_ankle":        _a(150, 170, 180),
            "right_hip_knee_ankle":       _a(150, 170, 180),
            "left_hip_shoulder_elbow":    _a(20,  90,  170, 0.4),  # tossing arm: very variable
            "right_hip_shoulder_elbow":   _a(120, 150, 175, 0.6),  # hitting arm raised high
            "left_shoulder_elbow_wrist":  _a(30,  90,  160),       # tossing arm coming down
            "right_shoulder_elbow_wrist": _a(150, 170, 180),       # hitting arm near straight
            "left_elbow_wrist_index":     _a(110, 150, 180, 0.4),
            "right_elbow_wrist_index":    _a(130, 160, 180, 0.5),  # wrist snapping over the ball
            "left_shoulder_hip_knee":     _a(155, 172, 180),
            "right_shoulder_hip_knee":    _a(155, 172, 180),
        },
    },

    "drop_shot": {
        "label": "Drop Shot",
        "moment": "point of contact",
        "tips": "A soft, controlled touch. Knees bent to get low, racket arm "
                "only moderately extended with a gentle, short motion.",
        "angles": {
            "left_hip_knee_ankle":        _a(135, 158, 178),
            "right_hip_knee_ankle":       _a(135, 158, 178),
            "left_hip_shoulder_elbow":    _a(20,  50,  105, 0.5),
            "right_hip_shoulder_elbow":   _a(20,  55,  105, 0.5),
            "left_shoulder_elbow_wrist":  _a(40,  90,  140),
            "right_shoulder_elbow_wrist": _a(110, 138, 168),
            "left_elbow_wrist_index":     _a(120, 155, 180, 0.5),
            "right_elbow_wrist_index":    _a(110, 145, 180, 0.5),  # soft, open wrist for touch
            "left_shoulder_hip_knee":     _a(150, 167, 180),
            "right_shoulder_hip_knee":    _a(150, 167, 180),
        },
    },

    "volley": {
        "label": "Volley",
        "moment": "point of contact",
        "tips": "Compact punch near the net. Clearly bent knees for a low "
                "centre of gravity, short firm arm action, little backswing.",
        "angles": {
            "left_hip_knee_ankle":        _a(120, 150, 175),
            "right_hip_knee_ankle":       _a(120, 150, 175),
            "left_hip_shoulder_elbow":    _a(20,  50,  95,  0.5),
            "right_hip_shoulder_elbow":   _a(20,  50,  95,  0.5),
            "left_shoulder_elbow_wrist":  _a(90,  125, 162),
            "right_shoulder_elbow_wrist": _a(105, 135, 165),
            "left_elbow_wrist_index":     _a(120, 155, 180, 0.5),
            "right_elbow_wrist_index":    _a(120, 155, 180, 0.5),  # firm, blocked wrist
            "left_shoulder_hip_knee":     _a(145, 164, 180),
            "right_shoulder_hip_knee":    _a(145, 164, 180),
        },
    },

    "overhead_smash": {
        "label": "Overhead Smash",
        "moment": "point of contact (full extension)",
        "tips": "Like a serve during a rally. Full upward stretch at contact: "
                "legs and racket arm extended, body tall.",
        "angles": {
            "left_hip_knee_ankle":        _a(150, 170, 180),
            "right_hip_knee_ankle":       _a(150, 170, 180),
            "left_hip_shoulder_elbow":    _a(20,  90,  170, 0.4),
            "right_hip_shoulder_elbow":   _a(120, 150, 175, 0.6),
            "left_shoulder_elbow_wrist":  _a(30,  90,  160),
            "right_shoulder_elbow_wrist": _a(150, 170, 180),
            "left_elbow_wrist_index":     _a(110, 150, 180, 0.4),
            "right_elbow_wrist_index":    _a(130, 160, 180, 0.5),
            "left_shoulder_hip_knee":     _a(155, 173, 180),
            "right_shoulder_hip_knee":    _a(155, 173, 180),
        },
    },
}


# Shots that reach UP at contact (used by the video module to find the
# contact frame as the moment the racket wrist is highest).
OVERHEAD_SHOTS = {"serve", "overhead_smash"}


def list_shots():
    """Return the internal shot keys, e.g. ['forehand', 'backhand', ...]."""
    return list(SHOT_STANDARDS.keys())


def shot_label(shot_key):
    """Pretty name for a shot key."""
    return SHOT_STANDARDS[shot_key]["label"]


def get_standard(shot_key):
    """Return the full standard dict for one shot. Raises KeyError if unknown."""
    if shot_key not in SHOT_STANDARDS:
        raise KeyError(
            f"Unknown shot '{shot_key}'. Valid shots: {list_shots()}"
        )
    return SHOT_STANDARDS[shot_key]
