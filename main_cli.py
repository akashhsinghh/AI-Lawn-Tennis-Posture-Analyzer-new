"""
main_cli.py
===================================================================
Command-line runner - handy for quick tests without the web UI.

Examples
--------
Photo:
    python main_cli.py --shot forehand --image my_forehand.jpg

Video (right-handed serve), save annotated clip:
    python main_cli.py --shot serve --video my_serve.mp4 --out serve_out.mp4

Left-handed player:
    python main_cli.py --shot backhand --image bh.jpg --hand left

List the shot names the engine knows:
    python main_cli.py --list
===================================================================
"""

import argparse
import os

from shot_standards import list_shots, shot_label
from angle_calculator import GROUP_ORDER


def _print_report(analysis):
    print("\n" + "=" * 72)
    print(f"SHOT      : {analysis.get('shot_label', analysis.get('shot'))}")
    print(f"MOMENT    : {analysis.get('moment', '-')}")
    print(f"HANDEDNESS: {analysis.get('handedness', '-')}")
    print(f"SCORE     : {analysis.get('overall_score')}/100"
          f"  ({analysis.get('grade')})")
    print(f"JOINTS    : {analysis.get('n_good', '?')} good, "
          f"{analysis.get('n_off', '?')} off-range, "
          f"{analysis.get('n_missing', '?')} not visible")
    print("=" * 72)

    # Group scores
    gs = analysis.get("group_scores", {})
    if gs:
        for grp, v in gs.items():
            bar = int((v or 0) / 100 * 30) if v else 0
            print(f"  {grp:24s} {'█' * bar}{'░' * (30 - bar)}  "
                  f"{f'{v:.0f}' if v is not None else '—':>5}/100")
        print()

    # Per-angle table
    per = analysis.get("per_angle", {})
    if per:
        print(f"{'Joint':48s} {'You':>5s} {'Range':>12s}  Status")
        print("-" * 78)
        for name, info in per.items():
            you  = "—" if info["value"] is None else f"{info['value']:.0f}°"
            tgt  = info["target"]
            rng  = f"{tgt['min']}-{tgt['max']}°"
            flag = {"good": "✅", "too_small": "⬇ ", "too_large": "⬆ ",
                    "missing": "— "}.get(info["status"], "?")
            print(f"{flag} {info['label']:44s} {you:>5s} {rng:>12s}")

    # Top fixes
    fixes = analysis.get("top_fixes", [])
    if fixes:
        print("\n" + "-" * 78)
        print("TOP FIXES (worst first):")
        for p in fixes[:3]:
            print(f"  ❌ {p['label']}: {p['tip']}")
    print("-" * 78)
    print(analysis.get("summary", ""))
    print("=" * 72 + "\n")


def main():
    p = argparse.ArgumentParser(description="AI Lawn Tennis Posture Analyzer")
    p.add_argument("--shot", help="shot name, e.g. forehand / serve / volley")
    p.add_argument("--image", help="path to a photo")
    p.add_argument("--video", help="path to a video")
    p.add_argument("--out", help="output path for annotated image/video")
    p.add_argument("--hand", choices=["right", "left"], default="right",
                   help="player handedness (default: right)")
    p.add_argument("--sample-every", type=int, default=1,
                   help="analyse every Nth frame in videos (speed-up)")
    p.add_argument("--list", action="store_true", help="list known shots")
    args = p.parse_args()

    if args.list:
        print("Known shots:")
        for s in list_shots():
            print(f"  {s:16s} ({shot_label(s)})")
        return

    if not args.shot:
        p.error("--shot is required (or use --list)")
    if not args.image and not args.video:
        p.error("give either --image or --video")

    if args.image:
        from image_analyzer import analyze_image
        out = args.out or _default_out(args.image, "_analyzed.jpg")
        _, analysis = analyze_image(args.image, args.shot,
                                    handedness=args.hand, save_path=out)
        _print_report(analysis)
        print(f"Annotated image saved to: {out}")

    if args.video:
        from video_analyzer import analyze_video
        out = args.out or _default_out(args.video, "_analyzed.mp4")
        result = analyze_video(args.video, args.shot, handedness=args.hand,
                               out_path=out, sample_every=args.sample_every)
        _print_report(result["analysis"])
        if result["found"]:
            print(f"Contact frame: #{result['contact_frame_index']} "
                  f"of {result['n_frames']}")
        print(f"Annotated video saved to: {out}")


def _default_out(in_path, suffix):
    base, _ = os.path.splitext(in_path)
    return base + suffix


if __name__ == "__main__":
    main()
