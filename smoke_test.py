"""Lightweight project smoke test."""
from pathlib import Path

ROOT = Path(__file__).parent
required = [
    "app.py",
    "journalfit_core.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
    "tests/test_core.py",
    ".streamlit/config.toml",
    "Docs/01_Handbook.md",
    "Docs/02_Responsible_Use.md",
]

missing = [path for path in required if not (ROOT / path).exists()]
if missing:
    raise SystemExit(f"Missing required files: {missing}")

app_text = (ROOT / "app.py").read_text(encoding="utf-8")
core_text = (ROOT / "journalfit_core.py").read_text(encoding="utf-8")
if "if __name__ == \"__main__\"" not in app_text:
    raise SystemExit("app.py is missing its executable entrypoint")
if "def recommend(" not in core_text:
    raise SystemExit("journalfit_core.py is missing the recommendation engine")

print("JournalFit Studio smoke test passed.")
