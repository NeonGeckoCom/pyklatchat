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
from time import time

import ovos_utils.log
from fastapi import APIRouter, Form, Depends
from fastapi.responses import JSONResponse

from chat_server.server_utils.api_dependencies.models.chats import (
    GetLiveConversationModel,
)
from chat_server.server_utils.api_dependencies.validators.users import (
    get_authorized_user,
    has_admin_role,
)
from chat_server.server_utils.conversation_utils import build_message_json
from chat_server.server_utils.api_dependencies.extractors import CurrentUserData
from chat_server.server_utils.api_dependencies.models import GetConversationModel
from chat_server.services.popularity_counter import PopularityCounter
from klatchat_utils.common import generate_uuid
from klatchat_utils.database_utils.mongo_utils import MongoFilter, MongoLogicalOperators
from klatchat_utils.database_utils.mongo_utils.queries.mongo_queries import fetch_message_data
from klatchat_utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI
from klatchat_utils.http_utils import respond
from neon_utils.logger import LOG

router = APIRouter(
    prefix="/chat_api",
    responses={"404": {"description": "Unknown authorization endpoint"}},
)


@router.post("/new")
async def new_conversation(
    current_user: CurrentUserData = get_authorized_user,
    conversation_id: str = Form(""),  # DEPRECATED
    conversation_name: str = Form(...),
    is_private: str = Form(False),
    bound_service: str = Form(""),
    is_live_conversation: str = Form(False),
):
    """
    Creates new conversation from provided conversation data

    :param current_user: current user data
    :param conversation_id: new conversation id (DEPRECATED)
    :param conversation_name: new conversation name (optional)
    :param is_private: if new conversation should be private (defaults to False)
    :param bound_service: name of the bound service (ignored if empty value)
    :param is_live_conversation: if conversation is live (defaults to False)

    :returns JSON response with new conversation data if added, 401 error message otherwise
    """
    if conversation_id:
        ovos_utils.log.log_deprecation("Param conversation id is no longer considered")
    conversation_data = MongoDocumentsAPI.CHATS.get_chat(
        search_str=conversation_name,
        column_identifiers=["conversation_name"],
        requested_user_id=current_user.user_id,
    )
    if conversation_data:
        return respond(f'Conversation "{conversation_name}" already exists', 400)

    is_live_conversation = True if is_live_conversation == "1" else False
    if is_live_conversation and not has_admin_role(current_user=current_user):
        return respond("User is not authorized to create live conversations", 400)

    cid = generate_uuid()
    request_data_dict = {
        "_id": cid,
        "conversation_name": conversation_name,
        "is_private": True if is_private == "1" else False,
        "is_live_conversation": is_live_conversation,
        "bound_service": bound_service,
        "creator": current_user.user_id,
        "created_on": int(time()),
    }
    MongoDocumentsAPI.CHATS.add_item(data=request_data_dict)
    PopularityCounter.add_new_chat(cid=cid)
    return JSONResponse(content=request_data_dict)


@router.get("/search/{search_str}")
async def get_matching_conversation(
    current_user: CurrentUserData, model: GetConversationModel = Depends()
):
    """
    Gets conversation data matching search string

    :param current_user: current user data
    :param model: request data model described in GetConversationModel

    :returns conversation data if found, 401 error code otherwise
    """
    conversation_data = MongoDocumentsAPI.CHATS.get_chat(
        search_str=model.search_str,
        column_identifiers=["_id", "conversation_name"],
        requested_user_id=current_user.user_id,
    )

    if not conversation_data:
        return respond(f'No conversation matching = "{model.search_str}"', 404)

    if model.creation_time_from:
        query_filter = MongoFilter(
            key="created_on",
            logical_operator=MongoLogicalOperators.LT,
            value=int(model.creation_time_from),
        )
    else:
        query_filter = None

    message_data = (
        fetch_message_data(
            skin=model.skin,
            conversation_data=conversation_data,
            limit=model.limit_chat_history,
            creation_time_filter=query_filter,
        )
        or []
    )
    conversation_data["chat_flow"] = [
        build_message_json(raw_message=message_data[i], skin=model.skin)
        for i in range(len(message_data))
    ]

    return conversation_data


@router.get("/live")
async def get_live_conversation(
    current_user: CurrentUserData, model: GetLiveConversationModel = Depends()
):
    """
    Gets live conversation data

    :param current_user: current user data
    :param model: request data model described in GetConversationModel

    :returns conversation data if found, 401 error-code otherwise
    """
    conversation_data = MongoDocumentsAPI.CHATS.list_items(
        filters=(
            MongoFilter(
                key="is_private",
                logical_operator=MongoLogicalOperators.EQ,
                value=False,
            ),
            MongoFilter(
                key="is_live_conversation",
                logical_operator=MongoLogicalOperators.EQ,
                value=True,
            ),
        ),
        limit=1,
        ordering_expression={"created_on": -1},
        result_as_cursor=False,
    )

    if not conversation_data:
        LOG.warning("No live conversation data found, fetching `Global` conversation")

        conversation_data = MongoDocumentsAPI.CHATS.get_chat(
            search_str="1",
            column_identifiers=["_id"],
            requested_user_id=current_user.user_id,
        )
        if not conversation_data:
            return respond(f"Live conversation is missing", 404)
    else:
        conversation_data = conversation_data[0]

    message_data = (
        fetch_message_data(
            skin=model.skin,
            conversation_data=conversation_data,
            limit=model.limit_chat_history,
        )
        or []
    )
    conversation_data["chat_flow"] = [
        build_message_json(raw_message=message_data[i], skin=model.skin)
        for i in range(len(message_data))
    ]

    return conversation_data


@router.get("/get_popular_cids")
async def get_popular_cids(search_str: str = "", exclude_items="", limit: int = 10):
    """
    Returns n-most popular conversations

    :param search_str: Searched substring to match
    :param exclude_items: list of conversation ids to exclude from search
    :param limit: limit returned amount of matched instances
    """
    try:
        if exclude_items:
            exclude_items = exclude_items.split(",")
        items = PopularityCounter.get_first_n_items(search_str, exclude_items, limit)
    except Exception as ex:
        LOG.error(f"Failed to extract most popular items - {ex}")
        items = []
    return JSONResponse(content=items)
