import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))
    FALLBACK_MODE: bool = os.getenv("FALLBACK_MODE", "true").lower() == "true"


settings = Settings()
