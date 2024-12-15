from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    SLEEP_TIME: list[int] = [15000, 20000]
    START_DELAY: list[int] = [5, 25]
    REF_ID: str = 'q2Hltv27RjGnr1UVipvYIw'


settings = Settings()
