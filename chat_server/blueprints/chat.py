import jwt
import requests

from uuid import uuid4
from time import time
from typing import Optional
from fastapi import APIRouter, Depends, Form, Response, status, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from bson.objectid import ObjectId

from chat_server.config import db_connector
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, hash_password, \
    check_password_strength, generate_uuid

router = APIRouter(
    prefix="/chat_api",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


class NewConversationData(BaseModel):
    _id: str = uuid4().hex
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
    db_connector.exec_query(query=dict(document='chats', command='insert_one', data=(request_data.__dict__,)))
    return {"success": True}


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
                                                                        chat_history_from+limit_chat_history]
        for message in conversation_data['chat_flow']:
            user_data = requests.get('http://'+request.client.host+':'+str(8000)+f'/users_api/{message["user_id"]}',
                                     cookies=request.cookies)
            if user_data.status_code != 200:
                message['user_first_name'] = 'Deleted'
                message['user_last_name'] = 'User'
                message['user_nickname'] = 'deleted_user'
                message['user_avatar'] = 'default_avatar.png'
            else:
                response_data = user_data.json()['data']
                if response_data and len(list(response_data)) > 0:
                    message['user_first_name'] = response_data['first_name']
                    message['user_last_name'] = response_data['last_name']
                    message['user_nickname'] = response_data['nickname']
                    message['user_avatar'] = response_data['avatar']
    return {"conversation_data": conversation_data, "current_user": username}
