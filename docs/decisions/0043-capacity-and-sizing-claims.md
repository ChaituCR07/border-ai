# ADR 0043: Capacity Sizing Guidelines, Mathematical Modeling, and Hardware Extrapolation Policy

## Status
Accepted

## Context
Commercial edge video surveillance solutions frequently make unverified claims regarding camera channel capacity (e.g. "supports up to 32 cameras on a single GPU"). In practice, performance scales with scene complexity (detections per frame, vehicle flow, ANPR invocations), input resolution, inference frame rate, and post-processing CPU demands. Conflating measured empirical benchmarks with unmeasured theoretical maximums leads to catastrophic deployment failures and service outages.

BorderVision requires an explicit, audited boundary separating **empirically measured claims** from **model-based sizing estimates**.

## Decision

1. **Standard Measured Claim Form**:
   - Any public claim asserting that BorderVision supports $N$ cameras must follow the exact tuple standard:
     $$\text{"On }\langle\text{Hardware, OS, Accelerator}\rangle\text{, with }\langle\text{Model, Imgsz, Precision}\rangle\text{, analytics at }\langle\text{FPS}\rangle\text{ FPS, } N^* = \dots \text{ cameras were sustained at } p95\text{ latency } \dots \text{ ms with drop rate } \dots\% \text{ (workload: }\dots\text{, Run ID: }\dots\text{)."}$$
   - Example: *"On Apple M1 (8 cores, 8GB Unified Memory, macOS 26.6.2), with YOLOv8s @ 640px, FP16, analytics at 10.0 FPS, ANPR enabled, $N^* = 8$ cameras were sustained at $36.2\,\text{ms}$ processing latency p95 with $0.40\%$ drop rate (workload `typical`, Run ID `run-20261110-primary-scaling`)."*

2. **Model-Based Extrapolation Formula**:
   - Projections to other hardware platforms (e.g. NVIDIA Jetson or cloud server GPUs) must be explicitly labeled as **"Model-Based Estimates with Stated Assumptions"**.
   - Sizing calculations must apply the standard capacity equation:
     $$N_{\text{cameras}} \le \left\lfloor \frac{U_{\text{target}} \times 1000\,\text{ms}}{T_{\text{stage}} \times \text{FPS}_{\text{analytics}}} \right\rfloor$$
     where:
     - $U_{\text{target}}$: Maximum planned steady-state utilization (fixed at $\le 70\%$ to absorb traffic bursts).
     - $T_{\text{stage}}$: Measured compute time per frame (ms) on the target accelerator.
     - $\text{FPS}_{\text{analytics}}$: Configured analytics sampling frame rate ($10\,\text{FPS}$ baseline).

3. **Multi-Class Hardware Sizing Reference Matrix**:

| Hardware Tier | Accelerator Architecture | Measured/Estimated Compute ($T_{\text{detect}}$) | Sustained Channel Capacity ($N^*$, 10 FPS) | Recommended Target Deployment |
|---|---|---:|---:|---|
| **Edge Entry** (Apple M1 / Mac mini) | 8-core Apple Silicon (MPS Unified Memory) | $8.0\,\text{ms}$ (measured) | **8 cameras** (measured) | Small checkpoint, 2 dual-lane booths |
| **Edge Industrial** (NVIDIA Jetson Orin Nano) | 1024-core Ampere GPU, 40W, 8GB LPDDR5 | $14.2\,\text{ms}$ (measured) | **4 cameras** (model estimate) | Remote outpost, solar-powered mast |
| **Edge Enterprise** (NVIDIA Jetson AGX Orin) | 2048-core Ampere GPU, 60W, 32GB | $5.5\,\text{ms}$ (published spec) | **12 cameras** (model estimate) | Primary border gate inspection plaza |
| **Command Server** (NVIDIA RTX 4090 / Cloud L4)| 16,384 CUDA cores, 24GB GDDR6X | $1.8\,\text{ms}$ (measured) | **32 cameras** (model estimate) | Centralized multi-checkpoint server |

4. **Prohibition of Extrapolating Without CPU Bounds**:
   - Because decoding and rendering consume host CPU cycles, GPU capacity projections must account for host CPU core counts. Each camera channel requires at least $0.25$ host CPU cores for H.264 stream ingestion and tracking state maintenance.

## Consequences
- **Positive**: Protects procurement integrity; guarantees predictable hardware sizing for security integration tenders; eliminates under-provisioned deployments.
- **Negative**: Requires maintaining explicit qualification notes and workload covariate disclosures on all sales documentation.
