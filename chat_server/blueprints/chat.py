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
from typing import Optional

from time import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from chat_server.constants.conversations import ConversationSkins
from chat_server.server_config import db_controller
from chat_server.server_utils.auth import login_required
from chat_server.server_utils.conversation_utils import build_message_json
from chat_server.server_utils.db_utils import DbUtils
from chat_server.services.popularity_counter import PopularityCounter
from utils.http_utils import respond

router = APIRouter(
    prefix="/chat_api",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


class NewConversationData(BaseModel):
    """Model for new conversation data"""
    id: str = None
    conversation_name: str
    is_private: bool = False
    created_on: int = int(time())


@router.post("/new")
@login_required
async def new_conversation(request: Request, request_data: NewConversationData):
    """
        Creates new conversation from provided conversation data

        :param request: Starlette Request object
        :param request_data: data for new conversation described by NewConversationData model

        :returns JSON response with new conversation data if added, 401 error message otherwise
    """

    conversation_data = DbUtils.get_conversation_data(search_str=[request_data.id, request_data.conversation_name])
    if conversation_data:
        if conversation_data['_id'] == request_data.id:
            duplicated_field = 'id'
        else:
            duplicated_field = 'conversation name'
        return respond(f'Conversation with provided {duplicated_field} already exists', 400)
    request_data_dict = request_data.__dict__
    request_data_dict['_id'] = request_data_dict.pop('id', None)
    _id = db_controller.exec_query(query=dict(document='chats', command='insert_one', data=(request_data_dict,)))
    request_data_dict['_id'] = str(request_data_dict['_id'])
    json_compatible_item_data = jsonable_encoder(request_data_dict)
    json_compatible_item_data['_id'] = str(_id.inserted_id)
    return JSONResponse(content=json_compatible_item_data)


@router.get("/search/{search_str}")
# @login_required
async def get_matching_conversation(request: Request,
                                    search_str: str,
                                    chat_history_from: int = 0,
                                    first_message_id: Optional[str] = None,
                                    limit_chat_history: int = 100,
                                    skin: str = ConversationSkins.BASE):
    """
        Gets conversation data matching search string

        :param request: Starlette Request object
        :param search_str: provided search string
        :param chat_history_from: upper time bound for messages
        :param first_message_id: id of the first message to start from
        :param limit_chat_history: lower time bound for messages
        :param skin: conversation skin type from ConversationSkins

        :returns conversation data if found, 401 error code otherwise
    """
    conversation_data = DbUtils.get_conversation_data(search_str=search_str)

    if not conversation_data:
        return respond(f'No conversation matching = "{search_str}"', 404)

    message_data = DbUtils.fetch_skin_message_data(skin=skin,
                                                   conversation_data=conversation_data,
                                                   start_idx=chat_history_from,
                                                   limit=limit_chat_history,
                                                   start_message_id=first_message_id) or []
    conversation_data['chat_flow'] = []
    for i in range(len(message_data)):
        message_record = build_message_json(raw_message=message_data[i], skin=skin)
        conversation_data['chat_flow'].append(message_record)

    return conversation_data


@router.get("/get_popular_cids")
async def get_popular_cids(search_str: str = "",
                           limit: int = 10):
    """
        Returns n-most popular conversations

        :param search_str: Searched substring to match
        :param limit: limit returned amount of matched instances
    """
    items = PopularityCounter.get_first_n_items(search_str, limit)
    return JSONResponse(content=items)
