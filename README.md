# 🎾 AI Lawn Tennis Posture Analyzer

An AI posture-analysis engine for **lawn tennis**, built like the **Cricket
Analyzer** in PostureExpert: a player uploads a **photo or video** of a shot,
the engine maps the body with pose estimation, measures **10 joint angles**
across the whole body, compares them with the **ideal angles** for that shot,
and returns a **scored, colour-coded coaching report** with plain-English
feedback.

Built for the DEVDECAGON / Team 6 project. Covers all six shots:
**Forehand · Backhand · Serve · Drop Shot · Volley · Overhead Smash**

---

## 1. The 10 angles measured

MediaPipe Pose gives 33 body landmarks. We keep the 10 angles that genuinely
describe a tennis stroke **and** are reliable in a single photo, grouped into
three body regions:

### Legs & Base (2 angles)
| # | Angle | What it shows |
|---|-------|---------------|
| 1 | Left Hip – **Knee** – Ankle | Left knee bend |
| 2 | Right Hip – **Knee** – Ankle | Right knee bend |

### Arms & Racket (6 angles)
| # | Angle | What it shows |
|---|-------|---------------|
| 3 | Left Hip – **Shoulder** – Elbow | How far the left arm is lifted |
| 4 | Right Hip – **Shoulder** – Elbow | How far the right arm is lifted |
| 5 | Left Shoulder – **Elbow** – Wrist | Left elbow bend |
| 6 | Right Shoulder – **Elbow** – Wrist | Right elbow bend (racket arm) |
| 7 | Left Elbow – **Wrist** – Hand | Left wrist angle |
| 8 | Right Elbow – **Wrist** – Hand | **Right wrist angle** |

### Torso & Balance (2 angles)
| # | Angle | What it shows |
|---|-------|---------------|
| 9 | Left Shoulder – **Hip** – Knee | Left-side torso lean |
|10 | Right Shoulder – **Hip** – Knee | Right-side torso lean |

> **Why 10 and not "all 32"?** MediaPipe gives hundreds of possible 3-point
> angles, but most are meaningless (e.g. nose-ear-eye) or duplicate one another.
> These 10 are the ones coaches actually use. We deliberately **dropped the
> ankle/foot angle**: the toe landmark is the least reliable point in a clothed,
> side-on photo, so it added noise rather than insight. Every angle that remains
> is meaningful and trustworthy.

---

## 2. What changed (latest version)

| Area | Before | After |
|------|--------|-------|
| Angles measured | 6 | **10** (wrists + arm-lift added, noisy ankle removed) |
| Right wrist angle | ❌ missing | ✅ tracked |
| Right-side panel | Plain text | **Ideal ranges + clean angle-comparison table** |
| Comparison table | Dark, low-contrast | **High-contrast: pale tint + solid colour pills, readable** |
| Coaching report | Short text | **Full grouped breakdown with exact fixes** |
| Near-misses | 1° out = flagged red | **±3° tolerance** so tiny misses stay "good" |
| Scoring | Equal weight | **Weighted** (knees/elbows/torso count more than wrist/arm-lift) |
| Video output | Broken inline player (empty 0:00) | **Reliable download** of the annotated clip |
| Skeleton drawn | Arms + torso + legs | **+ hands + feet** |

---

## 3. How it works

```
Photo / Video
    │
    ▼
Pose detection (MediaPipe; model_complexity=2 for photos)
    │   ── 33 body landmarks (x, y, visibility)
    ▼
angle_calculator.py   ── 10 joint angles (degrees)
    │
    ▼
analyzer.py           ── compare to shot_standards.py targets (+ ±3° tolerance)
    │                    ── weighted score per angle → overall score
    │                    ── group scores (3 body regions)
    │                    ── top_fixes (worst joints, sorted)
    ▼
visualizer.py         ── draw skeleton + colour-coded angle boxes
    │                    ── green = good, red = off-range
    ▼
app.py (Streamlit)    ── left:  annotated image (+ download)
                         right: ideal ranges + your-angle comparison table
                         below: full grouped coaching report
```

For a **video**, the engine analyses every frame and automatically picks the
**contact frame** (serve/smash: highest wrist; others: wrist furthest from the
body), scores that frame, and lets you download the annotated clip.

---

## 4. Install

You need **Python 3.9–3.11** (MediaPipe does not yet support 3.12+ on all
platforms; 3.10 or 3.11 is safest).

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

---

## 5. Run the web app

```bash
cd tennis_engine
streamlit run app.py
```

Open http://localhost:8501.

**Using the app:**
1. Pick the shot in the left sidebar
2. Choose handedness (right / left)
3. **📷 Photo** tab → upload your shot → **Analyze photo**
4. **Left** → your body with all 10 angles drawn in colour (+ download button)
5. **Right** → ideal ranges + your-angle-vs-ideal comparison table
6. **Below** → full coaching report grouped by Legs, Arms, Torso
7. **🎬 Video** tab → upload a clip → analysis runs on the contact frame, and
   the annotated clip is offered as a download

---

## 6. Run the CLI

```bash
python main_cli.py --shot forehand --image my_forehand.jpg
python main_cli.py --shot backhand --video bh.mp4 --hand left --out bh_out.mp4
python main_cli.py --list
```

---

## 7. Run the logic tests (no MediaPipe needed)

```bash
python test_logic.py
```

All logic checks should pass in under a second with no camera required.

---

## 8. Calibrating the ideal ranges (Phase 3)

The numbers in `shot_standards.py` are biomechanics-based starting values.
Your Phase 3 produces the real, professional-data-backed numbers:

1. Collect MediaPipe angle readings from 10–20 professional videos per shot
2. For each of the 10 angles, compute **min**, **mean** (ideal), **max**
3. Paste those three numbers into `shot_standards.py`
4. Optionally adjust `weight` (0.4–1.0) if a joint proves noisy in your data

The `±3°` measurement tolerance lives in `analyzer.py` as `GRACE_DEGREES` —
raise or lower it if you want stricter or more forgiving scoring.

---

## 9. File map

| File | Role |
|------|------|
| `app.py` | Streamlit web UI (comparison table + coaching report) |
| `angle_calculator.py` | Angle maths + the 10-angle definitions |
| `analyzer.py` | Scoring, grading, tolerance, coaching-report builder |
| `shot_standards.py` | Ideal angle targets for all 6 shots |
| `visualizer.py` | OpenCV drawing (skeleton + angle labels) |
| `image_analyzer.py` | Photo pipeline |
| `video_analyzer.py` | Video pipeline |
| `pose_detector.py` | MediaPipe wrapper |
| `main_cli.py` | Command-line runner |
| `test_logic.py` | Unit tests (no camera needed) |
| `requirements.txt` | Python dependencies |
