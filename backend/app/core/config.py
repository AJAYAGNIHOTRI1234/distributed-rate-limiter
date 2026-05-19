from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    FRONTEND_URL: str = "http://localhost:3000"

    # MongoDB
    MONGO_URL: str = "mongodb://localhost:27017/rateguard"
    MONGO_DB: str = "rateguard"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"

    # JWT
    JWT_SECRET: str = "dev_jwt_secret_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate Limiting
    RATE_LIMIT_FREE: int = 60
    RATE_LIMIT_PRO: int = 600
    RATE_LIMIT_ENTERPRISE: int = 6000
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Daily Quotas
    QUOTA_LIMIT_FREE: int = 1000
    QUOTA_LIMIT_PRO: int = 50000
    QUOTA_LIMIT_ENTERPRISE: int = 500000

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
