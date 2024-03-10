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
from typing import Annotated

from fastapi import APIRouter, Query, Depends
from starlette.responses import JSONResponse

from chat_server.server_utils.auth import is_authorized_for_user_id
from chat_server.server_utils.dependencies import CurrentUserDependency
from chat_server.server_utils.exceptions import (
    UserUnauthorizedException,
    ItemNotFoundException,
    DuplicatedItemException,
)
from chat_server.server_utils.http_utils import KlatAPIResponse
from chat_server.server_utils.models.personas import (
    AddPersonaModel,
    DeletePersonaModel,
    SetPersonaModel,
    TogglePersonaStatusModel,
)
from utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI

router = APIRouter(
    prefix="/personas",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.get("/list")
async def list_personas(
    current_user: CurrentUserDependency,
    llms: Annotated[list[str] | None, Query()] = None,
    user_id: str | None = None,
):
    """Lists personas config matching query params"""
    filters = []
    if llms:
        filters.append(
            MongoFilter(
                key="supported_llms",
                value=llms,
                logical_operator=MongoLogicalOperators.ALL,
            )
        )
    if user_id:
        if user_id == "*":
            if "admin" not in current_user.roles:
                raise UserUnauthorizedException
        elif not is_authorized_for_user_id(current_user, user_id=user_id):
            raise UserUnauthorizedException
        else:
            filters.append(MongoFilter(key="user_id", value=user_id))
    else:
        user_filter = [{"user_id": None}, {"user_id": current_user.user_id}]
        filters.append(
            MongoFilter(value=user_filter, logical_operator=MongoLogicalOperators.OR)
        )
    items = MongoDocumentsAPI.PERSONAS.list_items(
        filters=filters, result_as_cursor=False
    )
    for item in items:
        item["id"] = item.pop("_id")
        item["enabled"] = item.get("enabled", False)
    return JSONResponse(content={"items": items})


@router.get("/get/{persona_id}")
async def get_persona(
    current_user: CurrentUserDependency,
    persona_id: str,
):
    """Lists personas config matching query params"""
    personas_tokens = persona_id.split("_")
    if len(personas_tokens) >= 2:
        persona_user_id = personas_tokens[1]
        if not is_authorized_for_user_id(current_user, user_id=persona_user_id):
            raise ItemNotFoundException
    item = MongoDocumentsAPI.PERSONAS.get_item(item_id=persona_id)
    if not item:
        raise ItemNotFoundException
    return JSONResponse(content=item)


@router.put("/add")
async def add_persona(current_user: CurrentUserDependency, model: AddPersonaModel):
    """Adds new persona"""
    if not is_authorized_for_user_id(current_user=current_user, user_id=model.user_id):
        raise UserUnauthorizedException
    existing_model = MongoDocumentsAPI.PERSONAS.get_item(item_id=model.persona_id)
    if existing_model:
        raise DuplicatedItemException
    MongoDocumentsAPI.PERSONAS.add_item(data=model.model_dump())
    return KlatAPIResponse.OK


@router.post("/set")
async def set_persona(current_user: CurrentUserDependency, model: SetPersonaModel):
    """Sets persona's data"""
    if not is_authorized_for_user_id(current_user=current_user, user_id=model.user_id):
        raise UserUnauthorizedException
    existing_model = MongoDocumentsAPI.PERSONAS.get_item(item_id=model.persona_id)
    if not existing_model:
        raise ItemNotFoundException
    mongo_filter = MongoFilter(key="_id", value=model.persona_id)
    MongoDocumentsAPI.PERSONAS.update_item(
        filters=mongo_filter, data=model.model_dump()
    )
    return KlatAPIResponse.OK


@router.delete("/delete")
async def delete_persona(
    current_user: CurrentUserDependency, model: DeletePersonaModel = Depends()
):
    """Deletes persona"""
    if not is_authorized_for_user_id(current_user=current_user, user_id=model.user_id):
        raise UserUnauthorizedException
    MongoDocumentsAPI.PERSONAS.delete_item(item_id=model.persona_id)
    return KlatAPIResponse.OK


@router.post("/toggle")
async def toggle_persona_state(
    current_user: CurrentUserDependency, model: TogglePersonaStatusModel
):
    if not is_authorized_for_user_id(current_user=current_user, user_id=model.user_id):
        raise UserUnauthorizedException
    updated_data = MongoDocumentsAPI.PERSONAS.update_item(
        filters=MongoFilter(key="_id", value=model.persona_id),
        data={"enabled": model.enabled},
    )
    if updated_data.matched_count == 0:
        raise ItemNotFoundException
    return KlatAPIResponse.OK


@router.get("/supported_llms/list")
async def list_supported_llms():
    """Lists supported LLMs"""
    items = MongoDocumentsAPI.CONFIGS.get_by_name(config_name="supported_llms") or []
    return JSONResponse(content=items)
