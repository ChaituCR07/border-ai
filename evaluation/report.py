"""Evaluation report aggregator generating publication-ready Markdown tables."""
import json
import os
from typing import Any, Dict, List, Optional

from evaluation.common.tables import markdown_table


def generate_detection_summary_markdown(manifest_path: str) -> str:
    """Reads a detection run manifest and formats a complete markdown summary."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_dir = os.path.dirname(manifest_path)
    metrics_path = os.path.join(run_dir, "metrics.json")
    classes_dict = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as mf:
            classes_dict = json.load(mf)
    else:
        classes_dict = data.get("metrics_summary", {}).get("evaluated_classes", {})

    model_name = data.get("model", {}).get("name") if isinstance(data.get("model"), dict) else data.get("model_name")
    dataset_name = data.get("dataset", {}).get("name") if isinstance(data.get("dataset"), dict) else data.get("dataset_name")
    timestamp = data.get("started_at") or data.get("timestamp") or "N/A"
    git_commit = (data.get("git_commit") or "unknown")[:8]

    meta = [
        f"**Run ID:** `{data.get('run_id')}`",
        f"**Model:** `{model_name}`",
        f"**Dataset:** `{dataset_name}`",
        f"**Git Commit:** `{git_commit}`",
        f"**Timestamp:** `{timestamp}`",
    ]

    headers = ["Class", "TP", "FP", "FN", "Precision", "Recall", "F1", "AP@50", "mAP@50:95", "Footpoint Err"]
    rows = []
    for cls_name, m in classes_dict.items():
        rows.append([
            cls_name,
            str(m.get("tp", 0)),
            str(m.get("fp", 0)),
            str(m.get("fn", 0)),
            f"{m.get('precision', 0.0):.3f}",
            f"{m.get('recall', 0.0):.3f}",
            f"{m.get('f1', 0.0):.3f}",
            f"{m.get('ap50', 0.0):.3f}",
            f"{m.get('map_50_95', 0.0):.3f}",
            f"{m.get('footpoint_err_px', 0.0):.1f} px",
        ])

    table_md = markdown_table(headers, rows)
    return "### Detection Evaluation Summary\n\n" + "\n".join(meta) + "\n\n" + table_md + "\n"


def generate_tracking_summary_markdown(manifest_path: str) -> str:
    """Reads a tracking run manifest and formats a complete markdown summary."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    run_dir = os.path.dirname(manifest_path)
    metrics_path = os.path.join(run_dir, "metrics.json")
    ms = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as mf:
            ms = json.load(mf)
    else:
        ms = data.get("metrics_summary", {})

    tracker_name = data.get("model", {}).get("name") if isinstance(data.get("model"), dict) else data.get("model_name")
    dataset_name = data.get("dataset", {}).get("name") if isinstance(data.get("dataset"), dict) else data.get("dataset_name")
    timestamp = data.get("started_at") or data.get("timestamp") or "N/A"
    git_commit = (data.get("git_commit") or "unknown")[:8]

    meta = [
        f"**Run ID:** `{data.get('run_id')}`",
        f"**Tracker:** `{tracker_name}`",
        f"**Dataset:** `{dataset_name}`",
        f"**Git Commit:** `{git_commit}`",
        f"**Timestamp:** `{timestamp}`",
    ]

    headers = ["Metric", "Value"]
    rows = [
        ["HOTA", f"{ms.get('hota', 0.0):.3f}"],
        ["MOTA", f"{ms.get('mota', 0.0):.3f}"],
        ["IDF1", f"{ms.get('idf1', 0.0):.3f}"],
        ["ID Switches", str(ms.get("idsw", 0))],
        ["Mean Track Continuity", f"{ms.get('continuity', 0.0):.2f}"],
    ]

    table_md = markdown_table(headers, rows)
    return "### Tracking Evaluation Summary\n\n" + "\n".join(meta) + "\n\n" + table_md + "\n"
