from config import CHAT_MODEL, EMBEDDING_MODEL
from ai.availability import is_available


def print_startup_info() -> None:
    state = "enabled" if is_available() else "disabled (OPENAI_API_KEY is not set)"
    print(f"[CMS] AI: {state} | chat={CHAT_MODEL} | embeddings={EMBEDDING_MODEL}")
