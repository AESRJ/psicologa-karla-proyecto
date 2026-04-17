from pydantic_settings import BaseSettings
from pydantic import Field
import pytz


class Settings(BaseSettings):
    # WhatsApp
    whatsapp_access_token: str = Field(..., env="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(..., env="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_business_account_id: str = Field(..., env="WHATSAPP_BUSINESS_ACCOUNT_ID")
    whatsapp_verify_token: str = Field(..., env="WHATSAPP_VERIFY_TOKEN")
    karla_phone_number: str = Field(..., env="KARLA_PHONE_NUMBER")

    # Ollama
    ollama_host: str = Field("http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field("gemma4", env="OLLAMA_MODEL")

    # Google Calendar
    google_calendar_id: str = Field(..., env="GOOGLE_CALENDAR_ID")
    google_credentials_file: str = Field("credentials.json", env="GOOGLE_CREDENTIALS_FILE")
    google_token_file: str = Field("token.json", env="GOOGLE_TOKEN_FILE")

    # General
    timezone: str = Field("America/Mexico_City", env="TIMEZONE")
    conversation_timeout_minutes: int = Field(60, env="CONVERSATION_TIMEOUT_MINUTES")
    port: int = Field(8000, env="PORT")

    @property
    def tz(self):
        return pytz.timezone(self.timezone)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
