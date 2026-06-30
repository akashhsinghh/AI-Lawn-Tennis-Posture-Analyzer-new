"""
image_analyzer.py
===================================================================
Photo pipeline. One picture in -> annotated picture + full report out.

Flow:
    read image -> detect pose (MediaPipe)
               -> measure 12 joint angles across the whole body
               -> compare to the shot's ideal ranges
               -> score + build coaching report
               -> draw skeleton overlay with colour-coded angle labels
===================================================================
"""

import cv2

from pose_detector import PoseDetector
from angle_calculator import compute_all_angles
from analyzer import analyze
from visualizer import draw_analysis


def analyze_image(image_path, shot_key, handedness="right",
                  detector=None, save_path=None):
    """
    Analyse a single photo.

    Parameters
    ----------
    image_path  : path to the input image (JPG or PNG)
    shot_key    : one of 'forehand', 'backhand', 'serve', etc.
    handedness  : 'right' (default) or 'left'
    detector    : re-use an existing PoseDetector (optional, for speed)
    save_path   : write the annotated image here too (optional)

    Returns
    -------
    annotated_bgr : the image with skeleton + angle boxes drawn (numpy array)
    analysis      : the full coaching report dict from analyzer.analyze(...)
                    (analysis["found"] is False if no body was detected)
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    # Reuse a passed-in detector, or create a one-shot one for this photo.
    own_detector = detector is None
    if own_detector:
        detector = PoseDetector(static_image_mode=True, model_complexity=2)

    try:
        det = detector.detect(image)
    finally:
        if own_detector:
            detector.close()

    if not det["found"]:
        analysis = {
            "found": False,
            "shot": shot_key,
            "shot_label": shot_key.replace("_", " ").title(),
            "overall_score": 0,
            "grade": "N/A",
            "summary": ("No body detected. Use a side-on photo with the whole "
                        "player in frame, good lighting and a clear background."),
            "per_angle": {},
            "group_scores": {},
            "top_fixes": [],
            "n_good": 0, "n_off": 0, "n_missing": 0, "n_measured": 0,
        }
        annotated = draw_analysis(image, None, analysis)
        if save_path:
            cv2.imwrite(save_path, annotated)
        return annotated, analysis

    # Measure all 12 joint angles from the normalized landmarks.
    angles = compute_all_angles(det["landmarks_norm"])
    analysis = analyze(angles, shot_key, handedness=handedness)
    analysis["found"] = True

    # Draw the skeleton and angle boxes onto the image.
    annotated = draw_analysis(image, det["landmarks_px"], analysis)
    if save_path:
        cv2.imwrite(save_path, annotated)

    return annotated, analysis
