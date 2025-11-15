class Settings:
    secret_key: str = "4a3bfcdfcedc53c9082e83dbc5a507ce19b8b6cb1f068ba6b97a282faa3c3d7e"          # musíš změnit!
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

settings = Settings()
