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
from utils.logging_utils import LOG

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


@router.get("/nano_demo")
async def nano_demo(request: Request):
    """
        Minimal working Example of Nano
    """
    client_url = f'"{request.url.scheme}://{request.url.netloc}"'
    server_url = f'"{app_config["SERVER_URL"]}"'
    if app_config.get('FORCE_HTTPS', False):
        client_url = client_url.replace('http://', 'https://')
        server_url = server_url.replace('http://', 'https://')
    client_url_unquoted = client_url.replace('"', '')
    return conversation_templates.TemplateResponse("sample_nano.html",
                                                   {"request": request,
                                                    'title': 'Nano Demonstration',
                                                    'description': 'Klatchat Nano is injectable JS module, '
                                                                   'allowing to render Klat conversations on any third-party pages, '
                                                                   'supporting essential features.',
                                                    'server_url': server_url,
                                                    'client_url': client_url,
                                                    'client_url_unquoted': client_url_unquoted})
