from pydantic import BaseModel, Field


class AddPersonaModel(BaseModel):
    user_id: str | None = Field(default=None, examples=["test_user_id"])
    persona_name: str = Field(examples=["doctor"])
    supported_llms: list[str] = Field(examples=[["chatgpt", "llama", "fastchat"]])
    description: str = Field(examples=["I am the doctor. I am helping people."])
