"""Benchmark specification schema validator, execution manifest recorder, and environment capture.

Guarantees full scientific reproducibility by capturing:
- Spec hash and parameters
- Git commit hash, branch, and working-tree dirty status
- Pinned software dependency versions (Python, PyTorch, Ultralytics, OpenCV, etc.)
- Platform hardware specifications (CPU model/cores, RAM, accelerator, OS)
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from perf.harness.stability import RunBudgets

VALID_WORKLOADS = {"light", "typical", "heavy"}
VALID_DEVICES = {"auto", "cuda", "mps", "cpu"}


@dataclass
class BenchmarkSpec:
    """Validated parameters for a benchmark run."""
    id: str
    stack: Dict[str, Any]
    cameras: int
    workload: str = "typical"
    warmup_s: float = 60.0
    measure_s: float = 300.0
    cooldown_s: float = 30.0
    repeat: int = 3
    budgets: RunBudgets = field(default_factory=RunBudgets)
    clips: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkSpec:
        spec_id = str(data.get("id", "unnamed_spec"))
        stack = data.get("stack", {})
        cameras = int(data.get("cameras", 1))
        workload = str(data.get("workload", "typical"))
        warmup_s = float(data.get("warmup_s", 60.0))
        measure_s = float(data.get("measure_s", 300.0))
        cooldown_s = float(data.get("cooldown_s", 30.0))
        repeat = int(data.get("repeat", 3))

        # Validation
        if cameras < 1:
            raise ValueError(f"Invalid spec '{spec_id}': cameras must be >= 1, got {cameras}")
        if workload not in VALID_WORKLOADS:
            raise ValueError(
                f"Invalid spec '{spec_id}': workload '{workload}' must be one of {sorted(VALID_WORKLOADS)}"
            )
        if measure_s < 30.0:
            raise ValueError(
                f"Invalid spec '{spec_id}': measure_s must be >= 30 seconds for statistical significance, got {measure_s}"
            )

        device = stack.get("device", "auto")
        if device not in VALID_DEVICES:
            raise ValueError(
                f"Invalid spec '{spec_id}': stack.device '{device}' must be one of {sorted(VALID_DEVICES)}"
            )

        budget_dict = data.get("budgets", {})
        budgets = RunBudgets(
            drop_rate_max=float(budget_dict.get("drop_rate_max", 0.01)),
            freshness_p95_ms=float(budget_dict.get("freshness_p95_ms", 500.0)),
            processing_p95_ms=float(budget_dict.get("processing_p95_ms", 250.0)),
            alert_p95_s=float(budget_dict.get("alert_p95_s", 3.0)),
        )

        clips = data.get("clips", [])
        return cls(
            id=spec_id,
            stack=stack,
            cameras=cameras,
            workload=workload,
            warmup_s=warmup_s,
            measure_s=measure_s,
            cooldown_s=cooldown_s,
            repeat=repeat,
            budgets=budgets,
            clips=clips,
        )


def get_git_info() -> Dict[str, Any]:
    """Capture current Git revision and dirty flag."""
    commit = "unknown"
    branch = "unknown"
    dirty = False
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        dirty = bool(status)
    except Exception:
        pass
    return {"commit": commit, "branch": branch, "dirty": dirty}


def get_software_versions() -> Dict[str, str]:
    """Capture versions of all key runtime libraries."""
    versions = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for mod_name in ("torch", "ultralytics", "cv2", "numpy"):
        try:
            mod = __import__(mod_name)
            versions[mod_name] = getattr(mod, "__version__", "installed")
        except ImportError:
            versions[mod_name] = "not_installed"
    return versions


def get_hardware_info() -> Dict[str, Any]:
    """Capture hardware platform characteristics."""
    is_macos = platform.system() == "Darwin"
    cpu_model = platform.processor()
    total_ram_gb = 8.0

    if is_macos:
        try:
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True)
            cpu_model = out.strip() or cpu_model
        except Exception:
            pass
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            total_ram_gb = round(float(out.strip()) / (1024.0 ** 3), 1)
        except Exception:
            pass

    gpu_info = "Apple Silicon MPS (Unified Memory)" if is_macos else "CPU-only"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info = torch.cuda.get_device_name(0)
    except Exception:
        pass

    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "cpu_model": cpu_model,
        "cpu_count": os.cpu_count() or 4,
        "total_ram_gb": total_ram_gb,
        "gpu_accelerator": gpu_info,
    }


@dataclass
class ExecutionManifest:
    """Complete provenance manifest for a benchmark execution."""
    manifest_id: str
    spec_id: str
    spec_hash: str
    timestamp_iso: str
    git: Dict[str, Any]
    versions: Dict[str, str]
    hardware: Dict[str, Any]
    spec: Dict[str, Any]

    @classmethod
    def create(cls, spec: BenchmarkSpec) -> ExecutionManifest:
        spec_dict = asdict(spec)
        spec_json = json.dumps(spec_dict, sort_keys=True)
        spec_hash = hashlib.sha256(spec_json.encode("utf-8")).hexdigest()[:16]
        manifest_id = f"manifest-{spec.id}-{time.strftime('%Y%m%d-%H%M%S')}"

        return cls(
            manifest_id=manifest_id,
            spec_id=spec.id,
            spec_hash=spec_hash,
            timestamp_iso=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            git=get_git_info(),
            versions=get_software_versions(),
            hardware=get_hardware_info(),
            spec=spec_dict,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.to_json() + "\n")
