from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "АгроЦифра"
    database_url: str = "postgresql+psycopg://agrocifra:agrocifra@localhost:5432/agrocifra"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 8
    jotform_api_key: str = ""  # выдаётся соискателем (задача Спринта 1/3)
    jotform_api_base: str = "https://eu-api.jotform.com"  # EU-облако (формы на eu.jotform.com)
    # Идентификаторы действующих анкет
    jotform_form_efficiency: str = "222133487281353"      # «Эффективность цифровизации»
    jotform_form_maturity: str = "241376010701342"        # «Цифровая зрелость» (подтверждена)
    # Прежний идентификатор 222084057175050 — отдельный банковский опросник
    # «Трансформация», к оценке цифровой зрелости отношения не имеет.
    jotform_form_transformation: str = "222084057175050"
    # qid показателей формы зрелости (режим отдельных показателей); по умолчанию
    # используется резолвинг агрегатов и итогового уровня по тексту полей
    jotform_maturity_need_qids: list[str] = []
    jotform_maturity_capability_qids: list[str] = []


settings = Settings()
