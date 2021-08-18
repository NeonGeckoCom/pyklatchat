import jwt

from uuid import uuid4
from time import time
from typing import Optional, List
from fastapi import APIRouter, Depends, Form, Response, status, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
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
    return {"data": user}


@router.get('/bulk_fetch/')
def fetch_received_user_ids(user_ids: List[str] = Query(None)):
    user_ids = user_ids[0].split(',')
    users = db_connector.exec_query(query={'document': 'users',
                                           'command': 'find',
                                           'data': {'_id': {'$in': list(set(user_ids))}}})
    users = list(users)

    formatted_users = dict()

    for user in users:
        formatted_users[user['_id']] = user

    result = list()

    for user_id in user_ids:
        desired_record = formatted_users.get(user_id, {})
        if len(list(desired_record)) > 0:
            desired_record.pop('password', None)
            desired_record.pop('is_tmp', None)
        result.append(desired_record)
    json_compatible_item_data = jsonable_encoder(result)
    return JSONResponse(content=json_compatible_item_data, status_code=200)
