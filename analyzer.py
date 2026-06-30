"""
analyzer.py
===================================================================
The "judge". It takes the angles measured from a player and compares
them to the perfect-form targets for the chosen shot.

For each angle it produces:
    value      - what the player did (degrees)
    target     - the {min, ideal, max, weight} window
    status     - "good" | "too_small" | "too_large" | "missing"
    score      - 0..100 for that one joint
    deviation  - how many degrees outside the window (0 if good)
    kind       - knee / shoulder / elbow / wrist / torso
    group      - body region (Legs & Base / Arms & Racket / Torso & Balance)
    mistake    - one short line naming the error (or "" if good)
    tip        - a short, plain-English correction

It also rolls everything up into:
    overall_score  - one weighted score 0..100
    grade          - Excellent / Good / Needs Work / Poor
    group_scores   - average score per body region
    top_fixes      - the worst problems, worst first (for the report)
    summary        - a short written paragraph

A small tolerance (GRACE_DEGREES) is applied around every window, so a
joint that is only a degree or two outside is still treated as good -
pose estimation is never pixel-perfect, and flagging a 1-degree miss as
a fault would be misleading.

Left-handed players: pass handedness="left" and the left/right targets
are mirrored automatically (your dominant arm is compared to the
"racket arm" target regardless of side).
===================================================================
"""

from shot_standards import get_standard
from angle_calculator import ANGLE_LABELS, ANGLE_KIND, group_of, GROUP_ORDER

# How many degrees of slack to allow around each ideal window before a
# joint is called a fault. Absorbs normal pose-estimation noise.
GRACE_DEGREES = 3.0

# Mapping used to mirror a standard for left-handed players.
# Every left_X angle swaps with its right_X partner.
_MIRROR = {
    "left_hip_knee_ankle":        "right_hip_knee_ankle",
    "right_hip_knee_ankle":       "left_hip_knee_ankle",
    "left_hip_shoulder_elbow":    "right_hip_shoulder_elbow",
    "right_hip_shoulder_elbow":   "left_hip_shoulder_elbow",
    "left_shoulder_elbow_wrist":  "right_shoulder_elbow_wrist",
    "right_shoulder_elbow_wrist": "left_shoulder_elbow_wrist",
    "left_elbow_wrist_index":     "right_elbow_wrist_index",
    "right_elbow_wrist_index":    "left_elbow_wrist_index",
    "left_shoulder_hip_knee":     "right_shoulder_hip_knee",
    "right_shoulder_hip_knee":    "left_shoulder_hip_knee",
}


def _mirror_targets(angles):
    """Swap left<->right target windows (for left-handed players)."""
    return {_MIRROR[k]: v for k, v in angles.items()}


# ------------------------------------------------------------------
# Plain-English wording for each joint type.
# Two halves: a SHORT "mistake" label (for tables / headlines) and a
# longer "tip" (how to fix it).
# ------------------------------------------------------------------
_MISTAKE = {
    ("knee",     "too_small"): "Knee over-bent (crouching too low)",
    ("knee",     "too_large"): "Knee too straight / stiff",
    ("shoulder", "too_small"): "Arm held too close to the body",
    ("shoulder", "too_large"): "Arm lifted too high / over-rotated",
    ("elbow",    "too_small"): "Arm too bent at contact",
    ("elbow",    "too_large"): "Arm too straight / locked",
    ("wrist",    "too_small"): "Wrist over-cocked (bent too far)",
    ("wrist",    "too_large"): "Wrist too flat / loose",
    ("torso",    "too_small"): "Leaning / hunching too much",
    ("torso",    "too_large"): "Too upright / over-extended",
}

_FIX = {
    ("knee",     "too_small"): "Straighten the knee a little; don't sink so low.",
    ("knee",     "too_large"): "Bend the knee a bit more for balance and power.",
    ("shoulder", "too_small"): "Let the arm separate from the body and swing freely.",
    ("shoulder", "too_large"): "Bring the arm down a touch; don't over-reach.",
    ("elbow",    "too_small"): "Extend the arm more towards the ball at contact.",
    ("elbow",    "too_large"): "Allow a little more bend; don't lock the elbow.",
    ("wrist",    "too_small"): "Firm the wrist up; don't collapse it at contact.",
    ("wrist",    "too_large"): "Keep a slight lay-back; don't let the wrist go floppy.",
    ("torso",    "too_small"): "Stand a bit taller and brace the core through contact.",
    ("torso",    "too_large"): "Allow a slight forward lean into the shot.",
}


def _mistake(kind, status):
    return _MISTAKE.get((kind, status), "Outside the ideal range")


def _make_tip(kind, status):
    if status == "good":
        return "Good - within the ideal range."
    return _FIX.get((kind, status), "Bring this angle back into the ideal range.")


def _deviation(value, target):
    """How many degrees the value sits outside the window (0 if inside)."""
    lo, hi = target["min"], target["max"]
    if value < lo:
        return round(lo - value, 1)
    if value > hi:
        return round(value - hi, 1)
    return 0.0


def _score_one(value, target):
    """
    Score a single angle 0..100 and classify it.

    Inside the window            -> 80..100 (closer to ideal = higher).
    Within GRACE of the window   -> treated as good (edge score ~78).
    Further outside              -> drops ~1.6 points per degree beyond
                                    the grace zone, floored at 0.
    """
    lo, ideal, hi = target["min"], target["ideal"], target["max"]

    if lo <= value <= hi:
        span = max(ideal - lo, hi - ideal, 1.0)
        closeness = 1.0 - (abs(value - ideal) / span)   # 1 at ideal, 0 at edge
        closeness = max(0.0, min(1.0, closeness))
        return 80.0 + 20.0 * closeness, "good"

    deviation = (lo - value) if value < lo else (value - hi)

    if deviation <= GRACE_DEGREES:
        # within measurement tolerance - still good, just at the edge
        return 78.0, "good"

    status = "too_small" if value < lo else "too_large"
    score = max(0.0, 80.0 - 1.6 * (deviation - GRACE_DEGREES))
    return score, status


def analyze(measured_angles, shot_key, handedness="right"):
    """
    Compare measured angles to a shot's standard.

    measured_angles : dict {angle_name: degrees or None}
    shot_key        : e.g. "forehand"
    handedness      : "right" (default) or "left"

    Returns a rich report dict (see module docstring).
    """
    standard = get_standard(shot_key)
    targets = standard["angles"]
    if handedness == "left":
        targets = _mirror_targets(targets)

    per_angle = {}
    weighted_sum = 0.0
    weight_total = 0.0
    n_good = n_off = n_missing = 0

    for name, target in targets.items():
        kind = ANGLE_KIND[name]
        group = group_of(name)
        weight = target.get("weight", 1.0)
        value = measured_angles.get(name)

        if value is None:
            n_missing += 1
            per_angle[name] = {
                "label":     ANGLE_LABELS[name],
                "kind":      kind,
                "group":     group,
                "weight":    weight,
                "value":     None,
                "target":    target,
                "status":    "missing",
                "score":     None,
                "deviation": None,
                "mistake":   "Joint not clearly visible",
                "tip":       "Joint not clearly visible - re-shoot from the side "
                             "with the whole body in frame.",
            }
            continue

        score, status = _score_one(value, target)
        weighted_sum += score * weight
        weight_total += weight
        if status == "good":
            n_good += 1
        else:
            n_off += 1

        per_angle[name] = {
            "label":     ANGLE_LABELS[name],
            "kind":      kind,
            "group":     group,
            "weight":    weight,
            "value":     round(value, 1),
            "target":    target,
            "status":    status,
            "score":     round(score, 1),
            "deviation": _deviation(value, target),
            "mistake":   "" if status == "good" else _mistake(kind, status),
            "tip":       _make_tip(kind, status),
        }

    overall = round(weighted_sum / weight_total, 1) if weight_total else 0.0
    grade = _grade(overall)
    group_scores = _group_scores(per_angle)
    top_fixes = _top_fixes(per_angle)
    summary = _summary(standard, overall, grade, top_fixes, n_good, n_off)

    return {
        "shot":          shot_key,
        "shot_label":    standard["label"],
        "moment":        standard["moment"],
        "handedness":    handedness,
        "overall_score": overall,
        "grade":         grade,
        "per_angle":     per_angle,
        "group_scores":  group_scores,
        "top_fixes":     top_fixes,
        "n_good":        n_good,
        "n_off":         n_off,
        "n_missing":     n_missing,
        "n_measured":    n_good + n_off,
        "summary":       summary,
    }


def _grade(score):
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs Work"
    return "Poor"


def _group_scores(per_angle):
    """Average score per body region (over measured angles only)."""
    out = {}
    for grp in GROUP_ORDER:
        vals = [i["score"] for i in per_angle.values()
                if i["group"] == grp and i["score"] is not None]
        out[grp] = round(sum(vals) / len(vals), 1) if vals else None
    return out


def _top_fixes(per_angle, limit=4):
    """The worst off-range joints, worst score first."""
    problems = [
        {
            "label":     i["label"],
            "value":     i["value"],
            "target":    i["target"],
            "status":    i["status"],
            "deviation": i["deviation"],
            "mistake":   i["mistake"],
            "tip":       i["tip"],
            "group":     i["group"],
            "kind":      i["kind"],
            "weight":    i["weight"],
            "score":     i["score"],
        }
        for i in per_angle.values()
        if i["status"] not in ("good", "missing")
    ]
    problems.sort(key=lambda x: x["score"])
    return problems[:limit]


def _summary(standard, overall, grade, top_fixes, n_good, n_off):
    lines = [
        f"{standard['label']} - overall form score: {overall}/100 ({grade}).",
        f"{n_good} joint(s) inside the ideal range, {n_off} need work.",
    ]
    if not top_fixes:
        lines.append("Every measured joint is inside the ideal range for this "
                     "shot. Strong, well-balanced technique.")
    else:
        nice = "; ".join(p["label"] for p in top_fixes[:3])
        lines.append(f"Main things to work on: {nice}.")
        for p in top_fixes[:3]:
            lines.append(f"  - {p['label']}: {p['tip']}")
    return "\n".join(lines)
