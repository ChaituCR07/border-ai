# Datasets and Media Policy

This directory stores evaluation footage, test videos, and model training/testing datasets.

## Important Note
Raw datasets, video files (`.mp4`, `.avi`, `.mkv`), and large binary files are excluded from Git version control via `.gitignore`.

## Dataset Sources & Licensing
Only authorized, open-source, or synthetic surveillance footage should be placed here:
- **Object Detection & Tracking:** COCO 2017, BDD100K, MOT17, UA-DETRAC
- **ANPR:** UFPR-ALPR, CCPD, Custom Indian ANPR samples
- **Custom CCTV Clips:** Local evaluation clips (ensure no personally identifiable private data is exposed)

## Directory Structure
- `videos/`: Test video streams and CCTV samples
- `plates/`: License plate test images
- `faces/`: Face detection / re-identification evaluation samples

## Inspected Test Videos (Day 2)

| File | Resolution | FPS | Duration | Codec | Source / License |
|---|---|---|---|---|---|
| `person_walking.mp4` | 1280x720 | 15.0 | 5.0s | mp4v / H.264 | Synthetic Surveillance Benchmark (MIT) |
| `vehicles.mp4` | 1280x720 | 15.0 | 5.0s | mp4v / H.264 | Synthetic Surveillance Benchmark (MIT) |
| `night.mp4` | 1280x720 | 15.0 | 5.0s | mp4v / H.264 | Synthetic Low-Light Benchmark (MIT) |
| `crowded.mp4` | 1280x720 | 15.0 | 5.0s | mp4v / H.264 | Synthetic Multi-Target Benchmark (MIT) |
| `sample_01.mp4` | 1280x720 | 15.0 | 5.0s | mp4v / H.264 | Synthetic Benchmark Baseline (MIT) |
