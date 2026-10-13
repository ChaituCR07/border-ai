from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse

router = APIRouter()
BOUNDARY = "frame"


def get_pipeline(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(status_code=503,
                            detail="Pipeline not running. Start it with: "
                                   "python scripts/run_pipeline.py --serve")
    return pipeline


def _check_camera(pipeline, camera_id: str) -> None:
    if camera_id not in pipeline.camera_ids:
        raise HTTPException(status_code=404, detail=f"Unknown camera: {camera_id}")


def mjpeg_chunks(pipeline, camera_id: str):
    """Yields multipart MJPEG chunks of the newest annotated frame, until the pipeline stops."""
    last_seq = 0
    while True:
        seq, image = pipeline.hub.wait_for_new(camera_id, last_seq, timeout=2.0)
        if seq is None:
            if pipeline.stopped:
                return
            continue
        last_seq = seq
        data = pipeline.hub.jpeg(camera_id, seq, image)
        if not data:
            continue
        yield (b"--" + BOUNDARY.encode() + b"\r\nContent-Type: image/jpeg\r\n"
               b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")


@router.get("/pipeline/status")
def pipeline_status(pipeline=Depends(get_pipeline)):
    return pipeline.status()


@router.get("/events/recent")
def recent_events(limit: int = Query(50, ge=1, le=500), camera_id: Optional[str] = None,
                  pipeline=Depends(get_pipeline)):
    return {"events": pipeline.events.recent_records(limit, camera_id)}


@router.get("/snapshot/{camera_id}")
def snapshot(camera_id: str, pipeline=Depends(get_pipeline)):
    _check_camera(pipeline, camera_id)
    image = pipeline.hub.latest_image(camera_id)
    if image is None:
        raise HTTPException(status_code=404, detail="No frame yet")
    data = pipeline.hub.jpeg(camera_id, pipeline.hub.seq(camera_id), image)
    return Response(content=data, media_type="image/jpeg")


@router.get("/stream/{camera_id}")
def stream(camera_id: str, pipeline=Depends(get_pipeline)):
    _check_camera(pipeline, camera_id)
    return StreamingResponse(mjpeg_chunks(pipeline, camera_id),
                             media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Border-AI Surveillance Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(17, 24, 39, 0.75);
      --border: rgba(255, 255, 255, 0.1);
      --accent: #06b6d4;
      --accent-glow: rgba(6, 182, 212, 0.25);
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }
    header {
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 0.85rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
    }
    .brand-badge {
      background: linear-gradient(135deg, #06b6d4, #3b82f6);
      color: #fff;
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .live-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--success);
      padding: 0.3rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .dot {
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }
    .links a {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.85rem;
      margin-left: 1rem;
      transition: color 0.2s;
    }
    .links a:hover { color: var(--text); }
    main {
      padding: 1.5rem;
      max-width: 1700px;
      margin: 0 auto;
      width: 100%;
      display: grid;
      grid-template-columns: 1fr 380px;
      gap: 1.5rem;
      flex: 1;
    }
    .video-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .card-header {
      padding: 0.85rem 1.25rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .camera-select {
      background: rgba(30, 41, 59, 0.8);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 500;
    }
    .stream-viewport {
      position: relative;
      background: #000;
      min-height: 480px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .stream-viewport img {
      width: 100%;
      height: auto;
      max-height: 720px;
      object-fit: contain;
      display: block;
    }
    .telemetry-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      padding: 0.75rem;
      background: rgba(15, 23, 42, 0.6);
      border-top: 1px solid var(--border);
      gap: 0.5rem;
    }
    .metric {
      padding: 0.5rem;
      text-align: center;
      border-right: 1px solid var(--border);
    }
    .metric:last-child { border-right: none; }
    .metric-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 1.15rem;
      font-weight: 700;
      color: #fff;
    }
    .metric-lbl {
      font-size: 0.7rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 2px;
    }
    .sidebar {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      display: flex;
      flex-direction: column;
      height: 100%;
      max-height: calc(100vh - 120px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .events-feed {
      flex: 1;
      overflow-y: auto;
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }
    .event-item {
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.75rem;
      transition: all 0.2s;
    }
    .event-item:hover {
      background: rgba(30, 41, 59, 0.9);
      border-color: rgba(6, 182, 212, 0.4);
    }
    .event-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.35rem;
    }
    .event-type {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      text-transform: uppercase;
      font-family: 'JetBrains Mono', monospace;
    }
    .type-plate { background: rgba(6, 182, 212, 0.2); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.4); }
    .type-zone { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .type-line { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .event-time { font-size: 0.7rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
    .event-desc { font-size: 0.8rem; color: #e2e8f0; line-height: 1.3; }
    .plate-badge {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      background: #fef08a;
      color: #713f12;
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
      border: 1px solid #ca8a04;
    }
    @media (max-width: 1024px) {
      main { grid-template-columns: 1fr; }
      .panel { max-height: 400px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>🛡️ Border-AI</span>
      <span class="brand-badge">Surveillance Console</span>
    </div>
    <div style="display:flex; align-items:center; gap: 1rem;">
      <div class="live-indicator">
        <span class="dot"></span>
        <span>Engine Active</span>
      </div>
      <div class="links">
        <a href="/pipeline/status" target="_blank">Status JSON</a>
        <a href="/docs" target="_blank">API Docs</a>
      </div>
    </div>
  </header>

  <main>
    <div class="video-card">
      <div class="card-header">
        <div style="display:flex; align-items:center; gap:0.6rem;">
          <strong id="cam-name">Live Camera Feed</strong>
          <span style="font-size:0.75rem; color:var(--text-muted);" id="cam-res">1280x720 • ByteTrack & ANPR Active</span>
        </div>
        <select class="camera-select" id="cam-picker" onchange="switchCamera(this.value)">
          <!-- Options populated dynamically -->
        </select>
      </div>

      <div class="stream-viewport">
        <img id="stream-img" src="/stream/CAM_001" alt="Live Stream" onerror="this.src='/snapshot/CAM_001';" />
      </div>

      <div class="telemetry-bar">
        <div class="metric">
          <div class="metric-val" id="metric-proc-fps">--</div>
          <div class="metric-lbl">Inference FPS</div>
        </div>
        <div class="metric">
          <div class="metric-val" id="metric-tracks">--</div>
          <div class="metric-lbl">Active Tracks</div>
        </div>
        <div class="metric">
          <div class="metric-val" id="metric-latency">--</div>
          <div class="metric-lbl">Detection Latency</div>
        </div>
        <div class="metric">
          <div class="metric-val" id="metric-events">--</div>
          <div class="metric-lbl">Events Emitted</div>
        </div>
      </div>
    </div>

    <div class="sidebar">
      <div class="panel">
        <div class="card-header">
          <strong>Security Events Stream</strong>
          <span style="font-size:0.75rem; color:var(--text-muted);" id="events-count">Live Feed</span>
        </div>
        <div class="events-feed" id="events-container">
          <div style="padding:1rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">
            Awaiting events...
          </div>
        </div>
      </div>
    </div>
  </main>

  <script>
    let currentCam = 'CAM_001';

    async function initCameras() {
      try {
        const res = await fetch('/pipeline/status');
        const data = await res.json();
        const picker = document.getElementById('cam-picker');
        picker.innerHTML = '';
        const cams = Object.keys(data.cameras || {});
        cams.forEach((cid, i) => {
          const opt = document.createElement('option');
          opt.value = cid;
          opt.textContent = cid;
          if (i === 0) currentCam = cid;
          picker.appendChild(opt);
        });
        if (cams.length > 0) switchCamera(currentCam);
      } catch (e) {
        console.error('Failed to init cameras:', e);
      }
    }

    function switchCamera(cid) {
      currentCam = cid;
      document.getElementById('cam-name').textContent = cid;
      document.getElementById('stream-img').src = `/stream/${cid}?t=${Date.now()}`;
    }

    async function updateTelemetry() {
      try {
        const res = await fetch('/pipeline/status');
        const data = await res.json();
        if (data.cameras && data.cameras[currentCam]) {
          const c = data.cameras[currentCam];
          document.getElementById('metric-proc-fps').textContent = (c.proc_fps || 0) + ' fps';
          document.getElementById('metric-tracks').textContent = c.tracks_active || 0;
          document.getElementById('metric-events').textContent = data.events_total || 0;
        }
        if (data.stages && data.stages.detect_ms_per_frame) {
          document.getElementById('metric-latency').textContent = data.stages.detect_ms_per_frame.mean_ms.toFixed(1) + ' ms';
        }
      } catch (e) {}
    }

    async function updateEvents() {
      try {
        const res = await fetch('/events/recent?limit=25');
        const json = await res.json();
        const container = document.getElementById('events-container');
        if (!json.events || json.events.length === 0) {
          return;
        }
        container.innerHTML = '';
        json.events.slice().reverse().forEach(ev => {
          const item = document.createElement('div');
          item.className = 'event-item';
          const type = ev.type || 'EVENT';
          let typeClass = 'type-zone';
          if (type.includes('PLATE')) typeClass = 'type-plate';
          else if (type.includes('LINE')) typeClass = 'type-line';

          let desc = `${ev.object?.class || 'object'} #${ev.object?.track_id || ''}`;
          if (ev.details?.plate) {
            desc += ` • Plate: <span class="plate-badge">${ev.details.plate}</span> (${Math.round((ev.confidence||0)*100)}%)`;
          } else if (ev.rule?.name) {
            desc += ` • ${ev.rule.name}`;
          }

          const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '';

          item.innerHTML = `
            <div class="event-top">
              <span class="event-type ${typeClass}">${type}</span>
              <span class="event-time">${timeStr}</span>
            </div>
            <div class="event-desc">${desc}</div>
          `;
          container.appendChild(item);
        });
        document.getElementById('events-count').textContent = `${json.events.length} Recent`;
      } catch (e) {}
    }

    initCameras();
    setInterval(updateTelemetry, 1500);
    setInterval(updateEvents, 2000);
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def index_dashboard(request: Request):
    get_pipeline(request)
    return HTMLResponse(content=DASHBOARD_HTML)
