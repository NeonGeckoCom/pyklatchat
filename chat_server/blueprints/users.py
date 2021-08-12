import jwt

from uuid import uuid4
from time import time
from typing import Optional
from fastapi import APIRouter, Depends, Form, Response, status, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from bson.objectid import ObjectId

from chat_server.config import db_connector
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, get_hash, \
    check_password_strength, generate_uuid

router = APIRouter(
    prefix="/users_api",
    responses={'404': {"description": "Unknown user"}},
)


@router.get("/")
def get_user(response: Response, request: Request):
    return dict(data=get_current_user(request=request, response=response))


@router.get("/{user_id}")
def get_user(user_id: str):
    user = db_connector.exec_query(query={'document': 'users',
                                          'command': 'find_one',
                                          'data': {'_id': user_id}})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
        )
    user.pop('password')
    user.pop('is_tmp')
    return {"data": user}
