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

from time import time

from fastapi import APIRouter, Form, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from chat_server.server_config import db_controller
from utils.common import get_hash, generate_uuid
from chat_server.server_utils.auth import get_current_user, secret_key, jwt_encryption_algo, \
    check_password_strength

router = APIRouter(
    prefix="/auth",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.post("/signup")
def signup(first_name: str = Form(...),
           last_name: str = Form(...),
           nickname: str = Form(...),
           password: str = Form(...)):
    """
        Creates new user based on received form data

        :param first_name: new user first name
        :param last_name: new user last name
        :param nickname: new user nickname (unique)
        :param password: new user password

        :returns JSON response with status corresponding to the new user creation status,
                 sets session cookies if creation is successful
    """
    existing_user = db_controller.exec_query(query={'command': 'find_one',
                                                    'document': 'users',
                                                    'data': {'nickname': nickname}})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nickname is already in use"
        )
    password_check = check_password_strength(password)
    if password_check != 'OK':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=password_check
        )
    new_user_record = dict(_id=generate_uuid(length=20),
                           first_name=first_name,
                           last_name=last_name,
                           password=get_hash(password),
                           nickname=nickname,
                           date_created=int(time()),
                           is_tmp=False)
    db_controller.exec_query(query=dict(document='users', command='insert_one', data=new_user_record))

    token = jwt.encode(payload={"sub": new_user_record['_id'],
                                'creation_time': new_user_record['date_created'],
                                'last_refresh_time': new_user_record['date_created']},
                       key=secret_key, algorithm=jwt_encryption_algo)

    response = JSONResponse(content=dict(signup=True))

    response.set_cookie("session", token, httponly=True)

    return response


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    """
        Logs In user based on provided credentials

        :param username: provided username (nickname)
        :param password: provided password matching username

        :returns JSON response with status corresponding to authorization status, sets session cookie with response
    """
    matching_user = db_controller.exec_query(query={'command': 'find_one',
                                                    'document': 'users',
                                                    'data': {'nickname': username}})
    if not matching_user or matching_user['is_tmp']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    db_password = matching_user["password"]
    if get_hash(password) != db_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    token = jwt.encode(payload={"sub": matching_user['_id'],
                                'creation_time': int(time()),
                                'last_refresh_time': int(time())
                                }, key=secret_key, algorithm=jwt_encryption_algo)
    response = JSONResponse(content=dict(login=True))

    response.set_cookie("session", token, httponly=True)

    return response


@router.get("/logout")
def logout(request: Request):
    """
        Erases current user session cookies and returns temporal credentials

        :param request: logout intended request

        :returns response with temporal cookie
    """
    response = JSONResponse(content=dict(logout=True))
    get_current_user(request=request, response=response, force_tmp=True)
    return response

