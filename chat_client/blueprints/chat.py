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
from fastapi import APIRouter, Request, status, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder

from chat_client.client_config import app_config

router = APIRouter(
    prefix="/chats",
    responses={'404': {"description": "Unknown endpoint"}},
)

conversation_templates = Jinja2Templates(directory="chat_client/templates")


@router.get('/')
async def chats(request: Request):
    return conversation_templates.TemplateResponse("conversation/base.html",
                                                   {"request": request,
                                                    'section': 'Followed Conversations',
                                                    'add_sio': True})


@router.post("/new", response_class=JSONResponse)
async def create_chat(conversation_name: str = Form(...),
                      conversation_id: str = Form(None),
                      is_private: bool = Form(False)):

    new_conversation = dict(_id=conversation_id or uuid4().hex,
                            conversation_name=conversation_name,
                            is_private=is_private,
                            created_on=int(time()))

    post_response = requests.post(f'{app_config["SERVER_URL"]}/chat_api/new', json=new_conversation)

    json_data = {}

    if post_response.status_code == 200:

        json_data = post_response.json()

        print(json_data)

    return JSONResponse(content=json_data, status_code=post_response.status_code)


@router.get('/search/{search_str}')
async def chats(search_str: str):
    post_response = requests.get(f'{app_config["SERVER_URL"]}/chat_api/search/{search_str}')

    json_data = {}

    if post_response.status_code == 200:

        json_data = jsonable_encoder(post_response.json())

    return JSONResponse(content=json_data, status_code=post_response.status_code)

