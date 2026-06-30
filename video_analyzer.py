"""
video_analyzer.py
===================================================================
Video pipeline. A clip in -> annotated clip + coaching report on the
contact frame.

A tennis clip has many frames, but the shot is "made" at one moment -
the point of contact. We:
    1. Run pose detection on every frame and store the 12 angles.
    2. Find the CONTACT frame:
         - serve / smash -> the frame where the racket wrist is highest
         - other shots   -> the frame where the racket wrist reaches
                           furthest from the hips (arm extended to ball)
    3. Score that contact frame against the shot's targets.
    4. Write an annotated video (skeleton + angles on every frame, with
       the contact frame clearly marked).
===================================================================
"""

import cv2
import numpy as np

from pose_detector import PoseDetector
from angle_calculator import (
    compute_all_angles, ANGLE_DEFS,
    RIGHT_WRIST, LEFT_WRIST,
    RIGHT_HIP, LEFT_HIP,
)
from analyzer import analyze
from visualizer import draw_analysis
from shot_standards import OVERHEAD_SHOTS


def _wrist_index(handedness):
    """Which wrist is the racket (dominant) wrist."""
    return RIGHT_WRIST if handedness == "right" else LEFT_WRIST


def _find_contact_frame(frames_data, shot_key, handedness):
    """
    Pick the index of the contact frame from the processed frame list.

    frames_data : list of per-frame dicts, each:
        {"found": bool, "landmarks_norm": [...] or None, "angles": {...}}

    Returns an int index (0-based), or None if no usable frame.
    """
    wrist = _wrist_index(handedness)
    best_idx = None

    if shot_key in OVERHEAD_SHOTS:
        # Highest wrist = smallest y (image y grows downward).
        best_y = None
        for i, fd in enumerate(frames_data):
            if not fd["found"]:
                continue
            wy = fd["landmarks_norm"][wrist][1]
            if best_y is None or wy < best_y:
                best_y, best_idx = wy, i
    else:
        # Wrist furthest from the mid-hip point (arm reaching to the ball).
        best_dist = None
        for i, fd in enumerate(frames_data):
            if not fd["found"]:
                continue
            lm = fd["landmarks_norm"]
            wx, wy = lm[wrist][0], lm[wrist][1]
            hip_x = (lm[LEFT_HIP][0] + lm[RIGHT_HIP][0]) / 2.0
            hip_y = (lm[LEFT_HIP][1] + lm[RIGHT_HIP][1]) / 2.0
            dist = np.hypot(wx - hip_x, wy - hip_y)
            if best_dist is None or dist > best_dist:
                best_dist, best_idx = dist, i

    return best_idx


def analyze_video(video_path, shot_key, handedness="right",
                  out_path=None, sample_every=1, model_complexity=1):
    """
    Analyse a tennis video.

    Parameters
    ----------
    video_path   : input clip path
    shot_key     : e.g. "serve"
    handedness   : "right" or "left"
    out_path     : where to write the annotated .mp4 (optional)
    sample_every : analyse every Nth frame for the angle search
                   (the OUTPUT video still contains every frame).
                   Use 2 or 3 to speed up long clips.
    model_complexity : 0 fast / 1 balanced / 2 most accurate

    Returns
    -------
    {
      "found": bool,
      "analysis": <full coaching report for the contact frame>,
      "contact_frame_index": int,
      "contact_frame_image": annotated BGR of the contact frame,
      "angle_timeline": {angle_name: [v0, v1, ...]},
      "fps": float,
      "n_frames": int,
      "out_path": str or None
    }
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    detector = PoseDetector(static_image_mode=False,
                            model_complexity=model_complexity)

    # First pass: read every frame, detect pose, store landmarks + all 12 angles.
    frames_bgr  = []
    frames_data = []
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames_bgr.append(frame)

            if idx % sample_every == 0:
                det = detector.detect(frame)
                if det["found"]:
                    angles = compute_all_angles(det["landmarks_norm"])
                    frames_data.append({
                        "found": True,
                        "landmarks_norm": det["landmarks_norm"],
                        "landmarks_px":   det["landmarks_px"],
                        "angles":         angles,
                    })
                else:
                    frames_data.append({"found": False,
                                        "landmarks_norm": None,
                                        "landmarks_px":   None,
                                        "angles":         None})
            else:
                frames_data.append({"found": False,
                                    "landmarks_norm": None,
                                    "landmarks_px":   None,
                                    "angles":         None})
            idx += 1
    finally:
        cap.release()

    n_frames = len(frames_bgr)
    if n_frames == 0:
        detector.close()
        raise ValueError("Video had no frames.")

    # Find the contact frame and score it.
    contact_idx = _find_contact_frame(frames_data, shot_key, handedness)

    if contact_idx is None:
        detector.close()
        analysis = {
            "found": False,
            "shot": shot_key,
            "shot_label": shot_key.replace("_", " ").title(),
            "overall_score": 0,
            "grade": "N/A",
            "summary": ("No body detected in any frame. Film side-on with the "
                        "whole player in frame and good lighting."),
            "per_angle": {},
            "group_scores": {},
            "top_fixes": [],
            "n_good": 0, "n_off": 0, "n_missing": 0, "n_measured": 0,
        }
        return {
            "found": False, "analysis": analysis,
            "contact_frame_index": None, "contact_frame_image": None,
            "angle_timeline": {}, "fps": fps, "n_frames": n_frames,
            "out_path": None,
        }

    contact  = frames_data[contact_idx]
    analysis = analyze(contact["angles"], shot_key, handedness=handedness)
    analysis["found"] = True

    contact_img = draw_analysis(frames_bgr[contact_idx],
                                contact["landmarks_px"], analysis)

    # Build the angle timeline (12 angles across every frame).
    timeline = {name: [] for name in ANGLE_DEFS}
    for fd in frames_data:
        for name in ANGLE_DEFS:
            timeline[name].append(
                None if fd["angles"] is None else fd["angles"][name]
            )

    # Second pass: write the annotated output video (every frame).
    if out_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
        for i, frame in enumerate(frames_bgr):
            fd = frames_data[i]
            if fd["found"]:
                a = analyze(fd["angles"], shot_key, handedness=handedness)
                a["found"] = True
                drawn = draw_analysis(frame, fd["landmarks_px"], a)
            else:
                drawn = frame
            if i == contact_idx:
                cv2.putText(drawn, ">> CONTACT FRAME (analysed) <<",
                            (20, height - 25), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 165, 255), 2, cv2.LINE_AA)
            writer.write(drawn)
        writer.release()

    detector.close()

    return {
        "found":               True,
        "analysis":            analysis,
        "contact_frame_index": contact_idx,
        "contact_frame_image": contact_img,
        "angle_timeline":      timeline,
        "fps":                 fps,
        "n_frames":            n_frames,
        "out_path":            out_path,
    }
