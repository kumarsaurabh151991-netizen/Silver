from config import OPENAI_API_KEY


def is_available() -> bool:
    return bool(OPENAI_API_KEY)
