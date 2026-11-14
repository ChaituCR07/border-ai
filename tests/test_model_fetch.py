import hashlib
import json
import os
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.tools.fetch_models import (
    compute_sha256,
    verify_or_fetch_models,
    ModelVerificationError,
    ModelNotFoundError,
)

class TestModelFetch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dest_dir = os.path.join(self.temp_dir.name, "models")
        os.makedirs(self.dest_dir, exist_ok=True)

        # Create dummy model file
        dummy_content = b"fake-yolo-weights-content-for-testing"
        self.dummy_sha = hashlib.sha256(dummy_content).hexdigest()
        
        self.model_rel_path = "detector/test_model.pt"
        self.full_model_path = os.path.join(self.dest_dir, self.model_rel_path)
        os.makedirs(os.path.dirname(self.full_model_path), exist_ok=True)
        with open(self.full_model_path, "wb") as f:
            f.write(dummy_content)

        # Manifest
        self.manifest_path = os.path.join(self.temp_dir.name, "models.lock.json")
        self.manifest = {
            "version": 1,
            "models": [
                {
                    "name": "test-yolo",
                    "path": self.model_rel_path,
                    "sha256": self.dummy_sha,
                    "source": "http://localhost:9999/test_model.pt",
                    "licence": "MIT",
                    "size_mb": 0.01,
                }
            ],
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_existing_valid_model(self):
        verified = verify_or_fetch_models(self.manifest_path, self.dest_dir, offline=True)
        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0]["name"], "test-yolo")

    def test_tampered_model_fails_closed(self):
        # Tamper with model content
        with open(self.full_model_path, "wb") as f:
            f.write(b"tampered-malicious-payload")

        with self.assertRaises(ModelVerificationError):
            verify_or_fetch_models(self.manifest_path, self.dest_dir, offline=True)

    def test_missing_model_in_offline_mode_fails(self):
        os.unlink(self.full_model_path)
        with self.assertRaises(ModelNotFoundError):
            verify_or_fetch_models(self.manifest_path, self.dest_dir, offline=True)

if __name__ == "__main__":
    unittest.main()
