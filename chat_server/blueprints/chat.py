import jwt

from uuid import uuid4
from time import time
from typing import Optional
from fastapi import APIRouter, Depends, Form, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from pydantic import BaseModel

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
                                                                  'data': {'_id': getattr(request_data, '_id')}})
        if matching_conversation_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Provided conversation id already exists'
            )
    db_connector.exec_query(query=dict(document='chats', command='insert_one', data=request_data.__dict__))
    return {"success": True}
