"""
pose_detector.py
===================================================================
The "eyes". A thin wrapper around MediaPipe Pose.

Give it an image (a normal OpenCV BGR frame) and it returns the 33
body landmarks. We keep both:
  - normalized landmarks (x,y in 0..1)   -> used for angle maths
  - pixel landmarks (x,y in pixels)       -> used for drawing

We create ONE PoseDetector and reuse it for every frame of a video
(creating a new MediaPipe model per frame is slow).
===================================================================
"""

import cv2
import mediapipe as mp


class PoseDetector:
    def __init__(self,
                 static_image_mode=False,
                 model_complexity=1,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5):
        """
        static_image_mode:
            False -> treat inputs as a video stream (faster, smoother).
            True  -> treat every call as an unrelated photo.
        model_complexity: 0 (fast) / 1 (balanced) / 2 (most accurate).
        """
        self.mp_pose = mp.solutions.pose
        self.mp_draw = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, image_bgr):
        """
        Run pose detection on one BGR image.

        Returns a dict:
            {
              "found": bool,
              "landmarks_norm": [(x, y, visibility), ...] or None,  # 0..1
              "landmarks_px":   [(x_px, y_px, visibility), ...] or None,
              "raw": the MediaPipe results object (for advanced drawing)
            }
        """
        h, w = image_bgr.shape[:2]
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        results = self.pose.process(image_rgb)

        if not results.pose_landmarks:
            return {"found": False, "landmarks_norm": None,
                    "landmarks_px": None, "raw": results}

        norm, px = [], []
        for lm in results.pose_landmarks.landmark:
            vis = lm.visibility
            norm.append((lm.x, lm.y, vis))
            px.append((int(lm.x * w), int(lm.y * h), vis))

        return {"found": True, "landmarks_norm": norm,
                "landmarks_px": px, "raw": results}

    def close(self):
        """Release the MediaPipe model. Call when completely done."""
        self.pose.close()

    # Allow use as a context manager:  with PoseDetector() as d: ...
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
