import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402

from app import config  # noqa: E402
from app.analytics.rules_config import load_camera_rules, parse_camera_rules  # noqa: E402
from app.pipeline.visualizer import FlashState, draw_lines, draw_zones, put_text  # noqa: E402

MAX_W = 1280
HELP = ("z=zone mode  l=line mode  click=add point  Enter=finish zone  "
        "u=undo point  d=delete last shape  s=save  q=quit")


def grab_frame(video: str, index: int):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, img = cap.read()
    cap.release()
    if not ok:
        sys.exit(f"Cannot read frame {index} from {video}")
    return img


def save_grid(img, camera: str) -> None:
    """Headless fallback: a frame with a labelled 0.1 grid, so you can read
    normalized coordinates by eye and type them into the JSON."""
    h, w = img.shape[:2]
    for i in range(1, 10):
        v = i / 10
        cv2.line(img, (int(v * w), 0), (int(v * w), h), (255, 255, 255), 1)
        cv2.line(img, (0, int(v * h)), (w, int(v * h)), (255, 255, 255), 1)
        put_text(img, f"{v:.1f}", (int(v * w) + 3, 14), 0.4)
        put_text(img, f"{v:.1f}", (3, int(v * h) - 3), 0.4)
    out = config.OUTPUT_DIR / "snapshots"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{camera}_grid.jpg"
    cv2.imwrite(str(path), img)
    print("Saved", path)


def next_id(prefix: str, items: list) -> str:
    used = {i["id"] for i in items if "id" in i}
    n = 1
    while f"{prefix}{n}" in used:
        n += 1
    return f"{prefix}{n}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--camera", default="CAM_001")
    ap.add_argument("--frame", type=int, default=30)
    ap.add_argument("--grid", action="store_true", help="save a labelled grid image and exit")
    args = ap.parse_args()

    img = grab_frame(args.video, args.frame)
    orig_h, orig_w = img.shape[:2]
    if orig_w > MAX_W:
        scale = MAX_W / orig_w
        img = cv2.resize(img, (MAX_W, int(orig_h * scale)))
    h, w = img.shape[:2]

    if args.grid:
        save_grid(img, args.camera)
        return

    out_path = config.CONFIG_DIR / "zones" / f"{args.camera}.json"
    data = {"camera_id": args.camera, "zones": [], "lines": []}
    if out_path.exists():
        with open(out_path) as f:
            data = json.load(f)
        data.setdefault("zones", [])
        data.setdefault("lines", [])
    data["reference_size"] = {"width": orig_w, "height": orig_h}

    state = {"mode": "zone", "points": [], "rules": parse_camera_rules(data, "<editing>")}
    flash = FlashState()

    def refresh():
        state["rules"] = parse_camera_rules(data, "<editing>")

    def finish_shape():
        pts = state["points"]
        if state["mode"] == "zone":
            if len(pts) < 3:
                print("A zone needs at least 3 points")
                return
            zid = next_id("Z", data["zones"])
            name = input(f"Zone name [{zid}]: ").strip() or zid
            ztype = input("Type restricted/monitored [monitored]: ").strip() or "monitored"
            data["zones"].append({"id": zid, "name": name, "type": ztype,
                                  "polygon": pts, "dwell_alert_s": 0.0, "loiter_s": 0.0})
            shape_list = data["zones"]
        else:
            lid = next_id("L", data["lines"])
            name = input(f"Line name [{lid}]: ").strip() or lid
            direction = (input("Label for the ARROW side, IN or OUT [IN]: ").strip().upper()
                         or "IN")
            data["lines"].append({"id": lid, "name": name, "type": "tripwire",
                                  "p1": pts[0], "p2": pts[1], "positive_direction": direction,
                                  "cooldown_s": 2.0})
            shape_list = data["lines"]
        state["points"] = []
        try:
            refresh()
        except ValueError as e:
            print("Invalid shape, discarded:", e)
            shape_list.pop()
            refresh()

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            state["points"].append([round(x / w, 4), round(y / h, 4)])
            if state["mode"] == "line" and len(state["points"]) == 2:
                finish_shape()

    cv2.namedWindow("draw zones")
    cv2.setMouseCallback("draw zones", on_mouse)

    while True:
        canvas = img.copy()
        draw_zones(canvas, state["rules"], {}, flash, 0.0)
        draw_lines(canvas, state["rules"], {}, flash, 0.0)
        pts_px = [(int(p[0] * w), int(p[1] * h)) for p in state["points"]]
        for p in pts_px:
            cv2.circle(canvas, p, 4, (0, 255, 0), -1)
        for a, b in zip(pts_px, pts_px[1:]):
            cv2.line(canvas, a, b, (0, 255, 0), 2)
        put_text(canvas, f"mode: {state['mode']}", (10, 25), 0.7)
        put_text(canvas, HELP, (10, h - 12), 0.45)
        cv2.imshow("draw zones", canvas)

        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("z"):
            state["mode"], state["points"] = "zone", []
        elif key == ord("l"):
            state["mode"], state["points"] = "line", []
        elif key == 13:
            if state["mode"] == "zone":
                finish_shape()
        elif key == ord("u") and state["points"]:
            state["points"].pop()
        elif key == ord("d"):
            lst = data["zones"] if state["mode"] == "zone" else data["lines"]
            if lst:
                lst.pop()
                refresh()
        elif key == ord("s"):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(data, f, indent=2)
            load_camera_rules(out_path)                       # re-validate what was saved
            print("Saved and validated:", out_path)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
