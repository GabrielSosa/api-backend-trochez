from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "Avalúos Trochez API"
    API_V1_STR: str = "/api/v1"
    
    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Database settings - updated to match .env file variable names
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Alias properties to maintain compatibility with existing code
    @property
    def MYSQL_HOST(self) -> str:
        return self.DB_HOST
    
    @property
    def MYSQL_PORT(self) -> str:
        return self.DB_PORT
    
    @property
    def MYSQL_USER(self) -> str:
        return self.DB_USER
    
    @property
    def MYSQL_PASSWORD(self) -> str:
        return self.DB_PASSWORD
    
    @property
    def MYSQL_DB(self) -> str:
        return self.DB_NAME

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()