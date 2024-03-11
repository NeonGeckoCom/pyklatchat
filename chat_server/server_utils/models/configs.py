from fastapi import Path, Query
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    config_property: str = Field(
        Path(title="Name of the config property"), examples=["supported_llms"]
    )
    version: str = Field(Query(default="latest"), examples=["latest"])


class SetConfigModel(ConfigModel):
    data: dict = Field([{"records": [{"label": "Chat GPT", "value": "chatgpt"}]}])
