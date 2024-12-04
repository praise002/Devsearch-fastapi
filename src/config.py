from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool = True 
    MAIL_SSL_TLS: bool = False 
    USE_CREDENTIALS: bool = True # Ensures email authentication is enabled.
    VALIDATE_CERTS: bool = True # Ensures email server certificates are validated
    DOMAIN: str
    
    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore'  # Ignores any additional fields in the .env file that are not defined in the Settings class
    ) 

Config = Settings() 