import os


class Settings:
    secret_key: str = os.environ.get("SECRET_KEY", "change-me-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

settings = Settings()
