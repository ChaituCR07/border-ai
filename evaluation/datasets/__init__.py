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
from evaluation.datasets.bdd100k import Bdd100kDetectionDataset
from evaluation.datasets.cctv_custom import CctvCustomDetectionDataset, CctvCustomTrackingSequence
from evaluation.datasets.coco import CocoDetectionDataset
from evaluation.datasets.mot17 import Mot17Dataset, Mot17Sequence

__all__ = [
    "Box",
    "GtObject",
    "PredObject",
    "DetSample",
    "DetectionDataset",
    "TrackingFrame",
    "TrackingSequence",
    "TrackingDataset",
    "CocoDetectionDataset",
    "Bdd100kDetectionDataset",
    "Mot17Dataset",
    "Mot17Sequence",
    "CctvCustomDetectionDataset",
    "CctvCustomTrackingSequence",
]
