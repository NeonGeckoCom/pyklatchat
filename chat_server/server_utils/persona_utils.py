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

import json
from time import time

from typing import Optional, List
from asyncio import Lock

from starlette.responses import JSONResponse

from chat_server.server_utils.api_dependencies import ListPersonasQueryModel, CurrentUserData
from chat_server.sio.server import sio
from utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI

_LOCK = Lock()


async def notify_personas_changed(supported_llms: Optional[List[str]] = None):
    """
    Emit an SIO event for each LLM affected by a persona change. This sends a
    complete set of personas rather than only the changed one to prevent sync
    conflicts and simplify client-side logic.
    :param supported_llms: List of LLM names affected by a transaction. If None,
        then updates all LLMs listed in database configuration
    """
    async with _LOCK:
        resp = await list_personas(None,
                                   ListPersonasQueryModel(only_enabled=True))
        update_time = time()
        enabled_personas = json.loads(resp.body.decode())
        valid_personas = {}
        if supported_llms:
            # Only broadcast updates for LLMs affected by an insert/change request
            for llm in supported_llms:
                valid_personas[llm] = [per for per in enabled_personas["items"] if
                                       llm in per["supported_llms"]]
        else:
            # Delete request does not have LLM context, update everything
            for persona in enabled_personas["items"]:
                for llm in persona["supported_llms"]:
                    valid_personas.setdefault(llm, [])
                    valid_personas[llm].append(persona)
        sio.emit("configured_personas_changed", {"personas": valid_personas,
                                                 "update_time": update_time})


async def list_personas(current_user: CurrentUserData,
                        request_model: ListPersonasQueryModel) -> JSONResponse:
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
    elif current_user:
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