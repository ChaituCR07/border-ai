# 0007. Automatic Number Plate Recognition (ANPR) Architecture and Consensus Engine

## Context
Vehicle detection alone cannot distinguish between authorized and unauthorized border vehicles. Day 8 introduces Automatic Number Plate Recognition (ANPR) into the video intelligence pipeline. Running raw OCR on full video frames on every frame is prohibitively expensive (hundreds of milliseconds per frame) and error-prone due to motion blur, glare, perspective skew, and OCR character confusions. 

## Decisions

1. **Pretrained PaddleOCR with Dual-Version Adapter:**
   - Framework & Versions: `paddlepaddle==3.3.1` and `paddleocr==3.7.0`.
   - Execution Device: CPU by default (`device: cpu`). This completely eliminates PyTorch/CUDA memory and runtime conflicts on shared hardware while delivering ~270-320 ms per OCR read.
   - Decoupled `OcrEngine` adapter abstracts away PaddleOCR 2.x and 3.x API differences (`OCRResult` extraction vs nested list polygons), with built-in HTTP server fallback (`HttpOcrEngine`) and test mock (`ScriptedOcrEngine`).

2. **Hierarchical Detection & Adaptive Locators:**
   - Pipeline flow: `Vehicle Detection → Plate Localization → Crop Quality Gate → Preprocessing → OCR → Consensus`.
   - Dedicated `YoloPlateLocator` runs on vehicle crops when `plate_detector.pt` weights are present.
   - When model weights are absent, `build_locator()` gracefully falls back to `LowerRegionLocator` (bottom 50% of the vehicle crop), letting the text detector segment plate text while format rules and consensus voting filter out extraneous vehicle decals.

3. **Position-Based Plate Format Rules & Correction:**
   - Indian license plate format (`KA01AB1234`) comprises state code (2 letters), district (1-2 digits), series (1-3 letters), and registration number (4 digits).
   - Position-aware correction automatically disambiguates look-alike characters (`O`/`0`, `I`/`1`, `B`/`8`, `S`/`5`, `Z`/`2`) based on slot syntax without blind replacement.
   - Strips leading HSRP country markers (e.g., `IND`) and validates against official Indian state/UT codes, tagging output with format levels (`strict`, `loose`, `invalid`). Generic alphanumeric fallback (`generic`) supports international formats.

4. **Periodic Background Scheduling & Early Stopping:**
   - OCR does NOT run on every frame. Vehicles must establish track persistence (`min_track_hits: 5`) and meet minimum size requirements (`min_vehicle_width_px: 90`).
   - Readings execute every N frames (`ocr_every_n_frames: 5`) up to a hard cap (`max_reads_per_track: 20`).
   - Crucially, **OCR halts immediately once consensus becomes stable**, drastically reducing total inference load.

5. **Two-Tier Consensus Voting Engine:**
   - **Exact-String Consensus:** Reads are weighted by OCR confidence, crop sharpness/quality, and format validity (`strict` = 1.0, `loose` = 0.6, `invalid` = 0.3). The plate text with dominant weighted share wins.
   - **Positional Character Vote:** If reads disagree or no single reading commands >= 50% share, character-by-character voting executes across the dominant string length. This successfully repairs plates where every single read had a differing transient error.

6. **Dedicated Thread Worker & Mode-Aware Queueing:**
   - ANPR runs on an isolated background worker thread (`anpr-worker`) connected via a bounded queue (`queue_size: 32`).
   - Offline mode uses blocking backpressure to ensure 100% deterministic reproducibility.
   - Live mode uses drop-oldest eviction so slow OCR never degrades video streaming or tracking latency.
   - Vehicle crops are strictly copied at submit time (`image[y1:y2, x1:x2].copy()`) so concurrent rendering operations never mutate OCR inputs.

7. **Event & Record Semantics:**
   - Emits `PLATE_RECOGNIZED` event when a plate first achieves stability (`final: false`).
   - On tracker removal, finalizes state and emits an event (`final: true`) if the finalized consensus differs or was never previously emitted.
   - Bounded records are streamed to `anpr/plates.jsonl` and best plate crops are saved to `anpr/plates/<camera>_<vehicle_id>.jpg` as security audit evidence.
   - Bounded memory guarantees: vehicle tracking states are pruned upon completion.

8. **Watchlist Integration Baseline:**
   - Based on confidence calibration experiments, a confidence threshold of **0.60** is established for automated Watchlist alerts on Day 9.

## Consequences
- Zero inference stall on primary video detection and tracking loops.
- Resilient character recognition even under transient occlusions and vibration artifacts.
- Zero committed personal data (all plate images and evaluation outputs remain strictly gitignored).
