# ADR 0040: Model Performance Reporting and Claims Policy

## Status
Accepted

## Context
Computer vision and AI surveillance benchmarks are prone to misleading or inflated marketing claims (e.g., claiming "99.8% ANPR accuracy" without stating lighting conditions, sample size, camera resolution, or whether near-misses or unreadable crops were excluded). Furthermore, models trained on open-source benchmarks can experience severe distribution shifts when deployed on border CCTV cameras.

To ensure scientific integrity, engineering credibility, and legal compliance, BorderVision enforces strict, verifiable guidelines for all published performance metrics.

## Decision

1. **Tuple Requirement for Every Public Metric**:
   - Every public performance figure in documentation, README files, presentations, and reports must be published as an explicit tuple:
     $$\langle \text{Metric Value}, 95\%\, \text{Confidence Interval}, n\, (\text{Sample Size}), \text{Dataset}, \text{Split}, \text{Run ID}, \text{Date} \rangle$$
   - Example: `87.5% [84.1%, 90.3%] (n=600 vehicles, BorderVision-India-ANPR test split, run-20261105-anpr-m3, 2026-11-05)`.
   - Standalone, unqualified numbers (such as "99% accurate") are strictly prohibited.

2. **Wording and Contextual Framing**:
   - Performance statements must be framed accurately: *"On our authorized test set ($N = \dots$ under specified camera heights $\ge 30\,\text{px}$)..."*.
   - **Read rate (coverage)** must always be reported side-by-side with exact accuracy to prevent selective reporting (i.e. achieving high accuracy by silently discarding low-confidence crops).

3. **Prohibition of Synthetic Data for Accuracy Claims**:
   - Synthetic plates, rendered crops, and overlay-plate fixtures are strictly reserved for:
     - CI automated regression gates.
     - Integration unit tests and determinism checks.
     - Software development demos.
   - Synthetic data must **never** be cited or blended into public operational accuracy statistics. All synthetic fixtures are explicitly labeled as such in metadata.

4. **Model Licensing and Intellectual Property Transparency**:
   - Pretrained model dependencies and their legal licensing obligations must be disclosed in `MODEL_LICENSES.md` and model cards:
     - YOLOv8 (Ultralytics): AGPL-3.0 (with commercial licensing considerations).
     - PaddleOCR: Apache-2.0.
     - ByteTrack: MIT.
   - Redistribution of proprietary or academic benchmark images (e.g. UFPR-ALPR) is strictly forbidden; only evaluation metadata and sample identifiers may be committed.

5. **Mandatory Limitations Disclosure**:
   - System limitations are treated as first-class findings and must appear prominently alongside summary numbers:
     - Sample size boundaries and regional plate distribution (e.g., predominantly Southern/Western Indian state codes).
     - Camera mounting geometry and optical limitations (minimum plate height $\ge 30\,\text{px}$, maximum viewing angle $\le 30^\circ$).
     - Degradation under adverse conditions (heavy motion blur, direct night glare).

6. **Intended Use vs. Out-of-Scope Use**:
   - **Intended Use**: Real-time operational lead generation, situational awareness, and forensic search assisting human operators.
   - **Out-of-Scope Use**: Autonomous punitive legal enforcement, automated ticketing without human operator verification, or biometric identity tracking of individuals.

7. **Automated Claims Policy Verification**:
   - A dedicated verification script (`scripts/report/check_claims.py`) runs in CI to audit all documentation and markdown files, verifying that every cited accuracy percentage contains a valid run ID and confidence interval tag.

## Consequences
- **Positive**: Eliminates misleading claims; builds operator trust; guarantees scientific reproducibility; prevents licensing violations.
- **Negative**: Adds documentation overhead; requires explicit run tracking and confidence interval calculation for all reported numbers.
