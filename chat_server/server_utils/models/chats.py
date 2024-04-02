from time import time

from fastapi import Query, Path
from pydantic import BaseModel, Field

from chat_server.constants.conversations import ConversationSkins


class GetConversationModel(BaseModel):
    search_str: str = Field(Path(), examples=["1"])
    limit_chat_history: int = (Field(Query(default=100), examples=[100]),)
    creation_time_from: str | None = Field(Query(default=None), examples=[int(time())])
    skin: str = Field(
        Query(default=ConversationSkins.BASE), examples=[ConversationSkins.BASE]
    )
