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
import os
from typing import List, Optional

from time import time
from fastapi import APIRouter, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from bson.objectid import ObjectId
from neon_utils import LOG

from chat_server.server_config import db_controller
from chat_server.server_utils.auth import login_required
from chat_server.server_utils.db_utils import DbUtils
from chat_server.server_utils.http_utils import get_file_response, save_file
from utils.http_utils import respond

router = APIRouter(
    prefix="/chat_api",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.post("/new")
@login_required
async def new_conversation(request: Request,
                           conversation_id: str = Form(''),
                           conversation_name: str = Form(...),
                           is_private: bool = Form(False)):
    """
        Creates new conversation from provided conversation data

        :param request: Starlette Request object
        :param request_data: data for new conversation described by NewConversationData model

        :returns JSON response with new conversation data if added, 401 error message otherwise
    """
    request_data = {
        '_id': conversation_id,
        'conversation_name': conversation_name,
        'is_private': is_private,
        'created_on': int(time())
    }
    if request_data['_id']:
        matching_conversation_id = db_controller.exec_query(query={'command': 'find_one',
                                                                   'document': 'chats',
                                                                   'data': ({'_id': request_data['_id']})})
        if matching_conversation_id:
            return respond('Provided conversation id already exists', 400)
    db_controller.exec_query(query=dict(document='chats', command='insert_one', data=(request_data,)))
    return JSONResponse(content=request_data)


@router.get("/search/{search_str}")
# @login_required
async def get_matching_conversation(request: Request,
                                    search_str: str,
                                    chat_history_from: int = 0,
                                    first_message_id: Optional[str] = None,
                                    limit_chat_history: int = 100):
    """
        Gets conversation data matching search string

        :param request: Starlette Request object
        :param search_str: provided search string
        :param chat_history_from: upper time bound for messages
        :param first_message_id: id of the first message to start from
        :param limit_chat_history: lower time bound for messages

        :returns conversation data if found, 401 error code otherwise
    """
    or_expression = [{'conversation_name': search_str}]

    if ObjectId.is_valid(search_str):
        search_str = ObjectId(search_str)
    or_expression.append({'_id': search_str})

    conversation_data = db_controller.exec_query(query={'command': 'find_one',
                                                        'document': 'chats',
                                                        'data': {"$or": or_expression}})
    if not conversation_data:
        return respond(f"Unable to get a chat by string: {search_str}", 404)
    conversation_data['_id'] = str(conversation_data['_id'])

    response_data, status_code = DbUtils.get_conversation_data(search_str=search_str)

    if status_code != 200:
        return respond(response_data, status_code)

    users_data = DbUtils.fetch_shout_data(conversation_data=response_data,
                                          start_idx=chat_history_from,
                                          limit=limit_chat_history,
                                          start_message_id=first_message_id)

    if users_data:
        conversation_data['chat_flow'] = []
        for i in range(len(users_data)):
            message_record = {'user_id': users_data[i]['user_id'],
                              'created_on': int(users_data[i]['created_on']),
                              'message_id': users_data[i]['message_id'],
                              'message_text': users_data[i]['message_text'],
                              'is_audio': users_data[i].get('is_audio', '0'),
                              'is_announcement': users_data[i].get('is_announcement', '0'),
                              'replied_message': users_data[i]['replied_message'],
                              'attachments': users_data[i].get('attachments', []),
                              'user_first_name': users_data[i]['first_name'],
                              'user_last_name': users_data[i]['last_name'],
                              'user_nickname': users_data[i]['nickname'],
                              'user_avatar': users_data[i].get('avatar', '')}
            conversation_data['chat_flow'].append(message_record)

    return conversation_data

