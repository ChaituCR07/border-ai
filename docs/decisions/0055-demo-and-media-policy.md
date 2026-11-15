# ADR 0055: Demo and Media Publication Policy

## Status
Accepted

## Context
Visual media (demonstration videos, animated GIFs, interface screenshots, architectural diagrams) are essential for portfolio presentation and open-source documentation. 

However, publishing unvetted surveillance imagery, operational video feeds, or development screenshots creates serious risks:
- Leaking private personally identifiable information (PII), including real vehicle license plates or identifiable human faces.
- Accidentally exposing secrets, API tokens, internal hostnames, or developer environment paths in URLs, browser address bars, or log console outputs.
- Committing giant binary video files directly into Git, permanently bloating the repository clone size.
- Publishing visual latency or accuracy claims that contradict audited benchmarks.

## Decision

1. **Synthetic and Controlled Media Only:**
   - All published screenshots and video recordings must utilize recorded synthetic feeds or controlled staging scenarios with synthetic license plates (`KA01AB1234`, `MH12DE5678`).
   - Real third-party vehicle plates and individual facial crops must be automatically blurred before publication.

2. **Automated Media Privacy Scan:**
   - Implement an automated media privacy audit (`scripts/media/privacy_check.py` or OCR verification) scanning all committed imagery for sensitive regex patterns: real email addresses, JWT tokens (`eyJ...`), private hostnames, or unlisted license plates.
   - Strip all image and video metadata (EXIF/GPS) using image hygiene tools prior to committing.

3. **External Video Hosting & Repository Hygiene:**
   - Video files (`demo-video.mp4`, full walkthroughs) must never be committed to Git. They are hosted on external streaming platforms (YouTube / Vimeo / CDN) and linked via lightweight thumbnail posters and optimized short GIFs ($\le 8\text{ MB}$).
   - High-resolution UI screenshots must be stored under `docs/media/screenshots/` and cataloged in a machine-readable `manifest.json`.

4. **Honest Latency & Speed Labeling:**
   - Any video segment that is sped up in post-production must be explicitly labeled with an on-screen indicator (e.g., `[2x Speed]`).
   - Every metric displayed on closing title cards must match the exact values recorded in `docs/release/facts.md`.

## Consequences

- Zero personally identifiable data or credentials are exposed across any public visual asset.
- Git repository clone size remains lightweight and fast.
- Demonstrations maintain impeccable engineering integrity without deceptive visual speedups.
