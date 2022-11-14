# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import requests

from time import time
from uuid import uuid4
from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from neon_utils import LOG

from chat_client.client_config import app_config

router = APIRouter(
    prefix="/chats",
    responses={'404': {"description": "Unknown endpoint"}},
)

conversation_templates = Jinja2Templates(directory="chat_client/templates")


@router.get('/')
async def chats(request: Request):
    """
        Renders chats page HTML as a response related to the input request

        :param request: input Request object

        :returns chats template response
    """
    return conversation_templates.TemplateResponse("conversation/base.html",
                                                   {"request": request,
                                                    'section': 'Followed Conversations',
                                                    'add_sio': True,
                                                    'redirect_to_https':
                                                        app_config.get('FORCE_HTTPS', False)})


@router.post("/new", response_class=JSONResponse)
async def create_chat(conversation_name: str = Form(...),
                      conversation_id: str = Form(None),
                      is_private: bool = Form(False)):
    """
        Forwards new chat creation data to the server API and handles the returned response

        :param conversation_name: posted Form Data conversation name
        :param conversation_id: posted Form Data conversation id
        :param is_private: posted Form Data is_private checkbox state

        :returns JSON-formatted response from server
    """

    new_conversation = dict(_id=conversation_id or uuid4().hex,
                            conversation_name=conversation_name,
                            is_private=is_private,
                            created_on=int(time()))

    post_response = requests.post(f'{app_config["SERVER_URL"]}/chat_api/new', json=new_conversation)

    json_data = post_response.json()
    LOG.debug(f'Chat data {new_conversation} creation response: {json_data}')

    return JSONResponse(content=json_data, status_code=post_response.status_code)


@router.get("/nano_demo")
async def nano_demo(request: Request):
    """
        Minimal working Example of Nano
    """
    return conversation_templates.TemplateResponse("sample_nano.html",
                                                   {"request": request,
                                                    'title': 'Nano Demonstration',
                                                    'description': 'Klatchat Nano is injectable JS module, '
                                                                   'allowing to render Klat conversations on any third-party pages, '
                                                                   'supporting essential features.'})
