"""Central configuration, read from environment variables (and an optional .env file)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[2]
if load_dotenv:
    load_dotenv(ROOT / ".env")

LLM_NAME = os.getenv("LLM_NAME", "apertus-v1-5-70b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MAX_INPUT_CHARS = int(os.getenv("LLM_MAX_INPUT_CHARS", "24000"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))

RELEVANCE_SUMMARY_THRESHOLD = int(os.getenv("RELEVANCE_SUMMARY_THRESHOLD", "60"))

DB_PATH = Path(os.getenv("SUVA_DB", ROOT / "data" / "suva.sqlite"))
CACHE_DIR = ROOT / "data" / "cache"
JUDGEMENTS_DIR = ROOT / "judgements"
EXAMPLES_JSON = ROOT / "data" / "examples.json"
GROUND_TRUTH_XLSX = JUDGEMENTS_DIR / "BG_Urteile_2025_Q4_2026_Q1.xlsx"

USE_MOCK_LLM = not LLM_BASE_URL
