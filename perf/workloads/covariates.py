"""Workload covariate calculator and clip metadata provider.

Covariates explain performance variance across runs:
- Mean and p95 detections per frame (governs detector and ByteTrack load)
- Expected vehicles per minute
- Expected OCR calls per second (governs PaddleOCR and consensus load)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class WorkloadCovariates:
    profile: str
    description: str
    nominal_resolution: str
    mean_detections_per_frame: float
    p95_detections_per_frame: float
    expected_vehicles_per_min: float
    expected_ocr_calls_per_sec: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "description": self.description,
            "nominal_resolution": self.nominal_resolution,
            "mean_detections_per_frame": self.mean_detections_per_frame,
            "p95_detections_per_frame": self.p95_detections_per_frame,
            "expected_vehicles_per_min": self.expected_vehicles_per_min,
            "expected_ocr_calls_per_sec": self.expected_ocr_calls_per_sec,
        }


COVARIATE_CATALOG: Dict[str, WorkloadCovariates] = {
    "light": WorkloadCovariates(
        profile="light",
        description="Sparse perimeter, open road, rare movement",
        nominal_resolution="720p",
        mean_detections_per_frame=1.4,
        p95_detections_per_frame=2.0,
        expected_vehicles_per_min=4.0,
        expected_ocr_calls_per_sec=0.1,
    ),
    "typical": WorkloadCovariates(
        profile="typical",
        description="Standard border gate traffic, mixed pedestrians and cars",
        nominal_resolution="720p",
        mean_detections_per_frame=4.2,
        p95_detections_per_frame=6.0,
        expected_vehicles_per_min=18.0,
        expected_ocr_calls_per_sec=1.2,
    ),
    "heavy": WorkloadCovariates(
        profile="heavy",
        description="Crowded border chokepoint, dense vehicle ingress",
        nominal_resolution="1080p",
        mean_detections_per_frame=8.8,
        p95_detections_per_frame=12.5,
        expected_vehicles_per_min=36.0,
        expected_ocr_calls_per_sec=4.5,
    ),
}


def get_workload_covariates(profile: str = "typical") -> WorkloadCovariates:
    """Retrieve verified covariates for a specific workload profile."""
    return COVARIATE_CATALOG.get(profile, COVARIATE_CATALOG["typical"])
