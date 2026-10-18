# Architecture Decision Record 0009: Face & Person Re-ID Prototype

- **Status:** Accepted
- **Date:** 2026-10-18
- **Branch:** feature/identity

## Context
Day 10 introduces optional advanced biometric and identity capabilities: face matching against enrolled watchlist entries, and cross-camera person re-identification (Re-ID). Biometric processing requires rigorous ethical safeguards, defensive engineering, and statistical realism.

## Decisions

1. **Disabled by Default:** `identity.enabled: false`. Activation requires explicit opt-in (`--identity`).
2. **Consent-Gated Enrollment:** Enrolling a subject requires `--consent-confirmed`. The system refuses without it.
3. **Embeddings Only:** The system persists numeric float32 embeddings; photos and crops are not stored.
4. **Matches as Review Leads:** Face matches default to status `review` (`allow_alert: false`). Re-ID events emit `status: candidate`.
5. **Quality Gating:** Face detections are filtered for score ($\ge 0.8$), resolution ($\ge 40\text{ px}$), profile yaw angle ($\le 0.5$), and Laplacian sharpness ($\ge 30$). Blurry or profile faces are discarded before embedding.
6. **Track Feature Fusion:** Embeddings across multiple frames of a track are aggregated via quality-weighted mean. A consistency check ($\ge 0.75$) rejects tracks contaminated by tracker ID switches.
7. **Ambiguity Rejection:** Matches must exceed a minimum margin ($\ge 0.05$) over the second-best candidate.
8. **Decoupled Asynchronous Worker:** Face detection and embedding run on a dedicated worker thread with bounded queues. Dropping occurs gracefully in live mode without stalling the vision pipeline.
9. **Two-Tier Engine Architecture:**
   - **Option A (Default):** OpenCV YuNet detector + SFace recognizer (128-d, permissive license).
   - **Option B (Optional):** InsightFace SCRFD + ArcFace (512-d, non-commercial research use only).
10. **Conservative Re-ID Baseline:** Default `ColorLayoutEmbedder` uses HSV torso/legs color histograms with gray-world normalization. Cross-camera candidate generation is constrained by maximum time gap ($600\text{s}$) and camera pairs.

## False-Match Arithmetic
With a gallery of $N$ enrolled faces and per-comparison false-match rate $\text{FAR}$:
$$\text{Expected False Matches per Day} = \text{Strangers/Day} \times [1 - (1 - \text{FAR})^N]$$
At $\text{FAR} = 0.1\%$ with $N = 50$ and 1,000 strangers/day, approximately 49 false matches would occur daily. Thus, strict review thresholds and multi-frame consistency gates are mandatory.
