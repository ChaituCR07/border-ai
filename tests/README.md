# Testing Suite & Verification Strategy (`tests`)

The `tests/` directory houses cross-service integration tests, end-to-end pipeline verifications, and regression suites for the Border AI platform.

---

## 1. Testing Architecture

The platform follows a three-tiered testing hierarchy:

1. **Unit & Ingestion Tests (`video-ingestion/tests/`):**
   - Validates `FileSource`, `RtspSource`, frame skipping, aspect-ratio preservation, and `CameraManager` worker threads using synthetic OpenCV videos.
2. **AI Engine Tests (`ai-engine/tests/`):**
   - Tests YOLO model loading, class filtering (`person`, `vehicle`), confidence thresholds, and spatial polygon intersections.
3. **Cross-Service Integration Tests (`tests/`):**
   - Validates the end-to-end flow: Ingested frame → AI Detection → Threat Scoring → Redis Streams message emission → PostgreSQL event record → WebSocket client reception.

---

## 2. Running Tests

### Run Ingestion Test Suite
```bash
source .venv/bin/activate
pytest video-ingestion/tests -v
```

### Run Cross-Service Integration Suite
```bash
source .venv/bin/activate
pytest tests/ -v
```

### Run Backend Tests
```bash
cd backend
npm test
```
