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

from time import time
from uuid import uuid4
from fastapi import APIRouter, Request, status, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from neon_utils import LOG

from chat_client.client_config import app_config

router = APIRouter(
    prefix="/auth",
    responses={'404': {"description": "Unknown endpoint"}},
)


@router.post("/login", response_class=JSONResponse)
async def login(username: str = Form(...),
                password: str = Form(...)):

    data = dict(username=username,
                password=password)

    post_response = requests.post(f'{app_config["SERVER_URL"]}/auth/login', data=data)

    json_data = post_response.json()

    response = JSONResponse(content=json_data, status_code=post_response.status_code)

    if post_response.status_code == 200:

        for cookie in post_response.cookies:

            response.delete_cookie('session')

            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

        LOG.info(f'{username}: {json_data}')

    return response


@router.post("/signup", response_class=JSONResponse)
async def signup(nickname: str = Form(...),
                 first_name: str = Form(...),
                 last_name: str = Form(...),
                 password: str = Form(...)):

    data = dict(nickname=nickname,
                first_name=first_name,
                last_name=last_name,
                password=password)

    post_response = requests.post(f'{app_config["SERVER_URL"]}/auth/signup', data=data)

    json_data = post_response.json()

    response = JSONResponse(content=json_data, status_code=post_response.status_code)

    if post_response.status_code == 200:

        response.delete_cookie('session')

        for cookie in post_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

    LOG.info(f'{nickname}: {json_data}')

    return response


@router.get("/logout", response_class=JSONResponse)
async def logout():

    logout_response = requests.get(f'{app_config["SERVER_URL"]}/auth/logout')

    json_data = logout_response.json()

    response = JSONResponse(content=json_data, status_code=logout_response.status_code)

    if logout_response.status_code == 200:

        response.delete_cookie('session')

        for cookie in logout_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)

    LOG.info(f'{json_data}')

    return response
