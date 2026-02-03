"""
Configuración central del orquestador E-14
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="e14_scraper", env="DB_NAME")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_password: str = Field(default="postgres", env="DB_PASSWORD")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Workers
    num_workers: int = Field(default=20, env="NUM_WORKERS")
    requests_per_minute_per_worker: int = Field(default=30, env="REQUESTS_PER_MINUTE")

    # Scraping
    base_url: str = "https://e14_congreso_2022.registraduria.gov.co"
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")

    # CAPTCHA (2Captcha)
    captcha_api_key: Optional[str] = Field(default=None, env="CAPTCHA_API_KEY")
    captcha_enabled: bool = Field(default=True, env="CAPTCHA_ENABLED")

    # Proxies
    proxy_list_file: Optional[str] = Field(default=None, env="PROXY_LIST_FILE")
    use_proxies: bool = Field(default=False, env="USE_PROXIES")

    # Storage
    output_dir: str = Field(default="./output", env="OUTPUT_DIR")
    save_images: bool = Field(default=True, env="SAVE_IMAGES")

    # Monitoring
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    progress_update_interval: int = Field(default=10, env="PROGRESS_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
