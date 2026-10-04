from typing import List

from pydantic import BaseModel, ConfigDict, Field


class FrameSize(BaseModel):
    width: int
    height: int


class ObjectOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    class_name: str = Field(alias="class")     # "class" is a reserved word in Python
    class_id: int
    confidence: float
    bbox: List[float]


class DetectionResponse(BaseModel):
    camera_id: str
    frame_id: int
    timestamp: str
    frame_size: FrameSize
    inference_ms: float
    objects: List[ObjectOut]
