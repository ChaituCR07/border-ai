"""Dataset definitions and protocols for detection and tracking evaluation."""
from evaluation.datasets.base import (
    Box,
    DetSample,
    DetectionDataset,
    GtObject,
    PredObject,
    TrackingDataset,
    TrackingFrame,
    TrackingSequence,
)

__all__ = [
    "Box",
    "GtObject",
    "PredObject",
    "DetSample",
    "DetectionDataset",
    "TrackingFrame",
    "TrackingSequence",
    "TrackingDataset",
]
