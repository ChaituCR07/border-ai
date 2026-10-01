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
