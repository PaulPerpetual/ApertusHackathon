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

# Optional protection for a public deployment: HTTP basic auth on every page and API call.
DEMO_USER = os.getenv("DEMO_USER", "suva")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")
# READ_ONLY=1 disables edits and on-demand summaries (e.g. for a public showcase link)
READ_ONLY = os.getenv("READ_ONLY", "").lower() in ("1", "true", "yes")

# Hosted API (docs/API.md "Hosted API"): reads are public, writes need a personal editor key
# in the X-Lex-Key header. Only SHA-256 hashes live on the server:
#   LEX_EDITOR_KEYS="miguel:<sha256 hex>,paul:<sha256 hex>"
# The key's name becomes the editor of record, so the "editor" field in a request can't be spoofed.
# Unset = no key check (local development).
EDITOR_KEYS = {}
for _pair in filter(None, (p.strip() for p in os.getenv("LEX_EDITOR_KEYS", "").split(","))):
    _name, _, _digest = _pair.partition(":")
    EDITOR_KEYS[_digest.strip().lower()] = _name.strip()
# Browser origins allowed to call the API cross-site, e.g. "https://paulperpetual.github.io"
CORS_ORIGINS = [o.strip() for o in os.getenv("LEX_CORS_ORIGINS", "").split(",") if o.strip()]
# Cap on concurrent on-demand Apertus jobs (POST /api/judgements), to protect the gateway quota
MAX_JOBS = int(os.getenv("LEX_MAX_JOBS", "2"))
