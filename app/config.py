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
        return os.getenv("GEMINI_API_KEY", os.getenv("OPENROUTER_API_KEY", "")).strip()

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", os.getenv("GEMINI_API_KEY", "")).strip()

    @property
    def openrouter_base_url(self) -> str:
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()

    @property
    def is_openrouter(self) -> bool:
        key = self.openrouter_api_key
        return bool(key and key.startswith("sk-or-"))

    @property
    def gemini_model(self) -> str:
        default_model = "google/gemini-2.5-flash" if self.is_openrouter else "gemini-2.5-flash"
        return os.getenv("GEMINI_MODEL", default_model).strip()

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
