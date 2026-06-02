from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    exact_client_id: str = Field(..., env="EXACT_CLIENT_ID")
    exact_client_secret: str = Field(..., env="EXACT_CLIENT_SECRET")
    exact_redirect_uri: str = Field("http://localhost:8000/auth/callback", env="EXACT_REDIRECT_URI")
    exact_base_url: str = Field("https://start.exactonline.nl", env="EXACT_BASE_URL")
    token_file: str = Field(".tokens.json", env="TOKEN_FILE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
