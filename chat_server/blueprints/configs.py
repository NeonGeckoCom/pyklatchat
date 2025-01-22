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

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from chat_server.server_utils.api_dependencies import permitted_access
from chat_server.server_utils.enums import UserRoles
from chat_server.server_utils.http_exceptions import (
    ItemNotFoundException,
)
from chat_server.server_utils.http_utils import KlatAPIResponse
from chat_server.server_utils.api_dependencies.models import SetConfigModel, ConfigModel
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI

router = APIRouter(
    prefix="/configs",
    responses={"404": {"description": "Unknown endpoint"}},
)


@router.get("/{config_property}")
async def get_config_data(model: ConfigModel = Depends()) -> JSONResponse:
    """Retrieves configured data by name"""
    items = await MongoDocumentsAPI.CONFIGS.get_by_name(
        config_name=model.config_property, version=model.version
    )
    return JSONResponse(content=items)


@router.put("/{config_property}")
async def update_config(
    model: SetConfigModel = permitted_access(
        SetConfigModel, min_required_role=UserRoles.ADMIN
    )
) -> JSONResponse:
    """Updates provided config by name"""
    updated_data = await MongoDocumentsAPI.CONFIGS.update_by_name(
        config_name=model.config_property, version=model.version, data=model.data
    )
    if updated_data.matched_count == 0:
        raise ItemNotFoundException
    return KlatAPIResponse.OK
