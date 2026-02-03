"""
Configuration for E-14 Scraper module.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    """Scraper configuration settings."""

    # Database (uses main Castor DB)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "castor_elecciones"
    db_user: str = "castor"
    db_password: str = ""

    # Workers
    num_workers: int = 10
    requests_per_minute_per_worker: int = 30

    # Scraping
    base_url: str = "https://e14_congreso_2022.registraduria.gov.co"
    request_timeout: int = 30
    max_retries: int = 3

    # CAPTCHA (2Captcha)
    captcha_api_key: Optional[str] = None
    captcha_enabled: bool = True

    # Proxies
    proxy_list_file: Optional[str] = None
    use_proxies: bool = False

    # Storage
    output_dir: str = "./output/e14_scraper"
    save_images: bool = True

    # Monitoring
    log_level: str = "INFO"
    progress_update_interval: int = 10

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @classmethod
    def from_env(cls) -> "ScraperConfig":
        """Load configuration from environment variables."""
        # Parse DATABASE_URL if available
        db_url = os.getenv("DATABASE_URL", "")
        db_host = "localhost"
        db_port = 5432
        db_name = "castor_elecciones"
        db_user = "castor"
        db_password = ""

        if db_url and db_url.startswith("postgresql://"):
            # Parse postgresql://user:pass@host:port/db
            try:
                from urllib.parse import urlparse
                parsed = urlparse(db_url)
                db_host = parsed.hostname or db_host
                db_port = parsed.port or db_port
                db_name = parsed.path.lstrip("/") or db_name
                db_user = parsed.username or db_user
                db_password = parsed.password or db_password
            except Exception:
                pass

        return cls(
            db_host=os.getenv("DB_HOST", db_host),
            db_port=int(os.getenv("DB_PORT", str(db_port))),
            db_name=os.getenv("DB_NAME", db_name),
            db_user=os.getenv("DB_USER", db_user),
            db_password=os.getenv("DB_PASSWORD", db_password),
            num_workers=int(os.getenv("SCRAPER_NUM_WORKERS", "10")),
            requests_per_minute_per_worker=int(os.getenv("SCRAPER_REQUESTS_PER_MINUTE", "30")),
            base_url=os.getenv(
                "SCRAPER_BASE_URL",
                "https://e14_congreso_2022.registraduria.gov.co"
            ),
            request_timeout=int(os.getenv("SCRAPER_REQUEST_TIMEOUT", "30")),
            max_retries=int(os.getenv("SCRAPER_MAX_RETRIES", "3")),
            captcha_api_key=os.getenv("CAPTCHA_2_API_KEY"),
            captcha_enabled=os.getenv("CAPTCHA_SOLVER_ENABLED", "true").lower() == "true",
            proxy_list_file=os.getenv("PROXY_LIST_FILE"),
            use_proxies=os.getenv("USE_PROXY_ROTATION", "false").lower() == "true",
            output_dir=os.getenv("SCRAPER_OUTPUT_DIR", "./output/e14_scraper"),
            save_images=os.getenv("SCRAPER_SAVE_IMAGES", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            progress_update_interval=int(os.getenv("SCRAPER_PROGRESS_INTERVAL", "10")),
        )


# Global config instance
_scraper_config: Optional[ScraperConfig] = None


def get_scraper_config() -> ScraperConfig:
    """Get the global scraper configuration."""
    global _scraper_config
    if _scraper_config is None:
        _scraper_config = ScraperConfig.from_env()
    return _scraper_config
