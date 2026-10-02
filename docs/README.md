# Platform Documentation (`docs`)

The `docs/` directory contains engineering specifications, architectural diagrams, benchmark records, and Architecture Decision Records (ADRs) guiding the development and operation of the Border AI platform.

---

## 1. Directory Structure

```text
docs/
├── architecture.md            # Comprehensive multi-service system architecture & data flow
├── benchmarks.md              # Performance metrics (FPS, latency, hardware utilization)
├── images/                    # Architectural diagrams, screenshots, and visual assets
└── decisions/                 # Architecture Decision Records (ADRs)
    ├── 0001-local-dev-approach.md       # ADR 0001: Local host vs containerization approach
    └── 0002-timestamp-convention.md     # ADR 0002: UTC epoch timestamp convention
```

---

## 2. Key Documentation Files

### [`architecture.md`](./architecture.md)
Detailed architectural document outlining:
- Multi-tier system pipeline (Ingestion → YOLO → ByteTrack → ANPR → Threat Scoring → Dashboard)
- Component responsibilities, ports, and communication protocols
- Core design principles (Decoupled observations from threat policies)
- ONVIF discovery specifications

### [`benchmarks.md`](./benchmarks.md)
Living performance log recording benchmark runs across different hardware profiles (NVIDIA GPUs, Apple Silicon MPS, and x86 CPUs), tracking:
- Target resolution and input sizes
- Preprocessing and inference latencies (ms/frame)
- Sustained pipeline FPS across concurrent camera streams

### [`decisions/`](./decisions/)
Architecture Decision Records (ADRs) capturing key architectural trade-offs:
- **ADR 0001:** Local host services (Weeks 1–2) + Docker infrastructure to eliminate GPU container friction during rapid development.
- **ADR 0002:** UTC wall-clock epoch timestamps (`time.time()`) across all live and pre-recorded feeds to maintain temporal consistency in cross-camera tracking.
