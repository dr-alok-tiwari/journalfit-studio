"""Lightweight project smoke test."""
from pathlib import Path

ROOT = Path(__file__).parent
required = [
    "app.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
    "Docs/01_Handbook.md",
    "Docs/02_Responsible_Use.md",
]

missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    raise SystemExit(f"Missing required files: {missing}")

print("JournalFit Studio smoke test passed.")
