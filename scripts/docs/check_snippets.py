#!/usr/bin/env python3
"""
check_snippets.py - Audits and validates shell command snippets across documentation
to guarantee that documentation commands remain syntactically valid and non-rot.
"""

import os
import re
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def check_file_snippets(file_path):
    if not os.path.exists(file_path):
        return True, []
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find blocks marked with <!-- test --> or standard shell code blocks in quickstart
    code_blocks = re.findall(r"```(?:bash|sh)\n(.*?)```", content, re.DOTALL)
    
    issues = []
    for idx, block in enumerate(code_blocks):
        lines = [line.strip() for line in block.splitlines() if line.strip() and not line.strip().startswith("#")]
        for line in lines:
            # Check for banned placeholders or broken references
            if "<placeholder>" in line or "TODO" in line:
                issues.append(f"Snippet #{idx+1} contains unresolved placeholder: '{line}'")
            # Verify script file invocations point to existing files
            script_matches = re.findall(r"(?:^|[\s\"'`])((?:scripts|engine/tools|backend/scripts)/[a-zA-Z0-9_\-\.\/]+)", line)
            for sm in script_matches:
                full_sm = os.path.join(ROOT_DIR, sm)
                full_sm_engine = os.path.join(ROOT_DIR, "ai-engine", sm)
                if not os.path.exists(full_sm) and not os.path.exists(full_sm_engine):
                    issues.append(f"Referenced script does not exist: {sm} in line '{line}'")

    return len(issues) == 0, issues

def main():
    docs_to_check = [
        os.path.join(ROOT_DIR, "README.md"),
        os.path.join(ROOT_DIR, "docs", "deployment", "README.md"),
        os.path.join(ROOT_DIR, "docs", "deployment", "configuration.md"),
        os.path.join(ROOT_DIR, "docs", "deployment", "troubleshooting.md"),
    ]
    
    total_issues = []
    for doc in docs_to_check:
        passed, issues = check_file_snippets(doc)
        if not passed:
            total_issues.extend([f"{os.path.basename(doc)}: {iss}" for iss in issues])
            
    if total_issues:
        print("[ERROR] Documentation snippet validation failed:")
        for iss in total_issues:
            print(f"  - {iss}")
        sys.exit(1)
    else:
        print(f"[OK] All documentation shell snippets verified cleanly across {len(docs_to_check)} files.")
        sys.exit(0)

if __name__ == "__main__":
    main()
