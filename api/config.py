from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "gaokao_ai"
    db_user: str = "gaokao_user"
    db_password: str = ""
    db_pool_size: int = 20
    db_max_overflow: int = 30

    # Redis
    redis_url: str = "redis://127.0.0.1:6379/0"

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    internal_jwt_secret: str = ""

    # Admin
    admin_username: str = "admin"
    admin_password: str = ""

    # LLM
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"

    # OSS
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = ""
    oss_endpoint: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )


settings = Settings()
