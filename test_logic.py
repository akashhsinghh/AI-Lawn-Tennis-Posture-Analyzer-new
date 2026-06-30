"""
test_logic.py
===================================================================
Quick self-checks for the maths and scoring layers.
These do NOT need MediaPipe or a camera, so they run anywhere and are
a fast way to confirm the core engine behaves.

Run:  python test_logic.py
===================================================================
"""

from angle_calculator import (
    calculate_angle, compute_all_angles, ANGLE_DEFS, ANGLE_KIND, group_of,
)
from analyzer import analyze, GRACE_DEGREES
from shot_standards import list_shots, get_standard


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_calculate_angle():
    assert approx(calculate_angle((0, 1), (0, 0), (1, 0)), 90.0)
    assert approx(calculate_angle((0, 1), (0, 0), (0, -1)), 180.0)
    assert approx(calculate_angle((0, 1), (0, 0), (0, 2)), 0.0)
    print("calculate_angle .......... OK")


def test_compute_all_angles_shape():
    lms = [(0.0, 0.0, 1.0)] * 33
    lms[23] = (0.5, 0.4, 1.0)   # hip
    lms[25] = (0.5, 0.6, 1.0)   # knee (vertex)
    lms[27] = (0.7, 0.6, 1.0)   # ankle
    angles = compute_all_angles(lms)
    assert set(angles.keys()) == set(ANGLE_DEFS.keys())
    assert approx(angles["left_hip_knee_ankle"], 90.0, tol=1e-3)
    print("compute_all_angles ....... OK", f"({len(angles)} angles)")


def test_angle_set():
    # Wrists must be present (the angle that was missing originally).
    must_have = [
        "left_elbow_wrist_index", "right_elbow_wrist_index",     # wrists
        "left_hip_shoulder_elbow", "right_hip_shoulder_elbow",   # arm lift
        "left_shoulder_elbow_wrist", "right_shoulder_elbow_wrist",
        "left_hip_knee_ankle", "right_hip_knee_ankle",
        "left_shoulder_hip_knee", "right_shoulder_hip_knee",
    ]
    for name in must_have:
        assert name in ANGLE_DEFS, name
        assert name in ANGLE_KIND, name
    # The noisy ankle/foot angle must be GONE.
    assert "left_knee_ankle_foot" not in ANGLE_DEFS
    assert "right_knee_ankle_foot" not in ANGLE_DEFS
    assert len(ANGLE_DEFS) == 10, len(ANGLE_DEFS)
    print("angle set (10, no ankle) . OK")


def test_visibility_gate():
    lms = [(0.0, 0.0, 1.0)] * 33
    lms[23] = (0.5, 0.4, 0.0)   # hip invisible -> angle should be None
    lms[25] = (0.5, 0.6, 1.0)
    lms[27] = (0.7, 0.6, 1.0)
    angles = compute_all_angles(lms, min_visibility=0.3)
    assert angles["left_hip_knee_ankle"] is None
    print("visibility gate .......... OK")


def test_analyze_scoring():
    std = get_standard("forehand")["angles"]
    ideal = {name: t["ideal"] for name, t in std.items()}
    report = analyze(ideal, "forehand", handedness="right")
    assert report["overall_score"] >= 95, report["overall_score"]
    assert report["grade"] == "Excellent"
    assert all(i["status"] == "good" for i in report["per_angle"].values())
    assert report["group_scores"]
    assert report["top_fixes"] == []
    assert report["n_off"] == 0
    print("analyze (ideal=high) ..... OK", report["overall_score"])

    bad = {name: 10 for name in std}
    bad_report = analyze(bad, "forehand", handedness="right")
    assert bad_report["overall_score"] < 50, bad_report["overall_score"]
    assert bad_report["top_fixes"]
    for fx in bad_report["top_fixes"]:
        assert fx["mistake"] and fx["tip"]
    print("analyze (bad=low) ........ OK", bad_report["overall_score"])


def test_grace_band():
    """A joint a couple of degrees out is 'good'; well out is a fault."""
    std = get_standard("forehand")["angles"]
    base = {name: t["ideal"] for name, t in std.items()}
    lo = std["left_hip_knee_ankle"]["min"]   # 150

    near = dict(base)
    near["left_hip_knee_ankle"] = lo - (GRACE_DEGREES - 1)   # 2 deg out
    r1 = analyze(near, "forehand")
    assert r1["per_angle"]["left_hip_knee_ankle"]["status"] == "good"

    far = dict(base)
    far["left_hip_knee_ankle"] = lo - (GRACE_DEGREES + 3)    # 6 deg out
    r2 = analyze(far, "forehand")
    assert r2["per_angle"]["left_hip_knee_ankle"]["status"] == "too_small"
    print("grace tolerance band ..... OK", f"(±{GRACE_DEGREES:.0f}°)")


def test_left_handed_mirror():
    """A lefty doing the exact mirror of the ideal should still score ~100."""
    std = get_standard("serve")["angles"]
    measured = {name: t["ideal"] for name, t in std.items()}

    swapped = {}
    for name, val in measured.items():
        if name.startswith("left_"):
            swapped[name] = measured["right_" + name[len("left_"):]]
        elif name.startswith("right_"):
            swapped[name] = measured["left_" + name[len("right_"):]]
        else:
            swapped[name] = val

    report = analyze(swapped, "serve", handedness="left")
    assert report["overall_score"] >= 95, report["overall_score"]
    print("left-handed mirror ....... OK", report["overall_score"])


def test_all_shots_well_formed():
    for s in list_shots():
        ang = get_standard(s)["angles"]
        assert set(ang.keys()) == set(ANGLE_DEFS.keys()), s
        for t in ang.values():
            assert t["min"] <= t["ideal"] <= t["max"], (s, t)
            assert 0.0 < t.get("weight", 1.0) <= 1.0, (s, t)
    print("all shots well-formed .... OK", list_shots())


if __name__ == "__main__":
    test_calculate_angle()
    test_compute_all_angles_shape()
    test_angle_set()
    test_visibility_gate()
    test_analyze_scoring()
    test_grace_band()
    test_left_handed_mirror()
    test_all_shots_well_formed()
    print("\nAll logic tests passed ✔")
