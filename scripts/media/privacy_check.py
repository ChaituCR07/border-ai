#!/usr/bin/env python3
"""
privacy_check.py - Audits media assets and documentation for privacy leaks,
sensitive tokens, credentials, and image size constraints per ADR 0055.
"""

import os
import re
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MEDIA_DIR = os.path.join(ROOT_DIR, "docs", "media")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")

MAX_GIF_BYTES = 8 * 1024 * 1024       # 8 MB
MAX_PNG_BYTES = 500 * 1024            # 500 KB

def audit_media_files():
    issues = []
    if not os.path.exists(MEDIA_DIR):
        return issues

    for root, _, files in os.walk(MEDIA_DIR):
        for f in files:
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            
            if f.endswith(".gif") and size > MAX_GIF_BYTES:
                issues.append(f"GIF exceeds 8MB budget: {f} ({size / 1024 / 1024:.2f} MB)")
            elif f.endswith(".png") and size > MAX_PNG_BYTES:
                issues.append(f"PNG exceeds 500KB budget: {f} ({size / 1024:.2f} KB)")
                
    return issues

def audit_text_privacy():
    issues = []
    jwt_pattern = re.compile(r"eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}")
    
    for root, _, files in os.walk(DOCS_DIR):
        for f in files:
            if not f.endswith((".md", ".json", ".html", ".sh")):
                continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
                
            if jwt_pattern.search(content):
                issues.append(f"Potential un-sanitized JWT token detected in {os.path.relpath(path, ROOT_DIR)}")
                
    return issues

def main():
    media_issues = audit_media_files()
    text_issues = audit_text_privacy()
    all_issues = media_issues + text_issues

    if all_issues:
        print("[ERROR] Privacy and media audit found issues:")
        for iss in all_issues:
            print(f"  - {iss}")
        sys.exit(1)
    else:
        print("[OK] Privacy and media hygiene audit passed with 0 violations.")
        sys.exit(0)

if __name__ == "__main__":
    main()
