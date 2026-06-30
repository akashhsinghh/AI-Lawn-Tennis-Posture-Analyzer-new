"""
angle_calculator.py
===================================================================
The maths layer of the engine.

It knows:
  1. Which MediaPipe body points (landmarks) we care about.
  2. How every project angle is built from those points.
  3. How to turn 3 points into an angle in degrees.

This file has NO MediaPipe dependency on its own (only numpy), so it is
easy to unit-test. The pose_detector feeds it landmark coordinates.

-------------------------------------------------------------------
WHY 10 ANGLES (not 6, not "all 32")
-------------------------------------------------------------------
MediaPipe Pose gives 33 body points (index 0..32). You could form
hundreds of 3-point angles, but most are meaningless (eye-ear-nose) or
duplicate information. We keep the 10 angles that genuinely describe a
tennis stroke AND are reliable in a single photo:

    legs    : both knees
    arms    : both shoulders (arm lift), both elbows, both wrists
    torso   : both sides

We deliberately dropped the ankle/foot angle: the toe landmark is the
least reliable point in a clothed, side-on photo, and the shin-vs-foot
angle is not something coaches score - it added noise, not insight.
Removing it makes every remaining angle meaningful and trustworthy.
===================================================================
"""

import numpy as np

# -------------------------------------------------------------------
# MediaPipe Pose returns 33 landmarks. These are the index numbers of
# the joints we use. (Full list: MediaPipe Pose documentation.)
# -------------------------------------------------------------------
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW,    RIGHT_ELBOW    = 13, 14
LEFT_WRIST,    RIGHT_WRIST    = 15, 16
LEFT_INDEX,    RIGHT_INDEX    = 19, 20    # hand (index-finger knuckle)
LEFT_HIP,      RIGHT_HIP      = 23, 24
LEFT_KNEE,     RIGHT_KNEE     = 25, 26
LEFT_ANKLE,    RIGHT_ANKLE    = 27, 28
LEFT_HEEL,     RIGHT_HEEL     = 29, 30    # used for drawing the foot only
LEFT_FOOT,     RIGHT_FOOT     = 31, 32    # used for drawing the foot only

# -------------------------------------------------------------------
# The 10 angles the engine measures.
# Each angle is (point_A, VERTEX, point_C); the angle is measured AT
# the vertex (the middle joint). Order = legs -> arms -> torso, so
# tables and overlays read top-to-bottom in a sensible way.
# -------------------------------------------------------------------
ANGLE_DEFS = {
    # ---- legs / base ----
    "left_hip_knee_ankle":        (LEFT_HIP,      LEFT_KNEE,     LEFT_ANKLE),
    "right_hip_knee_ankle":       (RIGHT_HIP,     RIGHT_KNEE,    RIGHT_ANKLE),
    # ---- shoulders (how far the upper arm is lifted from the torso) ----
    "left_hip_shoulder_elbow":    (LEFT_HIP,      LEFT_SHOULDER, LEFT_ELBOW),
    "right_hip_shoulder_elbow":   (RIGHT_HIP,     RIGHT_SHOULDER,RIGHT_ELBOW),
    # ---- arms (elbow bend) ----
    "left_shoulder_elbow_wrist":  (LEFT_SHOULDER, LEFT_ELBOW,    LEFT_WRIST),
    "right_shoulder_elbow_wrist": (RIGHT_SHOULDER,RIGHT_ELBOW,   RIGHT_WRIST),
    # ---- wrists (wrist cock / lay-back) ----
    "left_elbow_wrist_index":     (LEFT_ELBOW,    LEFT_WRIST,    LEFT_INDEX),
    "right_elbow_wrist_index":    (RIGHT_ELBOW,   RIGHT_WRIST,   RIGHT_INDEX),
    # ---- torso / balance ----
    "left_shoulder_hip_knee":     (LEFT_SHOULDER, LEFT_HIP,      LEFT_KNEE),
    "right_shoulder_hip_knee":    (RIGHT_SHOULDER,RIGHT_HIP,     RIGHT_KNEE),
}

# Human-readable names for reports / on-screen labels.
ANGLE_LABELS = {
    "left_hip_knee_ankle":        "Left Hip-Knee-Ankle (left knee bend)",
    "right_hip_knee_ankle":       "Right Hip-Knee-Ankle (right knee bend)",
    "left_hip_shoulder_elbow":    "Left Hip-Shoulder-Elbow (left arm lift)",
    "right_hip_shoulder_elbow":   "Right Hip-Shoulder-Elbow (right arm lift)",
    "left_shoulder_elbow_wrist":  "Left Shoulder-Elbow-Wrist (left arm)",
    "right_shoulder_elbow_wrist": "Right Shoulder-Elbow-Wrist (right arm)",
    "left_elbow_wrist_index":     "Left Elbow-Wrist-Hand (left wrist)",
    "right_elbow_wrist_index":    "Right Elbow-Wrist-Hand (right wrist)",
    "left_shoulder_hip_knee":     "Left Shoulder-Hip-Knee (left torso)",
    "right_shoulder_hip_knee":    "Right Shoulder-Hip-Knee (right torso)",
}

# Short, friendly names for the compact comparison table.
ANGLE_SHORT = {
    "left_hip_knee_ankle":        "Left knee bend",
    "right_hip_knee_ankle":       "Right knee bend",
    "left_hip_shoulder_elbow":    "Left arm lift",
    "right_hip_shoulder_elbow":   "Right arm lift",
    "left_shoulder_elbow_wrist":  "Left arm (elbow)",
    "right_shoulder_elbow_wrist": "Right arm (elbow)",
    "left_elbow_wrist_index":     "Left wrist",
    "right_elbow_wrist_index":    "Right wrist",
    "left_shoulder_hip_knee":     "Left torso lean",
    "right_shoulder_hip_knee":    "Right torso lean",
}

# What body part each angle is about (drives the wording of tips).
ANGLE_KIND = {
    "left_hip_knee_ankle":        "knee",
    "right_hip_knee_ankle":       "knee",
    "left_hip_shoulder_elbow":    "shoulder",
    "right_hip_shoulder_elbow":   "shoulder",
    "left_shoulder_elbow_wrist":  "elbow",
    "right_shoulder_elbow_wrist": "elbow",
    "left_elbow_wrist_index":     "wrist",
    "right_elbow_wrist_index":    "wrist",
    "left_shoulder_hip_knee":     "torso",
    "right_shoulder_hip_knee":    "torso",
}

# Body region each angle belongs to (used to group the detailed report).
ANGLE_GROUP = {
    "knee":     "Legs & Base",
    "shoulder": "Arms & Racket",
    "elbow":    "Arms & Racket",
    "wrist":    "Arms & Racket",
    "torso":    "Torso & Balance",
}

# Display order of the groups in the report.
GROUP_ORDER = ["Legs & Base", "Arms & Racket", "Torso & Balance"]

# The vertex joint of each angle (used to decide WHERE to draw the label).
ANGLE_VERTEX = {name: triple[1] for name, triple in ANGLE_DEFS.items()}


def group_of(angle_name):
    """Return the body-region group for an angle name."""
    return ANGLE_GROUP[ANGLE_KIND[angle_name]]


def short_label(angle_name):
    """Compact, friendly name for tables."""
    return ANGLE_SHORT.get(angle_name, angle_name)


def calculate_angle(a, b, c):
    """
    Return the angle (in degrees) at point b, formed by the points a-b-c.

    a, b, c are each an (x, y) pair. The result is always between 0 and 180.

    The maths:
      1. Make two vectors: ba = a - b  and  bc = c - b
      2. cos(angle) = (ba . bc) / (|ba| * |bc|)
      3. angle = arccos(...), then convert radians -> degrees
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)

    ba = a - b
    bc = c - b

    denom = (np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom == 0:
        return None  # two points landed on top of each other; angle undefined

    cosine = np.dot(ba, bc) / denom
    cosine = np.clip(cosine, -1.0, 1.0)        # guard against tiny float errors
    angle = np.degrees(np.arccos(cosine))
    return float(angle)


def compute_all_angles(landmarks, min_visibility=0.3):
    """
    Given a list of landmarks, compute all 10 angles.

    `landmarks` is a list of objects/tuples that each have at least
    (x, y) and optionally a `visibility`. We accept either:
        - a list of (x, y) or (x, y, visibility) tuples, OR
        - a list of objects with .x, .y, .visibility (MediaPipe style).

    Returns a dict: { angle_name: value_in_degrees or None }.
    A value is None if a required joint is missing / low confidence,
    so noisy or off-screen joints simply drop out instead of lying.
    """
    def get_xy(idx):
        lm = landmarks[idx]
        # MediaPipe landmark object?
        if hasattr(lm, "x"):
            vis = getattr(lm, "visibility", 1.0)
            if vis is not None and vis < min_visibility:
                return None
            return (lm.x, lm.y)
        # plain tuple/list
        if len(lm) >= 3:
            x, y, vis = lm[0], lm[1], lm[2]
            if vis is not None and vis < min_visibility:
                return None
            return (x, y)
        return (lm[0], lm[1])

    results = {}
    for name, (ia, ib, ic) in ANGLE_DEFS.items():
        pa, pb, pc = get_xy(ia), get_xy(ib), get_xy(ic)
        if pa is None or pb is None or pc is None:
            results[name] = None
        else:
            results[name] = calculate_angle(pa, pb, pc)
    return results
