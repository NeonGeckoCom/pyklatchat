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
from typing import List

import requests

from time import time
from fastapi import APIRouter, status, Request, Query, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from bson.objectid import ObjectId
from neon_utils import LOG

from chat_server.constants.users import UserPatterns
from chat_server.server_config import db_controller, app_config
from chat_server.server_utils.message_utils import fetch_shouts
from chat_server.server_utils.user_utils import create_from_pattern
from chat_server.server_utils.http_utils import get_file_response, save_file

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
def new_conversation(request_data: NewConversationData):
    """
        Creates new conversation from provided conversation data

        :param request_data: data for new conversation described by NewConversationData model

        :returns JSON response with new conversation data if added, 401 error message otherwise
    """
    if request_data.id:
        matching_conversation_id = db_controller.exec_query(query={'command': 'find_one',
                                                                   'document': 'chats',
                                                                   'data': ({'_id': request_data.id})})
        if matching_conversation_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Provided conversation id already exists'
            )
    _id = db_controller.exec_query(query=dict(document='chats', command='insert_one', data=(request_data.__dict__,)))
    request_data.__dict__['_id'] = str(request_data.__dict__['_id'])
    json_compatible_item_data = jsonable_encoder(request_data.__dict__)
    json_compatible_item_data['_id'] = str(_id.inserted_id)
    return JSONResponse(content=json_compatible_item_data)


@router.get("/search/{search_str}")
def get_matching_conversation(request: Request,
                              search_str: str,
                              chat_history_from: int = 0,
                              limit_chat_history: int = 100):
    """
        Gets conversation data matching search string

        :param request: client request
        :param search_str: provided search string
        :param chat_history_from: upper time bound for messages
        :param limit_chat_history: lower time bound for messages

        :returns conversation data if found, 401 error code otherwise
    """
    or_expression = [{'conversation_name': search_str}]

    if ObjectId.is_valid(search_str):
        cid_search = ObjectId(search_str)
        or_expression.append({'_id': cid_search})
    else:
        or_expression.append({'_id': search_str})

    conversation_data = db_controller.exec_query(query={'command': 'find_one',
                                                        'document': 'chats',
                                                        'data': {"$or": or_expression}})
    if not conversation_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unable to get a chat by string: {search_str}"
        )
    conversation_data['_id'] = str(conversation_data['_id'])

    if conversation_data.get('chat_flow', None):
        if chat_history_from == 0:
            conversation_data['chat_flow'] = conversation_data['chat_flow'][chat_history_from - limit_chat_history:]
        else:
            conversation_data['chat_flow'] = conversation_data['chat_flow'][chat_history_from - limit_chat_history:
                                                                            -chat_history_from]
        shout_ids = [str(msg_id) for msg_id in conversation_data["chat_flow"]]
        if shout_ids:
            users_data = fetch_shouts(shout_ids=shout_ids)
            users_data = sorted(users_data, key=lambda user_shout: user_shout['created_on'])
            conversation_data['chat_flow'] = []
            for i in range(len(users_data)):
                message_record = {'user_id': users_data[i]['user_id'],
                                  'created_on': users_data[i]['created_on'],
                                  'message_id': users_data[i]['message_id'],
                                  'message_text': users_data[i]['message_text'],
                                  'attachments': users_data[i].get('attachments', []),
                                  'user_first_name': users_data[i]['first_name'],
                                  'user_last_name': users_data[i]['last_name'],
                                  'user_nickname': users_data[i]['nickname'],
                                  'user_avatar': users_data[i].get('avatar', '')}
                conversation_data['chat_flow'].append(message_record)

    return conversation_data


@router.post("/{cid}/store_files")
async def send_file(cid: str,
                    files: List[UploadFile] = File(...)):
    """
        Stores received files in filesystem

        :param cid: target conversation id
        :param files: list of files to process

        :returns JSON-formatted response from server
    """
    # TODO: any file validation before storing it (Kirill)
    for file in files:
        await save_file(location_prefix='attachments', file=file)
    return JSONResponse(content={'success': '1'})


@router.get("/{msg_id}/get_file/{filename}")
def get_message_attachment(msg_id: str, filename: str):
    """
        Gets file from the server

        :param msg_id: parent message id
        :param filename: name of the file to get
    """
    LOG.debug(f'{msg_id} - {filename}')
    message_files = db_controller.exec_query(query={'document': 'shouts',
                                                    'command': 'find_one',
                                                    'data': {'_id': msg_id}})
    if message_files:
        attachment_data = [attachment for attachment in message_files['attachments'] if attachment['name'] == filename][0]
        media_type = attachment_data['mime']
        file_response = get_file_response(filename=filename, media_type=media_type, location_prefix='attachments')
        if file_response is None:
            return JSONResponse({'msg': 'Missing attachments in destination'}, 400)
        return file_response
    else:
        return JSONResponse({'msg': f'invalid message id: {msg_id}'}, 400)
