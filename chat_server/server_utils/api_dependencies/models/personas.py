# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from fastapi import Query
from pydantic import Field, computed_field, BaseModel


class PersonaModel(BaseModel):
    persona_name: str = Field(examples=["doctor"])
    user_id: str | None = Field(default=None, examples=["test_user_id"])

    @computed_field
    @property
    def _id(self) -> str:
        persona_id = self.persona_name
        if self.user_id:
            persona_id += f"_{self.user_id}"
        return persona_id

    @property
    def persona_id(self):
        return self._id

    @classmethod
    def create_from_id(cls, persona_id: str):
        tokens = persona_id.split("_")
        if len(tokens) == 2:
            persona_name, user_id = tokens
        else:
            persona_name = tokens[0]
            user_id = None
        return cls(persona_name=persona_name, user_id=user_id)


class AddPersonaModel(PersonaModel):
    supported_llms: list[str] = Field(
        examples=[["chat_gpt", "llama", "fastchat"]], default=[]
    )
    default_llm: str | None = Field(examples=["chat_gpt"], default=None)
    description: str = Field(examples=["I am the doctor. I am helping people."])
    enabled: bool = False


class SetPersonaModel(PersonaModel):
    supported_llms: list[str] = Field(
        examples=[["chat_gpt", "llama", "fastchat"]], default=[]
    )
    default_llm: str | None = Field(examples=["chat_gpt"], default=None)
    description: str = Field(examples=["I am the doctor. I am helping people."])


class DeletePersonaModel(PersonaModel):
    persona_name: str = Field(Query(), examples=["doctor"])
    user_id: str | None = Field(Query(None), examples=["test_user_id"])


class TogglePersonaStatusModel(PersonaModel):
    enabled: bool = Field(examples=[True, False], default=True)


class ListPersonasQueryModel(BaseModel):
    llms: list[str] | None = Field(Query(default=None), examples=[["doctor"]])
    user_id: str | None = Field(Query(default=None), examples=["test_user_id"])
    only_enabled: bool = Field(Query(default=False), examples=[True, False])
