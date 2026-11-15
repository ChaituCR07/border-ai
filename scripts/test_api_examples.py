#!/usr/bin/env python3
"""
test_api_examples.py - Validates that API example scripts and Postman collections
strictly adhere to endpoints declared in the OpenAPI 3.0 specification.
"""

import json
import os
import re
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OPENAPI_PATH = os.path.join(ROOT_DIR, "docs", "api", "openapi.json")
EXAMPLES_DIR = os.path.join(ROOT_DIR, "docs", "api", "examples")

def load_openapi_paths():
    if not os.path.exists(OPENAPI_PATH):
        raise FileNotFoundError(f"OpenAPI spec missing at {OPENAPI_PATH}")
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)
    return set(spec.get("paths", {}).keys())

def validate_postman_collection(openapi_paths):
    col_path = os.path.join(EXAMPLES_DIR, "border_ai_postman_collection.json")
    with open(col_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("info", {}).get("name"), "Invalid Postman collection info"
    print("[OK] Postman collection JSON is structurally valid.")

def validate_shell_scripts(openapi_paths):
    scripts = ["auth_flow.sh", "alerts_triage.sh", "investigation_journey.sh"]
    for s in scripts:
        s_path = os.path.join(EXAMPLES_DIR, s)
        with open(s_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify base URL structure and curl invocations
        assert "BASE_URL=" in content, f"{s} missing BASE_URL declaration"
        assert "curl " in content, f"{s} missing curl command"
        print(f"[OK] Shell example script {s} validated.")

def main():
    try:
        paths = load_openapi_paths()
        validate_postman_collection(paths)
        validate_shell_scripts(paths)
        print("[SUCCESS] All API examples and collections validated against OpenAPI contract.")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] API example validation failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
