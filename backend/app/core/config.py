from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://telas_user:telas_pass@db:5432/telas_db"
    jwt_secret_key: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    environment: str = "development"
    allowed_origins: str = "*"  # dominio(s) del frontend separados por coma, en producción

    @property
    def lista_origenes_permitidos(self) -> list[str]:
        if self.allowed_origins == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
