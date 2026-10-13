import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def render_plate(text: str) -> np.ndarray:
    # Yellow background Indian commercial / standard plate (110x520)
    img = np.full((110, 520, 3), (40, 210, 255), dtype=np.uint8)
    cv2.rectangle(img, (4, 4), (515, 105), (0, 0, 0), 4)
    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 2.6, 5)
    cv2.putText(img, text, (max(8, (520 - tw) // 2), 78), cv2.FONT_HERSHEY_DUPLEX, 2.6, (0, 0, 0), 5, cv2.LINE_AA)
    return img


def generate_video(out_path: str, plate_text: str = "KA01AB1234", frames: int = 60, fps: int = 15):
    width, height = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    plate_img = render_plate(plate_text)
    pw_target, ph_target = 220, 48
    plate_resized = cv2.resize(plate_img, (pw_target, ph_target), interpolation=cv2.INTER_AREA)

    # Road background
    base_frame = np.full((height, width, 3), (120, 120, 120), dtype=np.uint8)
    # Road markings
    for x in range(0, width, 120):
        cv2.rectangle(base_frame, (x, 350), (x + 60, 370), (255, 255, 255), -1)

    # Vehicle motion parameters (car moving from left to right)
    car_w, car_h = 420, 220
    x_start = 50
    x_end = width - car_w - 50

    for i in range(frames):
        frame = base_frame.copy()
        t = i / max(frames - 1, 1)
        x_car = int(x_start + t * (x_end - x_start))
        y_car = 320

        # Draw vehicle body (dark blue sedan rear)
        cv2.rectangle(frame, (x_car, y_car), (x_car + car_w, y_car + car_h), (180, 80, 30), -1)
        cv2.rectangle(frame, (x_car, y_car), (x_car + car_w, y_car + car_h), (40, 40, 40), 4)
        
        # Rear windshield
        cv2.rectangle(frame, (x_car + 40, y_car + 20), (x_car + car_w - 40, y_car + 90), (60, 60, 60), -1)
        # Taillights
        cv2.rectangle(frame, (x_car + 15, y_car + 105), (x_car + 75, y_car + 140), (20, 20, 220), -1)
        cv2.rectangle(frame, (x_car + car_w - 75, y_car + 105), (x_car + car_w - 15, y_car + 140), (20, 20, 220), -1)

        # Place license plate on the lower bumper
        px = x_car + (car_w - pw_target) // 2
        py = y_car + 130
        frame[py:py + ph_target, px:px + pw_target] = plate_resized

        writer.write(frame)

    writer.release()
    print(f"Generated {frames} frames synthetic vehicle video at {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="datasets/videos/anpr_vehicle_track.mp4")
    p.add_argument("--plate", default="KA01AB1234")
    p.add_argument("--frames", type=int, default=60)
    args = p.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    generate_video(args.out, args.plate, args.frames)
