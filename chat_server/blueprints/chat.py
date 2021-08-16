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

from chat_server.config import db_connector
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
def new_conversation(response: Response, request_data: NewConversationData):
    if request_data.__dict__.get('_id', None):
        matching_conversation_id = db_connector.exec_query(query={'command': 'find_one',
                                                                  'document': 'chats',
                                                                  'data': ({'_id': getattr(request_data, '_id')})})
        if matching_conversation_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Provided conversation id already exists'
            )
    _id = db_connector.exec_query(query=dict(document='chats', command='insert_one', data=(request_data.__dict__,)))
    request_data.__dict__['_id'] = str(request_data.__dict__['_id'])
    json_compatible_item_data = jsonable_encoder(request_data.__dict__)
    json_compatible_item_data['_id'] = str(_id.inserted_id)
    return JSONResponse(content=json_compatible_item_data)


@router.get("/get/{cid}")
def get_conversation(response: Response, request: Request, cid: str, username: str = Depends(get_current_user),
                     chat_history_from: int = 0,
                     limit_chat_history: int = 100):
    if ObjectId.is_valid(cid):
        cid = ObjectId(cid)
    conversation_data = db_connector.exec_query(query={'command': 'find_one',
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
            print(users_data)
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
def get_conversation(response: Response, request: Request, search_str: str, username: str = Depends(get_current_user),
                     chat_history_from: int = 0,
                     limit_chat_history: int = 100):
    or_expression = [{'conversation_name': search_str}]

    if ObjectId.is_valid(search_str):
        cid_search = ObjectId(search_str)
        or_expression.append({'_id': cid_search})

    conversation_data = db_connector.exec_query(query={'command': 'find_one',
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
            print('Users data', users_data)
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

    return conversation_data
