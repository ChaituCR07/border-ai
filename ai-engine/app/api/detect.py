import time
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from app.detection.detector import Detector
from app.pipeline.visualizer import draw_detections
from app.schemas.api import DetectionResponse
from ingestion.frame import Frame

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024        # 10 MB


def get_detector(request: Request) -> Detector:
    detector = getattr(request.app.state, "detector", None)
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not loaded")
    return detector


def _decode_image(upload: UploadFile) -> np.ndarray:
    data = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image")
    return image


@router.post("/detect", response_model=DetectionResponse)
def detect(
    file: UploadFile = File(...),
    camera_id: str = Query("API"),
    conf: Optional[float] = Query(None, ge=0.0, le=1.0),
    iou: Optional[float] = Query(None, ge=0.0, le=1.0),
    detector: Detector = Depends(get_detector),
):
    """Image in, structured detections out."""
    image = _decode_image(file)
    frame = Frame(camera_id=camera_id, frame_id=0, timestamp=time.time(),
                  video_time_ms=0.0, image=image, source_fps=0.0)
    return detector.detect_frame(frame, conf=conf, iou=iou).to_dict()


@router.post("/detect/annotated")
def detect_annotated(
    file: UploadFile = File(...),
    conf: Optional[float] = Query(None, ge=0.0, le=1.0),
    iou: Optional[float] = Query(None, ge=0.0, le=1.0),
    detector: Detector = Depends(get_detector),
):
    """Image in, JPEG with boxes drawn out. Handy for visual checks in Swagger."""
    image = _decode_image(file)
    detections = detector.detect(image, conf=conf, iou=iou)
    ok, buf = cv2.imencode(".jpg", draw_detections(image, detections))
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode image")
    return Response(content=buf.tobytes(), media_type="image/jpeg",
                    headers={"X-Detections": str(len(detections))})


@router.get("/model/info")
def model_info(detector: Detector = Depends(get_detector)):
    return detector.info()
