# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Elon Gasper, Richard Leeds, Kirill Hrymailo
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending
import os
from typing import List, Optional

from time import time
from fastapi import APIRouter, status, Request, UploadFile, File
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
    if request_data.id:
        matching_conversation_id = db_controller.exec_query(query={'command': 'find_one',
                                                                   'document': 'chats',
                                                                   'data': ({'_id': request_data.id})})
        if matching_conversation_id:
            return respond('Provided conversation id already exists', 400)
    request_data_dict = request_data.__dict__
    request_data_dict['_id'] = request_data_dict.pop('id', None)
    _id = db_controller.exec_query(query=dict(document='chats', command='insert_one', data=(request_data_dict,)))
    request_data_dict['_id'] = str(request_data_dict['_id'])
    json_compatible_item_data = jsonable_encoder(request_data_dict)
    json_compatible_item_data['_id'] = str(_id.inserted_id)
    return JSONResponse(content=json_compatible_item_data)


@router.get("/search/{search_str}")
@login_required
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

