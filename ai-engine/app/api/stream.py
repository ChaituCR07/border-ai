from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

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
