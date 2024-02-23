# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
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

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from chat_server.server_utils.auth import login_required
from chat_server.server_utils.models.endpoints.persona import AddPersonaModel
from utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from utils.http_utils import respond, response_ok

router = APIRouter(
    prefix="/personas",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.get("/list")
@login_required
async def list_personas(request: Request, llm: str = None, user_id: str = None):
    """Lists personas config matching query params"""
    filters = []
    if llm:
        filters.append(
            MongoFilter(
                key="supported_llms",
                value=llm,
                logical_operator=MongoLogicalOperators.ANY,
            )
        )
    if user_id:
        filters.append(MongoFilter(key="user_id", value=user_id))
    items = MongoDocumentsAPI.PERSONAS.list_items(
        filters=filters, result_as_cursor=False
    )
    return JSONResponse(content={"items": items})


@router.put("/add")
@login_required
async def add_persona(request: Request, model: AddPersonaModel):
    """Adds new persona"""
    filters = [
        MongoFilter(key=key, value=getattr(model, key))
        for key in (
            "user_id",
            "persona_name",
        )
        if getattr(model, key)
    ]
    existing_model = MongoDocumentsAPI.PERSONAS.get_item(filters=filters)
    if existing_model:
        return respond("Requested persona name already exists", status_code=400)
    MongoDocumentsAPI.PERSONAS.add_item(data=model.model_dump())
    return response_ok
