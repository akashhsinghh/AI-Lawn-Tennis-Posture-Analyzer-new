"""
app.py  -  Streamlit web app for the AI Lawn Tennis Posture Engine
===================================================================
User flow:
    pick the shot  ->  upload a photo OR a video of yourself playing it
    ->  on the LEFT you see your body mapped with every joint angle
    ->  on the RIGHT you see your angles compared to the ideal ranges
    ->  BELOW you get a detailed coaching report: every mistake and
        exactly how to fix it.

Run it with:
    streamlit run app.py
===================================================================
"""

import os
import html
import tempfile

import cv2
import pandas as pd
import streamlit as st

from shot_standards import list_shots, shot_label, get_standard
from angle_calculator import GROUP_ORDER, short_label
from image_analyzer import analyze_image
from video_analyzer import analyze_video

# -------------------------------------------------------------------
# Streamlit has changed, over different releases, how you ask a widget
# to "fill the width of its container":
#     newest API : width="stretch"
#     older API  : use_container_width=True
#     oldest API : no such option at all
# Different hosts can end up running different Streamlit versions (this
# app hit exactly this when the host's installed version didn't match
# what was expected). This helper tries each option in turn so the app
# keeps working no matter which Streamlit version is actually installed.
# -------------------------------------------------------------------
def _full_width(fn, *args, **kwargs):
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        pass
    try:
        return fn(*args, use_container_width=True, **kwargs)
    except TypeError:
        pass
    return fn(*args, **kwargs)

st.set_page_config(page_title="AI Lawn Tennis Posture Analyzer",
                   page_icon="🎾", layout="wide")

st.title("🎾 AI Lawn Tennis Posture Analyzer")
st.caption("Upload a photo or video of your shot. The engine maps your body, "
           "measures 10 joint angles across the whole body, and compares them "
           "with the ideal form for that shot.")

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Settings")
    shots = list_shots()
    shot_key = st.selectbox("Tennis shot", shots, format_func=shot_label)
    handedness = st.radio("Player handedness", ["right", "left"], index=0,
                          horizontal=True)
    st.markdown("---")
    std = get_standard(shot_key)
    st.markdown(f"**{std['label']}** - analysed at the *{std['moment']}*.")
    st.caption(std["tips"])
    with st.expander("Ideal angle ranges for this shot"):
        rows = [{"Joint": k,
                 "Min": v["min"], "Ideal": v["ideal"], "Max": v["max"],
                 "Counts": "full" if v.get("weight", 1.0) >= 1.0 else "half"}
                for k, v in std["angles"].items()]
        _full_width(st.dataframe, pd.DataFrame(rows), hide_index=True)
        st.caption("'Counts' = how much the joint affects the overall score. "
                   "Wrist / arm-lift angles count 'half' because they are "
                   "noisier in a still photo.")


# ---------------- Right-hand comparison panel ----------------
# Colour palette chosen for HIGH CONTRAST on a light page: a pale row
# tint plus a solid coloured pill, with dark text everywhere.
_VERDICT_STYLE = {
    "good":      ("#eaf7ee", "#1a7f37"),   # row tint, pill colour
    "too_small": ("#fdeced", "#c0392b"),
    "too_large": ("#fdeced", "#c0392b"),
    "missing":   ("#fff6e5", "#9aa0a6"),
}


def _verdict_text(info):
    s = info["status"]
    if s == "good":
        return "✓ In range"
    if s == "missing":
        return "Not seen"
    if s == "too_small":
        return f"↓ {info['deviation']:.0f}° low"
    return f"↑ {info['deviation']:.0f}° high"


def _comparison_table_html(analysis):
    """A clean, readable HTML table: short joint name, your angle, ideal, pill."""
    head = (
        "<tr style='background:#f1f3f5'>"
        "<th style='text-align:left;padding:8px 10px;color:#111;"
        "border-bottom:2px solid #d0d7de'>Joint</th>"
        "<th style='text-align:center;padding:8px 6px;color:#111;"
        "border-bottom:2px solid #d0d7de'>You</th>"
        "<th style='text-align:center;padding:8px 6px;color:#111;"
        "border-bottom:2px solid #d0d7de'>Ideal</th>"
        "<th style='text-align:center;padding:8px 6px;color:#111;"
        "border-bottom:2px solid #d0d7de'>Verdict</th>"
        "</tr>"
    )
    body = ""
    for key, info in analysis["per_angle"].items():
        tint, pill = _VERDICT_STYLE.get(info["status"], ("#ffffff", "#666"))
        you = "—" if info["value"] is None else f"{info['value']:.0f}°"
        tgt = info["target"]
        ideal = f"{tgt['min']}–{tgt['max']}°"
        name = html.escape(short_label(key))
        verdict = html.escape(_verdict_text(info))
        badge = (f"<span style='background:{pill};color:#fff;padding:3px 9px;"
                 f"border-radius:11px;font-size:0.8rem;white-space:nowrap'>"
                 f"{verdict}</span>")
        body += (
            f"<tr style='background:{tint}'>"
            f"<td style='padding:7px 10px;color:#1f2937;"
            f"border-bottom:1px solid #e5e7eb'>{name}</td>"
            f"<td style='padding:7px 6px;color:#1f2937;text-align:center;"
            f"border-bottom:1px solid #e5e7eb'><b>{you}</b></td>"
            f"<td style='padding:7px 6px;color:#374151;text-align:center;"
            f"border-bottom:1px solid #e5e7eb'>{ideal}</td>"
            f"<td style='padding:7px 6px;text-align:center;"
            f"border-bottom:1px solid #e5e7eb'>{badge}</td>"
            f"</tr>"
        )
    return (f"<table style='width:100%;border-collapse:collapse;"
            f"font-size:0.9rem;border:1px solid #e5e7eb;border-radius:6px'>"
            f"{head}{body}</table>")


# Score colour by grade, for a clear at-a-glance headline.
_GRADE_COLOR = {
    "Excellent": "#1a7f37",
    "Good":      "#3f9142",
    "Needs Work": "#e08a00",
    "Poor":      "#c0392b",
}


def _score_header_html(score, grade):
    c = _GRADE_COLOR.get(grade, "#374151")
    return (
        "<div style='margin:2px 0 8px 0'>"
        "<div style='font-size:0.85rem;color:#6b7280'>Form score</div>"
        f"<div style='font-size:2.3rem;font-weight:800;color:{c};line-height:1.1'>"
        f"{score}<span style='font-size:1.1rem;color:#9ca3af'>/100</span></div>"
        f"<span style='background:{c};color:#fff;padding:2px 11px;border-radius:11px;"
        f"font-size:0.85rem;font-weight:600'>{html.escape(grade)}</span>"
        "</div>"
    )


def render_comparison(analysis):
    """Score + a clean, high-contrast 'your angle vs ideal' table (right column)."""
    if not analysis.get("found", False):
        st.error(analysis.get("summary", "No body detected."))
        return

    score = analysis["overall_score"]
    st.markdown(_score_header_html(score, analysis["grade"]),
                unsafe_allow_html=True)
    st.progress(min(int(score), 100) / 100)

    st.markdown("**Your angles vs the ideal**")
    st.markdown(_comparison_table_html(analysis), unsafe_allow_html=True)
    st.caption("🟩 Green = inside ideal range · 🟥 Red = needs work · "
               "🟨 Yellow = joint not clearly visible.")


# ---------------- Full-width detailed coaching report ----------------
def render_detailed_report(analysis):
    """Grouped, plain-English breakdown of every joint + how to fix it."""
    if not analysis.get("found", False):
        return

    st.subheader("📝 Detailed coaching report")
    st.caption(f"{analysis['shot_label']} · {analysis['handedness']}-handed · "
               f"analysed at the {analysis['moment']}. "
               f"{analysis['n_good']} joint(s) good, {analysis['n_off']} to fix, "
               f"{analysis['n_missing']} not clearly visible.")

    # Score per body region.
    gs = analysis["group_scores"]
    cols = st.columns(len(GROUP_ORDER))
    for col, grp in zip(cols, GROUP_ORDER):
        v = gs.get(grp)
        col.metric(grp, f"{v:.0f}/100" if v is not None else "—")

    # Top priorities first.
    fixes = analysis["top_fixes"]
    if fixes:
        st.markdown("**🎯 Fix these first**")
        for p in fixes[:3]:
            st.markdown(
                f"- **{p['label']}** — your {p['value']:.0f}° vs ideal "
                f"{p['target']['min']}–{p['target']['max']}° "
                f"({p['mistake']}, off by {p['deviation']:.0f}°). "
                f"**Fix:** {p['tip']}")
    else:
        st.success("No major faults detected — every measured joint is inside "
                   "the ideal range for this shot. Strong, balanced technique.")

    # Full breakdown, grouped by body region.
    st.markdown("**Full body-by-body breakdown**")
    for grp in GROUP_ORDER:
        items = [i for i in analysis["per_angle"].values()
                 if i["group"] == grp]
        if not items:
            continue
        with st.expander(f"{grp} — {len(items)} joints", expanded=True):
            for i in items:
                tgt = i["target"]
                rng = f"{tgt['min']}–{tgt['max']}° (ideal {tgt['ideal']}°)"
                if i["status"] == "good":
                    st.markdown(f"✅ **{i['label']}** — {i['value']:.0f}°. "
                                f"Inside the ideal range {rng}.")
                elif i["status"] == "missing":
                    st.markdown(f"⚠️ **{i['label']}** — not clearly visible. "
                                f"Ideal would be {rng}. Re-shoot from the side "
                                f"with the whole body in frame.")
                else:
                    st.markdown(f"❌ **{i['label']}** — {i['value']:.0f}° "
                                f"(ideal {rng}). {i['mistake']} — off by "
                                f"{i['deviation']:.0f}°. **Fix:** {i['tip']}")


# ---------------- Input tabs ----------------
tab_photo, tab_video = st.tabs(["📷 Photo", "🎬 Video"])

# ---------- Photo tab ----------
with tab_photo:
    up = st.file_uploader("Upload a photo (jpg / png)",
                          type=["jpg", "jpeg", "png"], key="photo")
    if up is not None and st.button("Analyze photo", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=os.path.splitext(up.name)[1]) as tf:
            tf.write(up.read())
            tmp_path = tf.name
        with st.spinner("Detecting body and measuring angles..."):
            annotated, analysis = analyze_image(tmp_path, shot_key,
                                                 handedness=handedness)

        col_img, col_cmp = st.columns([5, 4])
        with col_img:
            _full_width(st.image, cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                       caption="Your posture, mapped")
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                st.download_button("⬇️ Download annotated image", buf.tobytes(),
                                   file_name=f"{shot_key}_analyzed.jpg",
                                   mime="image/jpeg")
        with col_cmp:
            render_comparison(analysis)

        st.markdown("---")
        render_detailed_report(analysis)
        os.unlink(tmp_path)


# ---------- Video tab ----------
with tab_video:
    upv = st.file_uploader("Upload a video (mp4 / mov / avi)",
                           type=["mp4", "mov", "avi", "m4v"], key="video")
    sample = st.slider("Speed-up (analyse every Nth frame)", 1, 5, 1,
                       help="Higher = faster on long clips, slightly less "
                            "precise contact detection.")
    if upv is not None and st.button("Analyze video", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=os.path.splitext(upv.name)[1]) as tf:
            tf.write(upv.read())
            in_path = tf.name
        out_path = in_path + "_analyzed.mp4"
        with st.spinner("Processing video - this can take a moment..."):
            result = analyze_video(in_path, shot_key, handedness=handedness,
                                   out_path=out_path, sample_every=sample)

        analysis = result["analysis"]
        if result["found"]:
            col_img, col_cmp = st.columns([5, 4])
            with col_img:
                _full_width(st.image, cv2.cvtColor(result["contact_frame_image"],
                                                    cv2.COLOR_BGR2RGB),
                           caption=f"Contact frame "
                                   f"(#{result['contact_frame_index']})")
                # The annotated clip is offered as a reliable download. (We do
                # not embed a player: OpenCV's mp4v output does not play in all
                # browsers, which previously showed an empty 0:00 box.)
                if os.path.exists(out_path):
                    with open(out_path, "rb") as f:
                        data = f.read()
                    st.download_button("⬇️ Download annotated clip", data,
                                       file_name=f"{shot_key}_analyzed.mp4",
                                       mime="video/mp4")
                    st.caption("Open the downloaded clip in your video player "
                               "to watch the full annotated motion.")
            with col_cmp:
                render_comparison(analysis)

            st.markdown("---")
            render_detailed_report(analysis)
        else:
            render_comparison(analysis)

        for p in (in_path, out_path):
            if os.path.exists(p):
                os.unlink(p)

st.markdown("---")
st.caption("Built for the DEVDECAGON / Team 6 PostureExpert Lawn Tennis "
           "project. Angle targets in shot_standards.py are starting values - "
           "calibrate them with your Phase 3 professional data for best results.")
