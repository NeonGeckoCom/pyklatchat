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

from fastapi import APIRouter
from starlette.responses import JSONResponse

from chat_server.server_utils.enums import RequestModelType, UserRoles
from chat_server.server_utils.http_exceptions import (
    ItemNotFoundException,
    DuplicatedItemException,
)
from chat_server.server_utils.http_utils import KlatAPIResponse

from chat_server.server_utils.api_dependencies.models import (
    AddPersonaModel,
    DeletePersonaModel,
    SetPersonaModel,
    TogglePersonaStatusModel,
    ListPersonasQueryModel,
)
from chat_server.server_utils.api_dependencies.extractors import (
    CurrentUserData,
    PersonaData,
)
from chat_server.server_utils.api_dependencies.validators import permitted_access
from chat_server.server_utils.socketio_utils import notify_personas_changed
from utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI

router = APIRouter(
    prefix="/personas",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.get("/list")
async def list_personas(
    current_user: CurrentUserData,
    request_model: ListPersonasQueryModel = permitted_access(ListPersonasQueryModel),
) -> JSONResponse:
    """Lists personas matching query params"""
    filters = []
    if request_model.llms:
        filters.append(
            MongoFilter(
                key="supported_llms",
                value=request_model.llms,
                logical_operator=MongoLogicalOperators.ALL,
            )
        )
    if request_model.user_id and request_model.user_id != "*":
        filters.append(MongoFilter(key="user_id", value=request_model.user_id))
    else:
        user_filter = [{"user_id": None}, {"user_id": current_user.user_id}]
        filters.append(
            MongoFilter(value=user_filter, logical_operator=MongoLogicalOperators.OR)
        )
    if request_model.only_enabled:
        filters.append(MongoFilter(key="enabled", value=True))
    items = MongoDocumentsAPI.PERSONAS.list_items(
        filters=filters, result_as_cursor=False
    )
    for item in items:
        item["id"] = item.pop("_id")
        item["enabled"] = item.get("enabled", False)
    return JSONResponse(content={"items": items})


@router.get("/get/{persona_id}")
async def get_persona(request_model: PersonaData = permitted_access(PersonaData)):
    """Gets persona details for a given persona_id"""
    item = MongoDocumentsAPI.PERSONAS.get_item(item_id=request_model.persona_id)
    if not item:
        raise ItemNotFoundException
    return JSONResponse(content=item)


@router.put("/add")
async def add_persona(
    request_model: AddPersonaModel = permitted_access(
        AddPersonaModel, request_model_type=RequestModelType.DATA
    ),
):
    """Adds new persona"""
    existing_model = MongoDocumentsAPI.PERSONAS.get_item(
        item_id=request_model.persona_id
    )
    if existing_model:
        raise DuplicatedItemException
    MongoDocumentsAPI.PERSONAS.add_item(data=request_model.model_dump())
    await notify_personas_changed(request_model.supported_llms)
    return KlatAPIResponse.OK


@router.post("/set")
async def set_persona(
    request_model: SetPersonaModel = permitted_access(
        SetPersonaModel, request_model_type=RequestModelType.DATA
    ),
):
    """Sets persona's data"""
    existing_model = MongoDocumentsAPI.PERSONAS.get_item(
        item_id=request_model.persona_id
    )
    if not existing_model:
        raise ItemNotFoundException
    mongo_filter = MongoFilter(key="_id", value=request_model.persona_id)
    MongoDocumentsAPI.PERSONAS.update_item(
        filters=mongo_filter, data=request_model.model_dump()
    )
    await notify_personas_changed(request_model.supported_llms)
    return KlatAPIResponse.OK


@router.delete("/delete")
async def delete_persona(
    request_model: DeletePersonaModel = permitted_access(DeletePersonaModel),
):
    """Deletes persona"""
    MongoDocumentsAPI.PERSONAS.delete_item(item_id=request_model.persona_id)
    await notify_personas_changed()
    return KlatAPIResponse.OK


@router.post("/toggle")
async def toggle_persona_state(
    request_model: TogglePersonaStatusModel = permitted_access(
        TogglePersonaStatusModel,
        min_required_role=UserRoles.AUTHORIZED_USER,
        request_model_type=RequestModelType.DATA,
    ),
):
    updated_data = MongoDocumentsAPI.PERSONAS.update_item(
        filters=MongoFilter(key="_id", value=request_model.persona_id),
        data={"enabled": request_model.enabled},
    )
    if updated_data.matched_count == 0:
        raise ItemNotFoundException
    await notify_personas_changed()
    return KlatAPIResponse.OK
