from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ticker: str = "PETR4.SA"
    start_date: str = "2018-01-01"
    end_date: str | None = None

    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "b3pulse"
    minio_secret_key: str = "b3pulse123"
    bronze_bucket: str = "bronze"
    silver_bucket: str = "silver"
    features_bucket: str = "features"


settings = Settings()
