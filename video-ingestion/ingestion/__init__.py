import os

# Force TCP for RTSP (more reliable than UDP), keep latency low,
# and time out stuck connections (microseconds; 5 s).
# If your FFmpeg build rejects "stimeout", try "timeout;5000000" instead.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|stimeout;5000000",
)
