# Automation & Utility Scripts (`scripts`)

The `scripts/` directory contains shell and automation scripts used for project bootstrapping, environment preparation, and operational maintenance.

---

## 1. Directory Structure

```text
scripts/
└── setup.sh                   # Scaffolds the complete multi-service directory hierarchy
```

---

## 2. Available Scripts

### `setup.sh`
Automates the creation of all required directories, subdirectories, and `.gitkeep` placeholders for `ai-engine`, `video-ingestion`, `backend`, `frontend`, `configs`, `datasets`, and `outputs`.

#### Usage
From the project root:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

---

## 3. Script Conventions
- All shell scripts must start with `#!/usr/bin/env bash` and `set -e` to exit immediately if any command fails.
- Scripts must normalize line endings to Unix LF via `.gitattributes`.
