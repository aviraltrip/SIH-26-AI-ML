import os
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
env_example_path = Path(__file__).resolve().parent.parent / ".env.example"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
elif env_example_path.exists():
    load_dotenv(dotenv_path=env_example_path)
else:
    load_dotenv()


class Settings:
    """Application configuration settings loaded from environment variables."""

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "").strip()

    @property
    def gemini_model(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

    @property
    def port(self) -> int:
        port_val = os.getenv("PORT", "8000")
        try:
            return int(port_val)
        except ValueError:
            return 8000


@lru_cache()
def get_settings() -> Settings:
    return Settings()
