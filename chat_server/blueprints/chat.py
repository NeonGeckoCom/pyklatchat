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

import jwt
import requests
import re

from uuid import uuid4
from time import time
from typing import Optional
from fastapi import APIRouter, Depends, Form, Response, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from bson.objectid import ObjectId

from chat_server.server_config import db_controller
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, get_hash, \
    check_password_strength, generate_uuid

router = APIRouter(
    prefix="/chat_api",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


class NewConversationData(BaseModel):
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
    if request_data.__dict__.get('_id', None):
        matching_conversation_id = db_controller.exec_query(query={'command': 'find_one',
                                                                  'document': 'chats',
                                                                  'data': ({'_id': getattr(request_data, '_id')})})
        if matching_conversation_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Provided conversation id already exists'
            )
    _id = db_controller.exec_query(query=dict(document='chats', command='insert_one', data=(request_data.__dict__,)))
    request_data.__dict__['_id'] = str(request_data.__dict__['_id'])
    json_compatible_item_data = jsonable_encoder(request_data.__dict__)
    json_compatible_item_data['_id'] = str(_id.inserted_id)
    return JSONResponse(content=json_compatible_item_data)


@router.get("/get/{cid}")
def get_conversation(request: Request, cid: str, username: str = Depends(get_current_user),
                     chat_history_from: int = 0,
                     limit_chat_history: int = 100):
    """
        Gets conversation data by id

        Note: soon will be depreciated, consider to replace with /search/{search_str} instead

        :param request: client request
        :param cid: desired conversation id
        :param username: current user data
        :param chat_history_from: upper time bound for messages
        :param limit_chat_history: lower time bound for messages

        :returns conversation data if found, 401 error code otherwise
    """
    if ObjectId.is_valid(cid):
        cid = ObjectId(cid)
    conversation_data = db_controller.exec_query(query={'command': 'find_one',
                                                       'document': 'chats',
                                                       'data': {'_id': cid}})
    if not conversation_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unable to get a chat with id: {cid}"
        )
    conversation_data['_id'] = str(conversation_data['_id'])

    if conversation_data.get('chat_flow', None):
        conversation_data['chat_flow'] = conversation_data['chat_flow'][chat_history_from:
                                                                        chat_history_from + limit_chat_history]
        users_data_request = requests.get('http://' + request.client.host + ':' + str(8000) +
                                          f'/users_api/bulk_fetch/?user_ids='
                                          f'{",".join([x["user_id"] for x in conversation_data["chat_flow"]])}',
                                          cookies=request.cookies)
        if users_data_request.status_code == 200:
            users_data = users_data_request.json()
            for idx in range(len(users_data)):
                if len(list(users_data[idx])) > 0:
                    conversation_data['chat_flow'][idx]['user_first_name'] = users_data[idx]['first_name']
                    conversation_data['chat_flow'][idx]['user_last_name'] = users_data[idx]['last_name']
                    conversation_data['chat_flow'][idx]['user_nickname'] = users_data[idx]['nickname']
                    conversation_data['chat_flow'][idx]['user_avatar'] = users_data[idx]['avatar'] or \
                                                                         'default_avatar.png'
                else:
                    conversation_data['chat_flow'][idx]['user_first_name'] = 'Deleted'
                    conversation_data['chat_flow'][idx]['user_last_name'] = 'User'
                    conversation_data['chat_flow'][idx]['user_nickname'] = 'deleted_user'
                    conversation_data['chat_flow'][idx]['user_avatar'] = 'default_avatar.png'

    return {"conversation_data": conversation_data, "current_user": username}


@router.get("/search/{search_str}")
def get_conversation(request: Request, search_str: str, username: str = Depends(get_current_user),
                     chat_history_from: int = 0,
                     limit_chat_history: int = 100):
    """
        Gets conversation data matching search string

        :param request: client request
        :param search_str: provided search string
        :param username: current user data
        :param chat_history_from: upper time bound for messages
        :param limit_chat_history: lower time bound for messages

        :returns conversation data if found, 401 error code otherwise
    """
    or_expression = [{'conversation_name': search_str}]

    if ObjectId.is_valid(search_str):
        cid_search = ObjectId(search_str)
        or_expression.append({'_id': cid_search})

    conversation_data = db_controller.exec_query(query={'command': 'find_one',
                                                       'document': 'chats',
                                                       'data': {"$or": or_expression}})
    if not conversation_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unable to get a chat by string: {search_str}"
        )
    conversation_data['_id'] = str(conversation_data['_id'])

    if conversation_data.get('chat_flow', None):
        conversation_data['chat_flow'] = conversation_data['chat_flow'][chat_history_from:
                                                                        chat_history_from + limit_chat_history]

        request_url = f'http://' + request.client.host + ':' + str(8000) + \
                      f'/users_api/bulk_fetch/?user_ids=' + \
                      f'{",".join([x["user_id"] for x in conversation_data["chat_flow"]])}'
        users_data_request = requests.get(request_url,
                                          cookies=request.cookies)
        if users_data_request.status_code == 200:
            users_data = users_data_request.json()
            for idx in range(len(users_data)):
                if len(list(users_data[idx])) > 0:
                    conversation_data['chat_flow'][idx]['user_first_name'] = users_data[idx]['first_name']
                    conversation_data['chat_flow'][idx]['user_last_name'] = users_data[idx]['last_name']
                    conversation_data['chat_flow'][idx]['user_nickname'] = users_data[idx]['nickname']
                    conversation_data['chat_flow'][idx]['user_avatar'] = users_data[idx].get('avatar', None) or \
                                                                         'default_avatar.png'
                else:
                    conversation_data['chat_flow'][idx]['user_first_name'] = 'Deleted'
                    conversation_data['chat_flow'][idx]['user_last_name'] = 'User'
                    conversation_data['chat_flow'][idx]['user_nickname'] = 'deleted_user'
                    conversation_data['chat_flow'][idx]['user_avatar'] = 'default_avatar.png'

    return conversation_data
