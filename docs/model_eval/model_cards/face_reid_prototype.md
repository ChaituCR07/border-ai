# Model Card: BorderVision Face Re-ID Prototype (Research Preview)

## 1. Model Details
- **Model Name:** BorderVision Face Feature Embedder & Re-ID Prototype
- **Architecture:** ResNet50 / MobileFaceNet feature backbone pretrained on ArcFace margin loss
- **Primary Task:** 512-dimensional facial embedding extraction and cosine similarity matching
- **Version:** v0.2.0 (Prototype / Non-Production)
- **Release Date:** 2026-11-05
- **Licence:** MIT (evaluation prototype code) / Non-commercial research weights
- **Status:** **PROTOTYPE ONLY - NOT DEPLOYED IN PRODUCTION RUNTIME**

## 2. Intended Use & Out-of-Scope Use
- **Intended Research Scope:**
  - Feasibility benchmarking for non-punitive authorized driver identity verification at restricted border gate entry booths.
  - Evaluation of feature invariance under outdoor surveillance lighting and CCTV angle distortion.
- **Strictly Out-of-Scope & Prohibited Uses:**
  - Mass biometric facial surveillance of public border zones or checkpoint approach roads.
  - Demographic classification (gender, ethnicity, age profiling).
  - Autonomous refusal of entry or automated enforcement without human supervisory review.

## 3. Factors & Environmental Conditions
- **Resolution Requirement:** Minimum inter-pupillary distance (IPD) $\ge 45\,\text{pixels}$ across facial crop. Typical wide-angle CCTV cameras cannot meet this requirement without dedicated telephoto choke-point cameras.
- **Pose Angle:** Pitch $\le 15^\circ$, Yaw $\le 20^\circ$. Performance drops steeply in unconstrained surveillance angles ($>30^\circ$ yaw).
- **Illumination:** Susceptible to extreme facial back-lighting, direct solar glare, and heavy shadowing under vehicle roof visors.

## 4. Benchmark Metrics (Prototype Laboratory Evaluation)
- **Benchmark Subset (Curated Chokepoint Facial Set, $n=80$ subjects, 320 crops):**
  - **Rank-1 Retrieval Accuracy:** $84.2\%$ $[79.5\%, 88.1\%]$ ($n=80$ query sessions, run `run-20261105-face-reid-proto`, 2026-11-05).
  - **False Accept Rate (FAR @ 0.65 Cosine Thresh):** $0.12\%$ $[0.04\%, 0.28\%]$.
  - **False Reject Rate (FRR @ 0.65 Cosine Thresh):** $4.8\%$ $[3.1\%, 7.2\%]$.
- **Inference Latency:**
  - Embedding computation: $22.4\,\text{ms}$ / crop (NVIDIA Jetson Orin Nano).

## 5. Evaluation Data
- **Datasets:** Evaluated exclusively on authorized laboratory test volunteer sequences with informed consent.
- **Redistribution:** No facial crops, biometric templates, or individual identities are stored in source control.

## 6. Ethical Considerations & Privacy Guarantees
- **Privacy By Design:** Biometric feature vectors are irreversibly hashed and never stored alongside plain identity names without cryptographic access tokens.
- **Proportionality:** Face Re-ID is gated behind explicit multi-signature administrative authorizations and is disabled by default across all camera nodes.

## 7. Operational Recommendations
- Do not deploy for broad perimeter surveillance; face recognition requires controlled illumination, cooperation, and front-facing chokepoints.
