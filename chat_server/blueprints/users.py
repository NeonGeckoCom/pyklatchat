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

from uuid import uuid4
from time import time
from typing import Optional, List
from fastapi import APIRouter, Depends, Form, Response, status, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from bson.objectid import ObjectId

from chat_server.server_config import db_controller
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, get_hash, \
    check_password_strength, generate_uuid

router = APIRouter(
    prefix="/users_api",
    responses={'404': {"description": "Unknown user"}},
)


@router.get("/", response_class=JSONResponse)
def current_user_data(response: Response, request: Request):
    """
        Gets current user data from session cookies

        :param request: active client session request
        :param response: response object to be returned to user

        :returns JSON response containing data of current user
    """
    return dict(data=get_current_user(request=request, response=response))


@router.get("/{user_id}", response_class=JSONResponse)
def get_user(user_id: str):
    """
        Gets user by provided id

        :param user_id: provided user id

        :returns JSON response with fetched user data, 404 code otherwise
    """
    user = db_controller.exec_query(query={'document': 'users',
                                          'command': 'find_one',
                                          'data': {'_id': user_id}})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='User not found'
        )
    user.pop('password')
    return {"data": user}


@router.get('/bulk_fetch/', response_class=JSONResponse)
def fetch_received_user_ids(user_ids: List[str] = Query(None)):
    """
        Gets users data based on provided user ids

        :param user_ids: list of provided user ids

        :returns JSON response containing array of fetched user data
    """
    user_ids = user_ids[0].split(',')
    users = db_controller.exec_query(query={'document': 'users',
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
