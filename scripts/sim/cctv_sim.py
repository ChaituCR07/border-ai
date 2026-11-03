#!/usr/bin/env python3
"""
CCTV Simulator Supervisor: Streams scenario video clips via FFmpeg to MediaMTX RTSP endpoints.
Supports real-time pacing, clock overlays, looping, credential masking, and fault injection
(dropping streams or freezing frames to test STALLED state detection).
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Dict, List, Optional

logger = logging.getLogger("cctv_sim")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def mask_credentials(cmd_list: List[str]) -> str:
    """Masks user:pass in RTSP URLs for safe logging."""
    safe_tokens = []
    for token in cmd_list:
        if token.startswith("rtsp://") and "@" in token:
            prefix, rest = token.split("rtsp://", 1)
            creds, addr = rest.split("@", 1)
            safe_tokens.append(f"rtsp://***:***@{addr}")
        else:
            safe_tokens.append(token)
    return " ".join(safe_tokens)


def build_ffmpeg_cmd(
    clip_path: str,
    rtsp_url: str,
    loop: bool = False,
    burn_clock: bool = True,
    freeze: bool = False,
) -> List[str]:
    """Builds the deterministic FFmpeg invocation argument list."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
    ]

    if not freeze:
        cmd.extend(["-re"])

    loop_flag = "-1" if loop else "0"
    if freeze:
        # Loop single still frame to simulate frozen camera with open RTSP session
        cmd.extend(["-loop", "1", "-i", clip_path, "-t", "3600"])
    else:
        cmd.extend(["-stream_loop", loop_flag, "-i", clip_path])

    vf_filters = ["scale=1280:720"]
    if burn_clock:
        vf_filters.append(
            r"drawtext=text='%{localtime\:%H\\\:%M\\\:%S}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5"
        )

    cmd.extend([
        "-an",
        "-vf",
        ",".join(vf_filters),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-profile:v",
        "baseline",
        "-pix_fmt",
        "yuv420p",
        "-g",
        "30",
        "-f",
        "rtsp",
        "-rtsp_transport",
        "tcp",
        rtsp_url,
    ])
    return cmd


class CCTVSimulator:
    def __init__(
        self,
        base_rtsp: str = "rtsp://localhost:8554",
        user: str = "",
        password: str = "",
        burn_clock: bool = True,
        log_dir: str = "logs/sim",
    ):
        self.base_rtsp = base_rtsp.rstrip("/")
        self.user = user or os.getenv("RTSP_PUB_USER", "rtsp_pub_user")
        self.password = password or os.getenv("RTSP_PUB_PASS", "zq9canaryRtspPub")
        self.burn_clock = burn_clock
        self.log_dir = log_dir
        self.processes: Dict[str, subprocess.Popen] = {}
        self.camera_configs: Dict[str, dict] = {}
        os.makedirs(self.log_dir, exist_ok=True)

    def _get_target_url(self, path: str) -> str:
        clean_path = path.lstrip("/").lower()
        if self.user and self.password:
            return f"{self.base_rtsp.replace('rtsp://', f'rtsp://{self.user}:{self.password}@')}/{clean_path}"
        return f"{self.base_rtsp}/{clean_path}"

    def start_camera(self, camera_id: str, clip_path: str, loop: bool = False, freeze: bool = False) -> subprocess.Popen:
        self.stop_camera(camera_id)
        self.camera_configs[camera_id] = {
            "clip_path": clip_path,
            "loop": loop,
            "freeze": freeze,
        }

        # camera_01 -> cam01
        channel = camera_id.lower().replace("-", "").replace("_", "")
        rtsp_target = self._get_target_url(channel)
        cmd = build_ffmpeg_cmd(clip_path, rtsp_target, loop=loop, burn_clock=self.burn_clock, freeze=freeze)

        log_file = os.path.join(self.log_dir, f"{camera_id.lower()}.log")
        f = open(log_file, "a", encoding="utf-8")

        masked = mask_credentials(cmd)
        logger.info(f"Starting camera {camera_id}: {masked}")

        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
        self.processes[camera_id] = proc
        return proc

    def stop_camera(self, camera_id: str) -> None:
        proc = self.processes.pop(camera_id, None)
        if proc and proc.poll() is None:
            logger.info(f"Stopping camera stream for {camera_id} (pid={proc.pid})")
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    def drop(self, camera_id: str, seconds: float = 20.0) -> None:
        """Simulates complete RTSP disconnection by stopping the publisher."""
        cfg = self.camera_configs.get(camera_id)
        if not cfg:
            logger.warning(f"Cannot drop unknown camera {camera_id}")
            return
        logger.warning(f"Dropping camera {camera_id} for {seconds:.1f}s")
        self.stop_camera(camera_id)
        time.sleep(seconds)
        logger.info(f"Resuming dropped camera {camera_id}")
        self.start_camera(camera_id, cfg["clip_path"], loop=cfg["loop"])

    def freeze(self, camera_id: str, seconds: float = 30.0) -> None:
        """Simulates a frozen camera (open TCP session, but no new frames) -> STALLED."""
        cfg = self.camera_configs.get(camera_id)
        if not cfg:
            logger.warning(f"Cannot freeze unknown camera {camera_id}")
            return
        logger.warning(f"Freezing camera {camera_id} for {seconds:.1f}s (STALLED simulation)")
        self.start_camera(camera_id, cfg["clip_path"], loop=cfg["loop"], freeze=True)
        time.sleep(seconds)
        logger.info(f"Unfreezing camera {camera_id}")
        self.start_camera(camera_id, cfg["clip_path"], loop=cfg["loop"], freeze=False)

    def stop_all(self) -> None:
        logger.info("Stopping all CCTV simulator camera streams...")
        for cam_id in list(self.processes.keys()):
            self.stop_camera(cam_id)


def main():
    parser = argparse.ArgumentParser(description="Border-AI CCTV Simulator")
    parser.add_argument("--camera", default="CAM-01", help="Camera ID (e.g. CAM-01)")
    parser.add_argument("--clip", default="footage/camera_01/normal.mp4", help="Path to video clip")
    parser.add_argument("--loop", action="store_true", help="Loop playback continuously")
    parser.add_argument("--burn-clock", action="store_true", default=True, help="Burn wall clock overlay")
    args = parser.parse_args()

    sim = CCTVSimulator(burn_clock=args.burn_clock)

    def handle_signal(sig, frame):
        sim.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if not os.path.exists(args.clip):
        logger.warning(f"Clip {args.clip} does not exist on disk yet. Exiting simulator.")
        return

    sim.start_camera(args.camera, args.clip, loop=args.loop)
    logger.info("Simulator running. Press Ctrl+C to terminate.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sim.stop_all()


if __name__ == "__main__":
    main()
