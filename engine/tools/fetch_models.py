import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from typing import Dict, Any, List

class ModelVerificationError(Exception):
    """Raised when model file SHA-256 does not match lockfile manifest."""
    pass

class ModelNotFoundError(Exception):
    """Raised when model file is missing in offline mode or download fails."""
    pass

def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 digest of a local file in chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def verify_or_fetch_models(manifest_path: str, dest_dir: str, offline: bool = False) -> List[Dict[str, Any]]:
    """
    Verifies existing model files or securely downloads and verifies them from manifest.
    """
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Model manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    models = manifest.get("models", [])
    verified_models = []

    for item in models:
        name = item.get("name", "unknown")
        rel_path = item.get("path")
        expected_sha = item.get("sha256", "").lower()
        source_url = item.get("source")

        if not rel_path or not expected_sha:
            raise ValueError(f"Invalid manifest entry: {item}")

        target_file = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        if os.path.exists(target_file):
            actual_sha = compute_sha256(target_file)
            if actual_sha == expected_sha:
                print(f"[MODEL OK] Verified {name} at {rel_path} ({expected_sha[:12]}...)")
                verified_models.append(item)
                continue
            else:
                msg = (
                    f"Integrity check failed for {name}!\n"
                    f"Target file: {target_file}\n"
                    f"Expected SHA-256: {expected_sha}\n"
                    f"Actual SHA-256:   {actual_sha}"
                )
                print(f"[MODEL ERROR] {msg}", file=sys.stderr)
                raise ModelVerificationError(msg)

        # File does not exist
        if offline:
            msg = (
                f"Model {name} is missing in offline mode!\n"
                f"Required location: {target_file}\n"
                f"Please pre-populate the models volume or set OFFLINE=0 to allow download."
            )
            print(f"[MODEL OFFLINE ERROR] {msg}", file=sys.stderr)
            raise ModelNotFoundError(msg)

        print(f"[MODEL FETCH] Downloading {name} from {source_url}...")
        dir_name = os.path.dirname(target_file)
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tmp_f:
            tmp_path = tmp_f.name
            try:
                urllib.request.urlretrieve(source_url, tmp_path)
                downloaded_sha = compute_sha256(tmp_path)
                if downloaded_sha != expected_sha:
                    os.unlink(tmp_path)
                    msg = f"Downloaded {name} SHA-256 mismatch! Expected {expected_sha}, got {downloaded_sha}"
                    raise ModelVerificationError(msg)
                
                os.replace(tmp_path, target_file)
                print(f"[MODEL FETCH] Successfully verified and installed {name} to {rel_path}")
                verified_models.append(item)
            except Exception as e:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise e

    print(f"[MODEL INIT SUCCESS] All {len(verified_models)} models verified.")
    return verified_models

def main():
    parser = argparse.ArgumentParser(description="Border-AI Model Initializer and Verifier")
    parser.add_argument("--manifest", default="configs/models.lock.json", help="Path to models.lock.json")
    parser.add_argument("--dest", default="/models", help="Destination directory for model weights")
    parser.add_argument("--offline", action="store_true", help="Disallow downloading from internet")
    args = parser.parse_args()

    offline_env = os.environ.get("OFFLINE", "0") in ("1", "true", "True")
    offline = args.offline or offline_env

    try:
        verify_or_fetch_models(args.manifest, args.dest, offline=offline)
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL] Model initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
