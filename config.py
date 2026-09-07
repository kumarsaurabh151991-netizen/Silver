from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DB_PATH", str(ROOT_DIR / "data")))
if DATA_DIR.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
    DB_FILE = DATA_DIR
    DATA_DIR = DB_FILE.parent
else:
    DB_FILE = DATA_DIR / "cms.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
SIDECAR_URL = os.getenv("SIDECAR_URL", "http://127.0.0.1:8001").rstrip("/")
