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

from fastapi import APIRouter, Depends, Form, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

from chat_server.config import db_connector
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, hash_password, \
    check_password_strength, generate_uuid

router = APIRouter(
    prefix="/auth",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.post("/signup")
def signup(response: Response,
           first_name: str = Form(...),
           last_name: str = Form(...),
           nickname: str = Form(...),
           password: str = Form(...)):
    existing_user = db_connector.exec_query(query={'command': 'find_one',
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
                           password=hash_password(password),
                           nickname=nickname,
                           creation_time=time(),
                           is_tmp=False)
    db_connector.exec_query(query=dict(document='users', command='insert_one', data=new_user_record))

    token = jwt.encode(payload={"sub": new_user_record['_id']}, key=secret_key, algorithm=jwt_encryption_algo)
    response.set_cookie("session", token, httponly=True)

    return {'signup': True}


@router.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    matching_user = db_connector.exec_query(query={'command': 'find_one',
                                                   'document': 'users',
                                                   'data': {'nickname': username}})
    if not matching_user or matching_user['is_tmp']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    db_password = matching_user["password"]
    if hash_password(password) != db_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    token = jwt.encode(payload={"sub": matching_user['_id']}, key=secret_key, algorithm=jwt_encryption_algo)
    response.set_cookie("session", token, httponly=True)
    return {"login": True}


@router.get("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"logout": True}

