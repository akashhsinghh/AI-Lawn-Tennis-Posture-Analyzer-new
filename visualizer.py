"""
visualizer.py
===================================================================
The "artist". Draws the analysis on top of the player's image:
orange skeleton lines (now including hands and feet), glowing joint
dots, and a small dark box at each measured joint showing the angle.

Each angle box is GREEN when the joint is inside the ideal range and
RED when it is out of range, so the player instantly sees what is
right and what to fix.

Because we now measure 12 joints, labels for LEFT-side angles are
nudged to the left of the joint and RIGHT-side angles to the right,
which keeps the boxes from piling on top of each other.
===================================================================
"""

import cv2

from angle_calculator import (
    ANGLE_VERTEX,
    LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW,
    LEFT_WRIST, RIGHT_WRIST, LEFT_INDEX, RIGHT_INDEX,
    LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE,
    LEFT_ANKLE, RIGHT_ANKLE, LEFT_HEEL, RIGHT_HEEL,
    LEFT_FOOT, RIGHT_FOOT,
)

# Colours are BGR (OpenCV order), not RGB.
ORANGE = (0, 165, 255)
WHITE  = (255, 255, 255)
GREEN  = (60, 200, 80)
RED    = (60, 60, 230)
DARK   = (35, 30, 25)

# The bones we draw (pairs of landmark indices).
SKELETON = [
    # arms + hands
    (LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (LEFT_WRIST, LEFT_INDEX),
    (RIGHT_SHOULDER, RIGHT_ELBOW), (RIGHT_ELBOW, RIGHT_WRIST), (RIGHT_WRIST, RIGHT_INDEX),
    # shoulders + torso
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_HIP), (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    # legs + feet
    (LEFT_HIP, LEFT_KNEE), (LEFT_KNEE, LEFT_ANKLE),
    (LEFT_ANKLE, LEFT_HEEL), (LEFT_ANKLE, LEFT_FOOT), (LEFT_HEEL, LEFT_FOOT),
    (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
    (RIGHT_ANKLE, RIGHT_HEEL), (RIGHT_ANKLE, RIGHT_FOOT), (RIGHT_HEEL, RIGHT_FOOT),
]

# Joints we mark with a dot.
JOINTS = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW,
          LEFT_WRIST, RIGHT_WRIST, LEFT_INDEX, RIGHT_INDEX,
          LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE,
          LEFT_ANKLE, RIGHT_ANKLE, LEFT_FOOT, RIGHT_FOOT]


def _draw_label(img, text, anchor, ok, scale=0.5):
    """Draw a small dark box with the angle text at `anchor`."""
    x, y = anchor
    font = cv2.FONT_HERSHEY_SIMPLEX
    thick = 1
    (tw, th), base = cv2.getTextSize(text, font, scale, thick)
    pad = 5

    # Keep the box inside the image.
    x = max(3, min(x, img.shape[1] - tw - 2 * pad - 3))
    y = max(th + pad + 3, min(y, img.shape[0] - 3))

    top_left = (x, y - th - 2 * pad)
    bot_right = (x + tw + 2 * pad, y)

    cv2.rectangle(img, top_left, bot_right, DARK, -1)
    border = GREEN if ok else RED
    cv2.rectangle(img, top_left, bot_right, border, 2)
    cv2.putText(img, text, (x + pad, y - pad), font, scale, WHITE, thick,
                cv2.LINE_AA)


def draw_analysis(image_bgr, landmarks_px, analysis):
    """
    Return a copy of the image with skeleton + angle boxes drawn.

    landmarks_px : list of (x_px, y_px, visibility)
    analysis     : the dict returned by analyzer.analyze(...)
    """
    img = image_bgr.copy()
    if landmarks_px is None:
        cv2.putText(img, "No body detected", (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, RED, 2, cv2.LINE_AA)
        return img

    def pt(idx):
        return (landmarks_px[idx][0], landmarks_px[idx][1])

    # 1) skeleton bones
    for a, b in SKELETON:
        cv2.line(img, pt(a), pt(b), ORANGE, 3, cv2.LINE_AA)

    # 2) glowing joint dots (white core + orange ring)
    for j in JOINTS:
        cv2.circle(img, pt(j), 6, ORANGE, -1, cv2.LINE_AA)
        cv2.circle(img, pt(j), 3, WHITE, -1, cv2.LINE_AA)

    # 3) angle boxes at each measured vertex (every angle we could read)
    per_angle = analysis.get("per_angle", {})
    for name, info in per_angle.items():
        if info["value"] is None:
            continue
        vertex_idx = ANGLE_VERTEX[name]
        vx, vy = pt(vertex_idx)
        ok = (info["status"] == "good")
        text = f"{int(round(info['value']))}deg"
        # Spread labels out: left-side angles to the left, right to the right.
        if name.startswith("left_"):
            anchor = (vx - 70, vy - 6)
        else:
            anchor = (vx + 12, vy - 6)
        _draw_label(img, text, anchor, ok)

    # 4) score banner (top-left)
    score = analysis.get("overall_score", 0)
    grade = analysis.get("grade", "")
    label = analysis.get("shot_label", "")
    banner = f"{label}  |  Score: {score}/100  ({grade})"
    (tw, th), _ = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.rectangle(img, (10, 10), (10 + tw + 20, 10 + th + 20), DARK, -1)
    cv2.rectangle(img, (10, 10), (10 + tw + 20, 10 + th + 20), ORANGE, 2)
    cv2.putText(img, banner, (20, 10 + th + 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2, cv2.LINE_AA)

    return img
